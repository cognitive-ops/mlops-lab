# Insurance Intake Agent (LangGraph Multi-Agent)

A multi-agent **auto insurance policy application intake** pipeline built with
LangGraph. Collects applicant + vehicle details across turns, validates
completeness/format, screens underwriting risk, and produces a structured
application record.

## Architecture

```
              ┌─────────────┐
   User ─────►│ Supervisor  │◄────────────────┐
              └──────┬──────┘                 │
                      │ routes to              │
       ┌──────────────┼───────────────┬────────┴──────┐
       ▼               ▼               ▼               ▼
 ┌───────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐
 │ Extractor │  │ Validator  │  │ Risk       │  │ Ask User       │
 │           │  │            │  │ Screener   │  │ (pause turn)   │
 └─────┬─────┘  └─────┬──────┘  └─────┬──────┘  └───────┬────────┘
       │              │               │                 │
       └──────────────┴───────────────┘                 ▼
                      ▼                                 END
               ┌────────────┐
               │  Finalize  │
               └──────┬─────┘
                      ▼
                     END
```

**Supervisor** – deterministic router. Intake is a fixed pipeline with one
conditional branch (missing info → ask the user), so a rule-based router is
simpler and more reliable than an LLM routing decision every turn.

**Extractor** – LLM structured-output extraction (`ApplicantExtraction`
pydantic schema) pulls whatever fields the latest message mentions and
merges them into `applicant_data`. No tool-calling here — pure field
extraction fits structured output better than an agentic tool loop.

**Validator** – checks the 10 required fields (name, DOB, email, phone,
address, license number, vehicle make/model/year/VIN) are present and
well-formed. Anything missing/invalid goes into `missing_fields`.

**Ask User** – turns `missing_fields` into a follow-up question and ends the
turn (`status: "awaiting_info"`); the caller supplies the reply and
re-invokes the graph.

**Risk Screener** – mock underwriting rules (young/senior driver, vehicle
age, accident/violation mentions in the conversation) → `risk_flags`,
`risk_tier` (low/medium/high), and a mock `premium_estimate`.

**Finalize** – assembles `final_application`: applicant data + risk tier +
premium + decision (`approved_pending_review` or `submitted_for_underwriting`
for high-risk cases).

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenAI key
export OPENAI_API_KEY="sk-..."

# 3. Run the scripted scenarios (complete info, follow-up loop, high-risk case)
python main.py

# 4. Or chat with the agent live
python main.py --interactive
```

## Files

| File | Description |
|---|---|
| `state.py` | Shared `IntakeState` TypedDict used by every node |
| `schema.py` | `ApplicantExtraction` pydantic schema, required fields, follow-up prompts |
| `tools.py` | Validation helpers (email/phone/VIN/year/DOB) + mock premium estimator |
| `agents/extractor.py` | Extracts fields from the latest message |
| `agents/validator.py` | Checks completeness/format of `applicant_data` |
| `agents/ask_user.py` | Asks the follow-up question, pauses the turn |
| `agents/risk_screener.py` | Mock underwriting risk scoring |
| `supervisor.py` | Deterministic router + `finalize_node` |
| `graph.py` | LangGraph `StateGraph` wiring |
| `main.py` | Entry point: scripted scenarios + `--interactive` chat mode |

## Customisation

- **Extend to another policy type** (home, health): add fields to
  `schema.py`, adjust `REQUIRED_FIELDS`/`FIELD_PROMPTS`, and update
  `risk_screener.py`'s rules.
- **Real underwriting rules**: swap the mock logic in `tools.py` /
  `agents/risk_screener.py` for real rating tables or an external API call.
- **Persistence across sessions**: add a LangGraph checkpointer
  (`MemorySaver` or a DB-backed one) so `ask_user` pauses can resume across
  process restarts instead of just within one `main.py` run.
