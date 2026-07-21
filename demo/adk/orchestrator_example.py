"""
Example: Multi-Agent Orchestrator

Demonstrates how the AgentOrchestrator routes user requests
to specialised agents, executes them, and synthesises results.
"""

import os
import sys

from dotenv import load_dotenv

# Ensure the parent directory is on sys.path so relative imports work
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

from agents import (
    AgentOrchestrator,
    MathAgent,
    ResearchAgent,
    WeatherAgent,
    WriterAgent,
)


def demo():
    """Run pre-defined scenarios to showcase multi-agent orchestration."""

    print("\n" + "=" * 80)
    print("  MULTI-AGENT ORCHESTRATOR DEMO")
    print("=" * 80)

    # --- Build the orchestrator ---
    print("\nRegistering agents...")
    orchestrator = (
        AgentOrchestrator(verbose=True)
        .register_agent(WeatherAgent())
        .register_agent(MathAgent())
        .register_agent(ResearchAgent())
        .register_agent(WriterAgent())
    )

    print(f"\nAvailable agents: {[a['name'] for a in orchestrator.list_agents()]}\n")

    # ---------------------------------------------------------------
    # Scenario 1 – Single-agent routing
    # ---------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Scenario 1: Single-agent task (weather)")
    print("-" * 80)
    orchestrator.run("What is the current weather in Tokyo?")

    # ---------------------------------------------------------------
    # Scenario 2 – Parallel multi-agent
    # ---------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Scenario 2: Parallel multi-agent task")
    print("-" * 80)
    orchestrator.run(
        "Get the weather in London and Paris, calculate the average of their "
        "temperatures, and search for the best time to visit Europe."
    )

    # ---------------------------------------------------------------
    # Scenario 3 – Sequential (depends on earlier results)
    # ---------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Scenario 3: Sequential task with cross-agent dependency")
    print("-" * 80)
    orchestrator.run(
        "Find out the temperature in Berlin, convert it from Celsius to "
        "Fahrenheit, and then write a short travel advisory note about it."
    )

    # ---------------------------------------------------------------
    # Scenario 4 – Complex multi-step
    # ---------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Scenario 4: Complex research + write task")
    print("-" * 80)
    orchestrator.run(
        "Research the latest trends in agentic AI, summarise the key points, "
        "and save a note titled 'AI Trends Report' with a professional summary."
    )

    # --- Summary ---
    print("\n" + "=" * 80)
    print("  EXECUTION TRACE SUMMARY")
    print("=" * 80)
    for entry in orchestrator.get_trace():
        print(f"  Step {entry['step']} [{entry['agent']}]: {entry['task'][:70]}...")
    print()


def interactive():
    """Interactive mode – type any request and the orchestrator will handle it."""

    print("\n" + "=" * 80)
    print("  INTERACTIVE MULTI-AGENT ORCHESTRATOR")
    print("=" * 80)

    orchestrator = (
        AgentOrchestrator(verbose=True)
        .register_agent(WeatherAgent())
        .register_agent(MathAgent())
        .register_agent(ResearchAgent())
        .register_agent(WriterAgent())
    )

    print("\nRegistered agents:")
    for info in orchestrator.list_agents():
        tools = ", ".join(info["tools"]) if info["tools"] else "none"
        print(f"  [{info['name']}] {info['description']}  (tools: {tools})")

    print("\nType your request (or 'quit' to exit).\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            if not user_input:
                continue
            orchestrator.run(user_input)
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye!")
            break
        except Exception as exc:
            print(f"\n[Error] {exc}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive()
    else:
        demo()
