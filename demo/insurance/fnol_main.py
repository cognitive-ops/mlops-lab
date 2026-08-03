"""
FNOL Claims Intake Agent – entry point.

Two things happen BEFORE the LangGraph engine ever runs, matching the
target architecture:
  1. Multi-modal ingestion — PDF/voice input is converted to plain text
     (app text passes through as-is).
  2. The Deterministic Rail — a rule-based input sanitizer (see
     fnol_guardrails.py) either passes the text through (redacting any
     detected PII) or rejects it outright (prompt-injection patterns,
     empty/garbage input) before a graph thread is even created.

State is persisted to a local SQLite checkpoint DB, so the mandatory
human-review pause survives a process restart — resume a claim later just
by re-running with the same claim_id.

Run:
    cp .env.example .env   # fill in OPENAI_API_KEY
    python fnol_main.py                    # scripted scenarios (no TTY needed)
    python fnol_main.py --interactive      # chat + review claims live in your terminal
    python fnol_main.py --claim --channel pdf --file claim_form.pdf --photo damage.jpg --claim-id my-claim-1
"""

import argparse
import os
import sqlite3
import sys

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from fnol_graph import compile_graph
from fnol_guardrails import run_deterministic_rail
from fnol_tools import extract_pdf_text, transcribe_voice

load_dotenv()

CHECKPOINT_DB = os.path.join(os.path.dirname(__file__), "fnol_checkpoints.sqlite")


def get_checkpointer() -> SqliteSaver:
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    return SqliteSaver(conn)


def thread_config(claim_id: str) -> dict:
    return {"configurable": {"thread_id": claim_id}}


def run_preflight(channel: str, raw_input: str) -> dict:
    """Multi-modal ingestion + deterministic rail, run before the graph.

    Returns {"text": ..., "passed": bool, "flags": [...]}. `text` is already
    redacted for detected PII when passed=True.
    """

    if channel == "pdf":
        text = extract_pdf_text(raw_input)
    elif channel == "voice":
        text = transcribe_voice(raw_input)
    else:
        text = raw_input

    rail = run_deterministic_rail(text)
    return {"text": rail["redacted_text"], "passed": rail["passed"], "flags": rail["flags"]}


def initial_state(text: str, input_channel: str, photo_path: str = "") -> dict:
    return {
        "messages": [],
        "input_channel": input_channel,
        "raw_input": text,
        "photo_path": photo_path,
        "ingested": False,
        "claim_data": {},
        "missing_fields": [],
        "validated_stage_a": False,
        "validated_stage_b": False,
        "policy_verified": False,
        "coverage_status": "",
        "coverage_context": {},
        "damage_analyzed": False,
        "damage_analysis": {},
        "risk_assessed": False,
        "risk_flags": [],
        "risk_score": 0.0,
        "route_decision": "",
        "siu_escalated": False,
        "human_review_requested": False,
        "human_decision": "",
        "pending_user_reply": True,
        "next_agent": "",
        "status": "collecting",
        "cms_claim_id": "",
        "final_claim": {},
        "iterations": 0,
    }


def run_scenario(
    name: str,
    claim_id: str,
    channel: str,
    first_input: str,
    followups: list,
    reviewer_decisions: list,
    photo_path: str = "",
    max_rounds: int = 12,
) -> dict:
    """Drive the graph turn-by-turn: run the pre-flight rail on every
    claimant message, feed canned follow-ups when the agent asks for
    missing/invalid fields, and canned reviewer decisions at the HITL gate."""

    print(f"\n{'=' * 80}")
    print(f"  SCENARIO: {name}  (claim_id={claim_id})")
    print(f"{'=' * 80}\n")

    pre = run_preflight(channel, first_input)
    if not pre["passed"]:
        print(f"⛔ Deterministic rail rejected input: {pre['flags']}")
        return {}
    if pre["flags"]:
        print(f"⚠️  Deterministic rail flags (non-blocking): {pre['flags']}")
    print(f"Claimant ({channel}): {pre['text']}\n")

    checkpointer = get_checkpointer()
    app = compile_graph(checkpointer)
    config = thread_config(claim_id)

    result = app.invoke(initial_state(pre["text"], channel, photo_path), config)

    followup_iter = iter(followups)
    decision_iter = iter(reviewer_decisions)

    for _ in range(max_rounds):
        status = result["status"]

        if status == "complete":
            return result["final_claim"]

        if status == "awaiting_info":
            item = next(followup_iter, None)
            if item is None:
                print("⚠️  No more scripted follow-ups; stopping scenario.")
                return result.get("final_claim", {})
            f_channel, f_text = item if isinstance(item, tuple) else ("app", item)

            f_pre = run_preflight(f_channel, f_text)
            if not f_pre["passed"]:
                print(f"⛔ Deterministic rail rejected follow-up: {f_pre['flags']}")
                return result.get("final_claim", {})
            print(f"Claimant ({f_channel}): {f_pre['text']}\n")

            app.update_state(
                config,
                {"raw_input": f_pre["text"], "input_channel": f_channel, "pending_user_reply": True},
            )
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


def run_interactive(claim_id: str, photo_path: str = "") -> dict:
    """Chat with the FNOL agent live, acting as both claimant and reviewer."""

    checkpointer = get_checkpointer()
    app = compile_graph(checkpointer)
    config = thread_config(claim_id)

    print(f"Filing claim '{claim_id}'. Describe what happened (Ctrl+C to quit).\n")
    first_input = input("Claimant: ")

    pre = run_preflight("app", first_input)
    if not pre["passed"]:
        print(f"⛔ Deterministic rail rejected input: {pre['flags']}")
        return {}
    if pre["flags"]:
        print(f"⚠️  Deterministic rail flags (non-blocking): {pre['flags']}")

    result = app.invoke(initial_state(pre["text"], "app", photo_path), config)

    while True:
        status = result["status"]

        if status == "complete":
            return result["final_claim"]

        if status == "awaiting_info":
            reply = input("Claimant: ")
            f_pre = run_preflight("app", reply)
            if not f_pre["passed"]:
                print(f"⛔ Deterministic rail rejected input: {f_pre['flags']}")
                continue
            app.update_state(
                config,
                {"raw_input": f_pre["text"], "input_channel": "app", "pending_user_reply": True},
            )
            result = app.invoke(None, config)
            continue

        if status == "awaiting_human_review":
            decision = input("Reviewer decision [approved/rejected/needs_more_info]: ").strip()
            app.update_state(config, {"human_decision": decision})
            result = app.invoke(None, config)
            continue


def run_single_claim(channel: str, raw_input: str, claim_id: str, photo_path: str = "") -> dict:
    """One-shot real-file run: `python fnol_main.py --claim --channel pdf --file
    claim_form.pdf --photo damage.jpg --claim-id my-claim-1`. Any follow-up
    questions or human review decisions are handled interactively."""

    pre = run_preflight(channel, raw_input)
    if not pre["passed"]:
        print(f"⛔ Deterministic rail rejected input: {pre['flags']}")
        return {}
    if pre["flags"]:
        print(f"⚠️  Deterministic rail flags (non-blocking): {pre['flags']}")
    print(f"Claimant ({channel}): {pre['text']}\n")

    checkpointer = get_checkpointer()
    app = compile_graph(checkpointer)
    config = thread_config(claim_id)

    result = app.invoke(initial_state(pre["text"], channel, photo_path), config)

    while True:
        status = result["status"]
        if status == "complete":
            return result["final_claim"]
        if status == "awaiting_info":
            reply = input("Claimant: ")
            f_pre = run_preflight("app", reply)
            if not f_pre["passed"]:
                print(f"⛔ Deterministic rail rejected input: {f_pre['flags']}")
                continue
            app.update_state(
                config,
                {"raw_input": f_pre["text"], "input_channel": "app", "pending_user_reply": True},
            )
            result = app.invoke(None, config)
            continue
        if status == "awaiting_human_review":
            decision = input("Reviewer decision [approved/rejected/needs_more_info]: ").strip()
            app.update_state(config, {"human_decision": decision})
            result = app.invoke(None, config)
            continue


SCENARIOS = [
    dict(
        name="Fast track — clean, low-value, in-coverage claim",
        claim_id="claim-fasttrack-001",
        channel="app",
        first_input=(
            "My policy is POL-100001, I'm Jane Carter. I had a collision on 2024-03-10 "
            "at Main St & 5th Ave — another car hit me at a red light, no injuries. "
            "Police report PR-88213. Estimated damage $4,200."
        ),
        followups=[],
        reviewer_decisions=[],
    ),
    dict(
        name="HITL ambiguous — no police report + no-witnesses language, quick sign-off",
        claim_id="claim-hitl-002",
        channel="app",
        first_input=(
            "I'm Morgan Lee, policy POL-100001. Collision on 2024-03-15 at 5th & Elm — "
            "hit a parked car, no witnesses around, no injuries. Haven't filed a police "
            "report. Estimated damage $6,000."
        ),
        followups=[],
        reviewer_decisions=["approved"],
    ),
    dict(
        name="Adjuster review + SIU — high-risk theft claim",
        claim_id="claim-siu-003",
        channel="app",
        first_input=(
            "I'm Alex Kim, policy POL-100003. Theft of my car on 2025-12-05 at "
            "7 Birch Rd, Lakeview. No injuries. No police report yet — it was cash only "
            "so I don't have receipts. Estimated damage $28,000."
        ),
        followups=["Filed the police report today, number PR-55210."],
        reviewer_decisions=["needs_more_info", "approved"],
    ),
    dict(
        name="Adjuster review — lapsed policy, denied",
        claim_id="claim-lapsed-004",
        channel="app",
        first_input=(
            "I'm Sam Lee, policy POL-100002. My car was hit on 2025-11-02 at "
            "10 Oak Ave, Riverside. No injuries. Estimated damage $9,000."
        ),
        followups=[],
        reviewer_decisions=["rejected"],
    ),
]


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY is not set.")
        print("   cp .env.example .env  # then fill it in")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="FNOL Claims Intake Agent")
    parser.add_argument("--interactive", action="store_true", help="Chat live in the terminal")
    parser.add_argument("--claim", action="store_true", help="File a single real claim (see --channel/--file)")
    parser.add_argument("--channel", choices=["app", "pdf", "voice"], default="app")
    parser.add_argument("--file", help="Path to a PDF or audio file (required for --channel pdf/voice)")
    parser.add_argument("--text", help="Inline claim text (for --channel app)")
    parser.add_argument("--photo", default="", help="Optional path to a damage photo")
    parser.add_argument("--claim-id", default="cli-claim-1")
    args = parser.parse_args()

    if args.interactive:
        run_interactive(claim_id="interactive-claim", photo_path=args.photo)
    elif args.claim:
        raw = args.file if args.channel in ("pdf", "voice") else (args.text or "")
        if not raw:
            print("⚠️  --claim needs --file (pdf/voice) or --text (app).")
            sys.exit(1)
        run_single_claim(args.channel, raw, args.claim_id, photo_path=args.photo)
    else:
        for scenario in SCENARIOS:
            run_scenario(**scenario)
