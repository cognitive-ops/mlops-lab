"""
Supervisor – routes the FNOL intake pipeline to the next node.

Deterministic rule router, not an LLM: ingestion, validation, policy
verification, and damage/risk scoring are fixed, unambiguous stages. The
one point of real judgment — the risk-based approve/deny/escalate decision
— is made once, deterministically, by fraud_risk_node itself (via
route_decision), and the actual approve/deny call for anything above
fast-track is handed to a human at the HITL gate. The supervisor never
makes that call.
"""

from fnol_state import FNOLState


def supervisor_node(state: FNOLState) -> dict:
    """Decide the next node based on what stage the claim intake is at."""

    if state.get("pending_user_reply"):
        next_agent = "ingest"
    elif state.get("ingested"):
        next_agent = "extractor"
    elif not state.get("validated_stage_a", False):
        next_agent = "validate_stage_a"
    elif state.get("missing_fields") and not state.get("policy_verified", False):
        next_agent = "disambiguate"
    elif not state.get("policy_verified", False):
        next_agent = "verify_policy"
    elif not state.get("validated_stage_b", False):
        next_agent = "validate_stage_b"
    elif state.get("missing_fields"):
        next_agent = "disambiguate"
    elif not state.get("damage_analyzed", False):
        next_agent = "damage_analysis"
    elif not state.get("risk_assessed", False):
        next_agent = "fraud_risk"
    else:
        # fraud_risk's own conditional edge sends fast-track claims straight
        # to fast_track_approve and everything else to await_human_review —
        # reaching the supervisor with risk_assessed=True only happens on
        # the await_human_review -> supervisor loop-back, at which point
        # human_review_requested is already set and assign_or_deny is next.
        next_agent = "assign_or_deny"

    iterations = state.get("iterations", 0) + 1
    if iterations > 25:
        next_agent = "assign_or_deny"

    print(f"🎯 Supervisor → {next_agent}  (iteration {iterations})")

    return {
        "next_agent": next_agent,
        "iterations": iterations,
    }
