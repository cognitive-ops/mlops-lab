"""
Multi-Agent Supervisor Demo – entry point.

Run:
    export OPENAI_API_KEY="sk-..."
    python main.py
"""

from itertools import chain
import os
import sys

from langchain_core.messages import HumanMessage
from IPython.display import Image, display

from graph import compile_graph


def run_query(query: str, verbose: bool = True) -> str:
    """Send a query through the multi-agent supervisor graph.

    Args:
        query: User question or task.
        verbose: Print step-by-step node outputs.

    Returns:
        The final synthesised answer.
    """
    app = compile_graph()

    # Show workflow
    png_bytes = app.get_graph().draw_mermaid_png()
    display(Image(png_bytes))
    print(app.get_graph().draw_mermaid())
    # Export PNG to file
    with open("workflow_graph.png", "wb") as f:
        f.write(png_bytes)

    initial_state = {
        "messages": [HumanMessage(content=query)],
        "next_agent": "",
        "worker_outputs": {},
        "iterations": 0,
        "final_answer": "",
    }

    print(f"\n{'=' * 80}")
    print(f"  USER QUERY: {query}")
    print(f"{'=' * 80}\n")

    final_state = {}
    for step in app.stream(initial_state):
        for node_name, node_output in step.items():
            if verbose:
                print(f"--- {node_name} ---")
                if "messages" in node_output and node_output["messages"]:
                    last_msg = node_output["messages"][-1]
                    print(
                        f"  {last_msg.content[:200]}{'…' if len(last_msg.content) > 200 else ''}")
                if "next_agent" in node_output:
                    print(f"  → next: {node_output['next_agent']}")
                print()
            final_state.update(node_output)

    answer = final_state.get("final_answer", "(no answer)")
    print(f"{'=' * 80}")
    print(f"  FINAL ANSWER:\n\n{answer}")
    print(f"{'=' * 80}\n")
    return answer


# ---------------------------------------------------------------------------
# Demo queries
# ---------------------------------------------------------------------------
DEMO_QUERIES = [
    # 1. Research-only query
    "What is LangGraph and how does it differ from LangChain?",

    # 2. Code-only query
    "Write a Python function to compute the Fibonacci sequence using memoisation.",

    # 3. Analysis-only query
    "Calculate (123 * 456) + (789 / 3) and explain the steps.",

    # 4. Multi-agent query (research + code + analysis)
    (
        "Research what Kubernetes is, write a Python script that generates a "
        "basic K8s deployment YAML, and calculate how many pods would exist "
        "if we have 3 replicas across 5 microservices."
    ),
]


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY is not set.")
        print("   export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    # Run a specific query index, or all of them
    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        run_query(DEMO_QUERIES[idx])
    else:
        for i, q in enumerate(DEMO_QUERIES):
            print(f"\n{'#' * 80}")
            print(f"  DEMO {i + 1}/{len(DEMO_QUERIES)}")
            print(f"{'#' * 80}")
            run_query(q)
