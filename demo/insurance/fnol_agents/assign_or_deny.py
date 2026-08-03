"""
Assign-or-deny agent – the node the graph pauses BEFORE (interrupt_before)
so it only ever runs once a human reviewer has written a decision into
state via graph.update_state(). No auto-approval path exists here — the
only auto-approval path in the whole pipeline is fast_track_approve, and
fraud_risk_node only sends a claim there when it never reaches this node.
"""

from langchain_core.messages import AIMessage

from fnol_state import FNOLState
from fnol_tools import assign_adjuster, assign_siu_investigator, submit_to_cms


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
            "risk_score": state.get("risk_score"),
            "decision": "assigned_to_adjuster",
            "adjuster": adjuster,
        }
        if state.get("siu_escalated"):
            final_claim["siu_investigator"] = assign_siu_investigator(claim_id)
        cms_claim_id = submit_to_cms(final_claim)
        final_claim["cms_claim_id"] = cms_claim_id

        summary = f"Claim approved. Assigned to adjuster {adjuster}. CMS claim ID: {cms_claim_id}."
        if state.get("siu_escalated"):
            summary += f" SIU investigator: {final_claim['siu_investigator']}."
        print(f"\n📋 {summary}\n")
        return {
            "final_claim": final_claim,
            "cms_claim_id": cms_claim_id,
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
            "risk_score": state.get("risk_score"),
            "decision": "denied",
        }
        cms_claim_id = submit_to_cms(final_claim)
        final_claim["cms_claim_id"] = cms_claim_id

        summary = f"Claim denied by reviewer. Coverage status: {state.get('coverage_status')}. CMS claim ID: {cms_claim_id}."
        print(f"\n📋 {summary}\n")
        return {
            "final_claim": final_claim,
            "cms_claim_id": cms_claim_id,
            "status": "complete",
            "human_decision": "",
            "human_review_requested": False,
            "messages": [AIMessage(content=summary)],
        }

    # needs_more_info: reopens the loop for one more round of claimant detail.
    # Deliberately leaves validated_stage_b=True untouched — validate_stage_b
    # would recompute missing_fields from STAGE_B_FIELDS alone and immediately
    # erase this sentinel, since every required field is already filled by
    # this point in the flow. See disambiguate_node / fnol_supervisor routing.
    summary = "Reviewer requested more information before deciding."
    print(f"\n🔁 {summary}\n")
    return {
        "missing_fields": ["additional_details_requested_by_reviewer"],
        "status": "awaiting_info",
        "damage_analyzed": False,
        "risk_assessed": False,
        "route_decision": "",
        "human_decision": "",
        "human_review_requested": False,
        "messages": [AIMessage(content=summary)],
    }
