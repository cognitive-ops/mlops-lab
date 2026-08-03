"""
FNOL Claims Intake Agent – entry point.

Persists intake state to a local SQLite checkpoint DB, so the mandatory
human-review pause (and any awaiting_info pause) survives a process
restart — resume a claim later just by re-running with the same claim_id.

Run:
    cp .env.example .env   # fill in OPENAI_API_KEY
    python fnol_main.py                 # scripted scenarios (no TTY needed)
    python fnol_main.py --interactive   # chat + review claims live in your terminal
"""

import os
import sqlite3
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from fnol_graph import compile_graph

load_dotenv()

CHECKPOINT_DB = os.path.join(os.path.dirname(__file__), "fnol_checkpoints.sqlite")


def get_checkpointer() -> SqliteSaver:
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    return SqliteSaver(conn)


def thread_config(claim_id: str) -> dict:
    return {"configurable": {"thread_id": claim_id}}


def initial_state(message: str) -> dict:
    return {
        "messages": [HumanMessage(content=message)],
        "claim_data": {},
        "missing_fields": [],
        "validated": False,
        "coverage_checked": False,
        "coverage_status": "",
        "coverage_context": {},
        "risk_assessed": False,
        "risk_flags": [],
        "severity_tier": "",
        "human_review_requested": False,
        "human_decision": "",
        "pending_user_reply": True,
        "next_agent": "",
        "status": "collecting",
        "final_claim": {},
        "iterations": 0,
    }


def run_scenario(
    name: str,
    claim_id: str,
    first_message: str,
    followups: list,
    reviewer_decisions: list,
    max_rounds: int = 10,
) -> dict:
    """Drive the graph turn-by-turn: feed canned claimant follow-ups when the
    agent asks for missing/invalid fields, and canned reviewer decisions at
    the mandatory human-review gate."""

    checkpointer = get_checkpointer()
    app = compile_graph(checkpointer)
    config = thread_config(claim_id)

    followup_iter = iter(followups)
    decision_iter = iter(reviewer_decisions)

    print(f"\n{'=' * 80}")
    print(f"  SCENARIO: {name}  (claim_id={claim_id})")
    print(f"{'=' * 80}\n")
    print(f"Claimant: {first_message}\n")

    result = app.invoke(initial_state(first_message), config)

    for _ in range(max_rounds):
        status = result["status"]

        if status == "complete":
            return result["final_claim"]

        if status == "awaiting_info":
            reply = next(followup_iter, None)
            if reply is None:
                print("⚠️  No more scripted follow-ups; stopping scenario.")
                return result.get("final_claim", {})
            print(f"Claimant: {reply}\n")
            app.update_state(config, {"messages": [HumanMessage(content=reply)], "pending_user_reply": True})
            result = app.invoke(None, config)
            continue

        if status == "awaiting_human_review":
            decision = next(decision_iter, "approved")
            print(f"[Reviewer decision: {decision}]")
            app.update_state(config, {"human_decision": decision})
            result = app.invoke(None, config)
            continue

    print("⚠️  Hit max rounds without completing intake.")
    return result.get("final_claim", {})


def run_interactive(claim_id: str) -> dict:
    """Chat with the FNOL agent live, acting as both claimant and reviewer."""

    checkpointer = get_checkpointer()
    app = compile_graph(checkpointer)
    config = thread_config(claim_id)

    print(f"Filing claim '{claim_id}'. Describe what happened (Ctrl+C to quit).\n")
    first_message = input("Claimant: ")
    result = app.invoke(initial_state(first_message), config)

    while True:
        status = result["status"]

        if status == "complete":
            return result["final_claim"]

        if status == "awaiting_info":
            reply = input("Claimant: ")
            app.update_state(config, {"messages": [HumanMessage(content=reply)], "pending_user_reply": True})
            result = app.invoke(None, config)
            continue

        if status == "awaiting_human_review":
            decision = input("Reviewer decision [approved/rejected/needs_more_info]: ").strip()
            app.update_state(config, {"human_decision": decision})
            result = app.invoke(None, config)
            continue


SCENARIOS = [
    dict(
        name="Clean claim, approved",
        claim_id="claim-001",
        first_message=(
            "My policy is POL-100001, I'm Jane Carter. I had a collision on 2024-03-10 "
            "at Main St & 5th Ave — another car hit me at a red light, no injuries. "
            "Police report PR-88213. Estimated damage $4,200."
        ),
        followups=[],
        reviewer_decisions=["approved"],
    ),
    dict(
        name="Partial info, then denied for excluded loss type",
        claim_id="claim-002",
        first_message="I'm Sam Lee, policy POL-100002. My house had storm damage yesterday.",
        followups=[
            "Sorry — date of loss was 2025-11-02, at 10 Oak Ave, Riverside. No injuries. "
            "Estimated damage $9,000."
        ],
        reviewer_decisions=["rejected"],
    ),
    dict(
        name="High-risk claim → reviewer asks for more info, then approves",
        claim_id="claim-003",
        first_message=(
            "I'm Alex Kim, policy POL-100003. Theft of my car on 2025-12-05 at "
            "7 Birch Rd, Lakeview. No injuries. No police report yet — it was cash only "
            "so I don't have receipts. Estimated damage $28,000."
        ),
        followups=["Filed the police report today, number PR-55210."],
        reviewer_decisions=["needs_more_info", "approved"],
    ),
]


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY is not set.")
        print("   cp .env.example .env  # then fill it in")
        sys.exit(1)

    if "--interactive" in sys.argv:
        run_interactive(claim_id="interactive-claim")
    else:
        for scenario in SCENARIOS:
            run_scenario(**scenario)
