# Multi-Agent Supervisor Pattern with LangGraph

A demonstration of the **supervisor multi-agent** architecture using LangGraph,
where a supervisor agent delegates tasks to specialised worker agents and
synthesises their outputs into a final answer.

## Architecture

```
                ┌─────────────┐
     User ─────►  Supervisor  │
                └──────┬──────┘
                       │ routes to
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │Researcher│ │  Coder   │ │ Analyst  │
    └────┬─────┘ └────┬─────┘ └────┬─────┘
         │            │            │
         └────────────┼────────────┘
                      ▼
               ┌────────────┐
               │  Synthesize │
               └──────┬─────┘
                      ▼
                    END
```

**Supervisor** – decides which worker(s) to invoke based on the user query.
**Researcher** – searches the web / knowledge base for facts.
**Coder** – writes, explains, or reviews code.
**Analyst** – performs calculations, data analysis, and reasoning.
**Synthesize** – merges all worker outputs into a coherent final answer.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenAI key
export OPENAI_API_KEY="sk-..."

# 3. Run the demo
python main.py
```

## Files

| File | Description |
|---|---|
| `state.py` | Shared `AgentState` TypedDict used by every node |
| `tools.py` | Tool definitions (calculator, search, code runner, …) |
| `agents/researcher.py` | Researcher worker agent |
| `agents/coder.py` | Coder worker agent |
| `agents/analyst.py` | Analyst worker agent |
| `supervisor.py` | Supervisor routing logic |
| `graph.py` | LangGraph `StateGraph` wiring |
| `main.py` | Entry point with example queries |

## Customisation

- **Add a new agent**: create a file under `agents/`, register it in `graph.py`, and update the supervisor prompt.
- **Change the LLM**: edit the model name in `supervisor.py` or each agent file.
- **Add tools**: define them in `tools.py` and bind them in the relevant agent.
