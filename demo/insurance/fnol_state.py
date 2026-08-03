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
        input_channel: How the claim narrative arrived — "app" | "voice" | "pdf".
        raw_input: The raw payload for the current turn (text, or a file path
            for voice/pdf channels) before ingestion normalizes it into `messages`.
        photo_path: Optional path to a damage photo, independent of input_channel
            (a claimant can file by phone and still attach a photo later).
        ingested: Whether the ingest node has normalized raw_input for this turn.
        claim_data: Fields collected so far, merged across turns.
        missing_fields: Required fields (current stage) still absent or invalid.
        validated_stage_a: Whether policy-identifying fields (policy_number,
            claimant_name) have been checked since the last extraction.
        validated_stage_b: Whether full loss-detail fields have been checked
            since policy verification passed.
        policy_verified: Whether verify_policy has run for the current data.
        coverage_status: "in_force" | "lapsed" | "excluded" | "unknown" | "".
        coverage_context: Raw result from the mock Guidewire policy lookup.
        damage_analyzed: Whether the multi-modal damage node has run.
        damage_analysis: Result of photo analysis (or a "no photo" stand-in).
        risk_assessed: Whether the fraud/risk node has run for the current data.
        risk_flags: Fraud/severity risk flags raised by the risk node.
        risk_score: Numeric fraud/severity risk score in [0, 1].
        route_decision: "fast_track" | "hitl_ambiguous" | "adjuster_review" | "".
        siu_escalated: Whether this claim is flagged for Special Investigations
            Unit attention (set for high-risk adjuster_review routing).
        human_review_requested: Whether the await-human-review gate has fired
            for the current cycle (guards against re-requesting on every loop).
        human_decision: "" | "approved" | "rejected" | "needs_more_info" — set
            externally (by the human reviewer) via graph.update_state().
        pending_user_reply: A new claimant message is waiting to be ingested.
        next_agent: Which node the supervisor wants to invoke next.
        status: "collecting" | "awaiting_info" | "awaiting_human_review" | "complete".
        cms_claim_id: The ID returned by the mock Core CMS (Guidewire/Duck Creek)
            submission, once the claim reaches a terminal decision.
        final_claim: The finished, structured claim record (once complete).
        iterations: Safety counter to prevent infinite loops.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    input_channel: str
    raw_input: str
    photo_path: str
    ingested: bool
    claim_data: dict
    missing_fields: List[str]
    validated_stage_a: bool
    validated_stage_b: bool
    policy_verified: bool
    coverage_status: str
    coverage_context: dict
    damage_analyzed: bool
    damage_analysis: dict
    risk_assessed: bool
    risk_flags: List[str]
    risk_score: float
    route_decision: str
    siu_escalated: bool
    human_review_requested: bool
    human_decision: str
    pending_user_reply: bool
    next_agent: str
    status: str
    cms_claim_id: str
    final_claim: dict
    iterations: int
