"""
LangGraph StateGraph wiring for the FNOL claims intake pipeline.

Graph topology:

    START ──► supervisor ◄────────────────────────────────────────────┐
                  │ routes to                                        │
     ┌────────────┼────────────┬──────────────┬─────────────┬────────┘
     ▼            ▼            ▼              ▼             ▼
  ingest ──► extractor    validate_stage_a  verify_policy  validate_stage_b
     │            │              │              │               │
     └────────────┴──────────────┴──────────────┴───────────────┘
                                  │ (all loop back to supervisor except
                                  │  the two branches below)
                                  ▼
                validate_stage_a / validate_stage_b ──► disambiguate ──► END (pause)
                                  │ (fields complete)
                                  ▼
                          damage_analysis ──► fraud_risk
                                                  │
                                     ┌────────────┴────────────┐
                                (fast_track)              (hitl_ambiguous /
                                     │                     adjuster_review)
                                     ▼                          ▼
                          fast_track_approve          await_human_review
                                     │                          │
                                    END                    supervisor
                                                                 │
                                                        ── interrupt_before ──
                                                                 │
                                                          assign_or_deny
                                                        ┌────────┴────────┐
                                              (needs_more_info)      (approved/
                                                     │                rejected)
                                                     ▼                   ▼
                                                supervisor               END

`interrupt_before=["assign_or_deny"]` means that node can only run once a
human reviewer has written a decision into state via `graph.update_state()`
— fast_track_approve is the only auto-approval path, and it's only reachable
when fraud_risk_node's own routing decision sends a claim there directly.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from fnol_agents.assign_or_deny import assign_or_deny_node
from fnol_agents.await_human_review import await_human_review_node
from fnol_agents.damage_analysis import damage_analysis_node
from fnol_agents.disambiguate import disambiguate_node
from fnol_agents.extractor import extractor_node
from fnol_agents.fast_track_approve import fast_track_approve_node
from fnol_agents.fraud_risk import fraud_risk_node
from fnol_agents.ingest import ingest_node
from fnol_agents.validate_stage_a import validate_stage_a_node
from fnol_agents.validate_stage_b import validate_stage_b_node
from fnol_agents.verify_policy import verify_policy_node
from fnol_state import FNOLState
from fnol_supervisor import supervisor_node


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------
def route_supervisor(state: FNOLState) -> Literal[
    "ingest", "extractor", "validate_stage_a", "disambiguate",
    "verify_policy", "validate_stage_b", "damage_analysis",
    "fraud_risk", "assign_or_deny",
]:
    """Read next_agent from state and route accordingly."""
    next_agent = state.get("next_agent", "assign_or_deny")
    valid = (
        "ingest", "extractor", "validate_stage_a", "disambiguate",
        "verify_policy", "validate_stage_b", "damage_analysis",
        "fraud_risk", "assign_or_deny",
    )
    return next_agent if next_agent in valid else "assign_or_deny"


def route_after_risk(state: FNOLState) -> Literal["fast_track_approve", "await_human_review"]:
    """fraud_risk_node's own routing decision — the risk-based conditional
    branch from the target architecture (risk < 0.3 / ambiguous / high-risk)."""
    return "fast_track_approve" if state.get("route_decision") == "fast_track" else "await_human_review"


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
    workflow.add_node("ingest", ingest_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("validate_stage_a", validate_stage_a_node)
    workflow.add_node("verify_policy", verify_policy_node)
    workflow.add_node("validate_stage_b", validate_stage_b_node)
    workflow.add_node("disambiguate", disambiguate_node)
    workflow.add_node("damage_analysis", damage_analysis_node)
    workflow.add_node("fraud_risk", fraud_risk_node)
    workflow.add_node("fast_track_approve", fast_track_approve_node)
    workflow.add_node("await_human_review", await_human_review_node)
    workflow.add_node("assign_or_deny", assign_or_deny_node)

    # ── Entry point ────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Edges: connect nodes ───────────────────────────────────────────────
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "ingest": "ingest",
            "extractor": "extractor",
            "validate_stage_a": "validate_stage_a",
            "disambiguate": "disambiguate",
            "verify_policy": "verify_policy",
            "validate_stage_b": "validate_stage_b",
            "damage_analysis": "damage_analysis",
            "fraud_risk": "fraud_risk",
            "assign_or_deny": "assign_or_deny",
        },
    )

    # Deterministic sequential stages loop back to the supervisor, which
    # decides the next stage (or branches to disambiguate on missing fields).
    workflow.add_edge("ingest", "extractor")
    workflow.add_edge("extractor", "supervisor")
    workflow.add_edge("validate_stage_a", "supervisor")
    workflow.add_edge("verify_policy", "supervisor")
    workflow.add_edge("validate_stage_b", "supervisor")
    workflow.add_edge("damage_analysis", "supervisor")
    workflow.add_edge("await_human_review", "supervisor")

    # disambiguate pauses the turn (caller supplies the reply and re-invokes).
    workflow.add_edge("disambiguate", END)

    # fraud_risk makes the one real routing call itself (risk-based), and
    # its outgoing edge acts on that decision directly.
    workflow.add_conditional_edges(
        "fraud_risk",
        route_after_risk,
        {"fast_track_approve": "fast_track_approve", "await_human_review": "await_human_review"},
    )

    # fast_track_approve is the only auto-approval path; it ends the run.
    workflow.add_edge("fast_track_approve", END)

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
