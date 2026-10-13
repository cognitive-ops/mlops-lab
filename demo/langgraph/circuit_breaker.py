"""Circuit breaker pattern in a LangGraph agent.

pip install langgraph

Flow:
    START -> gate --allow--> call_tool --ok--> END
               |                 |
               |                 +--fail, attempts left--> gate
               |                 +--fail, no attempts----> fallback
               +--open (blocked)--------------------------> fallback -> END

Breaker states:
    CLOSED     normal, calls pass through
    OPEN       too many failures, calls blocked until cooldown expires
    HALF_OPEN  cooldown over, one trial call allowed; success closes, failure reopens
"""
import random
import threading
import time
from enum import Enum
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Shared across graph runs (module/process scope), so failures accumulate."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = BreakerState.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == BreakerState.OPEN:
                if time.monotonic() - self.opened_at >= self.recovery_timeout:
                    self.state = BreakerState.HALF_OPEN  # allow one trial call
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.state = BreakerState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == BreakerState.HALF_OPEN or self.failures >= self.failure_threshold:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()


breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)


# ---- flaky downstream dependency (LLM / API / tool) ----
def flaky_service(query: str) -> str:
    if random.random() < 0.7:
        raise ConnectionError("upstream unavailable")
    return f"answer for: {query}"


# ---- graph ----
class AgentState(TypedDict):
    query: str
    result: str
    error: str
    attempts: int
    max_attempts: int
    breaker_state: str


def gate(state: AgentState) -> dict:
    return {"breaker_state": breaker.state.value}


def route_gate(state: AgentState) -> Literal["call_tool", "fallback"]:
    return "call_tool" if breaker.allow() else "fallback"


def call_tool(state: AgentState) -> dict:
    attempts = state["attempts"] + 1
    try:
        result = flaky_service(state["query"])
        breaker.record_success()
        return {"result": result, "error": "", "attempts": attempts,
                "breaker_state": breaker.state.value}
    except Exception as exc:
        breaker.record_failure()
        return {"error": str(exc), "attempts": attempts,
                "breaker_state": breaker.state.value}


def route_after_call(state: AgentState) -> Literal["gate", "fallback", "__end__"]:
    if not state["error"]:
        return END
    if state["attempts"] >= state["max_attempts"]:
        return "fallback"
    return "gate"  # retry through the gate, so an opened breaker stops retries


def fallback(state: AgentState) -> dict:
    return {"result": "FALLBACK: service degraded, try later (cached/default answer)"}


builder = StateGraph(AgentState)
builder.add_node("gate", gate)
builder.add_node("call_tool", call_tool)
builder.add_node("fallback", fallback)

builder.add_edge(START, "gate")
builder.add_conditional_edges("gate", route_gate)
builder.add_conditional_edges("call_tool", route_after_call)
builder.add_edge("fallback", END)

graph = builder.compile()


if __name__ == "__main__":
    random.seed(1)
    for i in range(12):
        out = graph.invoke({
            "query": f"q{i}", "result": "", "error": "",
            "attempts": 0, "max_attempts": 15, "breaker_state": "",
        })
        print(f"run {i:2d} | breaker={breaker.state.value:9s} "
              f"attempts={out['attempts']} | {out['result']}")
        time.sleep(1)
