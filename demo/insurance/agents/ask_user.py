"""
Ask-user agent – turns the validator's missing/invalid field list into a
follow-up question and pauses the graph (ends the turn) so the caller can
supply the answer on the next invocation.
"""

from langchain_core.messages import AIMessage

from schema import FIELD_PROMPTS
from state import IntakeState


def ask_user_node(state: IntakeState) -> dict:
    """LangGraph node: prompt the user for the still-missing fields."""

    missing = state.get("missing_fields", [])
    questions = [FIELD_PROMPTS.get(field, f"Please provide: {field}") for field in missing]
    question_text = "I still need a few details:\n- " + "\n- ".join(questions)

    print(f"\n🧾 Agent: {question_text}\n")

    return {
        "messages": [AIMessage(content=question_text)],
        "status": "awaiting_info",
    }
