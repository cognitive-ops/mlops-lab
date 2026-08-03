"""
Validate stage B – runs once the policy is verified. Checks the full loss-
detail fields are present and well-formed. Deterministic for the same
reason as stage A: completeness/format checks have no ambiguity.
"""

from fnol_schema import STAGE_B_FIELDS, VALID_LOSS_TYPES
from fnol_state import FNOLState
from fnol_tools import parse_date


def validate_stage_b_node(state: FNOLState) -> dict:
    """LangGraph node: check loss-detail fields are present and well-formed."""

    claim_data = state.get("claim_data", {})
    missing = []

    for field in STAGE_B_FIELDS:
        value = claim_data.get(field)
        # injuries_reported is a bool — False is a valid answer, only None/absent is missing
        if field == "injuries_reported":
            if value is None:
                missing.append(field)
            continue
        if value in (None, ""):
            missing.append(field)

    if claim_data.get("loss_type") and claim_data["loss_type"] not in VALID_LOSS_TYPES:
        missing.append("loss_type")
    if claim_data.get("date_of_loss") and parse_date(claim_data["date_of_loss"]) is None:
        missing.append("date_of_loss")
    if claim_data.get("estimated_damage_amount") is not None and claim_data["estimated_damage_amount"] <= 0:
        missing.append("estimated_damage_amount")

    missing = list(dict.fromkeys(missing))

    print(f"✅ Validate (stage B) → missing/invalid: {missing or '(none — complete)'}")

    return {
        "missing_fields": missing,
        "validated_stage_b": True,
    }
