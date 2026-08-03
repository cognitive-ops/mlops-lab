"""
Validator agent – checks the merged applicant data against the required
field list and per-field format rules. Deterministic, not LLM-based:
completeness/format checking has no ambiguity, so a rule engine is more
reliable (and cheaper) than an LLM judgment call here.
"""

from schema import REQUIRED_FIELDS
from state import IntakeState
from tools import (
    parse_dob,
    validate_email,
    validate_phone,
    validate_vehicle_year,
    validate_vin,
)


def validator_node(state: IntakeState) -> dict:
    """LangGraph node: find missing or invalid required fields."""

    applicant_data = state.get("applicant_data", {})
    missing = []

    for field in REQUIRED_FIELDS:
        value = applicant_data.get(field)
        if value in (None, ""):
            missing.append(field)

    if applicant_data.get("email") and not validate_email(applicant_data["email"]):
        missing.append("email")
    if applicant_data.get("phone") and not validate_phone(applicant_data["phone"]):
        missing.append("phone")
    if applicant_data.get("vehicle_vin") and not validate_vin(applicant_data["vehicle_vin"]):
        missing.append("vehicle_vin")
    if applicant_data.get("vehicle_year") and not validate_vehicle_year(applicant_data["vehicle_year"]):
        missing.append("vehicle_year")
    if applicant_data.get("date_of_birth") and parse_dob(applicant_data["date_of_birth"]) is None:
        missing.append("date_of_birth")

    # De-dupe while preserving order
    missing = list(dict.fromkeys(missing))

    print(f"✅ Validator → missing/invalid: {missing or '(none — complete)'}")

    return {
        "missing_fields": missing,
        "validated": True,
    }
