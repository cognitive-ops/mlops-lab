import os

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.tools import ComponentTool
from haystack.components.websearch import SerperDevWebSearch

for _name in ("OPENAI_API_KEY", "SERPERDEV_API_KEY"):
    if not os.environ.get(_name):
        raise SystemExit(f"Set {_name} in your environment before running this demo.")

search_tool = ComponentTool(component=SerperDevWebSearch())

basic_agent = Agent(
    chat_generator=OpenAIChatGenerator(model="gpt-4o-mini"),
    system_prompt="You are a helpful web agent.",
    tools=[search_tool],
)

result = basic_agent.run(messages=[ChatMessage.from_user("When was the first version of Haystack released?")])

print(result['last_message'].text)
