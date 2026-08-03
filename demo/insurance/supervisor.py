"""
Supervisor – routes the intake pipeline to the next node, and finalizes
the completed application.

Unlike a free-form task (where an LLM must judge which specialist to call),
insurance intake is a fixed pipeline with one conditional branch (missing
info → ask the user). A deterministic rule router is simpler, cheaper, and
more reliable here than asking an LLM to decide the next step every turn.
"""

from langchain_core.messages import AIMessage

from state import IntakeState


def supervisor_node(state: IntakeState) -> dict:
    """Decide the next node based on what stage the intake is at."""

    if state.get("pending_user_reply"):
        next_agent = "extractor"
    elif not state.get("validated", False):
        next_agent = "validator"
    elif state.get("missing_fields"):
        next_agent = "ask_user"
    elif not state.get("risk_assessed", False):
        next_agent = "risk_screener"
    else:
        next_agent = "finalize"

    iterations = state.get("iterations", 0) + 1
    if iterations > 12:
        next_agent = "finalize"

    print(f"🎯 Supervisor → {next_agent}  (iteration {iterations})")

    return {
        "next_agent": next_agent,
        "iterations": iterations,
    }


def finalize_node(state: IntakeState) -> dict:
    """Assemble the final structured application record."""

    applicant_data = state.get("applicant_data", {})
    risk_tier = state.get("risk_tier", "low")
    decision = "submitted_for_underwriting" if risk_tier == "high" else "approved_pending_review"

    final_application = {
        **applicant_data,
        "risk_tier": risk_tier,
        "risk_flags": state.get("risk_flags", []),
        "premium_estimate": state.get("premium_estimate", 0.0),
        "decision": decision,
    }

    summary = (
        f"Application complete for {applicant_data.get('full_name', 'applicant')}.\n"
        f"Risk tier: {risk_tier} (flags: {', '.join(state.get('risk_flags', [])) or 'none'})\n"
        f"Estimated premium: ${state.get('premium_estimate', 0.0)}\n"
        f"Decision: {decision}"
    )

    print(f"\n📋 {summary}\n")

    return {
        "final_application": final_application,
        "status": "complete",
        "messages": [AIMessage(content=summary)],
    }
