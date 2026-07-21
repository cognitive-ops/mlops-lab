"""
Agent Orchestrator – routes user requests to the best-suited
specialised agent(s), aggregates results, and returns a unified answer.

The orchestrator itself uses a Gemini model for:
1. **Task analysis** – understanding the user's intent.
2. **Agent selection** – deciding which agent(s) should handle the task.
3. **Result synthesis** – combining sub-agent outputs into one response.

Supports three routing strategies:
    - ``single``   : send the whole task to a single best agent.
    - ``parallel``  : split the task into subtasks and fan-out to agents.
    - ``sequential``: run agents one after another, passing context forward.
"""

import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from .base_agent import BaseAgent


class AgentOrchestrator:
    """
    Central controller for a fleet of specialised agents.

    Usage::

        orchestrator = AgentOrchestrator()
        orchestrator.register_agent(WeatherAgent())
        orchestrator.register_agent(MathAgent())
        result = orchestrator.run("What's the weather in Paris and convert 25°C to °F?")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/gemini-2.5-flash",
        verbose: bool = True,
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.verbose = verbose

        # Registry of available agents
        self.agents: Dict[str, BaseAgent] = {}

        # Execution trace for debugging / transparency
        self.trace: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def register_agent(self, agent: BaseAgent) -> "AgentOrchestrator":
        """Add an agent to the orchestrator. Returns self for chaining."""
        self.agents[agent.name] = agent
        if self.verbose:
            tools = ", ".join(agent.describe()["tools"]) or "none"
            print(f"  Registered [{agent.name}] – tools: {tools}")
        return self

    def list_agents(self) -> List[Dict[str, str]]:
        """Return metadata for every registered agent."""
        return [a.describe() for a in self.agents.values()]

    # ------------------------------------------------------------------
    # Planning – uses Gemini to decide which agents handle what
    # ------------------------------------------------------------------

    def _build_agent_catalog(self) -> str:
        """Build a textual catalogue of agents for the planner prompt."""
        lines = []
        for agent in self.agents.values():
            info = agent.describe()
            tools_str = ", ".join(info["tools"]) if info["tools"] else "none"
            lines.append(
                f'- name: "{info["name"]}", description: "{info["description"]}", tools: [{tools_str}]'
            )
        return "\n".join(lines)

    def _plan(self, user_prompt: str) -> Dict[str, Any]:
        """
        Ask Gemini to produce an execution plan.

        Returns a dict shaped like::

            {
                "strategy": "single" | "parallel" | "sequential",
                "steps": [
                    {"agent": "<name>", "task": "<sub-task description>"},
                    ...
                ]
            }
        """
        catalog = self._build_agent_catalog()

        planner_prompt = f"""You are a task planner for a multi-agent system.

Available agents:
{catalog}

User request:
\"\"\"{user_prompt}\"\"\"

Analyse the request and produce a JSON execution plan.

Rules:
1. Choose "strategy":
   - "single"     – the task maps to exactly one agent.
   - "parallel"   – the task has independent subtasks for different agents.
   - "sequential" – subtasks depend on each other (later steps need earlier results).
2. List the "steps" in order, each with:
   - "agent" – must be one of the registered agent *names*.
   - "task"  – a clear, self-contained description of what the agent should do. 
               For sequential steps, reference results from prior steps as {{step_N}}.

Respond with ONLY valid JSON, no markdown fences. Example:
{{"strategy": "parallel", "steps": [{{"agent": "weather_agent", "task": "Get current weather for Tokyo"}}, {{"agent": "math_agent", "task": "Calculate 2+2"}}]}}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[types.Content(
                role="user", parts=[types.Part(text=planner_prompt)])],
            config=types.GenerateContentConfig(temperature=0.1),
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
        raw = raw.strip()

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: route everything to the first agent
            first = next(iter(self.agents))
            plan = {"strategy": "single", "steps": [
                {"agent": first, "task": user_prompt}]}

        if self.verbose:
            print(f"\n{'='*60}")
            print("EXECUTION PLAN")
            print(f"{'='*60}")
            print(f"  Strategy : {plan.get('strategy', '?')}")
            for i, step in enumerate(plan.get("steps", []), 1):
                print(f"  Step {i}   : [{step['agent']}] {step['task']}")
            print(f"{'='*60}\n")

        return plan

    # ------------------------------------------------------------------
    # Execution strategies
    # ------------------------------------------------------------------

    def _run_single(self, steps: List[Dict], verbose: bool) -> str:
        step = steps[0]
        agent = self.agents[step["agent"]]
        agent.reset()
        return agent.run(step["task"], verbose=verbose)

    def _run_parallel(self, steps: List[Dict], verbose: bool) -> Dict[str, str]:
        """Run all steps independently and collect results."""
        results: Dict[str, str] = {}
        for i, step in enumerate(steps, 1):
            agent = self.agents.get(step["agent"])
            if not agent:
                results[f"step_{i}"] = f"[Error] Agent '{step['agent']}' not found."
                continue
            agent.reset()
            result = agent.run(step["task"], verbose=verbose)
            results[f"step_{i}"] = result
            self.trace.append(
                {"step": i, "agent": step["agent"],
                    "task": step["task"], "result": result}
            )
        return results

    def _run_sequential(self, steps: List[Dict], verbose: bool) -> Dict[str, str]:
        """Run steps one-by-one, substituting prior results into later prompts."""
        results: Dict[str, str] = {}
        for i, step in enumerate(steps, 1):
            task = step["task"]
            # Replace {{step_N}} placeholders with earlier results
            for j in range(1, i):
                placeholder = f"{{{{step_{j}}}}}"
                if placeholder in task:
                    task = task.replace(
                        placeholder, results.get(f"step_{j}", ""))

            agent = self.agents.get(step["agent"])
            if not agent:
                results[f"step_{i}"] = f"[Error] Agent '{step['agent']}' not found."
                continue

            agent.reset()
            result = agent.run(task, verbose=verbose)
            results[f"step_{i}"] = result
            self.trace.append(
                {"step": i, "agent": step["agent"],
                    "task": task, "result": result}
            )
        return results

    # ------------------------------------------------------------------
    # Synthesis – combine sub-results into a single answer
    # ------------------------------------------------------------------

    def _synthesise(self, user_prompt: str, results: Dict[str, str]) -> str:
        """Use Gemini to merge multiple sub-agent results into one answer."""
        parts_text = "\n\n".join(
            f"--- Result from step {k} ---\n{v}" for k, v in results.items()
        )

        synthesis_prompt = f"""You are a synthesis agent. The user asked:
\"\"\"{user_prompt}\"\"\"

Multiple specialised agents worked on parts of the task. Their results:
{parts_text}

Combine all results into a single, coherent, well-formatted answer for the user.
Do NOT include meta-commentary about the agents – just answer the user directly."""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[types.Content(
                role="user", parts=[types.Part(text=synthesis_prompt)])],
            config=types.GenerateContentConfig(temperature=0.3),
        )
        return response.text.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, prompt: str, *, verbose: Optional[bool] = None) -> str:
        """
        Execute a user request through the multi-agent pipeline.

        1. Plan  → which agents handle which parts
        2. Execute → run the agents
        3. Synthesise → merge results into one answer

        Returns the final text answer.
        """
        v = verbose if verbose is not None else self.verbose
        self.trace = []

        if not self.agents:
            return "[Error] No agents registered in the orchestrator."

        # 1) Plan
        plan = self._plan(prompt)
        strategy = plan.get("strategy", "single")
        steps = plan.get("steps", [])

        if not steps:
            return "[Error] Planner returned no steps."

        # Validate agent names
        for step in steps:
            if step["agent"] not in self.agents:
                # Try fuzzy-match on description keywords
                matched = False
                for name, ag in self.agents.items():
                    if any(kw in step["agent"] for kw in name.split("_")):
                        step["agent"] = name
                        matched = True
                        break
                if not matched:
                    step["agent"] = next(iter(self.agents))

        # 2) Execute
        if strategy == "single":
            final = self._run_single(steps, verbose=v)
            self.trace.append(
                {"step": 1, "agent": steps[0]["agent"],
                    "task": steps[0]["task"], "result": final}
            )
        elif strategy == "parallel":
            results = self._run_parallel(steps, verbose=v)
            final = self._synthesise(prompt, results)
        elif strategy == "sequential":
            results = self._run_sequential(steps, verbose=v)
            final = self._synthesise(prompt, results)
        else:
            # Unknown strategy – treat as parallel
            results = self._run_parallel(steps, verbose=v)
            final = self._synthesise(prompt, results)

        if v:
            print(f"\n{'='*60}")
            print("FINAL ANSWER")
            print(f"{'='*60}")
            print(final)
            print(f"{'='*60}\n")

        return final

    def get_trace(self) -> List[Dict[str, Any]]:
        """Return the execution trace for the last ``run()``."""
        return self.trace
