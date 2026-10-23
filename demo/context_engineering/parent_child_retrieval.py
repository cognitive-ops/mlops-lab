"""Hierarchical Chunking & Parent-Child Retrieval on Underwriting Guidelines.

  Guideline (markdown)
     |  split by headings
     v
  PARENT = whole section (breadcrumb + full text)   -> DocStore  (dict, id -> Parent)
     |  split by sentence/bullet, merge to ~40 words
     v
  CHILD  = short precise chunk, carries parent_id    -> VectorStore (embeddings)

  Query -> embed -> top-k CHILD hits -> map to parent_id -> dedupe, rank -> load full PARENTS
        -> Agent context.  Child = precision for search, Parent = context for the decision.

Why: the rating table row (child) is the best match for "stage 2 hypertension, 150/95",
but the clause that voids it ("uncontrolled readings -> postpone") lives in a different
sentence of the same section. Flat child retrieval misses it -> wrong decision.

Compares FLAT (children only) vs PARENT-CHILD on 3 cases. Metric: evidence recall = does the
context contain the clause the decision depends on. With OPENAI_API_KEY it also asks an LLM.

Embeddings: OpenAI text-embedding-3-small if OPENAI_API_KEY set, else an offline hashing
bag-of-words embedder (no deps) so the demo always runs.

Run: python parent_child_retrieval.py              # compare all cases
     python parent_child_retrieval.py --show-chunks  # print parent/child structure
     python parent_child_retrieval.py --offline      # force offline embedder, no LLM
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
from dataclasses import dataclass, field

# =============================================================================
# Source document (synthetic underwriting guideline)
# =============================================================================
GUIDELINE = """\
# Chapter 4. Cardiovascular Conditions

## 4.1 Hypertension
Scope: applies to applicants aged 18-65 with a diagnosis of essential hypertension. Secondary hypertension is referred to the Chief Medical Officer (CMO).
Rating table, based on the average of the last three readings: Stage 1 (130-139 / 80-89) is rated Standard. Stage 2 (140-159 / 90-99) is rated +75% extra mortality. Stage 3 (160 / 100 or higher) is declined.
The table above is valid ONLY when readings have been controlled below 140/90 for the last 12 months and the applicant is on no more than two antihypertensive drugs.
If the readings in the last 12 months exceeded 140/90 on two or more occasions, or three or more drugs are needed, the rating table is void: POSTPONE the case for 6 months and request a new cardiology report.
Any history of stroke or TIA overrides this section: DECLINE.

## 4.2 Coronary Artery Disease
Scope: applies to confirmed CAD, prior MI, stents or bypass surgery.
An MI within the last 12 months is declined. MI 1-5 years ago is rated +150%. MI more than 5 years ago with a normal stress test is rated +100%.
Stents placed within 6 months are postponed. Stents older than 6 months follow the MI table based on the original event date.

# Chapter 5. Metabolic Conditions

## 5.1 Type 2 Diabetes
Scope: this section applies ONLY to Type 2 diabetes without complications. If retinopathy, nephropathy, neuropathy or any vascular complication is present, do not use this table; refer to section 5.3.
Rating table by latest HbA1c: below 7.0 is rated +25%. 7.0 to 8.0 is rated +50%. Above 8.0 is postponed until HbA1c is below 8.0 for two consecutive tests.
Diagnosis before age 40 adds +25% to the table rating. Applicants on insulin are referred to the CMO.

## 5.2 Obesity
Scope: BMI-based rating for applicants without other metabolic conditions.
BMI below 30 is Standard. BMI 30 to 34.9 is rated +25%. BMI 35 to 39.9 is rated +50%. BMI 40 or above is rated +100%.
Obesity combined with hypertension or diabetes is not rated additively; refer to the CMO.

## 5.3 Diabetes with Complications
Diabetes with retinopathy, nephropathy, neuropathy or vascular complications is rated individually by the CMO. Do not apply the section 5.1 table. Typical outcome is decline for nephropathy with eGFR below 45.

# Chapter 6. Lifestyle and Disclosure

## 6.1 Tobacco Use
Scope: smoker status is determined by application answers and laboratory cotinine testing.
A positive cotinine test overrides a non-smoker declaration. Misrepresentation of smoker status is referred to Claims Fraud Review and the policy is issued, if at all, at smoker rates.
Cigar or pipe use at fewer than 12 per year without inhalation may be rated non-smoker.
Nicotine replacement therapy does not by itself indicate smoker status.
"""

# =============================================================================
# Parent / child chunking
# =============================================================================
@dataclass
class Parent:
    id: str
    chapter: str
    section: str
    text: str

    @property
    def breadcrumb(self) -> str:
        return f"{self.chapter} > {self.section}"

    def render(self) -> str:
        return f"[{self.breadcrumb}]\n{self.text}"


@dataclass
class Child:
    id: str
    parent_id: str
    text: str
    vec: list[float] = field(default_factory=list, repr=False)


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def split_parents(doc: str) -> list[Parent]:
    """Parent = one '##' section (a whole clause group), tagged with its '#' chapter."""
    parents: list[Parent] = []
    chapter, section, buf = "", "", []

    def flush():
        if section and buf:
            parents.append(Parent(f"P{len(parents) + 1:02d}", chapter, section, "\n".join(buf).strip()))

    for line in doc.splitlines():
        if line.startswith("# "):
            flush(); buf.clear(); section = ""; chapter = line[2:].strip()
        elif line.startswith("## "):
            flush(); buf.clear(); section = line[3:].strip()
        elif line.strip():
            buf.append(line.strip())
    flush()
    return parents


def split_children(parent: Parent, max_words: int = 25) -> list[Child]:
    """Child = sentence group of <= max_words. Small on purpose: sharp vectors."""
    sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+(?=[A-Z0-9(])", parent.text.replace("\n", " ")) if s.strip()]
    chunks, cur = [], []
    for s in sentences:
        if cur and sum(len(x.split()) for x in cur) + len(s.split()) > max_words:
            chunks.append(" ".join(cur)); cur = []
        cur.append(s)
    if cur:
        chunks.append(" ".join(cur))
    return [Child(f"{parent.id}-c{i + 1}", parent.id, c) for i, c in enumerate(chunks)]


# =============================================================================
# Embedders
# =============================================================================
STOP = set("the a an of to in on for and or is are be by with as at from that this it its if any not no".split())


class HashEmbedder:
    """Offline bag-of-words(+bigram) hashing embedder. Good enough lexical retrieval, zero deps."""
    name = "offline-hash"
    dim = 512

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            toks = [w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", t.lower()) if w not in STOP]
            feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
            v = [0.0] * self.dim
            for f in feats:
                h = int(hashlib.md5(f.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


class OpenAIEmbedder:
    def __init__(self, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.client, self.name = OpenAI(), model

    def embed(self, texts: list[str]) -> list[list[float]]:
        r = self.client.embeddings.create(model=self.name, input=texts)
        out = []
        for d in r.data:
            n = math.sqrt(sum(x * x for x in d.embedding)) or 1.0
            out.append([x / n for x in d.embedding])
        return out


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# =============================================================================
# Stores + retriever
# =============================================================================
class DocStore:
    def __init__(self, parents: list[Parent]):
        self._d = {p.id: p for p in parents}

    def get(self, pid: str) -> Parent:
        return self._d[pid]


class VectorStore:
    def __init__(self, embedder, children: list[Child]):
        self.embedder, self.children = embedder, children
        for c, v in zip(children, embedder.embed([c.text for c in children])):
            c.vec = v

    def search(self, query: str, k: int) -> list[tuple[float, Child]]:
        q = self.embedder.embed([query])[0]
        return sorted(((cosine(q, c.vec), c) for c in self.children), key=lambda x: -x[0])[:k]


class ParentChildRetriever:
    def __init__(self, vstore: VectorStore, dstore: DocStore):
        self.v, self.d = vstore, dstore

    def flat(self, query: str, k: int = 3) -> tuple[str, list[str]]:
        """Baseline: return the child chunks themselves."""
        hits = self.v.search(query, k)
        return "\n".join(f"- {c.text}" for _, c in hits), [c.id for _, c in hits]

    def parent_child(self, query: str, k: int = 3, max_parents: int = 1) -> tuple[str, list[str]]:
        """Search children, load their PARENTS (deduped, ranked by best child score)."""
        best: dict[str, float] = {}
        for s, c in self.v.search(query, k):
            best[c.parent_id] = max(best.get(c.parent_id, -1), s)
        pids = [p for p, _ in sorted(best.items(), key=lambda x: -x[1])][:max_parents]
        return "\n\n".join(self.d.get(p).render() for p in pids), pids


# =============================================================================
# Test cases: the decision depends on evidence NOT in the best-matching child
# =============================================================================
CASES = [
    {
        "q": "Applicant 45 with stage 2 hypertension, BP 150/95, currently taking three BP drugs. What rating do we give?",
        "evidence": "POSTPONE",          # voiding clause lives in a different sentence of 4.1
        "decision": "postpone",
    },
    {
        "q": "Type 2 diabetic, diagnosed at age 38, latest HbA1c 7.4. What total extra rating?",
        "evidence": "adds +25%",         # age-at-diagnosis modifier sits in a different child than the table row
        "decision": "75",                 # +50% table + 25% modifier
    },
    {
        "q": "Applicant declared non-smoker but lab cotinine is positive. What are all the required actions on this case?",
        "evidence": "Claims Fraud Review",
        "decision": "fraud",
    },
]

ANSWER_SYS = ("You are an underwriting assistant. Decide using ONLY the CONTEXT. Quote the clause "
              "(section number) that drives the decision. If the context is insufficient, say so.")


def ask_llm(question: str, context: str) -> str:
    from openai import OpenAI
    r = OpenAI().chat.completions.create(
        model=os.getenv("AGENT_MODEL", "gpt-4o-mini"), temperature=0, max_tokens=250,
        messages=[{"role": "system", "content": ANSWER_SYS},
                  {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"}])
    return (r.choices[0].message.content or "").strip()


# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-chunks", action="store_true")
    ap.add_argument("--offline", action="store_true", help="offline embedder, no LLM")
    ap.add_argument("--k", type=int, default=3, help="child hits searched (parent-child)")
    ap.add_argument("--flat-k", type=int, default=1, help="child chunks returned by the flat baseline")
    ap.add_argument("--max-parents", type=int, default=1, help="parents loaded into context")
    ap.add_argument("--child-words", type=int, default=25)
    a = ap.parse_args()

    use_openai = bool(os.getenv("OPENAI_API_KEY")) and not a.offline
    embedder = OpenAIEmbedder() if use_openai else HashEmbedder()

    parents = split_parents(GUIDELINE)
    children = [c for p in parents for c in split_children(p, a.child_words)]
    print(f"embedder={embedder.name}  parents={len(parents)}  children={len(children)}  "
          f"avg parent={sum(count_tokens(p.text) for p in parents) // len(parents)}t  "
          f"avg child={sum(count_tokens(c.text) for c in children) // len(children)}t")

    if a.show_chunks:
        for p in parents:
            print(f"\n{p.id} {p.breadcrumb}  ({count_tokens(p.text)}t)")
            for c in (c for c in children if c.parent_id == p.id):
                print(f"   {c.id}: {c.text}")

    retr = ParentChildRetriever(VectorStore(embedder, children), DocStore(parents))

    summary = []
    for i, case in enumerate(CASES, 1):
        print(f"\n{'=' * 78}\nQ{i}: {case['q']}")
        row = {}
        for mode, fn in (("FLAT (children only)", retr.flat), ("PARENT-CHILD", retr.parent_child)):
            ctx, ids = (fn(case["q"], a.flat_k) if mode.startswith("FLAT")
                        else fn(case["q"], a.k, a.max_parents))
            ok = case["evidence"].lower() in ctx.lower()
            row[mode] = (ok, count_tokens(ctx))
            print(f"\n--- {mode}: hits={ids} context={count_tokens(ctx)}t evidence_in_context={ok}")
            if mode == "PARENT-CHILD" or not ok:
                print(ctx if len(ctx) < 900 else ctx[:900] + "...")
            if use_openai:
                ans = ask_llm(case["q"], ctx)
                print(f"LLM> {ans}")
                row[mode] += (case["decision"].lower() in ans.lower(),)
        summary.append(row)

    print(f"\n{'=' * 78}\nSUMMARY  (evidence recall = clause needed for the decision is in context)")
    for mode in ("FLAT (children only)", "PARENT-CHILD"):
        rec = sum(r[mode][0] for r in summary)
        toks = sum(r[mode][1] for r in summary) // len(summary)
        line = f"{mode:22} evidence recall {rec}/{len(CASES)}   avg context {toks}t"
        if use_openai:
            line += f"   correct decision {sum(r[mode][2] for r in summary)}/{len(CASES)}"
        print(line)


if __name__ == "__main__":
    main()
