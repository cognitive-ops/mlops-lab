"""
Agentic RAG demo.

Classic RAG: retrieve top-k once -> stuff into prompt -> answer.
Agentic RAG: an LLM agent DECIDES whether to retrieve, which query to use, how to
decompose multi-hop questions, whether results are good enough, and when to stop.

Loop (OpenAI function calling):
    question -> agent -> [search_docs(query, k)]* -> grade/rewrite/decompose -> final answer

Tools:
    search_docs(query, k)  semantic search over an in-memory vector store
    grade_results(...)     not a tool: the agent self-grades in its reasoning, and
                           re-queries with a rewritten query if chunks are irrelevant
    answer(text, sources)  terminates the loop with a cited answer

Usage:
    pip install openai numpy
    export OPENAI_API_KEY=...
    python agentic_rag.py                                   # runs demo questions
    python agentic_rag.py -q "Which index trades recall for memory, and how does vLLM cut memory use?"
    python agentic_rag.py --naive -q "..."                  # single-shot RAG baseline
"""

import argparse
import json
import os
from typing import Any, Dict, List

import numpy as np
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"

CORPUS: List[Dict[str, str]] = [
    {"id": "k8s-1", "text": "Kubernetes scheduler scores each node using resource requests and affinity rules. Pods that cannot be placed stay Pending."},
    {"id": "k8s-2", "text": "Horizontal Pod Autoscaler adds replicas when average CPU usage crosses a target utilization, and removes them when load drops."},
    {"id": "k8s-3", "text": "A Kubernetes Service gives pods a stable virtual IP. Ingress controllers route external HTTP traffic to Services."},
    {"id": "vdb-1", "text": "HNSW builds a layered proximity graph for fast approximate nearest-neighbour search. Higher M and efSearch raise recall but cost more memory and latency."},
    {"id": "vdb-2", "text": "IVF-PQ clusters vectors and compresses them with product quantization, cutting memory by 10-30x at some recall cost."},
    {"id": "vdb-3", "text": "Hybrid search combines BM25 keyword scores with vector similarity, usually fused with reciprocal rank fusion (RRF). Weaviate and Qdrant support it."},
    {"id": "llm-1", "text": "LLMs generate one token at a time. The KV cache stores attention keys and values so earlier tokens are not recomputed."},
    {"id": "llm-2", "text": "vLLM uses PagedAttention: the KV cache is split into fixed-size blocks, which removes memory fragmentation and enables higher batch sizes."},
    {"id": "llm-3", "text": "Quantization (INT8/INT4, AWQ, GPTQ) shrinks model weights so larger models fit on a single GPU, with a small quality loss."},
]


# --------------------------------------------------------------------------
# In-memory vector store
# --------------------------------------------------------------------------
class VectorStore:
    def __init__(self, docs: List[Dict[str, str]], client: OpenAI):
        self.client = client
        self.docs = docs
        self.vecs = self._embed([d["text"] for d in docs])

    def _embed(self, texts: List[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=EMBED_MODEL, input=texts)
        v = np.array([e.embedding for e in resp.data], dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        q = self._embed([query])[0]
        scores = self.vecs @ q
        top = np.argsort(-scores)[:k]
        return [{**self.docs[i], "score": round(float(scores[i]), 3)} for i in top]


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Semantic search over the internal knowledge base. Returns chunks with id and "
                           "cosine score (higher = more relevant; < 0.30 is usually noise). "
                           "Use one focused query per call; call repeatedly for multi-part questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Standalone, keyword-rich search query"},
                    "k": {"type": "integer", "description": "Number of chunks (1-5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer",
            "description": "Submit the final answer. Call exactly once when done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}, "description": "Chunk ids used"},
                },
                "required": ["text", "sources"],
            },
        },
    },
]

SYSTEM = """You are a RAG agent answering from an internal knowledge base (Kubernetes, vector DBs, LLM serving).
Policy:
1. Decide first: if the question is chit-chat or general knowledge needing no docs, call answer directly with sources=[].
2. Otherwise decompose multi-part questions and call search_docs once per sub-question.
3. After each search, grade the results. If chunks are irrelevant or scores are low, REWRITE the query
   (synonyms, more specific terms) and search again. Do not repeat an identical query.
4. Answer ONLY from retrieved chunks. If the KB lacks the info, say so; never invent facts.
5. Cite chunk ids in sources. Stop as soon as you have enough evidence."""


def run_agent(question: str, store: VectorStore, client: OpenAI, max_steps: int = 8) -> Dict[str, Any]:
    messages: List[Any] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for step in range(max_steps):
        msg = client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, tools=TOOLS, tool_choice="required"
        ).choices[0].message
        messages.append(msg)
        for call in msg.tool_calls or []:
            args = json.loads(call.function.arguments or "{}")
            if call.function.name == "answer":
                print(f"[agent {step}] answer(sources={args.get('sources')})")
                return args
            try:
                hits = store.search(args["query"], max(1, min(int(args.get("k", 3)), 5)))
                result = json.dumps(hits)
            except Exception as e:  # feed errors back so the agent can recover
                result = f"error: {e}"
            print(f"[agent {step}] search_docs({args}) -> {[(h['id'], h['score']) for h in hits]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return {"text": "Step limit reached without a final answer.", "sources": []}


# --------------------------------------------------------------------------
# Baseline: single-shot RAG
# --------------------------------------------------------------------------
def naive_rag(question: str, store: VectorStore, client: OpenAI, k: int = 3) -> Dict[str, Any]:
    hits = store.search(question, k)
    ctx = "\n".join(f"[{h['id']}] {h['text']}" for h in hits)
    out = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "Answer using only the context. Say if it is insufficient."},
            {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {question}"},
        ],
    ).choices[0].message.content
    return {"text": out, "sources": [h["id"] for h in hits]}


DEMO_QUESTIONS = [
    "Hi, what can you help with?",                                                      # no retrieval needed
    "How does HPA decide to scale pods?",                                               # single hop
    "Which index trades recall for memory, and how does vLLM reduce GPU memory waste?", # multi-hop
    "What is the capital of Peru in our docs?",                                         # not in KB
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--question", help="question (default: run demo set)")
    ap.add_argument("--naive", action="store_true", help="single-shot RAG baseline instead of agent")
    args = ap.parse_args()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    store = VectorStore(CORPUS, client)

    for q in [args.question] if args.question else DEMO_QUESTIONS:
        print(f"\n=== Q: {q}")
        res = naive_rag(q, store, client) if args.naive else run_agent(q, store, client)
        print(f"A: {res['text']}\nsources: {res['sources']}")


if __name__ == "__main__":
    main()
