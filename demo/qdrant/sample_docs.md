# Vector Databases, RAG, and Agentic Search

## What is a Vector Database?

A vector database is a specialized data store built to index and query high-dimensional
vectors, also called embeddings. Unlike traditional relational databases that match rows
by exact values, vector databases find records by similarity — given a query vector, they
return the stored vectors that are "closest" to it in the embedding space. This makes them
the backbone of modern semantic search, recommendation systems, and retrieval-augmented
generation pipelines.

Qdrant is an open-source vector database written in Rust, designed for speed and
production reliability. It exposes a gRPC and REST API, supports payload filtering
alongside vector search, and can run as a single node or a distributed cluster. Qdrant
stores each vector together with an optional JSON payload, so you can attach metadata
like the source document, chunk index, timestamp, or access permissions and filter on
that metadata during search.

### Core concepts in Qdrant

- **Collection**: a named set of vectors that share the same dimensionality and distance
  metric (cosine, dot product, or Euclidean).
- **Point**: a single vector plus an id and an optional payload.
- **Distance metric**: the function used to compare two vectors. Cosine similarity is the
  most common choice for text embeddings because it ignores vector magnitude and focuses
  on direction.
- **HNSW index**: Qdrant uses Hierarchical Navigable Small World graphs under the hood to
  perform approximate nearest neighbor search efficiently, trading a small amount of
  recall for large gains in query speed at scale.
- **Payload filtering**: Qdrant can combine vector similarity with exact-match or range
  filters on payload fields, so you can search "find similar documents where
  source = 'handbook.md' and chunk_index < 50" in a single query.

## Embeddings and Sentence Transformers

An embedding model maps a piece of text into a fixed-length vector of floating point
numbers, positioned so that semantically similar text ends up close together in that
vector space and unrelated text ends up far apart. Sentence Transformers (the
`sentence-transformers` Python library) is a popular way to produce these embeddings
locally, without calling an external API.

The `all-MiniLM-L6-v2` model used in this demo is a compact, fast sentence transformer
that outputs 384-dimensional embeddings. It is not the most powerful embedding model
available, but it runs comfortably on a laptop CPU and is more than good enough for demo
and prototyping purposes. Larger, more accurate embedding models exist (some with 768 or
1536 dimensions) but require more memory and compute per encode call.

Choosing an embedding model involves a few tradeoffs:

1. **Dimensionality** — higher dimensional embeddings can capture more nuance but cost
   more to store and search.
2. **Domain fit** — a model trained on general web text may underperform on legal,
   medical, or code-heavy corpora compared to a domain-tuned model.
3. **Latency** — embedding a query at request time adds to end-to-end response latency,
   so smaller models are often preferred for interactive applications.
4. **Cost** — locally-run open models like MiniLM avoid per-call API costs, while hosted
   embedding APIs charge per token but require no local compute.

## Retrieval-Augmented Generation (RAG)

Large language models are trained on a fixed snapshot of data and have no direct
knowledge of private documents, recent events, or proprietary company data. RAG solves
this by retrieving relevant text from an external knowledge base at query time and
injecting it into the model's prompt as context, so the model can ground its answer in
real, up-to-date information rather than relying solely on what it memorized during
training.

A typical RAG pipeline has three stages:

1. **Indexing** — documents are split into chunks, each chunk is embedded, and the
   resulting vectors are stored in a vector database along with metadata pointing back to
   the source.
2. **Retrieval** — when a user asks a question, the question itself is embedded with the
   same model, and the vector database returns the top-K most similar chunks.
3. **Generation** — the retrieved chunks are inserted into a prompt template along with
   the original question, and an LLM generates an answer that is grounded in that
   context.

RAG reduces hallucination because the model is explicitly told to answer using the
provided context rather than inventing facts. It also makes it possible to update the
knowledge base (by re-indexing new documents) without retraining or fine-tuning the
underlying LLM at all.

### Chunking strategy

How you split documents into chunks has a big impact on retrieval quality. Chunks that
are too large dilute the embedding with multiple unrelated ideas, making it harder for
the retriever to find the exact passage that answers a question. Chunks that are too
small lose surrounding context and can be ambiguous on their own.

A common approach is fixed-size chunking with overlap: split the document into chunks of
roughly N characters (or tokens), and let each chunk overlap with the previous one by some
smaller number of characters. The overlap ensures that information sitting near a chunk
boundary is not split in a way that destroys its meaning — if a sentence gets cut off at
the end of one chunk, the overlap means it will appear complete at the start of the next
chunk too.

More advanced strategies include semantic chunking (splitting at natural paragraph or
section boundaries), recursive chunking (trying larger separators like double newlines
first, then falling back to sentences or words), and document-aware chunking that
respects markdown headers, code blocks, or table structures so a chunk never splits code
mid-function or a table mid-row.

## Agentic RAG with LangGraph

A plain RAG pipeline always retrieves before answering, even for questions that don't
need external context — like "what's 2 + 2" or "hello, how are you." An agentic RAG
system instead gives the LLM a retrieval tool and lets the model decide, per query,
whether and how many times to call it.

LangGraph implements this pattern as a state graph: an `agent` node calls the LLM, which
may choose to invoke a `retrieve_context` tool. If it does, control passes to a `tools`
node that executes the tool call and appends the results back into the conversation
history, then loops back to the `agent` node so the LLM can decide what to do next —
answer directly, or call the tool again with a refined query. Once the LLM responds
without requesting a tool call, the graph routes to a `finalize` node that extracts the
final answer.

This loop, commonly called the ReAct pattern (Reason + Act), allows the agent to perform
multi-hop retrieval: it can issue a first search, notice the results are insufficient or
point toward a related sub-question, and issue a second, more specific search before
answering. It generalizes RAG from a single fixed retrieval step into a flexible research
loop.

### Why this matters in production

In a production support-bot or internal-knowledge-base assistant, agentic RAG lets the
system:

- Skip retrieval entirely for small talk or general knowledge questions, saving latency
  and vector database load.
- Chain multiple retrievals together to answer compound questions ("compare the pricing
  of plan A and plan B") that a single vector search would not resolve well.
- Say "I don't know" when the retrieved context genuinely does not contain the answer,
  rather than confidently fabricating a response, because the system prompt explicitly
  instructs the model to rely on retrieved context.

## Docker Compose for Local Development

Running Qdrant locally is typically done through Docker Compose, which lets you describe
one or more containers, their ports, volumes, and environment variables in a single YAML
file and bring the whole stack up with one command: `docker-compose up -d`. For this demo,
Compose starts a Qdrant container exposing its REST API on port 6333 and gRPC on port
6334, with a mounted volume so indexed vectors persist across container restarts.

Using Compose for local development keeps the setup reproducible: any developer on the
team can clone the repository, run one command, and have an identical Qdrant instance
running locally, without manually installing or configuring the database.

## Summary

Together, these pieces form a complete local RAG stack: Qdrant as the vector store,
Sentence Transformers for local embeddings, chunking utilities to prepare large documents
for indexing, and a LangGraph agent that decides when to retrieve and when to answer
directly. This sample file itself exists to be chunked and indexed by
`index_document_file`, so that the agent has enough real content to search over instead of
the six one-line `DOCUMENTS` strings used in the basic demo.
