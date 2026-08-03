"""
Coverage checker agent – looks up the policy in the mock policy database
and determines whether the claimed loss is in force, lapsed, excluded, or
unknown. Deterministic guardrail against paying out claims with no coverage.
"""

from fnol_state import FNOLState
from fnol_tools import check_coverage


def coverage_checker_node(state: FNOLState) -> dict:
    """LangGraph node: determine coverage status for the claim."""

    claim_data = state.get("claim_data", {})
    result = check_coverage(
        claim_data.get("policy_number", ""),
        claim_data.get("loss_type", ""),
        claim_data.get("date_of_loss", ""),
    )

    print(f"🛡️  Coverage checker → {result['status']} ({result['reason']})")

    return {
        "coverage_status": result["status"],
        "coverage_context": result,
        "coverage_checked": True,
    }
