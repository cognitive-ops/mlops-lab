"""
Extractor agent – pulls structured claim fields out of the latest claimant
input using LLM structured output.

Two modes, chosen by `input_channel`:
  - app/voice: plain conversational text → `ClaimExtraction` straight off
    the message, same as before.
  - pdf: submitted document → `DocumentExtraction` (document-type
    classification + fields + confidence), since PDFs cover several
    distinct form types and — especially once OCR'd — can contain noisy
    text that shouldn't be trusted as blindly as a typed chat message.
"""

import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from fnol_schema import ClaimExtraction, DocumentExtraction
from fnol_state import FNOLState

EXTRACTION_INSTRUCTIONS = (
    "Extract any First Notice of Loss (FNOL) claim details mentioned in this "
    "message. Only fill fields explicitly stated — leave everything else "
    "null. Do not guess or infer missing details."
)

DOCUMENT_EXTRACTION_INSTRUCTIONS = (
    "This text was extracted from a claimant-submitted PDF document (possibly "
    "via OCR, so it may contain garbled words or misread characters). "
    "First classify what kind of document this is. Then extract any First "
    "Notice of Loss (FNOL) claim details it states. Only fill fields "
    "explicitly stated — leave everything else null; do not guess or infer. "
    "Set confidence to how sure you are the extracted values are accurate — "
    "lower it for text that looks OCR-garbled or ambiguous. List any field "
    "names in low_confidence_fields where the source text was unclear, "
    "abbreviated, or possibly misread, even if you still filled a value in."
)


def extractor_node(state: FNOLState) -> dict:
    """LangGraph node: extract claim fields from the latest human input."""

    latest_human = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_human = msg.content
            break

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    if state.get("input_channel") == "pdf":
        return _extract_from_document(llm, latest_human, state)
    return _extract_from_text(llm, latest_human, state)


def _extract_from_text(llm: ChatOpenAI, text: str, state: FNOLState) -> dict:
    structured_llm = llm.with_structured_output(ClaimExtraction)
    prompt = f"{EXTRACTION_INSTRUCTIONS}\n\nMessage:\n{text}"
    extraction = structured_llm.invoke(prompt)
    new_fields = extraction.model_dump(exclude_none=True)

    claim_data = dict(state.get("claim_data", {}))
    claim_data.update(new_fields)

    print(f"🔍 Extractor → captured: {list(new_fields.keys()) or '(nothing new)'}")

    return {
        "claim_data": claim_data,
        "validated_stage_a": False,
        "validated_stage_b": False,
        "ingested": False,
    }


def _extract_from_document(llm: ChatOpenAI, text: str, state: FNOLState) -> dict:
    structured_llm = llm.with_structured_output(DocumentExtraction)
    prompt = f"{DOCUMENT_EXTRACTION_INSTRUCTIONS}\n\nDocument text:\n{text}"
    extraction = structured_llm.invoke(prompt)
    new_fields = extraction.fields.model_dump(exclude_none=True)

    claim_data = dict(state.get("claim_data", {}))
    claim_data.update(new_fields)

    print(
        f"🔍 Extractor (doc: {extraction.document_type.value}, "
        f"confidence: {extraction.confidence:.2f}) → captured: "
        f"{list(new_fields.keys()) or '(nothing new)'}"
    )
    if extraction.low_confidence_fields:
        print(f"⚠️  Low-confidence fields, worth confirming: {extraction.low_confidence_fields}")

    return {
        "claim_data": claim_data,
        "document_type": extraction.document_type.value,
        "extraction_confidence": extraction.confidence,
        "low_confidence_fields": extraction.low_confidence_fields,
        "validated_stage_a": False,
        "validated_stage_b": False,
        "ingested": False,
    }
