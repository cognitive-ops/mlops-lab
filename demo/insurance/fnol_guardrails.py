"""
Deterministic Rail — input sanitization gate that runs BEFORE the LangGraph
engine, matching the target architecture where the guardrail sits outside
the graph entirely. Rule-based on purpose: sanitization decisions (prompt
injection, unredacted PII, empty/garbage input) should be deterministic and
auditable, not left to an LLM's judgment.

This is a lightweight stand-in for a real deployment's NeMo Guardrails /
Guardrails AI rail — same contract (text in, pass/fail + flags out), so
swapping in the real thing later only touches this one module.
"""

import re

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


def run_deterministic_rail(text: str) -> dict:
    """Check raw claim narrative text before it ever reaches the LangGraph
    engine. Returns {"passed": bool, "flags": [...], "redacted_text": str}.

    `redacted_text` masks detected PII patterns (SSN/credit-card-shaped
    numbers) so the LLM extractor never sees raw sensitive numbers even for
    inputs that otherwise pass the rail.
    """

    flags = []
    stripped = (text or "").strip()

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

    # PII redaction doesn't fail the rail — it sanitizes and lets the claim
    # through. Injection attempts and malformed input do fail it.
    blocking_flags = {"input_too_short", "input_too_long", "prompt_injection_pattern"}
    passed = not any(flag in blocking_flags for flag in flags)

    return {"passed": passed, "flags": flags, "redacted_text": redacted}
