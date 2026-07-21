import os

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.tools import ComponentTool
from haystack.components.websearch import SerperDevWebSearch

os.environ["OPENAI_API_KEY"] = "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"
os.environ["SERPERDEV_API_KEY"] = "e3d46ef2f76715fea7b94eb590c26dd6cc1faa5e"

search_tool = ComponentTool(component=SerperDevWebSearch())

basic_agent = Agent(
    chat_generator=OpenAIChatGenerator(model="gpt-4o-mini"),
    system_prompt="You are a helpful web agent.",
    tools=[search_tool],
)

result = basic_agent.run(messages=[ChatMessage.from_user("When was the first version of Haystack released?")])

print(result['last_message'].text)
