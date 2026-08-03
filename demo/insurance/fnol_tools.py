"""
Mock policy database, coverage check, fraud/severity heuristics, and
adjuster assignment for the FNOL claims intake pipeline. All deterministic
— stand-ins for a real policy admin system / rating engine / claims queue.
"""

from datetime import date, datetime
from typing import Optional

MOCK_POLICIES = {
    "POL-100001": {
        "status": "active",
        "effective_date": date(2024, 1, 1),
        "covered_losses": {"collision", "theft", "weather", "vandalism"},
        "prior_claims_count": 0,
    },
    "POL-100002": {
        "status": "lapsed",
        "effective_date": date(2022, 6, 1),
        "covered_losses": {"collision", "fire"},
        "prior_claims_count": 2,
    },
    "POL-100003": {
        "status": "active",
        "effective_date": date(2025, 12, 1),
        "covered_losses": {"collision", "theft", "fire", "weather", "liability", "vandalism"},
        "prior_claims_count": 3,
    },
}

ADJUSTERS = ["A. Reyes", "B. Chen", "C. Okafor", "D. Patel"]


def parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def lookup_policy(policy_number: str) -> Optional[dict]:
    return MOCK_POLICIES.get(policy_number)


def check_coverage(policy_number: str, loss_type: str, date_of_loss: str) -> dict:
    """Mock coverage determination. Returns status + reason + policy context."""

    policy = lookup_policy(policy_number)
    if not policy:
        return {"status": "unknown", "reason": f"Policy '{policy_number}' not found", "prior_claims_count": 0}

    if policy["status"] != "active":
        return {
            "status": "lapsed",
            "reason": f"Policy status is '{policy['status']}'",
            "prior_claims_count": policy["prior_claims_count"],
        }

    if loss_type not in policy["covered_losses"]:
        return {
            "status": "excluded",
            "reason": f"Loss type '{loss_type}' is not covered by this policy",
            "prior_claims_count": policy["prior_claims_count"],
        }

    dol = parse_date(date_of_loss)
    effective_date = policy["effective_date"]
    if dol and dol < effective_date:
        return {
            "status": "excluded",
            "reason": "Date of loss precedes the policy's effective date",
            "prior_claims_count": policy["prior_claims_count"],
        }

    days_since_start = (dol - effective_date).days if dol else None
    return {
        "status": "in_force",
        "reason": "Coverage confirmed",
        "prior_claims_count": policy["prior_claims_count"],
        "days_since_policy_start": days_since_start,
    }


NARRATIVE_RED_FLAGS = ("cash only", "no witnesses", "staged", "paid in full", "desperate")


def estimate_fraud_score(claim_data: dict, coverage_context: dict, transcript: str) -> tuple:
    """Mock underwriting/fraud rules. Returns (risk_flags, severity_tier)."""

    flags = []

    days_since_start = coverage_context.get("days_since_policy_start")
    if days_since_start is not None and 0 <= days_since_start < 14:
        flags.append("very_recent_policy")

    loss_type = claim_data.get("loss_type", "")
    if loss_type in ("theft", "collision") and not claim_data.get("police_report_number"):
        flags.append("no_police_report")

    amount = claim_data.get("estimated_damage_amount") or 0
    if amount > 20000:
        flags.append("high_value_claim")

    if coverage_context.get("prior_claims_count", 0) >= 2:
        flags.append("prior_claims_history")

    transcript_lower = transcript.lower()
    if any(phrase in transcript_lower for phrase in NARRATIVE_RED_FLAGS):
        flags.append("narrative_red_flag")

    flags = list(dict.fromkeys(flags))

    if amount > 20000 or len(flags) >= 2:
        severity = "high"
    elif amount > 5000 or flags:
        severity = "medium"
    else:
        severity = "low"

    return flags, severity


def assign_adjuster(claim_id: str) -> str:
    """Deterministic round-robin assignment (stand-in for a real claims queue)."""
    idx = abs(hash(claim_id)) % len(ADJUSTERS)
    return ADJUSTERS[idx]
