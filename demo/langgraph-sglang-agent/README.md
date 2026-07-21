# LangGraph ReAct Agent on Self-Hosted SGLang

A LangGraph ReAct agent whose LLM calls go to a self-hosted SGLang server instead of a hosted API — no API key or per-token billing, runs entirely on infra you control.

```
START ──► agent ──► [has tool_calls?] ──► tools ──► agent (loop)
                            │
                            └─► end (no tool_calls) ──► END
```

Uses `langchain_openai.ChatOpenAI` pointed at SGLang's OpenAI-compatible endpoint — SGLang is a drop-in swap for `ChatOpenAI(base_url=...)`, no custom LangChain integration needed.

## Prerequisites

Start the SGLang server first (either target works, same API contract):

- **Local Docker**: [demo/sglang](../sglang) — `cd ../sglang && make up`
- **AWS**: [iac/sglang-selfhost](../../iac/sglang-selfhost) — use the `api_endpoint` Terraform output as `SGLANG_BASE_URL`

Tool calling requires the server launched with a `--tool-call-parser` matching the model family (already wired into both of the above for the default Llama-3.1-8B-Instruct — parser `llama3`). Using a different model family, update the parser there too.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env if SGLANG_BASE_URL / MODEL_REPO differ from the defaults
```

## Run

```bash
python agent.py "What's 47 * 89, and what's the weather in Tokyo?"
```

Expected flow: the agent calls `calculator` and `get_weather`, then synthesizes both results into a final answer. Verbose mode prints each graph step (tool calls, tool results, final response).

## Files

| File | Description |
|---|---|
| `tools.py` | Tool definitions (`calculator`, `get_weather`, `search_knowledge_base`) |
| `agent.py` | `ChatOpenAI` client wiring + LangGraph `StateGraph` (agent/tools loop) |

## Swapping models

Change `MODEL_REPO` in `.env` to match whatever the SGLang server is currently serving, and update `TOOL_CALL_PARSER` on the server side (see [demo/sglang/README.md](../sglang/README.md#swapping-models)) if it's a different model family.

## Notes

- `temperature=0` in `agent.py` for deterministic tool-routing — raise it for more creative final answers.
- This is a single ReAct agent. For a multi-agent supervisor pattern, see [demo/multi-agent-langgraph](../multi-agent-langgraph) — swap its `ChatOpenAI(...)` calls for the same `base_url`/`api_key` override used here to run it against SGLang too.
