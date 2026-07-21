# ReactAgent with StateGraph Example

A complete implementation of a ReactAgent using LangGraph's StateGraph pattern.

## 🎯 What This Demonstrates

This example shows how to build a **ReAct (Reasoning + Acting) Agent** using LangGraph's StateGraph, which is the same pattern used in Acme Agent Studio.

## 🏗️ Architecture

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   agent     │ ◄─────┐
│  (LLM call) │       │
└──────┬──────┘       │
       │              │
       ▼              │
   [Decision]         │
       │              │
   ┌───┴───┐          │
   │       │          │
   ▼       ▼          │
┌──────┐ ┌────────┐  │
│ end  │ │ tools  │──┘
└───┬──┘ └────────┘
    │
    ▼
┌──────────┐
│finalize  │
└─────┬────┘
      │
      ▼
   ┌─────┐
   │ END │
   └─────┘
```

## 📋 Key Components

### 1. **State Definition** (`AgentState`)
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # Conversation history
    iterations: int                                       # Loop counter
    final_answer: str                                     # Final result
```

### 2. **Tools**
- **calculator**: Math operations
- **get_weather**: Weather information
- **search_database**: Knowledge queries

### 3. **Graph Nodes**
- **agent**: LLM decides next action (call tool or finish)
- **tools**: Execute tool calls
- **finalize**: Extract final answer

### 4. **Conditional Routing**
- **should_continue()**: Routes to "tools" or "end" based on LLM decision

## 🚀 Installation

```bash
pip install langchain langchain-core langchain-openai langgraph
```

## 💻 Usage

### Set API Key
```bash
export OPENAI_API_KEY='your-openai-api-key'
```

### Run the Example
```bash
python react_agent_example.py
```

### Use in Your Code
```python
from react_agent_example import run_agent

# Run a query
result = run_agent("What is 25 times 4?", verbose=True)

# Access final answer
print(result["final_answer"])
```

## 📊 Example Output

```
================================================================================
User Query: Calculate 100 divided by 4, then tell me the weather in London
================================================================================

--- Node: agent ---
Tool Calls: [{'name': 'calculator', 'args': {'expression': '100/4'}}]
Iterations: 1

--- Node: tools ---
Tool Result: Result: 25.0

--- Node: agent ---
Tool Calls: [{'name': 'get_weather', 'args': {'location': 'London'}}]
Iterations: 2

--- Node: tools ---
Tool Result: Weather in London: Cloudy, 15°C

--- Node: agent ---
AI Response: The result of 100 divided by 4 is 25. The weather in London is currently cloudy with a temperature of 15°C.
Iterations: 3

--- Node: finalize ---

================================================================================
✅ Final Answer:
The result of 100 divided by 4 is 25. The weather in London is currently cloudy with a temperature of 15°C.
================================================================================
```

## 🔑 Key Concepts

### **StateGraph**
- Defines nodes (functions) and edges (transitions)
- Manages state flow through the graph
- Supports conditional routing

### **ReAct Pattern**
```
1. THOUGHT: What do I need to do?
2. ACTION: Call appropriate tool
3. OBSERVATION: See tool result
4. [Repeat or finish]
5. FINAL ANSWER: Provide response
```

### **Message Accumulation**
```python
messages: Annotated[list[BaseMessage], add_messages]
```
The `add_messages` reducer automatically accumulates messages instead of replacing them.

### **Conditional Edges**
```python
workflow.add_conditional_edges(
    "agent",
    should_continue,  # Decision function
    {
        "tools": "tools",   # If needs tools
        "end": "finalize"   # If done
    }
)
```

### **Tool Binding**
```python
llm_with_tools = llm.bind_tools(tools)
```
Enables LLM to call tools automatically.

## 🎨 Customization

### Add New Tools
```python
@tool
def my_custom_tool(input: str) -> str:
    """Tool description for the LLM."""
    # Your logic here
    return "result"

# Add to tools list
tools.append(my_custom_tool)
```

### Modify State
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    final_answer: str
    # Add your custom fields
    user_context: dict
    confidence_score: float
```

### Change LLM
```python
llm = ChatOpenAI(
    model="gpt-4",  # or "gpt-3.5-turbo", "claude-3", etc.
    temperature=0.7,
    max_tokens=2000
)
```

### Add Memory/Checkpoints
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

## 🔍 Comparison with Acme Agent Studio

This example mirrors the architecture in `acme-agent-studio/backend/src/core/agents/react_agent/`:

| **Component** | **This Example** | **Acme Agent Studio** |
|---------------|------------------|-------------------------|
| State | `AgentState` | `ReactAgentState` |
| Graph Builder | `create_react_agent_graph()` | `build_graph()` |
| LLM Node | `call_model()` | `run_react_agent()` |
| Tool Node | `ToolNode(tools)` | `ToolNode(tools)` |
| Routing | `should_continue()` | Built into graph |
| Finalization | `finalize_answer()` | `finalize()` |

**Key Differences:**
- Studio adds **Storage** for persistent state
- Studio has **Transparent Streaming** via SSE
- Studio includes **Validation** hooks
- Studio supports **Multi-tenancy**

## 📚 Learn More

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Acme Agent Studio Backend README](../../acme-agent-studio/backend/src/agents/README.md)
- [StateGraph Tutorial](https://langchain-ai.github.io/langgraph/tutorials/introduction/)

## 🐛 Troubleshooting

**Error: "OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY='sk-...'
```

**Error: "Import Error"**
```bash
pip install --upgrade langchain langchain-core langchain-openai langgraph
```

**Graph doesn't execute tools**
- Check that tools are properly decorated with `@tool`
- Verify tools are in the `tools` list
- Ensure LLM is bound with `llm.bind_tools(tools)`

## 🎯 Next Steps

1. **Add more tools** - Expand capabilities
2. **Add persistence** - Use checkpointers for memory
3. **Add streaming** - Stream responses in real-time
4. **Add validation** - Validate tool inputs/outputs
5. **Deploy** - Turn into a FastAPI service

---

**Happy Agent Building! 🤖**
