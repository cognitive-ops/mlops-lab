"""
Verify-policy agent – confirms the policy exists and is active (Guidewire-
style PolicyCenter lookup) before we bother collecting full loss details.
Deterministic guardrail: no point disambiguating loss details for a claim
against a policy that doesn't exist.
"""

from fnol_state import FNOLState
from fnol_tools import verify_policy


def verify_policy_node(state: FNOLState) -> dict:
    """LangGraph node: look up the policy's identity/status."""

    claim_data = state.get("claim_data", {})
    result = verify_policy(claim_data.get("policy_number", ""))

    print(f"🛡️  Verify policy → {result['status']} ({result['reason']})")

    return {
        "coverage_status": result["status"],
        "coverage_context": result,
        "policy_verified": True,
    }
