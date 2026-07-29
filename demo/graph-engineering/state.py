"""
Shared state for the graph-engineering multi-agent system.

Every node in the graph reads from and writes to this state.
"""

from typing import Annotated, List, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class GraphState(TypedDict):
    """State that flows through the ingest/query multi-agent graph.

    Attributes:
        messages: Conversation history (auto-accumulated via add_messages).
        mode: Supervisor's routing decision ("ingest" | "query" | "FINISH").
        input_text: Raw text to ingest (ingest mode).
        question: User question (query mode).
        extracted_triples: Triples the extractor just added to the KG.
        retrieved_triples: Subgraph triples the query agent retrieved.
        final_answer: Answer returned to the user.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    mode: Literal["ingest", "query", "FINISH"]
    input_text: str
    question: str
    extracted_triples: list[tuple[str, str, str]]
    retrieved_triples: list[tuple[str, str, str]]
    final_answer: str
