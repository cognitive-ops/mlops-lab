"""
Shared state definition for the multi-agent system.

Every node in the graph reads from and writes to this state.
"""

from typing import Annotated, List, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State that flows through the entire multi-agent graph.

    Attributes:
        messages: Full conversation history (auto-accumulated via add_messages).
        next_agent: Which worker the supervisor wants to invoke next.
        worker_outputs: Collected outputs from each worker agent.
        iterations: Safety counter to prevent infinite loops.
        final_answer: The synthesised answer returned to the user.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    next_agent: str                       # "researcher" | "coder" | "analyst" | "synthesize" | "FINISH"
    worker_outputs: dict[str, str]        # {agent_name: output_text}
    iterations: int
    final_answer: str
