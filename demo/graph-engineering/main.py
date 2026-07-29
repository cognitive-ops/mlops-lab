"""
Entry point — ingest a couple of sentences, then ask a question about them.

Usage:
    docker-compose up -d
    export OPENAI_API_KEY="sk-..."
    python main.py
"""

from graph import compile_graph
from kg import kg

app = compile_graph()


def ingest(text: str) -> None:
    result = app.invoke({"input_text": text, "mode": "ingest"})
    print(result["messages"][-1].content)


def ask(question: str) -> str:
    result = app.invoke({"question": question, "mode": "query"})
    answer = result["final_answer"]
    print(f"\nQ: {question}\nA: {answer}")
    print("Retrieved facts:", result["retrieved_triples"])
    return answer


if __name__ == "__main__":
    ingest("Satya Nadella is the CEO of Microsoft. Microsoft acquired GitHub in 2018.")
    ingest("GitHub was founded by Tom Preston-Werner.")

    print(f"\nKnowledge graph: {kg.stats()}\n")

    ask("Who leads the company that owns GitHub?")

    kg.close()
