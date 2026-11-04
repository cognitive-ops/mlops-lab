"""
Agentic RAG with Multi-Intent Decomposition (LangGraph).

Parent graph:
    START -> decompose --(0 intents)--> direct_answer -> END
                       \\--(N intents, Send fan-out, parallel)--> run_intent x N --> synthesize -> END

Worker subgraph (one per intent, corrective-RAG loop):
    retrieve -> grade --(relevant or out of retries)--> answer_sub -> END
                      \\--(irrelevant)--> rewrite -> retrieve

`results` in the parent state uses an `operator.add` reducer, so the parallel workers
append their sub-answers without overwriting each other.

Usage:
    pip install langgraph langchain-openai openai numpy pydantic
    export OPENAI_API_KEY=...
    python agentic_rag_langgraph.py
    python agentic_rag_langgraph.py -q "Which index trades recall for memory, and how does vLLM cut GPU memory waste?"
"""

import argparse
import operator
import os
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from openai import OpenAI
from pydantic import BaseModel, Field

from agentic_rag import CORPUS, VectorStore

CHAT_MODEL = "gpt-4o"
MAX_RETRIES = 2

llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
store = VectorStore(CORPUS, OpenAI(api_key=os.getenv("OPENAI_API_KEY")))


# --------------------------------------------------------------------------
# Structured outputs
# --------------------------------------------------------------------------
class Intent(BaseModel):
    question: str = Field(description="Self-contained sub-question for ONE intent")
    query: str = Field(description="Keyword-rich search query for the knowledge base")


class Decomposition(BaseModel):
    intents: List[Intent] = Field(
        description="Independent intents in the user question. One item if the question is single-intent. "
                    "Empty list if it is chit-chat or needs no knowledge-base lookup."
    )


class Grade(BaseModel):
    relevant: bool = Field(description="True if the chunks contain the answer to the question")
    reason: str


class Rewrite(BaseModel):
    query: str = Field(description="Improved search query: synonyms, more specific terms")


# --------------------------------------------------------------------------
# Worker subgraph: corrective RAG for one intent
# --------------------------------------------------------------------------
class WorkerState(TypedDict):
    question: str
    query: str
    hits: List[Dict[str, Any]]
    relevant: bool
    attempts: int
    sub_answer: str
    sources: List[str]


def retrieve(s: WorkerState) -> dict:
    hits = store.search(s["query"], k=3)
    print(f"  [retrieve] {s['query']!r} -> {[(h['id'], h['score']) for h in hits]}")
    return {"hits": hits}


def grade(s: WorkerState) -> dict:
    ctx = "\n".join(f"[{h['id']}] {h['text']}" for h in s["hits"])
    g = llm.with_structured_output(Grade).invoke(
        f"Question: {s['question']}\n\nChunks:\n{ctx}\n\nDo the chunks contain what is needed to answer?"
    )
    print(f"  [grade] relevant={g.relevant} ({g.reason})")
    return {"relevant": g.relevant}


def rewrite(s: WorkerState) -> dict:
    r = llm.with_structured_output(Rewrite).invoke(
        f"Question: {s['question']}\nFailed query: {s['query']}\nWrite a better search query."
    )
    return {"query": r.query, "attempts": s["attempts"] + 1}


def answer_sub(s: WorkerState) -> dict:
    if not s["relevant"]:
        return {"sub_answer": "Not found in the knowledge base.", "sources": []}
    ctx = "\n".join(f"[{h['id']}] {h['text']}" for h in s["hits"])
    out = llm.invoke(
        f"Answer using ONLY the context. Be concise.\n\nContext:\n{ctx}\n\nQuestion: {s['question']}"
    ).content
    return {"sub_answer": out, "sources": [h["id"] for h in s["hits"]]}


def after_grade(s: WorkerState) -> str:
    return "answer_sub" if s["relevant"] or s["attempts"] >= MAX_RETRIES else "rewrite"


_w = StateGraph(WorkerState)
_w.add_node("retrieve", retrieve)
_w.add_node("grade", grade)
_w.add_node("rewrite", rewrite)
_w.add_node("answer_sub", answer_sub)
_w.add_edge(START, "retrieve")
_w.add_edge("retrieve", "grade")
_w.add_conditional_edges("grade", after_grade, ["answer_sub", "rewrite"])
_w.add_edge("rewrite", "retrieve")
_w.add_edge("answer_sub", END)
worker = _w.compile()


# --------------------------------------------------------------------------
# Parent graph: decompose -> fan-out -> synthesize
# --------------------------------------------------------------------------
class State(TypedDict):
    question: str
    intents: List[Intent]
    results: Annotated[List[Dict[str, Any]], operator.add]  # reducer: parallel workers append
    answer: str
    sources: List[str]


def decompose(s: State) -> dict:
    d = llm.with_structured_output(Decomposition).invoke(
        "Split the user message into independent intents that each need their own knowledge-base lookup "
        "(topics: Kubernetes, vector databases, LLM serving). Do not split one intent into trivial pieces. "
        f"Return an empty list for chit-chat.\n\nUser message: {s['question']}"
    )
    print(f"[decompose] {len(d.intents)} intent(s): {[i.question for i in d.intents]}")
    return {"intents": d.intents}


def fan_out(s: State):
    """Conditional edge returning Send objects -> one parallel worker per intent."""
    if not s["intents"]:
        return "direct_answer"
    return [Send("run_intent", {"intent": i}) for i in s["intents"]]


def run_intent(payload: dict) -> dict:
    i: Intent = payload["intent"]
    print(f"[worker] {i.question}")
    out = worker.invoke(
        {"question": i.question, "query": i.query, "hits": [], "relevant": False,
         "attempts": 0, "sub_answer": "", "sources": []}
    )
    return {"results": [{"question": i.question, "answer": out["sub_answer"], "sources": out["sources"]}]}


def direct_answer(s: State) -> dict:
    return {"answer": llm.invoke(s["question"]).content, "sources": []}


def synthesize(s: State) -> dict:
    parts = "\n\n".join(f"Q: {r['question']}\nA: {r['answer']}" for r in s["results"])
    out = llm.invoke(
        "Combine the sub-answers into ONE coherent answer to the original question. "
        "Keep only facts present in the sub-answers; mention what is missing.\n\n"
        f"Original question: {s['question']}\n\n{parts}"
    ).content
    sources = sorted({src for r in s["results"] for src in r["sources"]})
    return {"answer": out, "sources": sources}


g = StateGraph(State)
g.add_node("decompose", decompose)
g.add_node("run_intent", run_intent)
g.add_node("direct_answer", direct_answer)
g.add_node("synthesize", synthesize)
g.add_edge(START, "decompose")
g.add_conditional_edges("decompose", fan_out, ["run_intent", "direct_answer"])
g.add_edge("run_intent", "synthesize")
g.add_edge("direct_answer", END)
g.add_edge("synthesize", END)
app = g.compile()

DEMO_QUESTIONS = [
    "Hi, what can you help with?",                                                       # 0 intents
    "How does HPA decide to scale pods?",                                                # 1 intent
    "Which index trades recall for memory, and how does vLLM reduce GPU memory waste?",  # 2 intents
    "How does Ingress route traffic, what is hybrid search, and what does INT4 quantization do?",  # 3 intents
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--question", help="question (default: run demo set)")
    args = ap.parse_args()

    for q in [args.question] if args.question else DEMO_QUESTIONS:
        print(f"\n=== Q: {q}")
        out = app.invoke({"question": q, "results": []})
        print(f"A: {out['answer']}\nsources: {out['sources']}")


if __name__ == "__main__":
    main()
