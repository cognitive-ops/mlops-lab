"""Full context-engineering workflow, 4 phases. Dependency-free, runnable.

  Phase 1  Ingestion & Intent Parsing   raw input -> normalized query + intent + entities
  Phase 2  Dynamic Injection            route by intent -> retrieve from selected sources only
  Phase 3  Pruning & Compression        dedup, relevance cutoff, truncate tool output, summarize history
  Phase 4  Structural Assembly          stable prefix (cacheable) -> semi-stable -> volatile -> task

Run: python context_pipeline.py
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # swap for tiktoken / API token counting


# =============================================================================
# Phase 1: Ingestion & Intent Parsing
# =============================================================================
@dataclass
class ParsedRequest:
    raw: str
    query: str
    intents: list[str]
    entities: dict = field(default_factory=dict)


INTENT_RULES = {  # production: small LLM / classifier; rules keep the demo offline
    "claim_status": r"\b(status|where is|progress)\b.*\bclaim\b|\bclaim\b.*\b(status|progress)\b",
    "policy_question": r"\b(policy|coverage|covered|deductible|approval|approve)\b",
    "fraud_check": r"\b(fraud|suspicious|duplicate claim)\b",
}


def parse_request(raw: str) -> ParsedRequest:
    query = re.sub(r"\s+", " ", raw).strip()
    intents = [name for name, pat in INTENT_RULES.items()
               if re.search(pat, query, re.I)] or ["general"]
    entities = {}
    if m := re.search(r"\bCLM-\d+\b", query, re.I):
        entities["claim_id"] = m.group(0).upper()
    if m := re.search(r"\$\s?([\d,]+)(k?)", query, re.I):
        amt = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
        entities["amount"] = amt
    return ParsedRequest(raw, query, intents, entities)


# =============================================================================
# Phase 2: Dynamic Injection (Retrieval & Routing)
# =============================================================================
@dataclass
class Chunk:
    id: str
    source: str  # "kb" | "claims_db" | "memory"
    text: str
    score: float = 0.0


KB = [
    Chunk("kb-1", "kb", "Claims over $10,000 require senior adjuster approval."),
    Chunk("kb-2", "kb", "Claims over $10,000 require senior adjuster approval."),  # dup
    Chunk("kb-3", "kb", "Auto FNOL must include a police report number."),
    Chunk("kb-4", "kb", "Deductible for collision coverage is $500 by default."),
    Chunk("kb-5", "kb", "Office holiday schedule: closed on public holidays."),
]
CLAIMS_DB = {"CLM-1001": "CLM-1001: auto, $15,000, status=UNDER_REVIEW, adjuster=unassigned. " + "log " * 400}
MEMORY = ["User role: claims triage agent.", "User prefers concise answers."]

# Router: intent -> sources worth paying tokens for
ROUTES = {
    "claim_status": ["claims_db", "memory"],
    "policy_question": ["kb", "memory"],
    "fraud_check": ["claims_db", "kb"],
    "general": ["kb", "memory"],
}


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9$]+", s.lower())


def bm25_like(query: str, docs: list[Chunk]) -> None:
    """Tiny TF-IDF scorer. Production: embeddings + vector DB (Qdrant/Pinecone) + reranker."""
    n = len(docs)
    df = Counter(t for d in docs for t in set(_tokens(d.text)))
    q = _tokens(query)
    for d in docs:
        tf = Counter(_tokens(d.text))
        d.score = sum(tf[t] * math.log(1 + n / df[t]) for t in q if t in tf) / (1 + len(tf) ** 0.5)


def retrieve(req: ParsedRequest) -> list[Chunk]:
    sources = sorted({s for i in req.intents for s in ROUTES[i]})  # union across intents
    out: list[Chunk] = []
    if "kb" in sources:
        pool = [Chunk(c.id, c.source, c.text) for c in KB]
        bm25_like(req.query, pool)
        out += pool
    if "claims_db" in sources and (cid := req.entities.get("claim_id")) in CLAIMS_DB:
        out.append(Chunk(cid, "claims_db", CLAIMS_DB[cid], score=99.0))  # exact lookup => top
    if "memory" in sources:
        out += [Chunk(f"mem-{i}", "memory", m, score=1.0) for i, m in enumerate(MEMORY)]
    return out


# =============================================================================
# Phase 3: Pruning & Compression (garbage collection)
# =============================================================================
@dataclass
class Turn:
    role: str
    content: str


def prune_chunks(chunks: list[Chunk], min_score: float = 0.3,
                 max_chunk_tokens: int = 120) -> list[Chunk]:
    seen, kept = set(), []
    for c in sorted(chunks, key=lambda c: c.score, reverse=True):
        key = re.sub(r"\W+", " ", c.text.lower()).strip()
        if key in seen or c.score < min_score:  # dedup + relevance floor
            continue
        seen.add(key)
        if count_tokens(c.text) > max_chunk_tokens:  # truncate bulky tool/db output
            c = Chunk(c.id, c.source, c.text[: max_chunk_tokens * 4] + " ...[truncated]", c.score)
        kept.append(c)
    return kept


def compress_history(turns: list[Turn], keep_recent: int = 2) -> tuple[str, list[Turn]]:
    """Old turns -> one summary line. Production: cheap LLM summarizer."""
    older, recent = turns[:-keep_recent], turns[-keep_recent:]
    summary = ""
    if older:
        summary = "Earlier: " + " | ".join(f"{t.role}: {t.content[:50]}" for t in older)
    return summary, recent


def fit_budget(chunks: list[Chunk], budget: int) -> list[Chunk]:
    kept, used = [], 0
    for c in chunks:  # already sorted by score
        cost = count_tokens(c.text)
        if used + cost <= budget:
            kept.append(c)
            used += cost
    return kept


# =============================================================================
# Phase 4: Structural Assembly (cache optimization)
# =============================================================================
SYSTEM_PROMPT = (
    "You are an insurance claims assistant. Answer ONLY from <context>. "
    "If the answer is not in <context>, say you don't know. Cite chunk ids."
)
TOOL_DEFS = "tools: lookup_claim(claim_id), escalate(claim_id, reason)"  # static => cacheable


def assemble(req: ParsedRequest, chunks: list[Chunk], summary: str, recent: list[Turn]) -> dict:
    """Ordering = cache strategy. Prefix must be byte-identical across calls to hit the cache.

      [1] system + tool defs   static     <- cache breakpoint A
      [2] memory / user profile slow      <- cache breakpoint B
      [3] retrieved context    volatile   (changes per query)
      [4] history + task       volatile   (task LAST: models weight the end most)
    """
    mem = [c for c in chunks if c.source == "memory"]
    ctx = [c for c in chunks if c.source != "memory"]
    fmt = lambda cs: "\n".join(f'<chunk id="{c.id}" src="{c.source}">{c.text}</chunk>' for c in cs)
    hist = (f"<summary>{summary}</summary>\n" if summary else "") + \
           "\n".join(f'<turn role="{t.role}">{t.content}</turn>' for t in recent)

    blocks = [  # Anthropic Messages API shape: system as blocks with cache_control
        {"type": "text", "text": SYSTEM_PROMPT + "\n" + TOOL_DEFS},
        {"type": "text", "text": f"<memory>\n{fmt(mem)}\n</memory>",
         "cache_control": {"type": "ephemeral"}},
    ]
    user = (f"<context>\n{fmt(ctx)}\n</context>\n\n<history>\n{hist}\n</history>\n\n"
            f"<intents>{req.intents}</intents> <entities>{req.entities}</entities>\n"
            f"<task>{req.query}</task>")
    return {"system": blocks, "messages": [{"role": "user", "content": user}]}


# =============================================================================
# Orchestration
# =============================================================================
def run_pipeline(raw: str, history: list[Turn], budget: int = 900) -> dict:
    req = parse_request(raw)                                        # Phase 1
    print(f"[P1] intents={req.intents} entities={req.entities}")

    chunks = retrieve(req)                                          # Phase 2
    print(f"[P2] route={sorted({s for i in req.intents for s in ROUTES[i]})} retrieved={len(chunks)}")

    pruned = prune_chunks(chunks)                                   # Phase 3
    pruned = fit_budget(pruned, budget // 2)
    summary, recent = compress_history(history)
    print(f"[P3] chunks {len(chunks)} -> {len(pruned)}; history {len(history)} -> "
          f"{len(recent)} turns + summary")

    payload = assemble(req, pruned, summary, recent)                # Phase 4
    total = sum(count_tokens(b["text"]) for b in payload["system"]) + \
        count_tokens(payload["messages"][0]["content"])
    print(f"[P4] assembled ~{total} tokens (budget {budget}); "
          f"cached prefix blocks={sum('cache_control' in b for b in payload['system'])}")
    return payload


if __name__ == "__main__":
    history = [Turn("user" if i % 2 == 0 else "assistant", f"earlier message {i} about claims")
               for i in range(6)]
    payload = run_pipeline(
        "Does claim CLM-1001 for $15k need extra approval?  What's its status?", history)

    print("\n--- SYSTEM BLOCKS ---")
    for b in payload["system"]:
        print(("[CACHE] " if "cache_control" in b else "") + b["text"], "\n")
    print("--- USER MESSAGE ---")
    print(payload["messages"][0]["content"])

    # Send to Claude (pip install anthropic; set ANTHROPIC_API_KEY):
    # import anthropic
    # resp = anthropic.Anthropic().messages.create(
    #     model="claude-sonnet-5-5", max_tokens=500, **payload)
    # print(resp.content[0].text, resp.usage)  # usage shows cache_read_input_tokens
