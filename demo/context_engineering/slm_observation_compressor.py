"""LLM middleware (OpenAI cheap model): compress a 10,000-line core-system JSON into a ~200-word Markdown list
BEFORE it enters the main agent's working memory (scratchpad pruning with a cheap OpenAI model).

  Core System (MIB + Rx, ~10k lines JSON)
        |
        v   Stage 0  deterministic   drop noise keys / nulls / long blobs, 1 record = 1 line
        v   Stage 1  SLM  (map)      per chunk: keep ONLY task-relevant facts as bullets
        v   Stage 2  SLM  (reduce)   merge + dedupe -> <= 200 words, Markdown list
        v
  Main Agent working memory  (~300 tokens instead of ~100k+)

Why map-reduce: 10k pretty-printed lines is >70k tokens; cheap models do better on small chunks.

Compressor = OpenAI API (cheap tier, default gpt-4o-mini). No self-hosting needed.

Env:
  OPENAI_API_KEY   required (unless --dry-run)
  SLM_MODEL        compressor model, default gpt-4o-mini
  SLM_BASE_URL     optional, any OpenAI-compatible endpoint
  AGENT_MODEL      main agent model, default gpt-4o

Run:
  pip install openai
  python slm_observation_compressor.py --dry-run     # payload + stage 0 stats, no LLM
  python slm_observation_compressor.py               # full pipeline + main agent answer
  python slm_observation_compressor.py --skip-agent  # compression only
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

log = logging.getLogger("slm_compress")


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # swap for tiktoken / HF tokenizer


# =============================================================================
# Synthetic core-system payload (MIB = medical info bureau, Rx = prescription history)
# =============================================================================
TASK = ("Underwriting risk review for member M-1001: list risk-relevant diagnoses, "
        "MIB flags, and ACTIVE prescriptions. Ignore routine/normal records.")

# planted facts the compressed memory MUST keep (id/keyword checked case-insensitively)
NEEDLES = ["MIB-0037", "MIB-0091", "MIB-0126", "RX-0078", "RX-0114", "warfarin", "cotinine"]


def _meta(rng: random.Random, i: int) -> dict:
    """Junk that real core systems attach to every record."""
    return {
        "request_id": f"req-{rng.getrandbits(64):016x}",
        "etag": f"W/\"{rng.getrandbits(96):024x}\"",
        "audit_log": [{"ts": f"2024-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}T0{rng.randint(0, 9)}:11:02Z",
                       "actor": f"svc-{rng.choice(['ingest', 'sync', 'etl'])}-{rng.randint(1, 9)}",
                       "op": rng.choice(["READ", "UPSERT", "REPLICATE"])} for _ in range(3)],
        "_links": {"self": f"/core/v3/records/{i}", "member": "/core/v3/members/M-1001"},
        "trace": {"span": f"{rng.getrandbits(48):012x}", "host": f"core-{rng.randint(1, 40)}.internal"},
        "raw_hl7": "MSH|^~\\&|CORE|HOSP|" + "x" * 90,
    }


def generate_payload(n_each: int = 140, seed: int = 7) -> dict:
    rng = random.Random(seed)
    routine_dx = ["Routine physical exam", "Seasonal allergic rhinitis", "Acute pharyngitis, resolved",
                  "Annual flu vaccination", "Lipid panel within normal limits", "Dental cleaning"]
    routine_rx = ["amoxicillin", "cetirizine", "ibuprofen", "vitamin D3", "omeprazole", "loratadine"]

    mib = [{"record_id": f"MIB-{i:04d}", "date": f"20{rng.randint(15, 24)}-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}",
            "code": f"Z{rng.randint(10, 99)}.{rng.randint(0, 9)}", "description": rng.choice(routine_dx),
            "severity": "none", "flag": None, "source": "claims", **_meta(rng, i)} for i in range(n_each)]
    rx = [{"fill_id": f"RX-{i:04d}", "date_filled": f"20{rng.randint(15, 24)}-0{rng.randint(1, 9)}-0{rng.randint(1, 9)}",
           "drug": rng.choice(routine_rx), "days_supply": rng.choice([7, 10, 30]), "status": "completed",
           "pharmacy": f"PH-{rng.randint(100, 999)}", **_meta(rng, i)} for i in range(n_each)]

    # needles
    mib[37].update(description="Essential hypertension, stage 2", code="I10", severity="high",
                    flag="RISK_CARDIO", date="2023-05-12")
    mib[91].update(description="Type 2 diabetes mellitus without complications", code="E11.9",
                    severity="moderate", flag="RISK_METABOLIC", date="2022-11-03")
    mib[126].update(description="Lab: cotinine positive (tobacco use) vs application 'non-smoker'",
                             code="R82.998", severity="high", flag="MISREP_SMOKER", date="2024-02-19")
    rx[78].update(drug="warfarin 5mg", status="active", days_supply=30, date_filled="2024-08-02")
    rx[114].update(drug="metformin 1000mg", status="active", days_supply=30, date_filled="2024-08-09")

    return {
        "envelope": {"api_version": "v3", "generated_at": "2024-08-20T03:00:00Z",
                     "pagination": {"page": 1, "pages": 1, "total": 2 * n_each}, "debug": {"node": "core-17"}},
        "member": {"id": "M-1001", "dob": "1979-03-02", "sex": "M"},
        "mib": {"records": mib},
        "rx": {"fills": rx},
    }


# =============================================================================
# Stage 0: deterministic pre-compaction (cheap, lossless w.r.t. useful fields)
# =============================================================================
NOISE_KEY = re.compile(r"^(_links|links|audit_log|trace|etag|request_id|raw_.*|debug|pagination|"
                       r"envelope|checksum|schema.*|internal_.*|vendor_.*)$", re.I)


def _clean(v, max_str: int = 160):
    if isinstance(v, dict):
        out = {k: _clean(x) for k, x in v.items() if not NOISE_KEY.match(k)}
        return {k: x for k, x in out.items() if x not in (None, "", [], {})}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, str) and len(v) > max_str:
        return v[:max_str] + "..."
    return v


def to_lines(data, path: str = "") -> list[str]:
    """Flatten into one compact line per record: 'path | {json}'."""
    lines: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if NOISE_KEY.match(k):
                continue
            lines += to_lines(v, f"{path}.{k}" if path else k)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{path} | {json.dumps(_clean(item), separators=(',', ':'))}")
            else:
                lines.append(f"{path} | {item}")
    elif data not in (None, ""):
        lines.append(f"{path} = {data}")
    return lines


def chunk_lines(lines: list[str], max_tokens: int) -> list[str]:
    chunks, cur, cur_t = [], [], 0
    for ln in lines:
        t = count_tokens(ln)
        if cur and cur_t + t > max_tokens:
            chunks.append("\n".join(cur))
            cur, cur_t = [], 0
        cur.append(ln)
        cur_t += t
    if cur:
        chunks.append("\n".join(cur))
    return chunks


# =============================================================================
# LLM client (OpenAI-compatible: vLLM / SGLang / Ollama / OpenAI)
# =============================================================================
class ChatLLM:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=api_key or os.getenv("OPENAI_API_KEY"), timeout=120)
        self.model = model
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        r = self.client.chat.completions.create(
            model=self.model, temperature=0, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        if r.usage:
            self.prompt_tokens += r.usage.prompt_tokens
            self.completion_tokens += r.usage.completion_tokens
        return (r.choices[0].message.content or "").strip()


MAP_SYS = ("You are a data-compression filter between a core system and an AI agent. "
           "From the records, extract ONLY facts relevant to the TASK as Markdown bullets: "
           "`- <fact> [record id, date, code]`. Skip routine/normal/completed/irrelevant records entirely. "
           "Never invent facts. Keep exact ids. If nothing is relevant reply exactly: NONE")
REDUCE_SYS = ("Merge these bullet lists into ONE Markdown list for an AI agent's working memory. "
              "Deduplicate, group under at most 3 bold headings (Diagnoses / MIB flags / Active Rx), "
              "keep every record id, date and code. HARD LIMIT: {limit} words. Output only the list.")


@dataclass
class CompressResult:
    markdown: str
    raw_tokens: int
    stage0_tokens: int
    out_tokens: int
    chunks: int
    seconds: float
    slm_prompt_tokens: int = 0
    slm_completion_tokens: int = 0
    notes: list[str] = field(default_factory=list)


class SLMCompressor:
    def __init__(self, slm: ChatLLM, chunk_tokens: int = 5000, word_limit: int = 200, workers: int = 4):
        self.slm, self.chunk_tokens, self.word_limit, self.workers = slm, chunk_tokens, word_limit, workers

    def compress(self, raw_json: str, task: str) -> CompressResult:
        t0 = time.perf_counter()
        lines = to_lines(json.loads(raw_json))
        stage0 = "\n".join(lines)
        chunks = chunk_lines(lines, self.chunk_tokens)
        log.info("stage0: %d lines, %d tokens -> %d chunks", len(lines), count_tokens(stage0), len(chunks))

        def map_one(i_c):
            i, c = i_c
            out = self.slm.chat(MAP_SYS, f"TASK: {task}\n\nRECORDS:\n{c}", max_tokens=500)
            log.info("map %d/%d -> %d tokens", i + 1, len(chunks), count_tokens(out))
            return out

        with ThreadPoolExecutor(self.workers) as ex:
            partial = [p for p in ex.map(map_one, enumerate(chunks)) if p.strip().upper() != "NONE"]

        notes: list[str] = []
        if not partial:
            md = "- (no task-relevant facts found)"
        else:
            md = self._reduce(partial, task, notes)

        return CompressResult(
            markdown=md, raw_tokens=count_tokens(raw_json), stage0_tokens=count_tokens(stage0),
            out_tokens=count_tokens(md), chunks=len(chunks), seconds=time.perf_counter() - t0,
            slm_prompt_tokens=self.slm.prompt_tokens, slm_completion_tokens=self.slm.completion_tokens,
            notes=notes)

    def _reduce(self, partial: list[str], task: str, notes: list[str]) -> str:
        merged = "\n".join(partial)
        sys_p = REDUCE_SYS.format(limit=self.word_limit)
        md = self.slm.chat(sys_p, f"TASK: {task}\n\nBULLETS:\n{merged}", max_tokens=450)
        if len(md.split()) > self.word_limit * 1.2:  # one corrective retry, then hard-trim
            notes.append(f"reduce over limit ({len(md.split())} words) -> retry")
            md = self.slm.chat(sys_p + " You were too long. Cut harder.", f"TASK: {task}\n\nBULLETS:\n{md}",
                               max_tokens=450)
        if len(md.split()) > self.word_limit * 1.5:
            notes.append("hard-trimmed by bullet")
            keep, words = [], 0
            for ln in md.splitlines():
                words += len(ln.split())
                if words > self.word_limit:
                    break
                keep.append(ln)
            md = "\n".join(keep)
        return md


# =============================================================================
# Main agent: sees ONLY the compressed working memory
# =============================================================================
AGENT_SYS = ("You are an underwriting assistant. Answer using ONLY the WORKING MEMORY. "
             "Cite record ids. If memory lacks the answer, say so.")


def main_agent_answer(llm: ChatLLM, memory_md: str, question: str) -> str:
    return llm.chat(AGENT_SYS, f"WORKING MEMORY:\n{memory_md}\n\nQUESTION: {question}", max_tokens=300)


def recall(text: str) -> tuple[int, list[str]]:
    missing = [n for n in NEEDLES if n.lower() not in text.lower()]
    return len(NEEDLES) - len(missing), missing


# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="payload + stage 0 only, no LLM calls")
    ap.add_argument("--skip-agent", action="store_true")
    ap.add_argument("--chunk-tokens", type=int, default=5000)
    ap.add_argument("--word-limit", type=int, default=200)
    ap.add_argument("--save", help="write raw payload JSON to this path")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="%(message)s")

    payload = generate_payload()
    raw = json.dumps(payload, indent=2)
    if a.save:
        open(a.save, "w", encoding="utf-8").write(raw)
    n_lines = raw.count("\n") + 1
    stage0_lines = to_lines(payload)
    print(f"raw payload   : {n_lines:,} lines, ~{count_tokens(raw):,} tokens")
    print(f"after stage 0 : {len(stage0_lines):,} lines, ~{count_tokens(chr(10).join(stage0_lines)):,} tokens")
    if a.dry_run:
        print("\nsample stage-0 line:\n ", stage0_lines[150][:300])
        return

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set (use --dry-run to skip LLM calls)")
    slm = ChatLLM(os.getenv("SLM_MODEL", "gpt-4o-mini"), os.getenv("SLM_BASE_URL"))
    res = SLMCompressor(slm, a.chunk_tokens, a.word_limit).compress(raw, TASK)

    print(f"\n=== compressed working memory ({len(res.markdown.split())} words) ===\n{res.markdown}\n")
    hit, missing = recall(res.markdown)
    print("=== metrics ===")
    print(f"tokens  raw -> stage0 -> SLM out : {res.raw_tokens:,} -> {res.stage0_tokens:,} -> {res.out_tokens:,} "
          f"({100 * (1 - res.out_tokens / res.raw_tokens):.1f}% smaller)")
    print(f"SLM calls                        : {res.chunks} map + 1 reduce, {res.seconds:.1f}s, "
          f"{res.slm_prompt_tokens:,} in / {res.slm_completion_tokens:,} out tokens")
    print(f"needle recall                    : {hit}/{len(NEEDLES)}" + (f"  MISSING {missing}" if missing else ""))
    for n in res.notes:
        print(f"note: {n}")

    if a.skip_agent:
        return
    agent = ChatLLM(os.getenv("AGENT_MODEL", "gpt-4o"))
    q = "Should this member be flagged for manual underwriting? List the evidence."
    ans = main_agent_answer(agent, res.markdown, q)
    print(f"\n=== main agent (sees {res.out_tokens} tokens of memory, not {res.raw_tokens:,}) ===\n{ans}")


if __name__ == "__main__":
    main()
