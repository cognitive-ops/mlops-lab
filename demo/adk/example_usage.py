"""
Example usage of the Agentic AI with Google Gemini.
"""

from tools import TOOL_DECLARATIONS, TOOL_FUNCTIONS
from agent import AgenticAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    """Run example scenarios with the agentic AI."""

    # Initialize the agent with tools
    agent = AgenticAI(
        model_name="models/gemini-2.5-flash",
        tools=TOOL_DECLARATIONS
    )

    # Register the tool implementations
    agent.register_tool_functions(TOOL_FUNCTIONS)

    # Start a conversation session
    agent.start_session()

    print("\n" + "="*80)
    print("AGENTIC AI DEMO - Google Gemini with Function Calling")
    print("="*80)

    # Example 1: Math calculation
    print("\n📊 Example 1: Mathematical Reasoning")
    print("-" * 80)
    agent.run(
        "What is the square root of 144 plus the sine of pi/2? Calculate this for me."
    )

    # Example 2: Multi-step task with multiple tools
    print("\n🌤️  Example 2: Multi-Tool Task")
    print("-" * 80)
    agent.run(
        "Get the weather for New York, then save a note with the title 'Weather Report' "
        "that includes the weather details and the current time."
    )

    # Example 3: Research and summarize
    print("\n🔍 Example 3: Research Task")
    print("-" * 80)
    agent.run(
        "Search for information about 'agentic AI systems', then calculate how many "
        "results were found times 5."
    )

    # Example 4: Complex reasoning
    print("\n🧠 Example 4: Complex Autonomous Task")
    print("-" * 80)
    agent.run(
        "I need to know the weather in London and Paris. Then calculate the average "
        "temperature between them. Finally, save a note comparing the weather in both cities."
    )

    # Print conversation summary
    print("\n" + "="*80)
    print("CONVERSATION SUMMARY")
    print("="*80)
    history = agent.get_history()
    for i, item in enumerate(history, 1):
        print(f"\nTask {i}:")
        print(f"  Iterations: {item['iterations']}")
        print(f"  Prompt: {item['prompt'][:60]}...")

    print("\n✅ Demo completed successfully!")


def interactive_mode():
    """Run the agent in interactive mode."""

    # Initialize the agent
    agent = AgenticAI(
        model_name="models/gemini-2.5-flash",
        tools=TOOL_DECLARATIONS
    )
    agent.register_tool_functions(TOOL_FUNCTIONS)
    agent.start_session()

    print("\n" + "="*80)
    print("INTERACTIVE AGENTIC AI MODE")
    print("="*80)
    print("\nThe agent has access to the following tools:")
    for tool in TOOL_DECLARATIONS:
        print(f"  • {tool['name']}: {tool['description']}")

    print("\nType 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Ending session. Goodbye!")
                break

            if not user_input:
                continue

            agent.run(user_input)

        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        main()
