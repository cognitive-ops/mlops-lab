"""
Fraud & risk evaluation node – runs the full loss-coverage check (now that
loss_type/date_of_loss are known), scores fraud/severity risk, and decides
the routing outcome:

    coverage != in_force            → adjuster_review (no auto-pay on a
                                       lapsed/excluded/unknown policy)
    risk_score >= 0.6 or amount>10k → adjuster_review (SIU-escalated if
                                       risk_score >= 0.6 — genuine fraud
                                       signal, not just a big clean claim)
    0.3 <= risk_score < 0.6         → hitl_ambiguous (quick human sign-off)
    risk_score < 0.3                → fast_track (auto-approve)
"""

from langchain_core.messages import BaseMessage

from fnol_state import FNOLState
from fnol_tools import check_loss_coverage, compute_risk_score

HIGH_RISK_THRESHOLD = 0.6
AMBIGUOUS_RISK_THRESHOLD = 0.3
HIGH_VALUE_THRESHOLD = 10_000


def fraud_risk_node(state: FNOLState) -> dict:
    """LangGraph node: score risk and pick the conditional-routing outcome."""

    claim_data = state.get("claim_data", {})
    damage_analysis = state.get("damage_analysis", {})

    coverage_context = check_loss_coverage(
        claim_data.get("policy_number", ""),
        claim_data.get("loss_type", ""),
        claim_data.get("date_of_loss", ""),
    )

    transcript = " ".join(
        msg.content
        for msg in state["messages"]
        if isinstance(msg, BaseMessage) and isinstance(msg.content, str)
    )

    risk_flags, risk_score = compute_risk_score(claim_data, coverage_context, damage_analysis, transcript)

    amount = claim_data.get("estimated_damage_amount") or 0
    coverage_ok = coverage_context.get("status") == "in_force"

    if not coverage_ok or risk_score >= HIGH_RISK_THRESHOLD or amount > HIGH_VALUE_THRESHOLD:
        route_decision = "adjuster_review"
        siu_escalated = risk_score >= HIGH_RISK_THRESHOLD
    elif risk_score >= AMBIGUOUS_RISK_THRESHOLD:
        route_decision = "hitl_ambiguous"
        siu_escalated = False
    else:
        route_decision = "fast_track"
        siu_escalated = False

    print(
        f"⚠️  Fraud & risk → flags: {risk_flags or '(none)'}, score: {risk_score}, "
        f"coverage: {coverage_context.get('status')} → route: {route_decision}"
        f"{' [SIU]' if siu_escalated else ''}"
    )

    return {
        "coverage_status": coverage_context.get("status", ""),
        "coverage_context": coverage_context,
        "risk_flags": risk_flags,
        "risk_score": risk_score,
        "risk_assessed": True,
        "route_decision": route_decision,
        "siu_escalated": siu_escalated,
    }
