"""
LangGraph StateGraph wiring for the insurance intake supervisor system.

Graph topology:

    START ──► supervisor ──► extractor ─────► supervisor
                         ├──► validator ─────► supervisor
                         ├──► ask_user ───────► END (pause for reply)
                         ├──► risk_screener ──► supervisor
                         └──► finalize ───────► END
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from agents.ask_user import ask_user_node
from agents.extractor import extractor_node
from agents.risk_screener import risk_screener_node
from agents.validator import validator_node
from state import IntakeState
from supervisor import finalize_node, supervisor_node


# ---------------------------------------------------------------------------
# Routing function (conditional edge from supervisor)
# ---------------------------------------------------------------------------
def route_supervisor(state: IntakeState) -> Literal[
    "extractor", "validator", "ask_user", "risk_screener", "finalize"
]:
    """Read next_agent from state and route accordingly."""
    next_agent = state.get("next_agent", "finalize")
    if next_agent in ("extractor", "validator", "ask_user", "risk_screener", "finalize"):
        return next_agent
    return "finalize"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_graph() -> StateGraph:
    """Construct and return the uncompiled intake StateGraph."""

    workflow = StateGraph(IntakeState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("ask_user", ask_user_node)
    workflow.add_node("risk_screener", risk_screener_node)
    workflow.add_node("finalize", finalize_node)

    # ── Entry point ────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Edges: connect nodes ───────────────────────────────────────────────
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "extractor": "extractor",
            "validator": "validator",
            "ask_user": "ask_user",
            "risk_screener": "risk_screener",
            "finalize": "finalize",
        },
    )

    # Extractor, validator, risk_screener loop back to the supervisor
    workflow.add_edge("extractor", "supervisor")
    workflow.add_edge("validator", "supervisor")
    workflow.add_edge("risk_screener", "supervisor")

    # ask_user pauses the turn (caller supplies the reply and re-invokes);
    # finalize terminates the graph with the completed application.
    workflow.add_edge("ask_user", END)
    workflow.add_edge("finalize", END)

    return workflow


def compile_graph():
    """Build and compile the graph, ready to invoke."""
    return build_graph().compile()
