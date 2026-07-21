# Agentic AI with Google Generative AI SDK (Gemini)

A demonstration of autonomous AI agents using Google's Gemini API (new `google-genai` SDK) with function calling capabilities.

## 🎯 Overview

This project showcases how to build an **agentic AI system** that can:
- ✅ Autonomously break down complex tasks
- ✅ Use multiple tools to accomplish goals
- ✅ Chain function calls together
- ✅ Reason about which tools to use and when
- ✅ Handle errors and adapt strategies

## 🏗️ Architecture

### Single Agent (v1)

```
┌─────────────┐
│    User     │
│   Prompt    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   Agentic AI (Gemini)       │
│  - Reasoning Engine         │
│  - Task Decomposition       │
│  - Tool Selection           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│        Tool Layer           │
│  • Calculator               │
│  • Weather API              │
│  • Web Search               │
│  • Note Taking              │
│  • Time/Date                │
└─────────────────────────────┘
```

### Multi-Agent Orchestrator (v2)

```
┌──────────────────┐
│   User Request   │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│            Agent Orchestrator                 │
│  ┌────────────────────────────────────────┐  │
│  │  1. Task Analysis     (Gemini)         │  │
│  │  2. Agent Selection   (Planner)        │  │
│  │  3. Strategy Choice                    │  │
│  │     • single / parallel / sequential   │  │
│  └────────────────┬───────────────────────┘  │
│                   │                          │
│    ┌──────────────┼──────────────┐           │
│    ▼              ▼              ▼           │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│ │ Weather  │ │  Math    │ │ Research │     │
│ │  Agent   │ │  Agent   │ │  Agent   │     │
│ └──────────┘ └──────────┘ └──────────┘     │
│                   │                          │
│                   ▼                          │
│          ┌──────────────┐                    │
│          │ Writer Agent │                    │
│          └──────────────┘                    │
│                   │                          │
│  ┌────────────────┴───────────────────────┐  │
│  │  4. Result Synthesis  (Gemini)         │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Unified Answer│
          └────────────────┘
```

## 📁 Project Structure

```
adk/
├── agent.py                    # Legacy single-agent AgenticAI class
├── tools.py                    # Legacy tool definitions
├── agents/                     # Multi-agent system
│   ├── __init__.py
│   ├── base_agent.py           # BaseAgent – shared agent foundation
│   ├── orchestrator.py         # AgentOrchestrator – routes & synthesises
│   ├── weather_agent.py        # Weather data retrieval
│   ├── math_agent.py           # Calculations & unit conversion
│   ├── research_agent.py       # Web search & research
│   └── writer_agent.py         # Note-taking & content generation
├── orchestrator_example.py     # Multi-agent demo & interactive mode
├── example_usage.py            # Single-agent examples
├── config.py                   # Configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Google AI API key ([Get one here](https://ai.google.dev/))

### Installation

1. **Navigate to this directory:**
   ```bash
   cd ai/backbone-mlops/demo/adk
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   
   Create a `.env` file:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and add your Google API key:
   ```
   GOOGLE_API_KEY=your_actual_api_key_here
   ```
   
   **Optional**: Add OpenWeatherMap API key for enhanced weather data:
   ```
   OPENWEATHER_API_KEY=your_openweather_key_here
   ```
   (Without this, the weather tool will use wttr.in, which works without an API key)

### Quick Test

Run a simple test to verify everything works:
```bash
python simple_test.py
```

You should see the agent autonomously calling tools and chaining multiple operations together!

## 💻 Usage

### Quick Test

```bash
python simple_test.py
```

This runs a simple demonstration showing the agent calling tools autonomously.

### Run Full Demo Examples

```bash
python example_usage.py
```

This will run several demonstrations showing the agent:
- Performing calculations
- Using multiple tools in sequence
- Conducting research
- Handling complex multi-step tasks

### Interactive Mode

```bash
python example_usage.py --interactive
```

This starts an interactive session where you can chat with the agent and see it use tools in real-time.

### Custom Implementation

```python
from agent import AgenticAI
from tools import TOOL_DECLARATIONS, TOOL_FUNCTIONS

# Initialize the agent
agent = AgenticAI(
    model_name="models/gemini-2.5-flash",
    tools=TOOL_DECLARATIONS
)

# Register tool implementations
agent.register_tool_functions(TOOL_FUNCTIONS)

# Start a session
agent.start_session()

# Run a task
response = agent.run(
    "Get the weather in Tokyo and save it to a note",
    verbose=True
)

print(response)
```

## 🤖 Multi-Agent Orchestrator (NEW)

The orchestrator manages multiple specialised agents and automatically routes
tasks to the right agent(s).

### Quick Start

```bash
python orchestrator_example.py
```

### Interactive Orchestrator Mode

```bash
python orchestrator_example.py --interactive
```

### How It Works

1. **Task Analysis** – Gemini analyses the user request.
2. **Agent Selection** – The planner picks one or more agents and chooses a strategy:
   - `single` – one agent handles everything.
   - `parallel` – independent subtasks run concurrently across agents.
   - `sequential` – subtasks execute in order; later steps receive earlier results.
3. **Execution** – Each selected agent runs its subtask autonomously.
4. **Synthesis** – Gemini merges all sub-results into a single, coherent answer.

### Available Agents

| Agent | Description | Tools |
|-------|-------------|-------|
| `weather_agent` | Real-time weather data | `get_weather`, `get_forecast` |
| `math_agent` | Calculations & conversions | `calculate`, `unit_convert` |
| `research_agent` | Web search & research | `search_web` |
| `writer_agent` | Content, notes & reports | `save_note`, `read_note`, `get_current_time` |

### Programmatic Usage

```python
from agents import (
    AgentOrchestrator,
    WeatherAgent,
    MathAgent,
    ResearchAgent,
    WriterAgent,
)

# Build the orchestrator
orchestrator = (
    AgentOrchestrator(verbose=True)
    .register_agent(WeatherAgent())
    .register_agent(MathAgent())
    .register_agent(ResearchAgent())
    .register_agent(WriterAgent())
)

# Single request – the orchestrator routes automatically
answer = orchestrator.run(
    "Get the weather in London and Paris, calculate the average "
    "temperature, and write a travel advisory note."
)
print(answer)

# Inspect what happened
for step in orchestrator.get_trace():
    print(f"  [{step['agent']}] {step['task'][:60]}...")
```

### Creating a Custom Agent

Extend `BaseAgent` to add your own specialised agent:

```python
from agents.base_agent import BaseAgent
from google.genai import types

class DatabaseAgent(BaseAgent):
    name = "database_agent"
    description = "Runs SQL queries against a database."

    def _build_tools(self):
        declarations = [
            types.FunctionDeclaration(
                name="run_query",
                description="Execute a SQL query.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "sql": {"type": "STRING", "description": "SQL statement"}
                    },
                    "required": ["sql"],
                },
            )
        ]
        functions = {"run_query": self._run_query}
        return declarations, functions

    def _run_query(self, sql: str):
        # ... your implementation ...
        return {"rows": []}

    def _system_instruction(self) -> str:
        return "You are a Database Agent. Write safe, read-only SQL."

# Register it
orchestrator.register_agent(DatabaseAgent())
```

## 🛠️ Available Tools

The agent has access to the following tools:

| Tool | Description |
|------|-------------|
| `calculate` | Evaluate mathematical expressions (supports sqrt, sin, cos, pi, etc.) |
| `get_weather` | **Get REAL weather information** for any city (uses wttr.in or OpenWeatherMap) 🌤️ |
| `search_web` | Search the web for information (simulated for demo) |
| `save_note` | Save notes to a file with title and content |
| `get_current_time` | Get current date and time in a timezone |

### 🌍 Weather API Details

The `get_weather` tool fetches **real-time weather data** using two APIs:

**Primary (wttr.in)** - No API key needed:
- ✅ Works out of the box
- ✅ Global coverage
- ✅ Provides temperature, conditions, humidity, wind speed, UV index
- 🔗 Free service: https://wttr.in

**Secondary (OpenWeatherMap)** - Optional, requires free API key:
- 📊 More detailed weather data
- 🎯 Additional fields like "feels like" temperature, pressure
- 🔑 Get free API key: https://openweathermap.org/api
- ⚙️ Set `OPENWEATHER_API_KEY` in your `.env` file to use

The agent automatically chooses the best available source!

## 🔧 Adding Custom Tools

To add your own tools:

1. **Implement the function in `tools.py`:**
   ```python
   def my_custom_tool(param1: str, param2: int) -> Dict[str, Any]:
       """Your tool implementation."""
       # Your logic here
       return {"result": "success"}
   ```

2. **Add the declaration to `TOOL_DECLARATIONS`:**
   ```python
   {
       "name": "my_custom_tool",
       "description": "What your tool does",
       "parameters": {
           "type": "object",
           "properties": {
               "param1": {
                   "type": "string",
                   "description": "Description of param1"
               },
               "param2": {
                   "type": "integer",
                   "description": "Description of param2"
               }
           },
           "required": ["param1", "param2"]
       }
   }
   ```

3. **Register it in `TOOL_FUNCTIONS`:**
   ```python
   TOOL_FUNCTIONS = {
       # ... existing tools ...
       "my_custom_tool": my_custom_tool
   }
   ```

## 🧪 Example Scenarios

### Scenario 1: Multi-Step Calculation
```python
agent.run("Calculate the square root of 256, then multiply it by pi")
```

The agent will:
1. Use `calculate` to find sqrt(256) = 16
2. Use `calculate` to multiply 16 * pi
3. Return the final result

### Scenario 2: Research and Save
```python
agent.run("Search for information about AI agents and save a summary note")
```

The agent will:
1. Use `search_web` to find information
2. Analyze the results
3. Use `save_note` to create a summary

### Scenario 3: Weather Comparison
```python
agent.run("Compare the weather in London and Paris, calculate the average temperature")
```

The agent will:
1. Use `get_weather` for London
2. Use `get_weather` for Paris
3. Use `calculate` to find the average
4. Provide a comparison

## 📊 How It Works

### Agentic Loop

```
1. User provides a task
       ↓
2. Agent analyzes and plans
       ↓
3. Agent selects appropriate tool(s)
       ↓
4. Tool(s) execute and return results
       ↓
5. Agent processes results
       ↓
6. If task incomplete, goto step 3
       ↓
7. Agent provides final response
```

### Key Features

- **Autonomous Decision Making**: The agent decides which tools to use and when
- **Chain of Thought**: Can perform multi-step reasoning
- **Error Handling**: Gracefully handles tool failures
- **Context Awareness**: Maintains conversation context across tool calls

## 🎓 Key Concepts

### What is an Agentic AI?

An **agentic AI** is an autonomous AI system that can:
- Set and pursue goals
- Use tools to interact with the environment
- Make decisions without constant human intervention
- Learn from feedback and adapt strategies

### Function Calling

Google's Gemini API supports **function calling**, allowing the model to:
- Recognize when a tool would be helpful
- Generate properly formatted function calls
- Process function results
- Chain multiple function calls together

## 🔐 Security Notes

- **API Keys**: Keep your `GOOGLE_API_KEY` and `OPENWEATHER_API_KEY` secret. Never commit them to version control.
- **Tool Safety**: The `calculate` function uses restricted `eval()`. Be cautious when modifying.
- **Weather API**: 
  - **wttr.in** (default): No API key needed, works out of the box
  - **OpenWeatherMap** (optional): Requires free API key, provides more detailed data
- **Production Ready**: Weather API is production-ready. Web search is currently simulated - replace with real search API for production.

## 📚 Resources

- [Google AI Studio](https://ai.google.dev/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Function Calling Guide](https://ai.google.dev/docs/function_calling)

## 🤝 Contributing

Feel free to extend this demo with:
- Additional tools (database access, file operations, API integrations)
- Multi-agent collaboration
- Long-term memory systems
- More sophisticated planning algorithms

## 📝 License

This is a demo project for learning purposes.

## ✨ Advanced Usage

### Custom System Instructions

```python
agent = AgenticAI(
    model_name="models/gemini-2.5-flash",
    tools=TOOL_DECLARATIONS,
    system_instruction="""You are a specialized research assistant.
    Always cite sources and verify information before responding."""
)
```

### Tracking Agent Behavior

```python
# Get conversation history
history = agent.get_history()

for task in history:
    print(f"Task: {task['prompt']}")
    print(f"Iterations: {task['iterations']}")
    print(f"Response: {task['response']}")
```

---

**Built with ❤️ using Google Gemini API**
