"""
Extractor agent – pulls structured applicant/vehicle fields out of the
latest user message using LLM structured output (no tool-calling needed
for this task; it's a pure extraction problem).
"""

import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from schema import ApplicantExtraction
from state import IntakeState

EXTRACTION_INSTRUCTIONS = (
    "Extract any applicant or vehicle details mentioned in this message for an "
    "auto insurance policy application. Only fill fields explicitly stated — "
    "leave everything else null. Do not guess or infer missing details."
)


def extractor_node(state: IntakeState) -> dict:
    """LangGraph node: extract fields from the latest human message."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    structured_llm = llm.with_structured_output(ApplicantExtraction)

    latest_human = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_human = msg.content
            break

    prompt = f"{EXTRACTION_INSTRUCTIONS}\n\nMessage:\n{latest_human}"
    extraction = structured_llm.invoke(prompt)
    new_fields = extraction.model_dump(exclude_none=True)

    applicant_data = dict(state.get("applicant_data", {}))
    applicant_data.update(new_fields)

    print(f"🔍 Extractor → captured: {list(new_fields.keys()) or '(nothing new)'}")

    return {
        "applicant_data": applicant_data,
        "validated": False,
        "pending_user_reply": False,
    }
