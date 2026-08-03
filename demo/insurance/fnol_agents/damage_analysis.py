"""
Multi-modal damage node – if the claimant attached a damage photo, analyze
it with OpenAI vision (severity estimate + description) so the fraud/risk
node can factor in what the damage actually looks like, not just what the
claimant wrote. Claims with no photo proceed with a neutral placeholder.
"""

from fnol_state import FNOLState
from fnol_tools import analyze_damage_photo, no_photo_analysis


def damage_analysis_node(state: FNOLState) -> dict:
    """LangGraph node: analyze the attached damage photo, if any."""

    photo_path = state.get("photo_path", "")

    if photo_path:
        analysis = analyze_damage_photo(photo_path)
        print(f"📸 Damage analysis → severity: {analysis['severity_estimate']}")
    else:
        analysis = no_photo_analysis()
        print("📸 Damage analysis → no photo attached")

    return {
        "damage_analysis": analysis,
        "damage_analyzed": True,
    }
