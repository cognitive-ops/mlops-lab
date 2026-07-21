"""
Agentic AI Agent using OpenAI Function Calling
A simple but powerful agent that can use tools to accomplish tasks.
"""

import json
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI
import os


class Tool:
    """Represents a tool that the agent can use."""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool function."""
        return self.function(**kwargs)


class Agent:
    """Agentic AI Agent with tool-using capabilities."""
    
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        max_iterations: int = 10
    ):
        """Initialize the agent.
        
        Args:
            model: OpenAI model to use
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            max_iterations: Maximum reasoning iterations
        """
        self.model = model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.max_iterations = max_iterations
        self.tools: List[Tool] = []
        self.conversation_history: List[Dict[str, Any]] = []
    
    def add_tool(self, tool: Tool):
        """Add a tool to the agent's toolkit."""
        self.tools.append(tool)
        print(f"✅ Added tool: {tool.name}")
    
    def run(self, user_message: str, verbose: bool = True) -> str:
        """Run the agent to accomplish a task.
        
        Args:
            user_message: The user's request
            verbose: Print reasoning steps
            
        Returns:
            Final answer from the agent
        """
        # Initialize conversation
        self.conversation_history = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant with access to tools. "
                          "Use the tools when needed to answer questions accurately. "
                          "Think step by step and explain your reasoning."
            },
            {"role": "user", "content": user_message}
        ]
        
        if verbose:
            print(f"\n🤔 User: {user_message}\n")
        
        # Agent reasoning loop
        for iteration in range(self.max_iterations):
            if verbose:
                print(f"💭 Iteration {iteration + 1}/{self.max_iterations}")
            
            # Get agent's response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=[tool.to_openai_format() for tool in self.tools] if self.tools else None,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Check if agent wants to use tools
            if message.tool_calls:
                # Add assistant's message to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    if verbose:
                        print(f"🔧 Using tool: {tool_name}")
                        print(f"   Arguments: {tool_args}")
                    
                    # Find and execute the tool
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool:
                        try:
                            result = tool.execute(**tool_args)
                            if verbose:
                                print(f"   Result: {result}\n")
                            
                            # Add tool result to conversation
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(result)
                            })
                        except Exception as e:
                            error_msg = f"Error executing {tool_name}: {str(e)}"
                            if verbose:
                                print(f"   ❌ {error_msg}\n")
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": error_msg
                            })
                    else:
                        if verbose:
                            print(f"   ❌ Tool not found: {tool_name}\n")
            else:
                # Agent has final answer
                final_answer = message.content
                if verbose:
                    print(f"✅ Final Answer: {final_answer}\n")
                return final_answer
        
        return "Maximum iterations reached without final answer."


# =============================================================================
# Example Tools
# =============================================================================

def calculator(expression: str) -> float:
    """Safely evaluate a mathematical expression."""
    try:
        # Only allow basic math operations
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        result = eval(expression)
        return result
    except Exception as e:
        return f"Error: {str(e)}"


def get_weather(location: str) -> str:
    """Get weather information for a location (mock function)."""
    # In real implementation, you'd call a weather API
    mock_data = {
        "new york": "Sunny, 72°F",
        "london": "Cloudy, 15°C",
        "tokyo": "Rainy, 18°C",
        "paris": "Partly cloudy, 20°C"
    }
    return mock_data.get(location.lower(), f"Weather data not available for {location}")


def search_web(query: str) -> str:
    """Search the web for information (mock function)."""
    # In real implementation, you'd call a search API
    return f"Mock search results for '{query}': Based on recent data, the answer to your query is available in multiple sources."


def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================================================================
# Main Example
# =============================================================================

if __name__ == "__main__":
    # Create agent
    agent = Agent(model="gpt-4o")
    
    # Add tools
    agent.add_tool(Tool(
        name="calculator",
        description="Calculate mathematical expressions. Use this for any math problems.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '2 + 2', '10 * 5 + 3')"
                }
            },
            "required": ["expression"]
        },
        function=calculator
    ))
    
    agent.add_tool(Tool(
        name="get_weather",
        description="Get current weather information for a city.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city name (e.g., 'New York', 'London')"
                }
            },
            "required": ["location"]
        },
        function=get_weather
    ))
    
    agent.add_tool(Tool(
        name="search_web",
        description="Search the web for information.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        },
        function=search_web
    ))
    
    agent.add_tool(Tool(
        name="get_current_time",
        description="Get the current date and time.",
        parameters={
            "type": "object",
            "properties": {}
        },
        function=get_current_time
    ))
    
    # Example 1: Math calculation
    print("="*80)
    print("EXAMPLE 1: Math Calculation")
    print("="*80)
    agent.run("What is (25 * 4) + (100 / 2) - 10?")
    
    # Example 2: Weather query
    print("\n" + "="*80)
    print("EXAMPLE 2: Weather Query")
    print("="*80)
    agent.run("What's the weather like in London?")
    
    # Example 3: Multi-step reasoning
    print("\n" + "="*80)
    print("EXAMPLE 3: Multi-Step Reasoning")
    print("="*80)
    agent.run("If I have 15 apples and give away 1/3 of them, how many do I have left? Also, what time is it now?")
    
    # Example 4: Complex task
    print("\n" + "="*80)
    print("EXAMPLE 4: Complex Task")
    print("="*80)
    agent.run("Calculate 123 * 456, then tell me what the weather is like in Tokyo.")
