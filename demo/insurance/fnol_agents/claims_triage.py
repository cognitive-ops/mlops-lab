"""
Claims Triage Agent – classifies claim complexity/priority and picks the
handling queue once damage has been analyzed, before fraud/risk scoring.
Sibling of the Fraud Agent under the orchestrator (see architecture
diagram): triage answers "how should this claim be handled", fraud/risk
answers "should we pay it".
"""

from fnol_state import FNOLState
from fnol_tools import triage_claim


def claims_triage_node(state: FNOLState) -> dict:
    """LangGraph node: classify claim complexity/priority/queue."""

    claim_data = state.get("claim_data", {})
    damage_analysis = state.get("damage_analysis", {})
    coverage_context = state.get("coverage_context", {})

    result = triage_claim(claim_data, damage_analysis, coverage_context)

    print(
        f"🗂️  Claims triage → complexity: {result['complexity']}, "
        f"priority: {result['priority']}, queue: {result['queue']}"
    )

    return {
        "claim_complexity": result["complexity"],
        "claim_priority": result["priority"],
        "claims_queue": result["queue"],
        "triage_completed": True,
    }
