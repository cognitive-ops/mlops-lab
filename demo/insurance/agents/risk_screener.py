"""
Risk-screener agent – applies mock underwriting rules to the completed
applicant data and produces risk flags, a risk tier, and a premium estimate.
"""

from datetime import datetime

from langchain_core.messages import BaseMessage

from state import IntakeState
from tools import calculate_age, estimate_premium, parse_dob

INCIDENT_KEYWORDS = ("accident", "dui", "violation", "suspended", "citation")


def risk_screener_node(state: IntakeState) -> dict:
    """LangGraph node: score underwriting risk from applicant data + conversation."""

    applicant_data = state.get("applicant_data", {})
    flags = []

    dob = parse_dob(applicant_data.get("date_of_birth", ""))
    if dob:
        age = calculate_age(dob)
        if age < 21:
            flags.append("young_driver")
        elif age > 70:
            flags.append("senior_driver_review")

    vehicle_year = applicant_data.get("vehicle_year")
    if vehicle_year and (datetime.now().year - vehicle_year) > 15:
        flags.append("older_vehicle_inspection_required")

    transcript = " ".join(
        msg.content.lower()
        for msg in state["messages"]
        if isinstance(msg, BaseMessage) and isinstance(msg.content, str)
    )
    if any(keyword in transcript for keyword in INCIDENT_KEYWORDS):
        flags.append("prior_incident_reported")

    flags = list(dict.fromkeys(flags))
    tier = "high" if len(flags) >= 2 else ("medium" if flags else "low")
    premium = estimate_premium(applicant_data, flags)

    print(f"⚠️  Risk screener → flags: {flags or '(none)'}, tier: {tier}, premium: ${premium}")

    return {
        "risk_flags": flags,
        "risk_tier": tier,
        "premium_estimate": premium,
        "risk_assessed": True,
    }
