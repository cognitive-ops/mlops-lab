"""
Analyst agent – performs calculations, data analysis, and logical reasoning.
"""

import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from state import AgentState
from tools import analyst_tools


SYSTEM_PROMPT = (
    "You are the **Analyst** agent. You excel at numerical calculations, "
    "data analysis, and structured reasoning.\n\n"
    "Guidelines:\n"
    "- Use the calculator tool for precise arithmetic.\n"
    "- Use the analyse_data tool for higher-level data interpretation.\n"
    "- Show your working / reasoning steps.\n"
    "- Be precise with numbers."
)


def analyst_node(state: AgentState) -> dict:
    """LangGraph node that runs the Analyst agent."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(analyst_tools)

    user_query = state["messages"][-1].content if state["messages"] else ""
    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Analyse the following:\n\n{user_query}"),
    ]

    max_steps = 5
    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        from langgraph.prebuilt import ToolNode

        tool_node = ToolNode(analyst_tools)
        tool_results = tool_node.invoke({"messages": messages})
        messages.extend(tool_results["messages"])

    output_text = response.content if isinstance(response, AIMessage) else str(response)

    worker_outputs = dict(state.get("worker_outputs", {}))
    worker_outputs["analyst"] = output_text

    return {
        "messages": [AIMessage(content=f"[Analyst] {output_text}")],
        "worker_outputs": worker_outputs,
    }
