"""Real-model comparison: HF transformers (static batching) vs vLLM (continuous batching + PagedAttention).

Same model, same prompts, same max_tokens, greedy decoding. Reports wall time, generated tokens, tokens/s.
Each engine runs in its own subprocess so GPU memory is fully released between runs.

Needs Linux + CUDA (WSL2 / Docker on Windows; vLLM has no native Windows build):
    pip install -r requirements-vllm.txt

Run:
    python vllm_vs_hf.py                       # runs both, prints table
    python vllm_vs_hf.py --engine vllm         # single engine, prints one JSON line
    python vllm_vs_hf.py --n 128 --model Qwen/Qwen2.5-0.5B-Instruct
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time

DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"  # fits 8GB VRAM with room for KV cache
TOPICS = ["black holes", "TCP congestion control", "photosynthesis", "the French Revolution",
          "gradient descent", "Kubernetes", "jazz", "the water cycle", "public-key crypto", "volcanoes"]


def make_workload(n: int, seed: int = 0) -> tuple[list[str], list[int]]:
    """Heavy-tailed output lengths (mostly short, some long) -> where continuous batching wins."""
    rnd = random.Random(seed)
    prompts = [f"Explain {rnd.choice(TOPICS)} in detail." for _ in range(n)]
    max_toks = [rnd.choice([16, 32, 32, 64, 64, 128, 256]) for _ in range(n)]
    return prompts, max_toks


def run_hf(model: str, prompts: list[str], max_toks: list[int], batch: int) -> dict:
    """Static batching: fixed batches, each runs until its longest request is done."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model, padding_side="left")
    lm = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch.float16).cuda().eval()
    chats = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                     add_generation_prompt=True) for p in prompts]
    # warmup
    lm.generate(**tok(chats[:1], return_tensors="pt").to("cuda"), max_new_tokens=4)
    torch.cuda.synchronize()

    t0, produced = time.perf_counter(), 0
    for i in range(0, len(chats), batch):
        enc = tok(chats[i:i + batch], return_tensors="pt", padding=True).to("cuda")
        # batch must run to its longest max_tokens (no per-request early exit slots)
        out = lm.generate(**enc, max_new_tokens=max(max_toks[i:i + batch]), do_sample=False,
                          pad_token_id=tok.pad_token_id)
        gen = out[:, enc["input_ids"].shape[1]:]
        for row, mt in zip(gen, max_toks[i:i + batch]):
            produced += min(mt, int((row != tok.pad_token_id).sum()))  # useful tokens only
    torch.cuda.synchronize()
    return {"engine": "hf-static", "sec": time.perf_counter() - t0, "tokens": produced,
            "peak_gb": torch.cuda.max_memory_allocated() / 1e9}


def run_vllm(model: str, prompts: list[str], max_toks: list[int], batch: int,
             prefix_cache: bool = False, mem: float = 0.6, eager: bool = False) -> dict:
    import os
    # FlashInfer JIT-compiles kernels and needs nvcc (CUDA toolkit). Use the PyTorch sampler instead.
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM, SamplingParams

    llm = LLM(model=model, dtype="float16", gpu_memory_utilization=mem, max_num_seqs=batch,
              enforce_eager=eager,
              enable_prefix_caching=prefix_cache, max_model_len=2048)
    sps = [SamplingParams(temperature=0.0, max_tokens=m) for m in max_toks]
    chats = [[{"role": "user", "content": p}] for p in prompts]
    llm.chat(chats[:1], SamplingParams(max_tokens=4))  # warmup

    t0 = time.perf_counter()
    outs = llm.chat(chats, sps)  # per-request sampling params; engine schedules continuously
    sec = time.perf_counter() - t0
    produced = sum(len(o.outputs[0].token_ids) for o in outs)
    return {"engine": "vllm", "sec": sec, "tokens": produced, "peak_gb": None}


def child(args: argparse.Namespace) -> None:
    prompts, max_toks = make_workload(args.n)
    if args.engine == "hf":
        res = run_hf(args.model, prompts, max_toks, args.batch)
    else:
        res = run_vllm(args.model, prompts, max_toks, args.batch, mem=args.mem, eager=args.eager)
    print("RESULT " + json.dumps(res))


def spawn(engine: str, args: argparse.Namespace) -> dict | None:
    cmd = [sys.executable, __file__, "--engine", engine, "--n", str(args.n),
           "--batch", str(args.batch), "--model", args.model, "--mem", str(args.mem)]
    cmd += ["--eager"] if args.eager else []
    print(f"[{engine}] running ...", flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    print(f"[{engine}] FAILED:\n{p.stderr[-6000:]}")
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["hf", "vllm", "both"], default="both")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--n", type=int, default=64, help="number of requests")
    ap.add_argument("--batch", type=int, default=16, help="HF batch size / vLLM max_num_seqs")
    ap.add_argument("--mem", type=float, default=0.6, help="vLLM gpu_memory_utilization (lower if OOM)")
    ap.add_argument("--eager", action="store_true", help="vLLM enforce_eager: skip CUDA graphs, less memory")
    args = ap.parse_args()

    if args.engine != "both":
        return child(args)

    results = [r for r in (spawn("hf", args), spawn("vllm", args)) if r]
    print(f"\n{'engine':<12} {'sec':>8} {'tokens':>8} {'tok/s':>9}")
    for r in results:
        print(f"{r['engine']:<12} {r['sec']:>8.1f} {r['tokens']:>8} {r['tokens'] / r['sec']:>9.1f}")
    if len(results) == 2:
        a, b = results
        print(f"\nvLLM speedup: {(b['tokens'] / b['sec']) / (a['tokens'] / a['sec']):.2f}x "
              "(continuous batching + PagedAttention + CUDA graphs)")


if __name__ == "__main__":
    main()
