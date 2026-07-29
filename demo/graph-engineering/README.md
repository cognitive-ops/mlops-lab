# Graph Engineering: Knowledge Graph + Multi-Agent (Graph-RAG)

A demonstration of **agents collaborating through a shared knowledge graph**
instead of a vector store — a multi-agent "graph engineering" pattern where
one agent *builds* the graph and another *reasons* over it (Graph-RAG).

## Architecture

```
                 ┌─────────────┐
     input ─────►│ Supervisor  │
                 └──────┬──────┘
                        │ routes by mode
           ┌────────────┴────────────┐
           ▼ mode="ingest"            ▼ mode="query"
    ┌──────────────┐           ┌──────────────┐
    │  Extractor    │           │ Query Agent  │
    │  text→triples │           │ Q → subgraph │
    └──────┬───────┘           │   → answer   │
           │                    └──────┬───────┘
           ▼                           ▼
      ┌─────────────────────────────────────┐
      │   Shared Knowledge Graph (networkx)  │
      └─────────────────────────────────────┘
```

**Supervisor** – routes each call to `extractor` (ingest mode) or `query_agent`
(query mode) based on `state["mode"]`.
**Extractor** – LLM extracts `(subject, relation, object)` triples from raw
text and writes them into the shared graph.
**Query Agent** – LLM identifies which known entities a question touches,
pulls the bounded subgraph around them (`k`-hop BFS), and answers grounded
*only* in those facts — the retrieved triples are printed alongside the
answer so the reasoning path is inspectable, unlike vector-RAG's opaque
similarity match.
**Knowledge Graph** (`kg.py`) – in-memory `networkx.MultiDiGraph` singleton,
shared by every node in the process. No external DB required for the demo;
swap in Neo4j/Memgraph by reimplementing `KnowledgeGraph` behind the same
interface if you need persistence or multi-process sharing.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenAI key
export OPENAI_API_KEY="sk-..."

# 3. Run the small example
python main.py

# 4. Run the full scripted demo (multi-source ingest + multi-hop questions + graph image)
python demo.py
```

`demo.py` ingests five sentences from different "sources," then asks
questions that require hopping across more than one edge to answer
(e.g. *"Who leads the company that owns GitHub?"* requires
`GitHub —acquired_by→ Microsoft —ceo→ Satya Nadella`). It also saves
`knowledge_graph.png` showing the graph built during the run.

## Files

| File | Description |
|---|---|
| `kg.py` | `KnowledgeGraph` wrapper around `networkx` — add triples, bounded-hop subgraph retrieval, shortest path, drawing |
| `state.py` | Shared `GraphState` TypedDict used by every node |
| `agents/extractor.py` | Extractor worker: text → triples → writes to KG |
| `agents/query_agent.py` | Query worker: question → entity match → subgraph retrieval → grounded answer |
| `supervisor.py` | Routes ingest vs. query |
| `graph.py` | LangGraph `StateGraph` wiring (the *orchestration* graph, distinct from the knowledge graph) |
| `main.py` | Minimal entry point |
| `demo.py` | Scripted multi-source ingest + multi-hop Q&A + visualization |

## Customisation

- **Swap the store**: reimplement `KnowledgeGraph` in `kg.py` against Neo4j/Memgraph for persistence across runs or multiple processes.
- **Add an agent**: e.g. a "curator" node that dedupes/merges near-duplicate entities before they're written to the graph.
- **Tune retrieval**: `hops` in `kg.subgraph_for()` controls how far the query agent looks from the seed entities — raise it for more context, lower it to reduce noise/token cost.
- **Change the LLM**: edit the model name in `agents/extractor.py` / `agents/query_agent.py`.
