"""
Agentic semantic chunking.

Step 1 (deterministic): embed sentences, cut where adjacent-sentence cosine
distance spikes (percentile threshold) -> initial semantic chunks.
Step 2 (agentic): an LLM agent inspects the chunks via tools and fixes
over/under-segmentation (merge, split, re-chunk with another threshold),
then calls `finish`.

Usage:
    export OPENAI_API_KEY=...
    python semantic_chunking_agent.py                  # agent refines chunks
    python semantic_chunking_agent.py --no-agent       # embeddings-only baseline
    python semantic_chunking_agent.py --file doc.txt
"""

import argparse
import json
import os
import re
from typing import Any, Dict, List

import numpy as np
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"

SAMPLE_TEXT = """
Kubernetes schedules containers onto nodes in a cluster. The scheduler scores each node based on resource requests and affinity rules. Pods that cannot be placed stay in the Pending state. Horizontal Pod Autoscaler adds replicas when CPU usage crosses a target.

Vector databases store high-dimensional embeddings for similarity search. HNSW graphs give fast approximate nearest neighbour lookups. Weaviate and Qdrant both support hybrid search that mixes BM25 with vectors. Choosing the right index type trades recall against memory.

Large language models generate text one token at a time. The KV cache stores attention keys and values so earlier tokens are not recomputed. Serving engines like vLLM use paged attention to reduce memory fragmentation. Quantization shrinks weights to fit bigger models on a single GPU.

Back to Kubernetes: a Service gives pods a stable virtual IP. Ingress controllers route external HTTP traffic to Services. Network policies restrict which pods may talk to each other.
""".strip()


# --------------------------------------------------------------------------
# Semantic chunking core
# --------------------------------------------------------------------------
def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


class Chunker:
    """Holds sentences + embeddings and the current chunking (list of sentence-index lists)."""

    def __init__(self, text: str, client: OpenAI):
        self.client = client
        self.sentences = split_sentences(text)
        resp = client.embeddings.create(model=EMBED_MODEL, input=self.sentences)
        vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
        self.vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
        # distance between sentence i and i+1
        self.dist = 1.0 - np.sum(self.vecs[:-1] * self.vecs[1:], axis=1)
        self.chunks: List[List[int]] = []
        self.semantic_chunk(95)

    def semantic_chunk(self, percentile: float) -> str:
        """Cut at adjacent-sentence distances above the given percentile."""
        threshold = np.percentile(self.dist, percentile)
        cuts = [i for i, d in enumerate(self.dist) if d > threshold]
        chunks, start = [], 0
        for c in cuts:
            chunks.append(list(range(start, c + 1)))
            start = c + 1
        chunks.append(list(range(start, len(self.sentences))))
        self.chunks = chunks
        return f"{len(chunks)} chunks (percentile={percentile}, threshold={threshold:.3f})"

    def text(self, idx: int) -> str:
        return " ".join(self.sentences[i] for i in self.chunks[idx])

    def coherence(self, idx: int) -> float:
        """Mean pairwise cosine similarity inside a chunk (1.0 for single sentence)."""
        ids = self.chunks[idx]
        if len(ids) < 2:
            return 1.0
        v = self.vecs[ids]
        sim = v @ v.T
        n = len(ids)
        return float((sim.sum() - n) / (n * (n - 1)))

    # ---- agent tools ----
    def list_chunks(self) -> str:
        rows = []
        for i, ids in enumerate(self.chunks):
            preview = self.text(i)
            preview = preview if len(preview) < 160 else preview[:157] + "..."
            gap = f"{self.dist[ids[-1]]:.3f}" if ids[-1] < len(self.dist) else "-"
            rows.append(
                f"[{i}] sents={len(ids)} coherence={self.coherence(i):.2f} "
                f"gap_to_next={gap} :: {preview}"
            )
        return "\n".join(rows)

    def get_chunk(self, index: int) -> str:
        if not 0 <= index < len(self.chunks):
            return f"error: index {index} out of range"
        return "\n".join(f"({s}) {self.sentences[s]}" for s in self.chunks[index])

    def merge_chunks(self, index: int) -> str:
        """Merge chunk `index` with the next one."""
        if not 0 <= index < len(self.chunks) - 1:
            return f"error: cannot merge chunk {index} with next"
        self.chunks[index] += self.chunks.pop(index + 1)
        return f"merged {index}+{index + 1}; now {len(self.chunks)} chunks"

    def split_chunk(self, index: int, after_sentence: int) -> str:
        """Split chunk `index` after global sentence id `after_sentence`."""
        if not 0 <= index < len(self.chunks):
            return f"error: index {index} out of range"
        ids = self.chunks[index]
        if after_sentence not in ids[:-1]:
            return f"error: after_sentence must be one of {ids[:-1]}"
        pos = ids.index(after_sentence) + 1
        self.chunks[index : index + 1] = [ids[:pos], ids[pos:]]
        return f"split {index}; now {len(self.chunks)} chunks"


# --------------------------------------------------------------------------
# Agent loop (OpenAI function calling)
# --------------------------------------------------------------------------
def _tool(name: str, desc: str, props: Dict[str, Any] | None = None) -> Dict[str, Any]:
    props = props or {}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": list(props)},
        },
    }


TOOLS = [
    _tool("list_chunks", "List current chunks with coherence score and distance to next chunk."),
    _tool("get_chunk", "Show the sentences (with global ids) of one chunk.",
          {"index": {"type": "integer"}}),
    _tool("merge_chunks", "Merge chunk `index` with the following chunk.",
          {"index": {"type": "integer"}}),
    _tool("split_chunk", "Split chunk `index` after global sentence id `after_sentence`.",
          {"index": {"type": "integer"}, "after_sentence": {"type": "integer"}}),
    _tool("rechunk", "Discard edits and re-run semantic chunking with a new breakpoint percentile "
          "(lower = more chunks, e.g. 70-99).", {"percentile": {"type": "number"}}),
    _tool("finish", "Accept the current chunks as final."),
]

SYSTEM = """You are a chunking agent preparing a document for RAG retrieval.
Goal: each chunk covers ONE topic, self-contained, roughly 2-8 sentences.
Inspect chunks with list_chunks/get_chunk. Fix problems:
- topic split across chunks -> merge_chunks
- chunk mixing topics -> split_chunk
- badly calibrated overall -> rechunk with a different percentile
Make few, justified edits, then call finish."""


def run_agent(chunker: Chunker, client: OpenAI, max_steps: int = 12) -> None:
    dispatch = {
        "list_chunks": lambda **_: chunker.list_chunks(),
        "get_chunk": lambda index, **_: chunker.get_chunk(index),
        "merge_chunks": lambda index, **_: chunker.merge_chunks(index),
        "split_chunk": lambda index, after_sentence, **_: chunker.split_chunk(index, after_sentence),
        "rechunk": lambda percentile, **_: chunker.semantic_chunk(percentile),
    }
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Document has {len(chunker.sentences)} sentences. "
                                    f"Initial chunking:\n{chunker.list_chunks()}"},
    ]
    for step in range(max_steps):
        msg = client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, tools=TOOLS
        ).choices[0].message
        messages.append(msg)
        if not msg.tool_calls:
            break
        done = False
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            if call.function.name == "finish":
                result, done = "accepted", True
            else:
                try:
                    result = dispatch[call.function.name](**args)
                except Exception as e:  # feed errors back so the agent can recover
                    result = f"error: {e}"
            print(f"[agent {step}] {call.function.name}({args}) -> {str(result)[:100]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
        if done:
            return
    print("[agent] step limit reached; using current chunks")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="text file to chunk (default: built-in sample)")
    ap.add_argument("--no-agent", action="store_true", help="skip agent refinement")
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read() if args.file else SAMPLE_TEXT
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunker = Chunker(text, client)
    print("=== initial semantic chunks ===")
    print(chunker.list_chunks())

    if not args.no_agent:
        print("\n=== agent refinement ===")
        run_agent(chunker, client)

    print("\n=== final chunks ===")
    for i in range(len(chunker.chunks)):
        print(f"\n--- chunk {i} (coherence {chunker.coherence(i):.2f}) ---\n{chunker.text(i)}")


if __name__ == "__main__":
    main()
