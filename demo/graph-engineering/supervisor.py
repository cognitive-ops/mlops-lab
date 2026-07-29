"""
Supervisor — routes each request to the extractor (ingest mode) or the
query agent (query mode). The caller sets state["mode"] before invoking
the graph; the supervisor node just confirms the route in the transcript.
"""

from langchain_core.messages import AIMessage

from state import GraphState


def supervisor_node(state: GraphState) -> dict:
    mode = state.get("mode", "FINISH")
    return {"messages": [AIMessage(content=f"[supervisor] routing to: {mode}")]}
