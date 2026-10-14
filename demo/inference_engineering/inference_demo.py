"""Inference Engineering demo. Dependency-free (stdlib only), offline, runnable.

Four core levers that make LLM serving fast/cheap, each simulated at toy scale:

  1. KV Cache              reuse past keys/values -> O(n) work per new token instead of O(n^2)
  2. Continuous Batching   refill finished slots every step vs wait for whole batch (static)
  3. Quantization          fp32 -> int8 weights: 4x less memory, small error
  4. Speculative Decoding  cheap draft proposes k tokens, big model verifies in one pass

Numbers are toy-scale; the *ratios* mirror what vLLM / TensorRT-LLM / llama.cpp exploit.

Run: python inference_demo.py
"""
from __future__ import annotations

import math
import random
import statistics
from collections import deque
from dataclasses import dataclass

random.seed(7)


def header(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


# =============================================================================
# 1. KV cache
# =============================================================================
def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    es = [math.exp(x - m) for x in xs]
    s = sum(es)
    return [e / s for e in es]


class ToyAttention:
    """Single-head attention with fixed random projections. Counts multiply-adds."""

    def __init__(self, d: int = 16):
        self.d = d
        rnd = lambda: [[random.gauss(0, 1 / math.sqrt(d)) for _ in range(d)] for _ in range(d)]
        self.wq, self.wk, self.wv = rnd(), rnd(), rnd()
        self.ops = 0

    def proj(self, w: list[list[float]], x: list[float]) -> list[float]:
        self.ops += self.d * self.d
        return [dot(row, x) for row in w]

    def attend(self, q, keys, values) -> list[float]:
        self.ops += 2 * len(keys) * self.d
        scores = softmax([dot(q, k) / math.sqrt(self.d) for k in keys])
        return [sum(s * v[i] for s, v in zip(scores, values)) for i in range(self.d)]

    def generate_no_cache(self, embeds: list[list[float]]) -> list[float]:
        """Every step re-projects K,V for the WHOLE prefix."""
        out = []
        for t in range(1, len(embeds) + 1):
            prefix = embeds[:t]
            ks = [self.proj(self.wk, e) for e in prefix]
            vs = [self.proj(self.wv, e) for e in prefix]
            out = self.attend(self.proj(self.wq, prefix[-1]), ks, vs)
        return out

    def generate_cached(self, embeds: list[list[float]]) -> list[float]:
        """K,V computed once per token, appended to cache."""
        kc, vc, out = [], [], []
        for e in embeds:
            kc.append(self.proj(self.wk, e))
            vc.append(self.proj(self.wv, e))
            out = self.attend(self.proj(self.wq, e), kc, vc)
        return out


def demo_kv_cache() -> None:
    header("1. KV CACHE  (same output, far fewer ops)")
    print(f"{'seq_len':>8} {'no-cache ops':>14} {'cached ops':>12} {'speedup':>9} {'same output':>12}")
    for n in (16, 64, 256):
        embeds = [[random.gauss(0, 1) for _ in range(16)] for _ in range(n)]
        a = ToyAttention()
        b = ToyAttention()
        b.wq, b.wk, b.wv = a.wq, a.wk, a.wv
        o1 = a.generate_no_cache(embeds)
        o2 = b.generate_cached(embeds)
        same = all(abs(x - y) < 1e-9 for x, y in zip(o1, o2))
        print(f"{n:>8} {a.ops:>14,} {b.ops:>12,} {a.ops / b.ops:>8.1f}x {str(same):>12}")
    print("Cost: cache memory grows with seq_len * layers * heads -> why PagedAttention exists.")


# =============================================================================
# 2. Static vs continuous batching
# =============================================================================
@dataclass
class Req:
    rid: int
    out_len: int  # tokens to generate


def static_batching(reqs: list[Req], slots: int) -> int:
    """Batch of `slots` runs until its LONGEST request finishes. Returns decode steps."""
    steps = 0
    for i in range(0, len(reqs), slots):
        steps += max(r.out_len for r in reqs[i:i + slots])
    return steps


def continuous_batching(reqs: list[Req], slots: int) -> int:
    """Finished request frees slot immediately; next waiting request joins next step."""
    waiting, running, steps = deque(reqs), [], 0
    while waiting or running:
        while waiting and len(running) < slots:
            running.append(waiting.popleft().out_len)
        steps += 1
        running = [r - 1 for r in running if r - 1 > 0]
    return steps


def demo_batching() -> None:
    header("2. CONTINUOUS BATCHING  (iteration-level scheduling)")
    slots = 8
    # chat-like: many short answers, a few long ones (heavy tail)
    reqs = [Req(i, random.choice([8, 12, 16, 24, 32, 256])) for i in range(64)]
    total_tokens = sum(r.out_len for r in reqs)
    s, c = static_batching(reqs, slots), continuous_batching(reqs, slots)
    print(f"requests={len(reqs)} slots={slots} total_tokens={total_tokens}")
    print(f"{'scheduler':<12} {'steps':>7} {'tokens/step':>12} {'GPU util':>9}")
    for name, steps in (("static", s), ("continuous", c)):
        tps = total_tokens / steps
        print(f"{name:<12} {steps:>7} {tps:>12.2f} {tps / slots:>8.0%}")
    print(f"Throughput gain: {s / c:.2f}x. Static wastes slots padding to the longest request.")


# =============================================================================
# 3. Quantization
# =============================================================================
def quantize_int8(w: list[float]) -> tuple[list[int], float]:
    scale = max(abs(x) for x in w) / 127 or 1.0  # symmetric, per-tensor
    return [max(-127, min(127, round(x / scale))) for x in w], scale


def demo_quantization() -> None:
    header("3. QUANTIZATION  (fp32 -> int8 weights)")
    n = 4096
    w = [random.gauss(0, 0.05) for _ in range(n)]
    x = [random.gauss(0, 1) for _ in range(n)]
    q, scale = quantize_int8(w)
    w_hat = [v * scale for v in q]

    exact = dot(w, x)
    approx = dot(w_hat, x)
    mse = statistics.fmean((a - b) ** 2 for a, b in zip(w, w_hat))
    fp32_b, int8_b = n * 4, n * 1 + 4  # +4 for the scale
    print(f"memory   fp32={fp32_b:,}B  int8={int8_b:,}B  -> {fp32_b / int8_b:.2f}x smaller")
    print(f"weight MSE={mse:.2e}")
    print(f"dot(w,x) exact={exact:.4f} int8={approx:.4f} rel.err={abs(exact - approx) / abs(exact):.3%}")
    # outliers hurt per-tensor scale -> motivation for per-channel / AWQ / GPTQ
    w_out = w[:-1] + [2.0]
    qo, so = quantize_int8(w_out)
    mse_o = statistics.fmean((a - b * so) ** 2 for a, b in zip(w_out, qo))
    print(f"with one outlier weight: MSE={mse_o:.2e} ({mse_o / mse:.0f}x worse) "
          "-> per-channel scales / AWQ / GPTQ")
    print("Decode is memory-bandwidth bound, so fewer bytes/weight ~ faster tokens.")


# =============================================================================
# 4. Speculative decoding
# =============================================================================
VOCAB = list(range(8))


def norm(p: list[float]) -> list[float]:
    s = sum(p)
    return [x / s for x in p]


def target_dist(ctx: tuple[int, ...]) -> list[float]:
    """Deterministic pseudo-distribution depending on last token (the 'big model')."""
    r = random.Random(1000 + ctx[-1])
    return norm([r.random() ** 2 + 0.02 for _ in VOCAB])


def draft_dist(ctx: tuple[int, ...]) -> list[float]:
    """Noisy approximation of target (the 'small model')."""
    t = target_dist(ctx)
    r = random.Random(2000 + ctx[-1])
    return norm([p * (0.6 + 0.8 * r.random()) for p in t])


def sample(p: list[float]) -> int:
    return random.choices(VOCAB, weights=p)[0]


def spec_step(ctx: list[int], k: int) -> tuple[list[int], int]:
    """One round: draft k tokens, target scores all positions in ONE call, accept/reject."""
    drafted, dists, c = [], [], tuple(ctx)
    for _ in range(k):
        q = draft_dist(c)
        t = sample(q)
        drafted.append(t)
        dists.append(q)
        c += (t,)
    out, c = [], tuple(ctx)
    for t, q in zip(drafted, dists):
        p = target_dist(c)
        if random.random() < min(1.0, p[t] / q[t]):  # accept
            out.append(t)
            c += (t,)
        else:  # reject -> resample from residual max(0, p-q), then stop
            resid = norm([max(0.0, a - b) for a, b in zip(p, q)])
            out.append(sample(resid))
            return out, 1
    out.append(sample(target_dist(c)))  # bonus token when all k accepted
    return out, 1


def demo_speculative() -> None:
    header("4. SPECULATIVE DECODING  (draft k, verify once)")
    n_tokens = 4000
    print(f"{'k':>3} {'tokens/target-call':>20} {'target calls saved':>20}")
    print(f"{'-':>3} {1.0:>20.2f} {'baseline':>20}")
    for k in (2, 4, 8):
        ctx, calls = [0], 0
        while len(ctx) - 1 < n_tokens:
            toks, c = spec_step(ctx, k)
            ctx += toks
            calls += c
        tpc = (len(ctx) - 1) / calls
        print(f"{k:>3} {tpc:>20.2f} {1 - 1 / tpc:>19.0%}")

    # correctness: marginal distribution after one token must equal target's
    ctx = [3]
    counts = [0] * len(VOCAB)
    trials = 20000
    for _ in range(trials):
        counts[spec_step(ctx, 4)[0][0]] += 1
    emp = [c / trials for c in counts]
    tgt = target_dist(tuple(ctx))
    tv = 0.5 * sum(abs(a - b) for a, b in zip(emp, tgt))
    print(f"lossless check: total-variation(spec, target) = {tv:.4f}  (~0 => same distribution)")
    print("Win depends on draft/target agreement (acceptance rate). Bad draft -> little gain.")


# =============================================================================
if __name__ == "__main__":
    demo_kv_cache()
    demo_batching()
    demo_quantization()
    demo_speculative()
    header("TAKEAWAY")
    print("Prefill = compute-bound, decode = memory-bound. Every lever above attacks decode:\n"
          "  KV cache -> skip recompute | batching -> fill the GPU | quant -> move fewer bytes |\n"
          "  speculation -> more tokens per big-model pass.")
