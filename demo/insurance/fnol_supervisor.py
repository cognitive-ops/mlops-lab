"""
Supervisor – routes the FNOL intake pipeline to the next node.

Deterministic rule router, not an LLM: intake/validation/coverage/risk are
fixed, unambiguous checks, and the one point of real judgment (approve /
deny / need more info) is handed to a human at the HITL gate rather than
decided by the supervisor itself.
"""

from fnol_state import FNOLState


def supervisor_node(state: FNOLState) -> dict:
    """Decide the next node based on what stage the claim intake is at."""

    if state.get("pending_user_reply"):
        next_agent = "extractor"
    elif not state.get("validated", False):
        next_agent = "validator"
    elif state.get("missing_fields"):
        next_agent = "ask_user"
    elif not state.get("coverage_checked", False):
        next_agent = "coverage_checker"
    elif not state.get("risk_assessed", False):
        next_agent = "risk_screener"
    elif not state.get("human_review_requested", False):
        next_agent = "await_human_review"
    else:
        next_agent = "assign_or_deny"

    iterations = state.get("iterations", 0) + 1
    if iterations > 20:
        next_agent = "assign_or_deny"

    print(f"🎯 Supervisor → {next_agent}  (iteration {iterations})")

    return {
        "next_agent": next_agent,
        "iterations": iterations,
    }
