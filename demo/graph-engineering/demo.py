"""
Scripted demo: ingest a small multi-source corpus (each source handled by
one call to the extractor agent), then run multi-hop questions against the
merged knowledge graph, and save a visualization.

Usage:
    export OPENAI_API_KEY="sk-..."
    python demo.py
"""

from graph import compile_graph
from kg import kg

app = compile_graph()

CORPUS = [
    "Satya Nadella is the CEO of Microsoft.",
    "Microsoft acquired GitHub in 2018.",
    "GitHub was founded by Tom Preston-Werner.",
    "Tom Preston-Werner also founded Chatterbug.",
    "Microsoft was founded by Bill Gates and Paul Allen.",
]

QUESTIONS = [
    "Who leads the company that owns GitHub?",
    "What companies did Tom Preston-Werner found?",
    "Is there a connection between Bill Gates and GitHub?",
]


def run() -> None:
    print("=== Ingest phase ===")
    for text in CORPUS:
        result = app.invoke({"input_text": text, "mode": "ingest"})
        print(f"  + {text!r} -> {result['messages'][-1].content}")

    print(f"\nKnowledge graph: {kg.stats()}")
    print("Entities:", kg.entities())

    print("\n=== Query phase (Graph-RAG) ===")
    for question in QUESTIONS:
        result = app.invoke({"question": question, "mode": "query"})
        print(f"\nQ: {question}")
        print(f"A: {result['final_answer']}")
        print(f"   retrieved: {result['retrieved_triples']}")

    kg.draw("knowledge_graph.png")
    print("\nSaved graph visualization -> knowledge_graph.png")


if __name__ == "__main__":
    run()
