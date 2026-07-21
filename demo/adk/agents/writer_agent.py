"""
Writer Agent – note taking, summarisation and content generation.
"""

from datetime import datetime
from typing import Any, Dict

from google.genai import types

from .base_agent import BaseAgent


def save_note(title: str, content: str) -> Dict[str, Any]:
    """Save a note to a local text file."""
    try:
        filename = f"notes_{title.replace(' ', '_')}.txt"
        with open(filename, "w") as fh:
            fh.write(f"Title: {title}\n")
            fh.write(f"Date: {datetime.now().isoformat()}\n\n")
            fh.write(content + "\n")
        return {"success": True, "filename": filename, "title": title}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def read_note(title: str) -> Dict[str, Any]:
    """Read a previously saved note."""
    try:
        filename = f"notes_{title.replace(' ', '_')}.txt"
        with open(filename) as fh:
            return {"success": True, "title": title, "content": fh.read()}
    except FileNotFoundError:
        return {"success": False, "error": f"Note '{title}' not found."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
    """Return the current date and time."""
    now = datetime.now()
    return {
        "timezone": timezone,
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
    }


_DECLARATIONS = [
    types.FunctionDeclaration(
        name="save_note",
        description="Save a note with a title and content to a file.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Title of the note"},
                "content": {"type": "STRING", "description": "Body of the note"},
            },
            "required": ["title", "content"],
        },
    ),
    types.FunctionDeclaration(
        name="read_note",
        description="Read a previously saved note by its title.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Title of the note to read"},
            },
            "required": ["title"],
        },
    ),
    types.FunctionDeclaration(
        name="get_current_time",
        description="Get the current date and time.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "timezone": {
                    "type": "STRING",
                    "description": "Timezone name (e.g. 'UTC', 'EST')",
                }
            },
        },
    ),
]

_FUNCTIONS = {
    "save_note": save_note,
    "read_note": read_note,
    "get_current_time": get_current_time,
}


class WriterAgent(BaseAgent):
    name = "writer_agent"
    description = (
        "Specialises in writing – drafting content, saving and reading notes, "
        "summarising information, and composing reports."
    )

    def _build_tools(self):
        return _DECLARATIONS, _FUNCTIONS

    def _system_instruction(self) -> str:
        return (
            "You are a **Writer Agent**. Your job is to create well-structured, "
            "clear written content. You can save and retrieve notes, and you excel "
            "at summarisation, report writing, and creative composition."
        )
