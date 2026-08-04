"""
Deterministic Rail — input sanitization gate that runs BEFORE the LangGraph
engine, matching the target architecture where the guardrail sits outside
the graph entirely.

Backed by real NeMo Guardrails (see guardrails_config/). The sanitization
logic itself (prompt-injection patterns, SSN/card-number redaction, length
checks) is a plain Python action — guardrails_config/actions.py — invoked
by an input-only Colang flow, so the pass/fail decision stays rule-based and
auditable rather than an LLM's judgment call. `run_deterministic_rail()`
calls NeMo Guardrails with `options.rails=["input"]`, so this never reaches
the main LLM — same cost/latency profile as the old inline-regex version.
"""

from pathlib import Path
from typing import Optional

from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import GenerationOptions

CONFIG_PATH = Path(__file__).parent / "guardrails_config"

_rails: Optional[LLMRails] = None


def _get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        config = RailsConfig.from_path(str(CONFIG_PATH))
        _rails = LLMRails(config)
    return _rails


def run_deterministic_rail(text: str) -> dict:
    """Check raw claim narrative text before it ever reaches the LangGraph
    engine. Returns {"passed": bool, "flags": [...], "redacted_text": str}.

    `redacted_text` masks detected PII patterns (SSN/credit-card-shaped
    numbers) so the LLM extractor never sees raw sensitive numbers even for
    inputs that otherwise pass the rail.
    """

    rails = _get_rails()
    options = GenerationOptions(rails=["input"], output_vars=["rail_result"])
    response = rails.generate(
        messages=[{"role": "user", "content": text or ""}],
        options=options,
    )

    output_data = response.output_data or {}
    rail_result = output_data.get("rail_result")
    if rail_result is None:
        # Input flow never ran (e.g. empty message short-circuited earlier) —
        # fail closed rather than silently letting unchecked text through.
        return {
            "passed": False,
            "flags": ["rail_result_missing"],
            "redacted_text": (text or "").strip(),
        }

    return rail_result
