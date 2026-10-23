"""Semantic Chunking vs Fixed-size vs Sentence-packing, measured.

  Underwriting handbook text (topics glued together, no headings)
     |
     +-- FIXED      every N chars (cuts mid-sentence, topic-blind)
     +-- SENTENCE   pack whole sentences up to N chars (topic-blind)
     +-- SEMANTIC   embed sentences -> cosine distance between neighbours ->
                    cut where distance spikes (percentile breakpoint) -> topic-aware

Ground truth: each sentence is labelled with its topic, so we can score:
  boundary F1     did cuts land on real topic changes?
  mid-sentence    cuts that sliced a sentence in half
  purity          % chunks containing a single topic
  retrieval top-1 question -> best chunk by embedding; hit if it has the answer sentence
                  AND is not polluted with other topics (pure)

Embeddings: OpenAI text-embedding-3-small if OPENAI_API_KEY is set, else offline hashing
bag-of-words (lexical, zero deps). Real embeddings capture meaning; offline is a rough stand-in.

Run: python semantic_chunking_demo.py              # compare + metrics
     python semantic_chunking_demo.py --plot       # ASCII distance curve with breakpoints
     python semantic_chunking_demo.py --show semantic
     python semantic_chunking_demo.py --offline --percentile 80
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import re

# =============================================================================
# Ground-truth corpus: (topic, sentences). Joined into ONE flat text on purpose.
# =============================================================================
CORPUS = [
    ("hypertension", [
        "Hypertension is rated by the average of the last three blood pressure readings.",
        "Stage 2 hypertension, 140-159 over 90-99, carries a 75 percent extra mortality rating.",
        "The rating table is void if readings exceeded 140/90 more than twice in twelve months.",
        "Applicants needing three or more antihypertensive drugs are postponed for six months.",
        "A history of stroke or transient ischemic attack overrides the blood pressure table.",
    ]),
    ("diabetes", [
        "Type 2 diabetes is rated from the latest HbA1c glycated hemoglobin result.",
        "An HbA1c from 7.0 to 8.0 percent adds 50 percent extra mortality.",
        "Diagnosis before age forty adds a further 25 percent to the diabetes rating.",
        "Diabetic retinopathy or nephropathy moves the case to the chief medical officer.",
        "Insulin dependent applicants are never rated from the standard glucose table.",
    ]),
    ("tobacco", [
        "Smoker status is established from the application and a laboratory cotinine test.",
        "A positive cotinine result overrides a non-smoker declaration on the form.",
        "Misrepresenting nicotine use is referred to claims fraud review.",
        "Occasional cigar use below twelve per year without inhalation may be rated non-smoker.",
    ]),
    ("claims_process", [
        "A claim must be reported to the insurer within thirty days of the insured event.",
        "The claimant submits the claim form, a death certificate and the policy schedule.",
        "Payment is released after the contestability review is complete.",
        "Beneficiary disputes are held in escrow until a court order is received.",
        "Late claim notices are accepted only with a documented reason for the delay.",
    ]),
    ("hypertension", [  # topic returns later in the doc: semantic search should still link it
        "Home blood pressure logs may support a lower rating if taken on validated devices.",
        "Isolated white coat readings are discounted when twenty four hour monitoring is normal.",
        "Beta blocker therapy alone is accepted for stage one hypertension at standard rates.",
    ]),
]

QUESTIONS = [  # (question, topic, keyword the correct chunk must contain)
    ("What happens if the rating table for blood pressure is void?", "hypertension", "postponed"),
    ("How much does an HbA1c of 7.5 add to the rating?", "diabetes", "50 percent"),
    ("The lab cotinine is positive but the applicant says non-smoker.", "tobacco", "cotinine result overrides"),
    ("Within how many days must a claim be reported?", "claims_process", "thirty days"),
    ("Are home blood pressure logs accepted?", "hypertension", "Home blood pressure"),
]


def build_text() -> tuple[str, list[str], list[str]]:
    sents, topics = [], []
    for topic, ss in CORPUS:
        sents += ss
        topics += [topic] * len(ss)
    return " ".join(sents), sents, topics


# =============================================================================
# Embedders
# =============================================================================
STOP = set("the a an of to in on for and or is are be by with as at from that this it its if any not no than".split())


class HashEmbedder:
    name, dim = "offline-hash", 512

    def embed(self, texts):
        out = []
        for t in texts:
            toks = [w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP]
            v = [0.0] * self.dim
            for f in toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]:
                v[int(hashlib.md5(f.encode()).hexdigest(), 16) % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


class OpenAIEmbedder:
    def __init__(self, model="text-embedding-3-small"):
        from openai import OpenAI
        self.client, self.name = OpenAI(), model

    def embed(self, texts):
        out = []
        for i in range(0, len(texts), 256):
            r = self.client.embeddings.create(model=self.name, input=texts[i:i + 256])
            for d in r.data:
                n = math.sqrt(sum(x * x for x in d.embedding)) or 1.0
                out.append([x / n for x in d.embedding])
        return out


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


# =============================================================================
# Chunkers. Each returns list of (start_char, end_char) spans over the flat text.
# =============================================================================
def sentence_spans(text: str, sents: list[str]) -> list[tuple[int, int]]:
    spans, pos = [], 0
    for s in sents:
        i = text.index(s, pos)
        spans.append((i, i + len(s)))
        pos = i + len(s)
    return spans


def chunk_fixed(text: str, size: int) -> list[tuple[int, int]]:
    return [(i, min(i + size, len(text))) for i in range(0, len(text), size)]


def chunk_sentence_pack(text: str, spans: list[tuple[int, int]], size: int) -> list[tuple[int, int]]:
    chunks, start = [], spans[0][0]
    for (a, b) in spans:
        if b - start > size and a > start:
            chunks.append((start, prev_end))
            start = a
        prev_end = b
    chunks.append((start, spans[-1][1]))
    return chunks


def distances(embedder, sents: list[str], window: int = 2) -> list[float]:
    """Distance at gap i|i+1 = cosine distance between the `window` sentences LEFT of the gap and
    the `window` sentences RIGHT of it (non-overlapping), so a topic change shows as a sharp peak
    and single short sentences do not make the curve noisy."""
    n = len(sents)
    left = [" ".join(sents[max(0, i - window + 1): i + 1]) for i in range(n - 1)]
    right = [" ".join(sents[i + 1: i + 1 + window]) for i in range(n - 1)]
    vecs = embedder.embed(left + right)
    return [1 - cos(vecs[i], vecs[n - 1 + i]) for i in range(n - 1)]


def percentile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    return s[f] + (s[c] - s[f]) * (k - f)


def chunk_semantic(embedder, sents, spans, pct: float, min_sents: int = 2, max_chars: int = 900,
                   window: int = 2):
    d = distances(embedder, sents, window)
    thr = percentile(d, pct)
    cuts, last = [], 0                       # cut AFTER sentence i if d[i] > thr
    for i, dist in enumerate(d):
        n_since = i + 1 - last
        size = spans[i][1] - spans[last][0]
        peak = dist >= max(d[max(0, i - 1): i + 2])      # local maximum: one cut per topic change
        if (dist > thr and peak and n_since >= min_sents) or size > max_chars:
            cuts.append(i + 1)
            last = i + 1
    bounds = [0] + cuts + [len(sents)]
    return [(spans[a][0], spans[b - 1][1]) for a, b in zip(bounds, bounds[1:])], d, thr


# =============================================================================
# Metrics
# =============================================================================
def chunk_sentence_ids(chunk, spans):
    a, b = chunk
    return [i for i, (s, e) in enumerate(spans) if s < b and e > a]


def evaluate(name, chunks, text, spans, topics, embedder):
    # boundaries = sentence index where a new chunk starts (nearest sentence for mid-sentence cuts)
    true_b = {i for i in range(1, len(topics)) if topics[i] != topics[i - 1]}
    pred_b, mid = set(), 0
    for (a, _) in chunks[1:]:
        sid = [i for i, (s, e) in enumerate(spans) if s <= a < e]
        i = sid[0] if sid else min(range(len(spans)), key=lambda j: abs(spans[j][0] - a))
        if sid and a != spans[i][0]:
            mid += 1                          # cut inside a sentence
            i += 1
        pred_b.add(i)
    tp = len(true_b & pred_b)
    prec = tp / len(pred_b) if pred_b else 0
    rec = tp / len(true_b) if true_b else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0

    pure = sum(len({topics[i] for i in chunk_sentence_ids(c, spans)}) == 1 for c in chunks)

    # retrieval: top-1 chunk must contain the answer AND be single-topic
    ctexts = [text[a:b] for a, b in chunks]
    cvecs = embedder.embed(ctexts)
    qvecs = embedder.embed([q for q, _, _ in QUESTIONS])
    hits = 0
    for (q, topic, kw), qv in zip(QUESTIONS, qvecs):
        j = max(range(len(chunks)), key=lambda x: cos(qv, cvecs[x]))
        ids = chunk_sentence_ids(chunks[j], spans)
        if kw.lower() in ctexts[j].lower() and {topics[i] for i in ids} == {topic}:
            hits += 1
    return {"name": name, "n": len(chunks), "avg_chars": sum(b - a for a, b in chunks) // len(chunks),
            "f1": f1, "prec": prec, "rec": rec, "mid": mid, "purity": pure / len(chunks), "hit": hits}


def ascii_plot(d, thr, topics):
    print(f"\nadjacent-sentence cosine distance  (threshold p-cut = {thr:.3f};  | = true topic change, # = cut)")
    mx = max(d) or 1
    for i, v in enumerate(d):
        tru = "|" if topics[i] != topics[i + 1] else " "
        cut = "#" if v > thr else " "
        print(f"{i + 1:>3}->{i + 2:<3}{tru}{cut} {'█' * int(40 * v / mx)} {v:.2f}")


# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--percentile", type=float, default=70, help="breakpoint percentile (lower = more cuts)")
    ap.add_argument("--size", type=int, default=0, help="fixed/sentence chunk chars (default: avg true segment)")
    ap.add_argument("--window", type=int, default=2, help="sentences per side when comparing a gap")
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--show", choices=["fixed", "sentence", "semantic"])
    a = ap.parse_args()

    embedder = OpenAIEmbedder() if os.getenv("OPENAI_API_KEY") and not a.offline else HashEmbedder()
    text, sents, topics = build_text()
    spans = sentence_spans(text, sents)
    size = a.size or len(text) // len(CORPUS)
    n_true = len([i for i in range(1, len(topics)) if topics[i] != topics[i - 1]])
    print(f"embedder={embedder.name}  sentences={len(sents)}  chars={len(text)}  "
          f"true topic boundaries={n_true}  baseline chunk size={size} chars")

    sem, d, thr = chunk_semantic(embedder, sents, spans, a.percentile, window=a.window)
    results = {
        "fixed": chunk_fixed(text, size),
        "sentence": chunk_sentence_pack(text, spans, size),
        "semantic": sem,
    }
    rows = [evaluate(k, v, text, spans, topics, embedder) for k, v in results.items()]

    if a.plot:
        ascii_plot(d, thr, topics)
    if a.show:
        print(f"\n--- {a.show} chunks ---")
        for i, (s, e) in enumerate(results[a.show], 1):
            ids = chunk_sentence_ids((s, e), spans)
            print(f"[{i}] topics={sorted({topics[j] for j in ids})} ({e - s} chars)\n    {text[s:e]}\n")

    print(f"\n{'chunker':10} {'chunks':>6} {'avg':>5} {'bndF1':>6} {'prec':>5} {'rec':>5} "
          f"{'midcut':>6} {'purity':>7} {'top1 hit':>9}")
    for r in rows:
        print(f"{r['name']:10} {r['n']:>6} {r['avg_chars']:>5} {r['f1']:>6.2f} {r['prec']:>5.2f} {r['rec']:>5.2f} "
              f"{r['mid']:>6} {r['purity']:>6.0%} {r['hit']:>6}/{len(QUESTIONS)}")


if __name__ == "__main__":
    main()
