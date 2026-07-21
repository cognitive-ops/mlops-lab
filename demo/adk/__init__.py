"""
Agentic AI package using Google Generative AI SDK.
"""

from .agent import AgenticAI
from .tools import TOOL_DECLARATIONS, TOOL_FUNCTIONS
from .config import Config
from .agents import (
    AgentOrchestrator,
    BaseAgent,
    MathAgent,
    ResearchAgent,
    WeatherAgent,
    WriterAgent,
)

__version__ = "2.0.0"
__all__ = [
    "AgenticAI",
    "TOOL_DECLARATIONS",
    "TOOL_FUNCTIONS",
    "Config",
    "AgentOrchestrator",
    "BaseAgent",
    "MathAgent",
    "ResearchAgent",
    "WeatherAgent",
    "WriterAgent",
]
