"""
Insurance Intake Agent – entry point.

Run:
    cp .env.example .env   # fill in OPENAI_API_KEY
    python main.py                 # scripted scenarios (no TTY needed)
    python main.py --interactive   # chat with the agent in your terminal
"""

import logging
import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from graph import compile_graph

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("insurance_demo")


def initial_state(message: str) -> dict:
    return {
        "messages": [HumanMessage(content=message)],
        "applicant_data": {},
        "missing_fields": [],
        "risk_flags": [],
        "risk_tier": "",
        "premium_estimate": 0.0,
        "validated": False,
        "risk_assessed": False,
        "pending_user_reply": True,
        "next_agent": "",
        "status": "collecting",
        "final_application": {},
        "iterations": 0,
    }


def run_scenario(name: str, first_message: str, followups: list, max_rounds: int = 6) -> dict:
    """Drive the graph turn-by-turn, feeding canned follow-up replies when
    the agent asks for missing/invalid fields."""

    app = compile_graph()
    state = initial_state(first_message)
    followup_iter = iter(followups)

    print(f"\n{'=' * 80}")
    print(f"  SCENARIO: {name}")
    print(f"{'=' * 80}\n")
    print(f"Applicant: {first_message}\n")

    for round_num in range(max_rounds):
        logger.debug("round %d: invoking graph, pre-status=%r", round_num, state.get("status"))
        state = app.invoke(state)
        logger.debug(
            "round %d: post-status=%r missing_fields=%r risk_flags=%r",
            round_num, state.get("status"), state.get("missing_fields"), state.get("risk_flags"),
        )

        if state["status"] == "complete":
            logger.debug("round %d: complete, returning final_application", round_num)
            return state["final_application"]

        if state["status"] == "awaiting_info":
            try:
                reply = next(followup_iter)
            except StopIteration:
                logger.debug("round %d: no more scripted follow-ups", round_num)
                print("⚠️  No more scripted follow-ups; stopping scenario.")
                return state["final_application"]
            print(f"Applicant: {reply}\n")
            state["messages"].append(HumanMessage(content=reply))
            state["pending_user_reply"] = True

    logger.debug("hit max_rounds=%d without completing intake", max_rounds)
    print("⚠️  Hit max rounds without completing intake.")
    return state["final_application"]


def run_interactive() -> dict:
    """Chat with the intake agent live via the terminal."""

    app = compile_graph()
    print("Describe yourself and the vehicle you want to insure (Ctrl+C to quit).\n")
    first_message = input("You: ")
    state = initial_state(first_message)

    while True:
        state = app.invoke(state)

        if state["status"] == "complete":
            return state["final_application"]

        if state["status"] == "awaiting_info":
            reply = input("You: ")
            state["messages"].append(HumanMessage(content=reply))
            state["pending_user_reply"] = True


SCENARIOS = [
    dict(
        name="Complete info in one message",
        first_message=(
            "My name is Jane Carter, DOB 1985-04-12, email jane.carter@example.com, "
            "phone 555-123-4567, address 42 Maple St, Springfield. License number "
            "D1234567. I drive a 2021 Toyota Camry, VIN 4T1BF1FK5CU123456."
        ),
        followups=[],
    ),
    dict(
        name="Partial info requiring follow-up",
        first_message="Hi, I'm Sam Lee, sam.lee@example.com, 555-987-6543.",
        followups=[
            "I was born 1990-07-22 and live at 10 Oak Ave, Riverside. "
            "License number L9988776.",
            "It's a 2019 Honda Civic, VIN 2HGFE2F59KH123789.",
        ],
    ),
    dict(
        name="High-risk applicant (young driver, prior accident, old vehicle)",
        first_message=(
            "I'm Alex Kim, born 2006-01-15, alex.kim@example.com, 555-222-3333, "
            "address 7 Birch Rd, Lakeview. License K5544332. I had a minor accident "
            "last year. My car is a 2004 Ford Focus, VIN 1FAFP34N04W123890."
        ),
        followups=[],
    ),
]


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY is not set.")
        print("   export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    if "--interactive" in sys.argv:
        run_interactive()
    else:
        for scenario in SCENARIOS:
            run_scenario(scenario["name"], scenario["first_message"], scenario["followups"])
