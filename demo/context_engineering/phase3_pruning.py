"""Phase 3: Pruning & Compression (garbage collection). Dependency-free, runnable.

  1. Observation Pruning         huge tool output -> cheap model -> ~100 tokens of relevant key/values
  2. Rolling State Summarization history > threshold -> old ReAct loops collapsed, last 2 kept verbatim

The "cheap model" is a Protocol. MockCheapModel keeps the demo offline; swap in a real
client (gpt-4o-mini, a Flash-tier model, ...) by implementing `complete(prompt) -> str`.

Run: python phase3_pruning.py
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger("phase3")


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # swap for tiktoken / API token counting


# =============================================================================
# Cheap model abstraction
# =============================================================================
class CheapModel(Protocol):
    def complete(self, prompt: str) -> str: ...


EXTRACT_PROMPT = (
    "You compress tool output. Task: {task}\n"
    "Drop metadata, headers, pagination, logs. Return ONLY a compact JSON object of the "
    "key-value pairs relevant to the task. Max {max_tokens} tokens.\n\nTOOL OUTPUT:\n{payload}"
)
SUMMARY_PROMPT = (
    "Collapse these agent Thought->Action->Observation steps into ONE dense paragraph. "
    "Keep decisions, IDs, amounts, outcomes. Drop chatter.\n\n{steps}"
)


class OpenAICheapModel:
    """Real cheap model via OpenAI chat completions (pip install openai; set OPENAI_API_KEY).
    Any OpenAI-compatible endpoint works via base_url."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None,
                 base_url: str | None = None, max_output_tokens: int = 300,
                 max_prompt_chars: int = 48_000):  # ~12k tokens
        import os
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=base_url)
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.max_prompt_chars = max_prompt_chars

    def complete(self, prompt: str) -> str:
        if len(prompt) > self.max_prompt_chars:
            log.warning("openai: prompt clipped %d -> %d chars", len(prompt), self.max_prompt_chars)
            prompt = prompt[:self.max_prompt_chars]  # cheap model context is finite too
        log.debug("openai: request model=%s prompt_chars=%d head=%r",
                  self.model, len(prompt), prompt[:120])
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=self.max_output_tokens,
        )
        out = (resp.choices[0].message.content or "").strip()
        u = resp.usage
        log.debug("openai: response %.2fs finish=%s usage(prompt=%s completion=%s) out=%r",
                  time.perf_counter() - t0, resp.choices[0].finish_reason,
                  getattr(u, "prompt_tokens", "?"), getattr(u, "completion_tokens", "?"), out[:200])
        return out


def make_llm() -> CheapModel:
    """Real model when key + SDK are present, else offline mock."""
    if os.getenv("OPENAI_API_KEY"):
        try:
            llm = OpenAICheapModel()
            log.info("make_llm: using OpenAICheapModel(%s)", llm.model)
            return llm
        except ImportError:
            log.warning("make_llm: openai not installed -> MockCheapModel")
    else:
        log.info("make_llm: OPENAI_API_KEY not set -> MockCheapModel")
    return MockCheapModel()


class MockCheapModel:
    """Offline stand-in. Real model reads the prompt; this one applies the same idea by rule."""

    NOISE_KEYS = {"metadata", "meta", "headers", "pagination", "links", "debug", "trace",
                  "request_id", "etag", "created_at", "updated_at", "logs", "audit_log"}

    def complete(self, prompt: str) -> str:
        if prompt.startswith("You compress tool output"):
            return self._extract(prompt)
        return self._summarize(prompt)

    # -- extraction: walk JSON, drop noise keys, keep scalars, sample big lists
    def _extract(self, prompt: str) -> str:
        task = prompt.split("Task: ", 1)[1].split("\n", 1)[0].lower()
        payload = prompt.split("TOOL OUTPUT:\n", 1)[1]
        data = json.loads(payload)
        wanted = {w.strip(".,?") for w in task.split() if len(w) > 3}

        def walk(node, path=""):
            if isinstance(node, dict):
                out = {}
                for k, v in node.items():
                    if k.lower() in self.NOISE_KEYS:
                        continue
                    sub = walk(v, k)
                    if sub not in (None, {}, []):
                        out[k] = sub
                return out
            if isinstance(node, list):
                if node and all(isinstance(x, dict) for x in node):
                    hits = [x for x in node if wanted & {str(v).lower() for v in x.values()}]
                    kept = [walk(x, path) for x in (hits or node)[:3]]
                    return {"count": len(node), "sample": kept}
                return node[:5]
            return node

        return json.dumps(walk(data), separators=(",", ":"))

    # -- summarization: one line per step, observations clipped hard
    def _summarize(self, prompt: str) -> str:
        steps = prompt.split("\n\n", 1)[1].strip().split("\n---\n")
        parts = []
        for i, s in enumerate(steps, 1):
            lines = {l.split(": ", 1)[0]: l.split(": ", 1)[1] for l in s.splitlines() if ": " in l}
            parts.append(f"({i}) {lines.get('Action', '?')} -> {lines.get('Observation', '')[:80]}")
        return "Earlier in this session: " + "; ".join(parts) + "."


# =============================================================================
# 1. Observation Pruning
# =============================================================================
def prune_observation(observation: str, task: str, llm: CheapModel,
                      trigger_tokens: int = 500, target_tokens: int = 100) -> str:
    """Compress a tool observation only when it is bulky. Small ones pass through untouched."""
    before = count_tokens(observation)
    if before <= trigger_tokens:
        log.debug("prune_obs: skip, %d tokens <= trigger %d", before, trigger_tokens)
        return observation
    log.info("prune_obs: %d tokens > trigger %d, extracting (task=%r)", before, trigger_tokens, task)
    try:
        compact = llm.complete(EXTRACT_PROMPT.format(
            task=task, max_tokens=target_tokens, payload=observation))
    except Exception:  # cheap model failed / bad JSON -> hard truncate, never blow the budget
        log.exception("prune_obs: cheap model failed, falling back to hard truncate")
        compact = observation[: target_tokens * 4] + " ...[truncated]"
    if count_tokens(compact) > target_tokens * 2:  # model ignored the limit
        log.warning("prune_obs: output %d tokens > 2x target %d, hard truncating",
                    count_tokens(compact), target_tokens)
        compact = compact[: target_tokens * 4] + " ...[truncated]"
    log.info("prune_obs: %d -> %d tokens (%.1f%% saved)", before, count_tokens(compact),
             100 * (1 - count_tokens(compact) / before))
    log.debug("prune_obs: result=%r", compact[:300])
    return compact


# =============================================================================
# 2. Rolling State Summarization
# =============================================================================
@dataclass
class ReActStep:
    thought: str
    action: str
    observation: str

    def render(self) -> str:
        return f"Thought: {self.thought}\nAction: {self.action}\nObservation: {self.observation}"


def history_tokens(summary: str, steps: list[ReActStep]) -> int:
    return count_tokens(summary) + sum(count_tokens(s.render()) for s in steps)


def roll_history(summary: str, steps: list[ReActStep], llm: CheapModel,
                 threshold: int = 4000, keep_recent: int = 2) -> tuple[str, list[ReActStep]]:
    """If history > threshold: fold older steps (and any prior summary) into one paragraph,
    keep the last `keep_recent` steps verbatim."""
    used = history_tokens(summary, steps)
    if used <= threshold or len(steps) <= keep_recent:
        log.debug("roll_history: skip, tokens=%d threshold=%d steps=%d keep_recent=%d",
                  used, threshold, len(steps), keep_recent)
        return summary, steps
    older, recent = steps[:-keep_recent], steps[-keep_recent:]
    log.info("roll_history: %d tokens > %d, folding %d older steps (prior summary=%s), keeping %d",
             used, threshold, len(older), bool(summary), len(recent))
    blocks = ([f"Thought: (prior summary)\nAction: summary\nObservation: {summary}"] if summary else [])
    blocks += [s.render() for s in older]
    new_summary = llm.complete(SUMMARY_PROMPT.format(steps="\n---\n".join(blocks)))
    log.info("roll_history: %d -> %d tokens", used, history_tokens(new_summary, recent))
    log.debug("roll_history: summary=%r", new_summary[:300])
    return new_summary, recent


# =============================================================================
# Demo
# =============================================================================
def fake_claims_payload(n: int = 1200) -> str:
    rows = [{"claim_id": f"CLM-{1000 + i}", "status": "UNDER_REVIEW" if i % 7 else "APPROVED",
             "amount": 1000 + i * 13, "adjuster": None if i % 3 else "A-42",
             "metadata": {"etag": f"{i:08x}", "created_at": "2026-01-01", "trace": "x" * 40}}
            for i in range(n)]
    return json.dumps({"metadata": {"request_id": "r-9", "headers": {"x": "y" * 50}},
                       "pagination": {"page": 1, "total": n}, "claims": rows}, indent=2)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "DEBUG").upper(),
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    llm = make_llm()
    print(f"cheap model: {type(llm).__name__}\n")

    print("== 1. Observation Pruning ==")
    raw = fake_claims_payload()
    pruned = prune_observation(raw, task="status of claim CLM-1001", llm=llm)
    print(f"lines: {len(raw.splitlines())}  tokens: {count_tokens(raw)} -> {count_tokens(pruned)}")
    print(f"pruned: {pruned[:300]}\n")

    print("== 2. Rolling State Summarization ==")
    steps = [ReActStep(f"Need info #{i}", f"search_claims(page={i})",
                       f"CLM-{1000 + i} status=UNDER_REVIEW " + "detail " * 600) for i in range(1, 7)]
    print(f"before: {len(steps)} steps, {history_tokens('', steps)} tokens")
    summary, steps = roll_history("", steps, llm, threshold=4000, keep_recent=2)
    print(f"after : {len(steps)} verbatim steps + summary, {history_tokens(summary, steps)} tokens")
    print(f"summary: {summary}")


if __name__ == "__main__":
    main()
