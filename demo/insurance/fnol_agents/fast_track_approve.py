"""
Fast-track approve – the ONLY node that reaches a decision without a human
in the loop. Only reachable when fraud_risk_node scored the claim below
the ambiguous-risk threshold, coverage is in force, and the amount is under
the high-value threshold. Submits straight to the Core CMS.
"""

from langchain_core.messages import AIMessage

from fnol_state import FNOLState
from fnol_tools import submit_to_cms


def fast_track_approve_node(state: FNOLState) -> dict:
    """LangGraph node: auto-approve a low-risk, in-coverage, low-value claim."""

    claim_data = state.get("claim_data", {})
    final_claim = {
        **claim_data,
        "coverage_status": state.get("coverage_status"),
        "risk_flags": state.get("risk_flags", []),
        "risk_score": state.get("risk_score"),
        "decision": "auto_approved_fast_track",
    }
    cms_claim_id = submit_to_cms(final_claim)
    final_claim["cms_claim_id"] = cms_claim_id

    summary = f"Claim auto-approved (fast track, risk_score={state.get('risk_score')}). CMS claim ID: {cms_claim_id}."
    print(f"\n📋 {summary}\n")

    return {
        "final_claim": final_claim,
        "cms_claim_id": cms_claim_id,
        "status": "complete",
        "messages": [AIMessage(content=summary)],
    }
