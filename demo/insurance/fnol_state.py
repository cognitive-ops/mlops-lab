"""
Shared state definition for the FNOL (First Notice of Loss) claims intake
graph. Separate from state.py (policy application intake) — same folder,
independent pipeline.
"""

from typing import Annotated, List, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class FNOLState(TypedDict):
    """State that flows through the FNOL claims intake graph.

    Attributes:
        messages: Full conversation history (auto-accumulated via add_messages).
        claim_data: Fields collected so far, merged across turns.
        missing_fields: Required fields still absent or invalid.
        validated: Whether the validator has run since the last extraction.
        coverage_checked: Whether the coverage checker has run for the current data.
        coverage_status: "in_force" | "lapsed" | "excluded" | "unknown" | "".
        coverage_context: Raw result from the mock policy lookup (reason, prior claims, ...).
        risk_assessed: Whether the risk screener has run for the current data.
        risk_flags: Fraud/severity risk flags raised by the risk screener.
        severity_tier: "low" | "medium" | "high".
        human_review_requested: Whether the await-human-review gate has fired
            for the current cycle (guards against re-requesting on every loop).
        human_decision: "" | "approved" | "rejected" | "needs_more_info" — set
            externally (by the human reviewer) via graph.update_state().
        pending_user_reply: A new claimant message is waiting to be extracted.
        next_agent: Which node the supervisor wants to invoke next.
        status: "collecting" | "awaiting_info" | "awaiting_human_review" | "complete".
        final_claim: The finished, structured claim record (once complete).
        iterations: Safety counter to prevent infinite loops.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    claim_data: dict
    missing_fields: List[str]
    validated: bool
    coverage_checked: bool
    coverage_status: str
    coverage_context: dict
    risk_assessed: bool
    risk_flags: List[str]
    severity_tier: str
    human_review_requested: bool
    human_decision: str
    pending_user_reply: bool
    next_agent: str
    status: str
    final_claim: dict
    iterations: int
