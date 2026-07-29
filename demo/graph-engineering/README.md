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
      │   Shared Knowledge Graph (Neo4j)     │
      └─────────────────────────────────────┘
```

**Supervisor** – routes each call to `extractor` (ingest mode) or `query_agent`
(query mode) based on `state["mode"]`.
**Extractor** – LLM extracts `(subject, relation, object)` triples from raw
text and writes them into the shared graph.
**Query Agent** – LLM identifies which known entities a question touches,
pulls the bounded subgraph around them (`k`-hop Cypher traversal), and
answers grounded *only* in those facts — the retrieved triples are printed
alongside the answer so the reasoning path is inspectable, unlike
vector-RAG's opaque similarity match.
**Knowledge Graph** (`kg.py`) – `KnowledgeGraph` wrapper over the Neo4j Python
driver. Entities are `(:Entity {name})` nodes with a uniqueness constraint;
relations become Cypher relationship types (sanitized from the LLM's free-text
relation label to prevent Cypher injection, original text kept as `r.label`).

## Quick Start

```bash
# 1. Start Neo4j (browser at http://localhost:7474, default login neo4j/password)
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your OpenAI key (and Neo4j creds if you changed them)
export OPENAI_API_KEY="sk-..."
# export NEO4J_URI="bolt://localhost:7687"
# export NEO4J_USER="neo4j"
# export NEO4J_PASSWORD="password"

# 4. Run the small example
python main.py

# 5. Run the full scripted demo (multi-source ingest + multi-hop questions)
python demo.py
```

`demo.py` ingests five sentences from different "sources," then asks
questions that require hopping across more than one edge to answer
(e.g. *"Who leads the company that owns GitHub?"* requires
`GitHub —acquired_by→ Microsoft —ceo→ Satya Nadella`). Open
http://localhost:7474 and run `MATCH (n)-[r]->(m) RETURN n, r, m` to see the
graph built during the run.

## Files

| File | Description |
|---|---|
| `kg.py` | `KnowledgeGraph` wrapper over the Neo4j driver — add triples, bounded-hop subgraph retrieval, shortest path |
| `docker-compose.yml` | Local Neo4j instance for the demo |
| `state.py` | Shared `GraphState` TypedDict used by every node |
| `agents/extractor.py` | Extractor worker: text → triples → writes to KG |
| `agents/query_agent.py` | Query worker: question → entity match → subgraph retrieval → grounded answer |
| `supervisor.py` | Routes ingest vs. query |
| `graph.py` | LangGraph `StateGraph` wiring (the *orchestration* graph, distinct from the knowledge graph) |
| `main.py` | Minimal entry point |
| `demo.py` | Scripted multi-source ingest + multi-hop Q&A |

## Customisation

- **Add an agent**: e.g. a "curator" node that dedupes/merges near-duplicate entities before they're written to the graph.
- **Tune retrieval**: `hops` in `kg.subgraph_for()` controls how far the query agent looks from the seed entities (variable-length Cypher path) — raise it for more context, lower it to reduce noise/token cost.
- **Change the LLM**: edit the model name in `agents/extractor.py` / `agents/query_agent.py`.
- **Remote/managed Neo4j**: point `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` at AuraDB or any Neo4j instance instead of the local container.
