"""
Researcher agent – searches the web / knowledge base and returns factual summaries.
"""

import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from state import AgentState
from tools import researcher_tools


SYSTEM_PROMPT = (
    "You are the **Researcher** agent. Your job is to find accurate, relevant "
    "information using the search and knowledge-base tools available to you.\n\n"
    "Guidelines:\n"
    "- Search for facts, not opinions.\n"
    "- Cite the source tool you used.\n"
    "- Be concise but thorough.\n"
    "- If no tool returns useful data, state that clearly."
)


def researcher_node(state: AgentState) -> dict:
    """LangGraph node that runs the Researcher agent."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(researcher_tools)

    # Build messages for this worker
    user_query = state["messages"][-1].content if state["messages"] else ""
    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Research the following request:\n\n{user_query}"),
    ]

    # Agentic loop: let the LLM call tools until it produces a final answer
    max_steps = 5
    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        # Execute tool calls
        from langgraph.prebuilt import ToolNode

        tool_node = ToolNode(researcher_tools)
        tool_results = tool_node.invoke({"messages": messages})
        messages.extend(tool_results["messages"])

    # Extract the final text answer
    output_text = response.content if isinstance(response, AIMessage) else str(response)

    # Merge into worker_outputs
    worker_outputs = dict(state.get("worker_outputs", {}))
    worker_outputs["researcher"] = output_text

    return {
        "messages": [AIMessage(content=f"[Researcher] {output_text}")],
        "worker_outputs": worker_outputs,
    }
