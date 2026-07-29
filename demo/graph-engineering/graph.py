"""
LangGraph StateGraph wiring for the graph-engineering multi-agent system.

Graph topology:

    START ──► supervisor ──┬──► extractor   ──► END   (mode="ingest")
                            └──► query_agent ──► END   (mode="query")
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from state import GraphState
from supervisor import supervisor_node
from agents.extractor import extractor_node
from agents.query_agent import query_node


def route_supervisor(state: GraphState) -> Literal["extractor", "query_agent"]:
    """Read mode from state and route accordingly."""
    return "extractor" if state.get("mode") == "ingest" else "query_agent"


def build_graph() -> StateGraph:
    """Construct and return the multi-agent StateGraph."""

    workflow = StateGraph(GraphState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("query_agent", query_node)

    # ── Entry point ────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Edges ──────────────────────────────────────────────────────────────
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {"extractor": "extractor", "query_agent": "query_agent"},
    )
    workflow.add_edge("extractor", END)
    workflow.add_edge("query_agent", END)

    return workflow


def compile_graph():
    """Build and compile the graph, ready to invoke."""
    return build_graph().compile()
