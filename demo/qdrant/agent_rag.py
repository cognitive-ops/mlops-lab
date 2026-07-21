"""
AI Agent with RAG using Qdrant as a retrieval tool.

ReAct-style agent (LangGraph StateGraph): the LLM decides when to call the
Qdrant retriever tool, observes results, and loops until it can answer.

Run docker-compose up -d first to start a local Qdrant instance.
Requires OPENAI_API_KEY.
"""

import logging
import os
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph, add_messages
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from qdrant_demo import initialize_client
from qdrant_rag import index_documents, retrieve as qdrant_retrieve

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agent_rag")

qdrant_client = initialize_client()
embedder = SentenceTransformer("all-MiniLM-L6-v2")


class AgentStep(BaseModel):
    """One ReAct step: forces the LLM to expose its reasoning before acting."""

    thought: str = Field(description="Step-by-step reasoning about what to do next and why")
    action: Literal["retrieve_context", "final_answer"] = Field(
        description="'retrieve_context' to search the knowledge base, or 'final_answer' to respond to the user"
    )
    action_input: str = Field(
        description="Search query if action=retrieve_context, otherwise the final answer text"
    )


def retrieve_context(query: str) -> str:
    """Search the Qdrant knowledge base for context relevant to a query."""
    logger.debug("retrieve_context: query=%r", query)
    chunks = qdrant_retrieve(qdrant_client, embedder, query, top_k=3)
    logger.debug("retrieve_context: found %d chunk(s)", len(chunks))
    if not chunks:
        return "No relevant context found."
    return "\n\n".join(chunks)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    current_step: Optional[AgentStep]
    final_answer: str


SYSTEM_PROMPT = """You are a helpful assistant with access to a knowledge base via a retrieve_context action.

For every turn, you MUST respond with a structured step containing:
- thought: your reasoning about what to do next
- action: "retrieve_context" to search the knowledge base, or "final_answer" to respond
- action_input: the search query (for retrieve_context) or the final answer text (for final_answer)

Always take a retrieve_context action first to check for relevant information before answering.
If the retrieved context doesn't contain the answer, use final_answer to say you don't know.
Keep final answers to 2-3 sentences."""


def call_model(state: AgentState) -> AgentState:
    messages = state["messages"]
    iterations = state.get("iterations", 0)
    logger.debug("call_model: iteration=%d, incoming_messages=%d", iterations, len(messages))

    llm = ChatAnthropic(model="claude-sonnet-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
    structured_llm = llm.with_structured_output(AgentStep)

    if iterations == 0:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    step: AgentStep = structured_llm.invoke(messages)
    logger.debug("call_model: thought=%r action=%s action_input=%r", step.thought, step.action, step.action_input)

    step_message = AIMessage(
        content=f"Thought: {step.thought}\nAction: {step.action}\nAction Input: {step.action_input}"
    )
    return {"messages": [step_message], "iterations": iterations + 1, "current_step": step}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    decision = "tools" if state["current_step"].action == "retrieve_context" else "end"
    logger.debug("should_continue: decision=%s", decision)
    return decision


def run_tool(state: AgentState) -> AgentState:
    step = state["current_step"]
    observation = retrieve_context(step.action_input)
    logger.debug("run_tool: observation=%r", observation)
    return {"messages": [HumanMessage(content=f"Observation: {observation}")]}


def finalize_answer(state: AgentState) -> AgentState:
    final_answer = state["current_step"].action_input
    logger.debug("finalize_answer: final_answer=%r", final_answer)
    return {"final_answer": final_answer}


def create_agent_graph() -> StateGraph:
    logger.debug("create_agent_graph: building graph")
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", run_tool)
    workflow.add_node("finalize", finalize_answer)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": "finalize"})
    workflow.add_edge("tools", "agent")
    workflow.add_edge("finalize", END)

    return workflow


def run_agent(user_query: str, verbose: bool = True):
    logger.debug("run_agent: starting for query=%r", user_query)
    workflow = create_agent_graph()
    app = workflow.compile()

    initial_state = {
        "messages": [HumanMessage(content=user_query)],
        "iterations": 0,
        "current_step": None,
        "final_answer": "",
    }

    print(f"\n{'=' * 80}\nUser Query: {user_query}\n{'=' * 80}\n")

    final_state = None
    for step_output in app.stream(initial_state):
        for node_name, node_state in step_output.items():
            logger.debug("run_agent: step node=%s state=%r", node_name, node_state)
            if verbose:
                print(f"--- Node: {node_name} ---")
                if "messages" in node_state:
                    last_message = node_state["messages"][-1]
                    print(f"Content: {getattr(last_message, 'content', last_message)}")
                print()
        final_state = node_state

    if final_state and final_state.get("final_answer"):
        print(f"{'=' * 80}\nFinal Answer:\n{final_state['final_answer']}\n{'=' * 80}\n")

    logger.debug("run_agent: finished for query=%r", user_query)
    return final_state


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY in your environment or .env file")

    logger.debug("main: indexing documents into Qdrant")
    print("Indexing documents into Qdrant...")
    index_documents(qdrant_client, embedder)

    queries = [
        "What is Qdrant used for?"     
    ]

    for query in queries:
        logger.debug("main: running agent for query=%r", query)
        run_agent(query)


if __name__ == "__main__":
    main()
