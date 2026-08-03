"""
Validation and mock-underwriting helpers shared by the validator and
risk-screener agents. Plain functions (not @tool) — nothing here is bound
to an LLM tool-calling loop, it's deterministic rule logic.
"""

import re
from datetime import date, datetime
from typing import Optional

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def validate_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 10


def validate_vin(vin: str) -> bool:
    return bool(_VIN_RE.match(vin.strip()))


def validate_vehicle_year(year: int) -> bool:
    current_year = datetime.now().year
    return 1980 <= year <= current_year + 1


def parse_dob(dob: str) -> Optional[date]:
    try:
        return datetime.strptime(dob.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def estimate_premium(applicant_data: dict, risk_flags: list) -> float:
    """Mock premium estimate — base rate plus flat adjustments per risk flag."""
    base = 800.0
    adjustments = {
        "young_driver": 350.0,
        "senior_driver_review": 120.0,
        "older_vehicle_inspection_required": 60.0,
        "prior_incident_reported": 500.0,
    }
    return round(base + sum(adjustments.get(flag, 0.0) for flag in risk_flags), 2)
