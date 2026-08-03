"""
LangGraph StateGraph wiring for the FNOL claims intake pipeline.

Graph topology:

    START ──► supervisor ──► extractor ─────────► supervisor
                         ├──► validator ─────────► supervisor
                         ├──► ask_user ───────────► END (pause for reply)
                         ├──► coverage_checker ───► supervisor
                         ├──► risk_screener ──────► supervisor
                         ├──► await_human_review ─► supervisor
                         └──► assign_or_deny ──┬──► supervisor (needs_more_info)
                                                └──► END (approved / rejected)

The graph is compiled with `interrupt_before=["assign_or_deny"]` — execution
halts right after await_human_review runs and before assign_or_deny ever
executes, so a claim can only be assigned to an adjuster or denied once a
human reviewer has written a decision into state via `graph.update_state()`.
There is no auto-approval path.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from fnol_agents.assign_or_deny import assign_or_deny_node
from fnol_agents.ask_user import ask_user_node
from fnol_agents.await_human_review import await_human_review_node
from fnol_agents.coverage_checker import coverage_checker_node
from fnol_agents.extractor import extractor_node
from fnol_agents.risk_screener import risk_screener_node
from fnol_agents.validator import validator_node
from fnol_state import FNOLState
from fnol_supervisor import supervisor_node


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------
def route_supervisor(state: FNOLState) -> Literal[
    "extractor", "validator", "ask_user", "coverage_checker",
    "risk_screener", "await_human_review", "assign_or_deny",
]:
    """Read next_agent from state and route accordingly."""
    next_agent = state.get("next_agent", "assign_or_deny")
    valid = (
        "extractor", "validator", "ask_user", "coverage_checker",
        "risk_screener", "await_human_review", "assign_or_deny",
    )
    return next_agent if next_agent in valid else "assign_or_deny"


def route_after_decision(state: FNOLState) -> Literal["supervisor", "end"]:
    """needs_more_info loops back into the pipeline; approved/rejected end the run."""
    return "supervisor" if state.get("status") == "awaiting_info" else "end"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_graph() -> StateGraph:
    """Construct and return the uncompiled FNOL intake StateGraph."""

    workflow = StateGraph(FNOLState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("ask_user", ask_user_node)
    workflow.add_node("coverage_checker", coverage_checker_node)
    workflow.add_node("risk_screener", risk_screener_node)
    workflow.add_node("await_human_review", await_human_review_node)
    workflow.add_node("assign_or_deny", assign_or_deny_node)

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
            "coverage_checker": "coverage_checker",
            "risk_screener": "risk_screener",
            "await_human_review": "await_human_review",
            "assign_or_deny": "assign_or_deny",
        },
    )

    # Extractor, validator, coverage_checker, risk_screener, await_human_review
    # all loop back to the supervisor.
    workflow.add_edge("extractor", "supervisor")
    workflow.add_edge("validator", "supervisor")
    workflow.add_edge("coverage_checker", "supervisor")
    workflow.add_edge("risk_screener", "supervisor")
    workflow.add_edge("await_human_review", "supervisor")

    # ask_user pauses the turn (caller supplies the reply and re-invokes).
    workflow.add_edge("ask_user", END)

    # assign_or_deny either reopens the loop (needs_more_info) or ends the run.
    workflow.add_conditional_edges(
        "assign_or_deny",
        route_after_decision,
        {"supervisor": "supervisor", "end": END},
    )

    return workflow


def compile_graph(checkpointer=None):
    """Build and compile the graph. A checkpointer is required for the
    interrupt_before HITL gate to survive across separate invoke() calls
    (and, with a persistent backend like SqliteSaver, across restarts)."""
    return build_graph().compile(
        checkpointer=checkpointer,
        interrupt_before=["assign_or_deny"],
    )
