"""
Finance Settlement Agent – computes reserve/settlement figures and
disburses payment for approved claims (fast-track or adjuster-approved).
Runs after the approve decision and before the claim is marked complete.
Sibling of Fraud/Claims Triage under the orchestrator; only reachable on
the approved path — denied claims skip settlement entirely.
"""

from langchain_core.messages import AIMessage

from fnol_state import FNOLState
from fnol_tools import calculate_settlement, disburse_payment


def finance_settlement_node(state: FNOLState) -> dict:
    """LangGraph node: calculate reserve/settlement and disburse payment."""

    claim_data = state.get("claim_data", {})
    coverage_context = state.get("coverage_context", {})
    final_claim = dict(state.get("final_claim", {}))

    result = calculate_settlement(claim_data, coverage_context)
    claim_id = claim_data.get("policy_number", "") + claim_data.get("claimant_name", "")
    payment_id = disburse_payment(claim_id, result["settlement_amount"])

    final_claim.update(
        {
            "deductible_applied": result["deductible"],
            "reserve_amount": result["reserve_amount"],
            "settlement_amount": result["settlement_amount"],
            "payment_id": payment_id,
        }
    )

    summary = (
        f"Settlement calculated: reserve ${result['reserve_amount']:.2f}, "
        f"payout ${result['settlement_amount']:.2f} (deductible ${result['deductible']:.2f}). "
        f"Payment ID: {payment_id}."
    )
    print(f"\n💰 {summary}\n")

    return {
        "final_claim": final_claim,
        "deductible_applied": result["deductible"],
        "reserve_amount": result["reserve_amount"],
        "settlement_amount": result["settlement_amount"],
        "payment_id": payment_id,
        "status": "complete",
        "messages": [AIMessage(content=summary)],
    }
