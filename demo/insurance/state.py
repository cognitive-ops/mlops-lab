"""
Shared state definition for the insurance intake multi-agent system.

Every node in the graph reads from and writes to this state.
"""

from typing import Annotated, List, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class IntakeState(TypedDict):
    """State that flows through the intake graph.

    Attributes:
        messages: Full conversation history (auto-accumulated via add_messages).
        applicant_data: Fields collected so far, merged across turns.
        missing_fields: Required fields still absent or invalid.
        risk_flags: Underwriting risk flags raised by the risk screener.
        risk_tier: "low" | "medium" | "high".
        premium_estimate: Mock premium estimate in currency units.
        validated: Whether the validator has run since the last extraction.
        risk_assessed: Whether the risk screener has run for the current data.
        pending_user_reply: A new user message is waiting to be extracted.
        next_agent: Which node the supervisor wants to invoke next.
        status: "collecting" | "awaiting_info" | "complete".
        final_application: The finished, structured application record.
        iterations: Safety counter to prevent infinite loops.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    applicant_data: dict
    missing_fields: List[str]
    risk_flags: List[str]
    risk_tier: str
    premium_estimate: float
    validated: bool
    risk_assessed: bool
    pending_user_reply: bool
    next_agent: str
    status: str
    final_application: dict
    iterations: int
