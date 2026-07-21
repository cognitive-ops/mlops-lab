"""
Supervisor agent – routes user queries to the appropriate worker agent(s).

The supervisor uses an LLM to decide which specialist should handle the task,
then loops until it decides to synthesise or finish.
"""

import json
import os
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from state import AgentState

# Available worker names (must match node names in graph.py)
WORKERS = ["researcher", "coder", "analyst"]

SYSTEM_PROMPT = f"""You are a **Supervisor** that routes tasks to specialised worker agents.

Available workers:
- **researcher** – searches the web and knowledge bases for factual information.
- **coder** – writes, runs, and reviews code.
- **analyst** – performs calculations and data analysis.

Given the user's query and any worker outputs so far, decide the NEXT action:
1. Route to a worker that has NOT yet contributed (or needs to run again).
2. Route to **synthesize** when all necessary information has been gathered.

Respond with ONLY a JSON object:
{{"next": "<worker_name | synthesize>"}}

Rules:
- Never pick the same worker twice unless the first attempt failed.
- If the query is simple and one worker can handle it, go straight to that worker then synthesize.
- If the query spans research + code + analysis, invoke each relevant worker before synthesizing.
"""


def supervisor_node(state: AgentState) -> dict:
    """LangGraph node: the supervisor decides which agent goes next."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Build context for the supervisor
    user_query = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break

    worker_outputs = state.get("worker_outputs", {})
    context_parts = [f"User query: {user_query}"]
    for name, output in worker_outputs.items():
        context_parts.append(f"\n--- {name} output ---\n{output}")

    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="\n".join(context_parts)),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # Parse the JSON decision
    try:
        decision = json.loads(content)
        next_agent = decision.get("next", "synthesize")
    except json.JSONDecodeError:
        # Fallback: try to extract from text
        content_lower = content.lower()
        next_agent = "synthesize"
        for worker in WORKERS:
            if worker in content_lower:
                next_agent = worker
                break

    # Safety: cap iterations
    iterations = state.get("iterations", 0) + 1
    if iterations > 8:
        next_agent = "synthesize"

    print(f"🎯 Supervisor → {next_agent}  (iteration {iterations})")

    return {
        "next_agent": next_agent,
        "iterations": iterations,
    }


def synthesize_node(state: AgentState) -> dict:
    """Merge all worker outputs into a single, coherent final answer."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    worker_outputs = state.get("worker_outputs", {})
    if not worker_outputs:
        return {"final_answer": "No worker produced output. Please refine your query."}

    parts = []
    for name, output in worker_outputs.items():
        parts.append(f"### {name.title()} output\n{output}")

    synthesis_prompt = (
        "You are a synthesis agent. Combine the following specialist outputs "
        "into one clear, well-structured answer for the user. Remove redundancy "
        "and resolve any contradictions.\n\n"
        + "\n\n".join(parts)
    )

    response = llm.invoke([HumanMessage(content=synthesis_prompt)])
    final = response.content

    print(f"\n✅ Synthesised final answer ({len(final)} chars)")

    return {
        "final_answer": final,
        "messages": [AIMessage(content=final)],
    }
