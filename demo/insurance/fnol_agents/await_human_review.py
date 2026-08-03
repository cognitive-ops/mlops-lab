"""
Await-human-review agent – marks the claim as ready for human review and
prints a summary for the reviewer. The actual pause happens one node later:
the graph is compiled with interrupt_before=["assign_or_deny"], so execution
halts right after this node runs and before adjuster assignment/denial.
"""

from fnol_state import FNOLState


def await_human_review_node(state: FNOLState) -> dict:
    """LangGraph node: flag the claim for mandatory human review."""

    claim_data = state.get("claim_data", {})
    summary = (
        f"\n🧑‍⚖️  HUMAN REVIEW REQUIRED\n"
        f"  Claimant: {claim_data.get('claimant_name')}\n"
        f"  Policy: {claim_data.get('policy_number')}  |  Coverage: {state.get('coverage_status')}\n"
        f"  Loss: {claim_data.get('loss_type')} on {claim_data.get('date_of_loss')}, "
        f"est. ${claim_data.get('estimated_damage_amount')}\n"
        f"  Risk flags: {state.get('risk_flags') or 'none'}  |  Severity: {state.get('severity_tier')}\n"
    )
    print(summary)

    return {
        "human_review_requested": True,
        "status": "awaiting_human_review",
    }
