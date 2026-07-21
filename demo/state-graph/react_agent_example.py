"""
Sample ReactAgent with StateGraph implementation.

This example demonstrates:
- Custom State definition with TypedDict
- StateGraph workflow creation
- ReAct pattern (Thought -> Action -> Observation)
- Tool integration
- Conditional routing based on agent decisions
"""

import os
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode


# ============================================================================
# STEP 1: Define State
# ============================================================================
class AgentState(TypedDict):
    """State for the React Agent.

    The state tracks:
    - messages: Conversation history (auto-accumulated with add_messages)
    - iterations: Number of reasoning loops
    - final_answer: The agent's final response
    """
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    final_answer: str


# ============================================================================
# STEP 2: Define Tools
# ============================================================================
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A valid Python math expression like "2+2" or "10*5"

    Returns:
        The result of the calculation
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_weather(location: str) -> str:
    """Get weather information for a location.

    Args:
        location: City name or location

    Returns:
        Weather information (mock data)
    """
    # Mock weather data
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
def search_database(query: str) -> str:
    """Search a database for information.

    Args:
        query: Search query

    Returns:
        Search results (mock data)
    """
    # Mock database
    database = {
        "Huyen": "Python is a high-level programming language.",
        "ai": "Artificial Intelligence simulates human intelligence.",
        "langgraph": "LangGraph is a library for building stateful AI agents.",
    }

    query_lower = query.lower()
    for key, value in database.items():
        if key in query_lower:
            return value

    return f"No results found for: {query}"


# Tool list
tools = [calculator, get_weather, search_database]


# ============================================================================
# STEP 3: Define Graph Nodes
# ============================================================================
def call_model(state: AgentState) -> AgentState:
    """Node that calls the LLM to decide next action.

    The LLM can either:
    - Call a tool (returns tool calls)
    - Provide final answer (no tool calls)
    """
    messages = state["messages"]
    iterations = state.get("iterations", 0)

    # Initialize LLM with tools
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    llm_with_tools = llm.bind_tools(tools)

    # Add system message on first iteration
    if iterations == 0:
        system_message = HumanMessage(
            content="""You are a helpful AI assistant with access to tools.

Available tools:
- calculator: For math calculations
- get_weather: For weather information
- search_database: For general knowledge queries

Think step by step:
1. Analyze the user's question
2. Decide which tool(s) to use
3. Call tools to gather information
4. Provide a comprehensive answer

If you have all the information needed, provide the final answer without calling more tools."""
        )
        messages = [system_message] + messages

    # Call LLM
    response = llm_with_tools.invoke(messages)

    # Update state
    return {
        "messages": [response],
        "iterations": iterations + 1
    }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Conditional edge that determines next step.

    Returns:
        "tools" if LLM wants to call tools
        "end" if LLM provided final answer
    """
    last_message = state["messages"][-1]

    # Check if there are tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def finalize_answer(state: AgentState) -> AgentState:
    """Extract final answer from the last message."""
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage):
        final_answer = last_message.content
    else:
        final_answer = str(last_message)

    return {
        "final_answer": final_answer
    }


# ============================================================================
# STEP 4: Build StateGraph
# ============================================================================
def create_react_agent_graph() -> StateGraph:
    """Create the ReactAgent StateGraph.

    Graph structure:
        START -> agent -> [tools OR end]
        tools -> agent (loop back)
        end -> finalize -> END
    """
    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("finalize", finalize_answer)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": "finalize"
        }
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Add edge from finalize to END
    workflow.add_edge("finalize", END)

    return workflow


# ============================================================================
# STEP 5: Run the Agent
# ============================================================================
def run_agent(user_query: str, verbose: bool = True):
    """Execute the ReactAgent with a user query.

    Args:
        user_query: The user's question
        verbose: Whether to print step-by-step output
    """
    # Create and compile graph
    workflow = create_react_agent_graph()
    app = workflow.compile()

    # Initial state
    initial_state = {
        "messages": [HumanMessage(content=user_query)],
        "iterations": 0,
        "final_answer": ""
    }

    print(f"\n{'='*80}")
    print(f"User Query: {user_query}")
    print(f"{'='*80}\n")

    # Run the agent
    final_state = None
    for step_output in app.stream(initial_state):
        if verbose:
            for node_name, node_state in step_output.items():
                print(f"--- Node: {node_name} ---")

                # Print messages
                if "messages" in node_state:
                    last_message = node_state["messages"][-1]

                    if isinstance(last_message, AIMessage):
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            print(f"Tool Calls: {last_message.tool_calls}")
                        else:
                            print(f"AI Response: {last_message.content}")
                    elif isinstance(last_message, ToolMessage):
                        print(f"Tool Result: {last_message.content}")

                # Print iterations
                if "iterations" in node_state:
                    print(f"Iterations: {node_state['iterations']}")

                print()

        final_state = node_state

    # Print final answer
    if final_state and "final_answer" in final_state:
        print(f"{'='*80}")
        print(f"✅ Final Answer:\n{final_state['final_answer']}")
        print(f"{'='*80}\n")

    return final_state


# ============================================================================
# STEP 6: Visualization (Optional)
# ============================================================================
def visualize_graph():
    """Generate a visual representation of the graph."""
    try:
        from IPython.display import Image, display

        workflow = create_react_agent_graph()
        app = workflow.compile()

        # Generate graph image
        img = Image(app.get_graph().draw_mermaid_png())
        display(img)

        print("Graph visualization displayed!")
    except ImportError:
        print("Install 'pygraphviz' and run in Jupyter to visualize the graph")
    except Exception as e:
        print(f"Visualization error: {e}")


# ============================================================================
# Main Execution
# ============================================================================
if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Error: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        exit(1)

    # Example queries
    queries = [
        "Who is Huyen?"
    ]

    for query in queries:
        run_agent(query, verbose=True)
        print("\n" + "="*80 + "\n")
    visualize_graph()
    print("Demo completed!")
