"""
Base agent class for the multi-agent orchestration system.

Each specialized agent extends BaseAgent to inherit common functionality
(Gemini API interaction, tool execution, agentic loop) while defining
its own tools and system instruction.
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional

from google import genai
from google.genai import types


class BaseAgent:
    """
    A reusable, self-contained agent that wraps a Gemini model,
    a set of tools, and an agentic execution loop.

    Subclasses should override:
        - ``name``          – human-readable agent name
        - ``description``   – one-line summary of what the agent does
        - ``_build_tools``  – returns (declarations, function_map)
        - ``_system_instruction`` – returns the system prompt
    """

    name: str = "base_agent"
    description: str = "A generic AI agent."

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

        # Each subclass builds its own tools
        self.tool_declarations, self.tool_functions = self._build_tools()

        # Conversation history (per-session)
        self.chat_history: List[types.Content] = []
        self.execution_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Override points
    # ------------------------------------------------------------------

    def _build_tools(self):
        """Return (list[FunctionDeclaration], dict[str, callable])."""
        return [], {}

    def _system_instruction(self) -> str:
        """Return the system instruction for this agent."""
        return (
            f"You are **{self.name}** – {self.description}.\n"
            "Use the tools at your disposal to fulfil the user's request. "
            "Think step-by-step, be concise, and return structured answers."
        )

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def reset(self):
        """Clear conversation state for a fresh session."""
        self.chat_history = []
        self.execution_log = []

    def _execute_function(self, name: str, args: Dict[str, Any]) -> Any:
        if name not in self.tool_functions:
            return {"error": f"Unknown function: {name}"}
        try:
            return self.tool_functions[name](**args)
        except Exception as exc:
            return {"error": str(exc)}

    def run(
        self,
        prompt: str,
        *,
        max_iterations: int = 10,
        verbose: bool = False,
    ) -> str:
        """
        Execute the agent loop: send *prompt* to Gemini, handle any
        tool calls iteratively, and return the final text response.
        """
        if verbose:
            print(f"\n[{self.name}] Received: {prompt}")

        # Prepare tool config
        tool_config = None
        if self.tool_declarations:
            tool_config = types.Tool(
                function_declarations=self.tool_declarations)

        self.chat_history.append(
            types.Content(role="user", parts=[types.Part(text=prompt)])
        )

        for iteration in range(1, max_iterations + 1):
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self.chat_history,
                config=types.GenerateContentConfig(
                    system_instruction=self._system_instruction(),
                    tools=[tool_config] if tool_config else None,
                    temperature=0.4,
                ),
            )

            assistant_content = response.candidates[0].content
            self.chat_history.append(assistant_content)

            # Process any function calls
            has_call = False
            for part in assistant_content.parts:
                if part.function_call:
                    has_call = True
                    fc = part.function_call
                    fn_name = fc.name
                    fn_args = dict(fc.args)

                    if verbose:
                        print(f"  [{self.name}] Calling {fn_name}({fn_args})")

                    result = self._execute_function(fn_name, fn_args)

                    if verbose:
                        print(f"  [{self.name}] Result: {result}")

                    self.execution_log.append(
                        {"function": fn_name, "args": fn_args, "result": result}
                    )

                    self.chat_history.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=fn_name,
                                        response={"result": result},
                                    )
                                )
                            ],
                        )
                    )

            if not has_call:
                break

        # Extract final text
        final_text = ""
        for part in response.candidates[0].content.parts:
            if part.text:
                final_text += part.text

        if verbose:
            print(f"  [{self.name}] Done ({iteration} iteration(s))\n")

        return final_text

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def describe(self) -> Dict[str, str]:
        """Return a serialisable description of this agent."""
        tool_names = [
            d.name for d in self.tool_declarations] if self.tool_declarations else []
        return {
            "name": self.name,
            "description": self.description,
            "tools": tool_names,
        }
