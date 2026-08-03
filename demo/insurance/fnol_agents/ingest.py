"""
Ingest node – the LangGraph engine's entry point. By the time execution
reaches here, `raw_input` is already plain text: multi-modal extraction
(PDF text, voice transcription) and the deterministic guardrail rail both
run BEFORE the graph is invoked at all (see fnol_main.run_preflight), same
as the target architecture's Ingestion + Deterministic Rail boxes sitting
outside the LangGraph Engine. This node just turns that text into the next
HumanMessage in the conversation.
"""

from langchain_core.messages import HumanMessage

from fnol_state import FNOLState


def ingest_node(state: FNOLState) -> dict:
    """LangGraph node: append the pre-processed raw_input as a HumanMessage."""

    text = state.get("raw_input", "")

    print(f"📥 Ingest → {len(text)} chars")

    return {
        "messages": [HumanMessage(content=text)],
        "ingested": True,
        "pending_user_reply": False,
        "raw_input": "",
    }
