"""
Await-human-review agent – marks the claim as ready for human review and
prints a summary for the reviewer. The actual pause happens one node later:
the graph is compiled with interrupt_before=["assign_or_deny"], so execution
halts right after this node runs and before adjuster assignment/denial.

Handles both HITL variants from the risk-based conditional routing:
  - hitl_ambiguous: a quick sign-off (risk score in the ambiguous band)
  - adjuster_review: a full manual review (high risk / high value / coverage
    issue), flagged for SIU if the risk score itself is what triggered it.
"""

from fnol_state import FNOLState


def await_human_review_node(state: FNOLState) -> dict:
    """LangGraph node: flag the claim for mandatory human review."""

    claim_data = state.get("claim_data", {})
    route = state.get("route_decision", "hitl_ambiguous")
    gate_label = "SIU ESCALATION — ADJUSTER REVIEW" if state.get("siu_escalated") else (
        "ADJUSTER REVIEW GATE" if route == "adjuster_review" else "QUICK HUMAN SIGN-OFF"
    )

    summary = (
        f"\n🧑‍⚖️  {gate_label}\n"
        f"  Claimant: {claim_data.get('claimant_name')}\n"
        f"  Policy: {claim_data.get('policy_number')}  |  Coverage: {state.get('coverage_status')}\n"
        f"  Loss: {claim_data.get('loss_type')} on {claim_data.get('date_of_loss')}, "
        f"est. ${claim_data.get('estimated_damage_amount')}\n"
        f"  Risk flags: {state.get('risk_flags') or 'none'}  |  Risk score: {state.get('risk_score')}\n"
        f"  Damage photo: {state.get('damage_analysis', {}).get('severity_estimate', 'n/a')}\n"
    )
    print(summary)

    return {
        "human_review_requested": True,
        "status": "awaiting_human_review",
    }
