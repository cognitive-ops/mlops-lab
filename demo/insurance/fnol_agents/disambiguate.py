"""
Disambiguate node – turns the current missing/invalid field list (from
either validation stage) into a follow-up question and pauses the graph
(ends the turn) so the caller can supply the answer on the next invocation.
"""

from langchain_core.messages import AIMessage

from fnol_schema import FIELD_PROMPTS
from fnol_state import FNOLState


def disambiguate_node(state: FNOLState) -> dict:
    """LangGraph node: prompt the claimant for the still-missing fields."""

    missing = state.get("missing_fields", [])
    questions = [FIELD_PROMPTS.get(field, f"Please provide: {field}") for field in missing]
    question_text = "I still need a few details:\n- " + "\n- ".join(questions)

    print(f"\n🧾 Agent: {question_text}\n")

    return {
        "messages": [AIMessage(content=question_text)],
        "status": "awaiting_info",
    }
