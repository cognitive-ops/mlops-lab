"""
Risk-screener agent – applies mock fraud/severity heuristics to the
completed claim data and produces risk flags + a severity tier, feeding
the human reviewer's decision at the HITL gate.
"""

from langchain_core.messages import BaseMessage

from fnol_state import FNOLState
from fnol_tools import estimate_fraud_score


def risk_screener_node(state: FNOLState) -> dict:
    """LangGraph node: score fraud/severity risk from claim data + conversation."""

    claim_data = state.get("claim_data", {})
    coverage_context = state.get("coverage_context", {})

    transcript = " ".join(
        msg.content
        for msg in state["messages"]
        if isinstance(msg, BaseMessage) and isinstance(msg.content, str)
    )

    flags, severity_tier = estimate_fraud_score(claim_data, coverage_context, transcript)

    print(f"⚠️  Risk screener → flags: {flags or '(none)'}, severity: {severity_tier}")

    return {
        "risk_flags": flags,
        "severity_tier": severity_tier,
        "risk_assessed": True,
    }
