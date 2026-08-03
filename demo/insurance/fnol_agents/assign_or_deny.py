"""
Assign-or-deny agent – the node the graph pauses BEFORE (interrupt_before)
so it only ever runs once a human reviewer has written a decision into
state via graph.update_state(). No auto-approval path exists.
"""

from langchain_core.messages import AIMessage

from fnol_state import FNOLState
from fnol_tools import assign_adjuster


def assign_or_deny_node(state: FNOLState) -> dict:
    """LangGraph node: act on the human reviewer's decision."""

    decision = state.get("human_decision", "")
    claim_data = state.get("claim_data", {})

    if decision == "approved":
        claim_id = claim_data.get("policy_number", "") + claim_data.get("claimant_name", "")
        adjuster = assign_adjuster(claim_id)
        final_claim = {
            **claim_data,
            "coverage_status": state.get("coverage_status"),
            "risk_flags": state.get("risk_flags", []),
            "severity_tier": state.get("severity_tier"),
            "decision": "assigned_to_adjuster",
            "adjuster": adjuster,
        }
        summary = f"Claim approved. Assigned to adjuster {adjuster}."
        print(f"\n📋 {summary}\n")
        return {
            "final_claim": final_claim,
            "status": "complete",
            "human_decision": "",
            "human_review_requested": False,
            "messages": [AIMessage(content=summary)],
        }

    if decision == "rejected":
        final_claim = {
            **claim_data,
            "coverage_status": state.get("coverage_status"),
            "risk_flags": state.get("risk_flags", []),
            "severity_tier": state.get("severity_tier"),
            "decision": "denied",
        }
        summary = f"Claim denied by reviewer. Coverage status: {state.get('coverage_status')}."
        print(f"\n📋 {summary}\n")
        return {
            "final_claim": final_claim,
            "status": "complete",
            "human_decision": "",
            "human_review_requested": False,
            "messages": [AIMessage(content=summary)],
        }

    # needs_more_info: reopen the intake loop for one more round of detail
    summary = "Reviewer requested more information before deciding."
    print(f"\n🔁 {summary}\n")
    # Keep validated=True so the supervisor routes straight to ask_user
    # instead of back through the validator, which would recompute
    # missing_fields from REQUIRED_FIELDS and immediately erase this flag
    # (every required field is already filled by this point in the flow).
    return {
        "missing_fields": ["additional_details_requested_by_reviewer"],
        "status": "awaiting_info",
        "coverage_checked": False,
        "risk_assessed": False,
        "human_decision": "",
        "human_review_requested": False,
        "messages": [AIMessage(content=summary)],
    }
