"""ReAct agent running against a self-hosted SGLang server (OpenAI-compatible API).

Run:
    cd demo/sglang && make up          # start the SGLang server (see demo/sglang)
    cp .env.example .env
    python agent.py "What's 47 * 89, and what's the weather in Tokyo?"
"""

import os
import sys
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from tools import tools

load_dotenv()

SGLANG_BASE_URL = os.getenv("SGLANG_BASE_URL", "http://localhost:30000/v1")
SGLANG_API_KEY = os.getenv("SGLANG_API_KEY", "EMPTY")
MODEL_REPO = os.getenv("MODEL_REPO", "meta-llama/Llama-3.1-8B-Instruct")

SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools: calculator, "
    "get_weather, search_knowledge_base. Call a tool when it would give a more "
    "accurate answer than reasoning alone. Once you have what you need, give a "
    "direct final answer without calling more tools."
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def get_llm() -> ChatOpenAI:
    """SGLang exposes an OpenAI-compatible /v1 endpoint — ChatOpenAI just needs
    base_url pointed at it. Requires the server launched with a matching
    --tool-call-parser (see demo/sglang) for bind_tools() to work."""
    return ChatOpenAI(
        model=MODEL_REPO,
        base_url=SGLANG_BASE_URL,
        api_key=SGLANG_API_KEY,
        temperature=0,
    )


def call_model(state: AgentState) -> dict:
    """Node that calls the self-hosted model to decide the next action."""
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    llm_with_tools = get_llm().bind_tools(tools)
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


def build_graph() -> StateGraph:
    """START -> agent -> [tools -> agent]* -> END"""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "agent")

    return workflow


def run_agent(query: str, verbose: bool = True) -> str:
    app = build_graph().compile()
    initial_state = {"messages": [HumanMessage(content=query)]}

    print(f"\n{'=' * 80}\nQuery: {query}\n{'=' * 80}\n")

    final_state = initial_state
    for step in app.stream(initial_state):
        for node_name, node_state in step.items():
            if verbose:
                last_message = node_state["messages"][-1]
                print(f"--- {node_name} ---")
                if isinstance(last_message, AIMessage) and last_message.tool_calls:
                    print(f"Tool calls: {last_message.tool_calls}")
                elif isinstance(last_message, ToolMessage):
                    print(f"Tool result: {last_message.content}")
                else:
                    print(f"Response: {last_message.content}")
                print()
            final_state = node_state

    answer = final_state["messages"][-1].content
    print(f"{'=' * 80}\nFinal answer:\n{answer}\n{'=' * 80}\n")
    return answer


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What's 47 * 89, and what's the weather in Tokyo?"
    run_agent(query)
