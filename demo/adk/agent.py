"""
Agentic AI using Google Generative AI SDK (Gemini)
Demonstrates autonomous agent with function calling and tool use.
"""

import os
from google import genai
from google.genai import types
from typing import Any, Dict, List, Optional
import json


class AgenticAI:
    """
    An autonomous AI agent powered by Google's Gemini API.

    The agent can:
    - Use tools/functions to perform actions
    - Reason about tasks and break them down
    - Make decisions autonomously
    - Chain multiple tool calls together
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/gemini-2.5-flash",
        tools: Optional[List[Dict]] = None,
        system_instruction: Optional[str] = None
    ):
        """
        Initialize the agentic AI.

        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY env var)
            model_name: Gemini model to use
            tools: List of tool definitions (function declarations)
            system_instruction: System prompt for the agent's behavior
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        self.client = genai.Client(api_key=self.api_key)

        self.model_name = model_name
        self.tools = tools or []
        self.system_instruction = system_instruction or self._default_system_instruction()

        self.chat_history = None
        self.conversation_history = []

    def _default_system_instruction(self) -> str:
        """Default system instruction for the agent."""
        return """You are an autonomous AI agent with access to tools.
        
Your capabilities:
- Analyze user requests and break them into steps
- Use available tools to accomplish tasks
- Chain multiple tool calls when needed
- Provide clear explanations of your actions
- Handle errors gracefully and try alternative approaches

Always think through the task step-by-step and use tools when they can help accomplish the goal."""

    def start_session(self):
        """Start a new chat session."""
        self.chat_history = []
        self.conversation_history = []
        return self

    def register_tool_functions(self, tool_functions: Dict[str, callable]):
        """
        Register Python functions that implement the tools.

        Args:
            tool_functions: Dict mapping function names to Python callables
        """
        self.tool_functions = tool_functions

    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool function.

        Args:
            function_name: Name of the function to execute
            arguments: Arguments to pass to the function

        Returns:
            Result of the function execution
        """
        if not hasattr(self, 'tool_functions'):
            raise ValueError("No tool functions registered")

        if function_name not in self.tool_functions:
            raise ValueError(f"Unknown function: {function_name}")

        func = self.tool_functions[function_name]

        try:
            result = func(**arguments)
            return result
        except Exception as e:
            return {"error": str(e)}

    def run(
        self,
        prompt: str,
        max_iterations: int = 10,
        verbose: bool = True
    ) -> str:
        """
        Run the agent with a prompt, allowing it to use tools autonomously.

        Args:
            prompt: User's task/question
            max_iterations: Maximum number of agent iterations
            verbose: Whether to print agent's reasoning

        Returns:
            Final response from the agent
        """
        if self.chat_history is None:
            self.start_session()

        if verbose:
            print(f"\n{'='*60}")
            print(f"User: {prompt}")
            print(f"{'='*60}\n")

        # Prepare tool configuration
        tool_config = None
        if self.tools:
            tool_config = types.Tool(function_declarations=self.tools)

        # Add user message to history
        self.chat_history.append(types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        ))

        iteration = 0

        # Agent loop: continue until agent stops using tools or max iterations
        while iteration < max_iterations:
            iteration += 1

            # Generate content with tools
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self.chat_history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=[tool_config] if tool_config else None,
                    temperature=0.7
                )
            )

            # Add assistant response to history
            self.chat_history.append(response.candidates[0].content)

            # Check if there are function calls
            has_function_call = False
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_function_call = True
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)

                    if verbose:
                        print(f"🤖 Agent calling tool: {function_name}")
                        print(
                            f"   Arguments: {json.dumps(function_args, indent=2)}\n")

                    # Execute the function
                    result = self.execute_function(
                        function_name, function_args)

                    if verbose:
                        print(f"🔧 Tool result: {result}\n")

                    # Add function response to history
                    self.chat_history.append(types.Content(
                        role="user",
                        parts=[types.Part(
                            function_response=types.FunctionResponse(
                                name=function_name,
                                response={"result": result}
                            )
                        )]
                    ))

            if not has_function_call:
                break

        # Extract final text response
        final_response = ""
        for part in response.candidates[0].content.parts:
            if part.text:
                final_response += part.text

        if verbose:
            print(f"\n{'='*60}")
            print(f"Agent: {final_response}")
            print(f"{'='*60}\n")

        self.conversation_history.append({
            "prompt": prompt,
            "response": final_response,
            "iterations": iteration
        })

        return final_response

    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history
