"""
LangGraph StateGraph wiring for the multi-agent supervisor system.

Graph topology:

    START ──► supervisor ──► researcher ──► supervisor
                         ├──► coder ──────► supervisor
                         ├──► analyst ────► supervisor
                         └──► synthesize ──► END
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from state import AgentState
from supervisor import supervisor_node, synthesize_node
from agents.researcher import researcher_node
from agents.coder import coder_node
from agents.analyst import analyst_node


# ---------------------------------------------------------------------------
# Routing function (conditional edge from supervisor)
# ---------------------------------------------------------------------------
def route_supervisor(state: AgentState) -> Literal[
    "researcher", "coder", "analyst", "synthesize"
]:
    """Read next_agent from state and route accordingly."""
    next_agent = state.get("next_agent", "synthesize")
    if next_agent in ("researcher", "coder", "analyst", "synthesize"):
        return next_agent
    return "synthesize"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_graph() -> StateGraph:
    """Construct and return the compiled multi-agent StateGraph."""

    workflow = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("synthesize", synthesize_node)

    # ── Entry point ────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Edges: connect nodes ───────────────────────────────────────────────
    # Supervisor routes to researcher, coder, analyst, or synthesize
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "researcher": "researcher",
            "coder": "coder",
            "analyst": "analyst",
            "synthesize": "synthesize",
        },
    )

    # Each worker loops back to supervisor
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("coder", "supervisor")
    workflow.add_edge("analyst", "supervisor")

    # Synthesize node terminates the graph
    workflow.add_edge("synthesize", END)

    # (Optional) Add direct edges if needed for future expansion
    # Example: workflow.add_edge("supervisor", "END")

    return workflow


def compile_graph():
    """Build and compile the graph, ready to invoke."""
    return build_graph().compile()
