"""
Extractor agent – pulls structured claim fields out of the latest claimant
message using LLM structured output.
"""

import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from fnol_schema import ClaimExtraction
from fnol_state import FNOLState

EXTRACTION_INSTRUCTIONS = (
    "Extract any First Notice of Loss (FNOL) claim details mentioned in this "
    "message. Only fill fields explicitly stated — leave everything else "
    "null. Do not guess or infer missing details."
)


def extractor_node(state: FNOLState) -> dict:
    """LangGraph node: extract claim fields from the latest human message."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    structured_llm = llm.with_structured_output(ClaimExtraction)

    latest_human = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_human = msg.content
            break

    prompt = f"{EXTRACTION_INSTRUCTIONS}\n\nMessage:\n{latest_human}"
    extraction = structured_llm.invoke(prompt)
    new_fields = extraction.model_dump(exclude_none=True)

    claim_data = dict(state.get("claim_data", {}))
    claim_data.update(new_fields)

    print(f"🔍 Extractor → captured: {list(new_fields.keys()) or '(nothing new)'}")

    return {
        "claim_data": claim_data,
        "validated": False,
        "pending_user_reply": False,
    }
