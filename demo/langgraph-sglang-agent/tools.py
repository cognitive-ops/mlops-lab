"""Tool definitions for the SGLang-backed ReAct agent."""

from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A valid math expression, e.g. "2+2" or "10**3".

    Returns:
        The numeric result as a string, or an error message.
    """
    allowed = set("0123456789+-*/(). eE")
    if not all(c in allowed for c in expression):
        return "Error: expression contains disallowed characters."
    try:
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@tool
def get_weather(location: str) -> str:
    """Get weather information for a location.

    Args:
        location: City name or location.

    Returns:
        Weather information (mock data).
    """
    weather_data = {
        "new york": "Sunny, 72°F",
        "london": "Cloudy, 15°C",
        "tokyo": "Rainy, 20°C",
        "paris": "Clear, 18°C",
    }
    location_lower = location.lower()
    for city, weather in weather_data.items():
        if city in location_lower:
            return f"Weather in {location}: {weather}"
    return f"Weather data not available for {location}"


@tool
def search_knowledge_base(query: str) -> str:
    """Search an internal knowledge base for information.

    Args:
        query: Search query.

    Returns:
        Matching entry, or a not-found message (mock data).
    """
    kb = {
        "sglang": "SGLang is an LLM serving engine with RadixAttention for automatic KV-cache reuse across requests.",
        "langgraph": "LangGraph is a library for building stateful, multi-actor applications with LLMs using graph-based workflows.",
        "acme": "Acme Software is a global software company with 500+ engineers.",
    }
    query_lower = query.lower()
    for key, value in kb.items():
        if key in query_lower:
            return value
    return f"No knowledge-base entry found for '{query}'."


tools = [calculator, get_weather, search_knowledge_base]
