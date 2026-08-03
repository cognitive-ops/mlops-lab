"""
Validate stage A – confirms we have enough identifying info (policy number,
claimant name) to even attempt a policy lookup. Deterministic: presence
checks have no ambiguity.
"""

from fnol_schema import STAGE_A_FIELDS
from fnol_state import FNOLState


def validate_stage_a_node(state: FNOLState) -> dict:
    """LangGraph node: check policy-identifying fields are present."""

    claim_data = state.get("claim_data", {})
    missing = [field for field in STAGE_A_FIELDS if not claim_data.get(field)]

    print(f"✅ Validate (stage A) → missing: {missing or '(none)'}")

    return {
        "missing_fields": missing,
        "validated_stage_a": True,
    }
