"""
Deterministic sanitization action for the NeMo Guardrails input rail.

Auto-discovered by NeMo Guardrails (it imports `actions.py` from the config
folder). Pure regex/length checks — no LLM call — so the FNOL pre-graph gate
stays rule-based and auditable rather than an LLM's judgment call, matching
the "Deterministic Rail" design in ../fnol_guardrails.py.
"""

import re
from typing import Optional

from nemoguardrails.actions import action

PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore (all |any )?(previous|prior|above) instructions", re.IGNORECASE),
    re.compile(r"you are now (in )?(dan|developer|jailbreak) mode", re.IGNORECASE),
    re.compile(r"^\s*system\s*:", re.IGNORECASE),
    re.compile(r"disregard (the|your) (system prompt|instructions)", re.IGNORECASE),
)

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

MIN_LENGTH = 3
MAX_LENGTH = 8000

BLOCKING_FLAGS = {"input_too_short", "input_too_long", "prompt_injection_pattern"}


@action(name="deterministic_sanitize_check")
async def deterministic_sanitize_check(context: Optional[dict] = None) -> dict:
    """Runs against `$user_message` (auto-injected via `context`). Returns
    {"passed": bool, "flags": [...], "redacted_text": str} — same contract
    fnol_guardrails.run_deterministic_rail() has always exposed."""

    text = (context or {}).get("user_message") or ""
    stripped = text.strip()
    flags = []

    if len(stripped) < MIN_LENGTH:
        flags.append("input_too_short")
    if len(stripped) > MAX_LENGTH:
        flags.append("input_too_long")

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(stripped):
            flags.append("prompt_injection_pattern")
            break

    redacted = stripped
    if SSN_PATTERN.search(stripped):
        flags.append("possible_ssn_detected")
        redacted = SSN_PATTERN.sub("[REDACTED-SSN]", redacted)
    if CREDIT_CARD_PATTERN.search(stripped):
        flags.append("possible_card_number_detected")
        redacted = CREDIT_CARD_PATTERN.sub("[REDACTED-CARD]", redacted)

    passed = not any(flag in BLOCKING_FLAGS for flag in flags)
    return {"passed": passed, "flags": flags, "redacted_text": redacted}
