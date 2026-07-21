"""
Research Agent – web search and information gathering.
"""

from google.genai import types

from .base_agent import BaseAgent


def search_web(query: str):
    """Search the web for information (simulated)."""
    return {
        "query": query,
        "results": [
            {
                "title": f"Result 1 for '{query}'",
                "snippet": "Simulated search result. Replace with a real search API in production.",
                "url": "https://example.com/result1",
            },
            {
                "title": f"Result 2 for '{query}'",
                "snippet": "Another simulated result demonstrating search functionality.",
                "url": "https://example.com/result2",
            },
        ],
        "total_results": 2,
    }


_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_web",
        description="Search the web for information on a given topic.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search query or topic to look up",
                }
            },
            "required": ["query"],
        },
    ),
]

_FUNCTIONS = {"search_web": search_web}


class ResearchAgent(BaseAgent):
    name = "research_agent"
    description = (
        "Specialises in web research – searching for information, "
        "summarising findings, and answering factual questions."
    )

    def _build_tools(self):
        return _DECLARATIONS, _FUNCTIONS

    def _system_instruction(self) -> str:
        return (
            "You are a **Research Agent**. Your job is to find information "
            "using web search and provide well-structured, factual summaries. "
            "Always cite your sources when possible. Be thorough but concise."
        )
