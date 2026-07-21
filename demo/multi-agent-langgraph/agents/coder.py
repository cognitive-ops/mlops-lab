"""
Coder agent – writes, explains, and reviews code.
"""

import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from state import AgentState
from tools import coder_tools


SYSTEM_PROMPT = (
    "You are the **Coder** agent. You write clean, well-documented code and "
    "can also review existing code for bugs and style issues.\n\n"
    "Guidelines:\n"
    "- Use the run_python_code tool to test snippets when asked.\n"
    "- Use the review_code tool to audit code for issues.\n"
    "- Provide explanations alongside code.\n"
    "- Default to Python unless another language is requested."
)


def coder_node(state: AgentState) -> dict:
    """LangGraph node that runs the Coder agent."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(coder_tools)

    user_query = state["messages"][-1].content if state["messages"] else ""
    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Handle this coding request:\n\n{user_query}"),
    ]

    max_steps = 5
    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        from langgraph.prebuilt import ToolNode

        tool_node = ToolNode(coder_tools)
        tool_results = tool_node.invoke({"messages": messages})
        messages.extend(tool_results["messages"])

    output_text = response.content if isinstance(response, AIMessage) else str(response)

    worker_outputs = dict(state.get("worker_outputs", {}))
    worker_outputs["coder"] = output_text

    return {
        "messages": [AIMessage(content=f"[Coder] {output_text}")],
        "worker_outputs": worker_outputs,
    }
