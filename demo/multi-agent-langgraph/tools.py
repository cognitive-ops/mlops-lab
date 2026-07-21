"""
Tool definitions shared across worker agents.

Each tool is a @tool-decorated function that LangGraph/LangChain can bind to an LLM.
"""

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Research / Knowledge tools
# ---------------------------------------------------------------------------
@tool
def search_web(query: str) -> str:
    """Search the web for information on a topic.

    Args:
        query: The search query string.

    Returns:
        A summary of search results (mock).
    """
    # Replace with a real search API (Tavily, SerpAPI, etc.) in production
    mock_results = {
        "langgraph": (
            "LangGraph is a library by LangChain for building stateful, "
            "multi-actor applications with LLMs using graph-based workflows."
        ),
        "python": (
            "Python is a high-level, interpreted programming language known "
            "for its readability and large ecosystem of libraries."
        ),
        "kubernetes": (
            "Kubernetes (K8s) is an open-source container orchestration "
            "platform for automating deployment, scaling, and management."
        ),
    }
    query_lower = query.lower()
    for key, value in mock_results.items():
        if key in query_lower:
            return value
    return (
        f"Search results for '{query}': Multiple authoritative sources "
        "confirm this is a well-documented topic. Key findings include …"
    )


@tool
def lookup_knowledge_base(topic: str) -> str:
    """Look up internal knowledge base articles.

    Args:
        topic: The topic to look up.

    Returns:
        Knowledge base entry (mock).
    """
    kb = {
        "acme": "Acme Software is a global software company with 500+ engineers.",
        "mlops": "MLOps combines ML, DevOps, and data engineering for reliable ML in production.",
        "cicd": "CI/CD automates build, test, and deploy pipelines for faster delivery.",
    }
    topic_lower = topic.lower()
    for key, value in kb.items():
        if key in topic_lower:
            return value
    return f"No knowledge-base entry found for '{topic}'."


# ---------------------------------------------------------------------------
# Code tools
# ---------------------------------------------------------------------------
@tool
def run_python_code(code: str) -> str:
    """Execute a Python code snippet and return its output.

    Args:
        code: Python source code to execute.

    Returns:
        stdout output or error message.
    """
    import io
    import contextlib

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {"__builtins__": __builtins__}, {})  # noqa: S102
        output = stdout.getvalue()
        return output if output else "(no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@tool
def review_code(code: str) -> str:
    """Review a code snippet for common issues.

    Args:
        code: The source code to review.

    Returns:
        Review feedback (mock heuristic-based).
    """
    issues: list[str] = []
    if "eval(" in code:
        issues.append("⚠️  Avoid eval() – potential security risk.")
    if "import os" in code and "os.system" in code:
        issues.append("⚠️  os.system() is insecure; prefer subprocess.run().")
    if len(code.splitlines()) > 50:
        issues.append("Consider breaking the code into smaller functions.")
    if not issues:
        issues.append("✅  No obvious issues found. Looks good!")
    return "\n".join(issues)


# ---------------------------------------------------------------------------
# Analysis / Math tools
# ---------------------------------------------------------------------------
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Args:
        expression: A valid math expression (e.g. '2+2', '10**3').

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
def analyse_data(data_description: str) -> str:
    """Perform a high-level analysis based on a textual description of data.

    Args:
        data_description: A plain-English description of the dataset or numbers.

    Returns:
        Analytical summary (mock).
    """
    return (
        f"Analysis of '{data_description}': Based on the described data, "
        "the key trends show an upward trajectory with seasonal variation. "
        "Recommend further statistical testing for significance."
    )


# ---------------------------------------------------------------------------
# Convenience collections
# ---------------------------------------------------------------------------
researcher_tools = [search_web, lookup_knowledge_base]
coder_tools = [run_python_code, review_code]
analyst_tools = [calculator, analyse_data]
all_tools = researcher_tools + coder_tools + analyst_tools
