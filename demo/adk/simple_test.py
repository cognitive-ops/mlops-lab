"""
Simple test of the Agentic AI.
Run this after setting up your GOOGLE_API_KEY in .env
"""

from tools import TOOL_DECLARATIONS, TOOL_FUNCTIONS
from agent import AgenticAI
import os
from dotenv import load_dotenv

load_dotenv()


def simple_test():
    """Run a simple test of the agent."""

    # Initialize the agent
    agent = AgenticAI(
        model_name="models/gemini-2.5-flash",
        tools=TOOL_DECLARATIONS
    )

    # Register tools
    agent.register_tool_functions(TOOL_FUNCTIONS)

    # Start session
    agent.start_session()

    print("\n🚀 Testing Agentic AI with Google Gemini\n")
    print("="*60)

    # Test 1: Simple calculation
    print("\n📊 Test 1: Simple Math")
    print("-"*60)
    result = agent.run(
        "Calculate the square root of 256",
        verbose=True
    )

    # Test 2: Multi-step task
    print("\n🌍 Test 2: Multi-Step Task")
    print("-"*60)
    result = agent.run(
        "Get the weather for Tokyo and save it to a note titled 'Tokyo Weather'",
        verbose=True
    )

    print("\n✅ Tests completed!")
    print("\nConversation history:")
    for i, item in enumerate(agent.get_history(), 1):
        print(
            f"  {i}. {item['prompt'][:50]}... ({item['iterations']} iterations)")


if __name__ == "__main__":
    simple_test()
