# Pinecone Vector Database Demo

This directory contains examples demonstrating how to use Pinecone, a high-performance vector database for semantic search, similarity matching, and AI applications.

## What is Pinecone?

Pinecone is a fully managed vector database that makes it easy to build high-performance vector search applications. It's commonly used for:
- Semantic search
- Recommendation systems
- Question answering systems
- Similarity matching
- RAG (Retrieval Augmented Generation) applications

## Prerequisites

1. **Pinecone Account**: Sign up for a free account at [pinecone.io](https://www.pinecone.io/)
2. **API Key**: Get your API key from the Pinecone console

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file or set the environment variable:

```bash
# On Windows (PowerShell)
$env:PINECONE_API_KEY="your-api-key-here"

# On Linux/Mac
export PINECONE_API_KEY="your-api-key-here"
```

Or copy the example env file and update it:
```bash
cp .env.example .env
# Edit .env and add your API key
```

## Examples Included

### 1. Basic Vector Operations (`basic_example()`)
Demonstrates fundamental Pinecone operations:
- Initializing the client
- Creating an index
- Upserting vectors
- Querying for similar vectors
- Getting index statistics

### 2. Text Embedding Search (`text_embedding_example()`)
Shows semantic search using sentence embeddings:
- Using SentenceTransformers to encode text
- Storing document embeddings
- Performing natural language queries
- Finding semantically similar documents

### 3. Namespace Organization (`namespace_example()`)
Demonstrates using namespaces to organize vectors:
- Creating multiple namespaces
- Upserting to specific namespaces
- Querying within namespaces
- Managing multi-tenant data

## Running the Examples

### Run All Examples
```bash
python pinecone_demo.py
```

### Run Specific Examples
You can modify `main()` to run specific examples:

```python
from pinecone_demo import basic_example, text_embedding_example

# Run only basic example
pc, index = basic_example()
```

## Key Concepts

### Index
A Pinecone index is a data structure that stores vectors and enables fast similarity search. Each index has:
- **Dimension**: The size of vectors it can store
- **Metric**: How similarity is calculated (cosine, euclidean, dotproduct)
- **Cloud/Region**: Where the index is hosted

### Vectors
Vectors are numerical representations of data (text, images, etc.). In ML, these are called embeddings.

### Metadata
Additional information stored with each vector. Useful for filtering and retrieving original data.

### Namespaces
Logical partitions within an index to organize vectors (e.g., by user, product category, etc.)

## Example Output

```
==================================================
Pinecone Basic Example
==================================================
Creating index 'demo-basic'...
Index 'demo-basic' is ready!
Upserted 10 vectors

Querying for similar vectors...

Top 3 similar vectors:
  ID: vec-5, Score: 0.8234, Metadata: {'text': 'Sample document 5', 'category': 'cat-2'}
  ID: vec-2, Score: 0.7891, Metadata: {'text': 'Sample document 2', 'category': 'cat-2'}
  ID: vec-7, Score: 0.7654, Metadata: {'text': 'Sample document 7', 'category': 'cat-1'}
```

## Common Use Cases

### 1. Semantic Search
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

# Encode documents
docs = ["Document 1 text", "Document 2 text"]
embeddings = model.encode(docs)

# Store in Pinecone
index.upsert(vectors=[(f"doc-{i}", emb.tolist()) for i, emb in enumerate(embeddings)])

# Search
query_emb = model.encode(["search query"])[0]
results = index.query(vector=query_emb.tolist(), top_k=5)
```

### 2. Filtering with Metadata
```python
# Upsert with metadata
index.upsert(vectors=[
    ("id1", vector1, {"category": "tech", "year": 2024}),
    ("id2", vector2, {"category": "science", "year": 2023})
])

# Query with filter
results = index.query(
    vector=query_vector,
    top_k=10,
    filter={"category": {"$eq": "tech"}, "year": {"$gte": 2024}}
)
```

### 3. RAG (Retrieval Augmented Generation)
```python
# 1. Retrieve relevant context
query_embedding = model.encode([user_question])[0]
results = index.query(vector=query_embedding.tolist(), top_k=3, include_metadata=True)

# 2. Build context from results
context = "\n".join([match['metadata']['text'] for match in results['matches']])

# 3. Generate answer with LLM
answer = llm.generate(f"Context: {context}\n\nQuestion: {user_question}")
```

## API Reference

### Key Methods

```python
# Initialize client
pc = Pinecone(api_key="your-api-key")

# Create index
pc.create_index(name="index-name", dimension=384, metric="cosine")

# Get index
index = pc.Index("index-name")

# Upsert vectors
index.upsert(vectors=[("id1", [0.1, 0.2, ...], {"key": "value"})])

# Query
results = index.query(vector=[0.1, 0.2, ...], top_k=10, include_metadata=True)

# Delete
index.delete(ids=["id1", "id2"])

# Delete by metadata filter
index.delete(filter={"category": "old"})

# Get stats
stats = index.describe_index_stats()
```

## Best Practices

1. **Choose the Right Dimension**: Match your embedding model's output dimension
2. **Use Metadata**: Store original text/data for easy retrieval
3. **Batch Operations**: Upsert in batches of 100-1000 for efficiency
4. **Use Namespaces**: Organize data logically (e.g., by user or tenant)
5. **Monitor Costs**: Be aware of index size and query volume
6. **Use Filters**: Reduce search space with metadata filters
7. **Test Locally First**: Use small dimensions for testing

## Troubleshooting

### API Key Not Found
```
ValueError: PINECONE_API_KEY not found in environment variables
```
**Solution**: Set the environment variable or pass it directly to `initialize_pinecone(api_key="your-key")`

### Index Already Exists
The code automatically handles this by deleting and recreating the index. In production, you'd typically check and reuse existing indexes.

### Dimension Mismatch
```
ValueError: dimension of upserted vectors must match index dimension
```
**Solution**: Ensure all vectors have the same dimension as the index

### Import Error for sentence-transformers
```
ImportError: No module named 'sentence_transformers'
```
**Solution**: `pip install sentence-transformers`

## Resources

- [Pinecone Documentation](https://docs.pinecone.io/)
- [Pinecone Python Client](https://github.com/pinecone-io/pinecone-python-client)
- [Sentence Transformers](https://www.sbert.net/)
- [Vector Database Use Cases](https://www.pinecone.io/learn/)

## Cleanup

To delete all demo indexes:

```python
from pinecone_demo import cleanup_indexes, initialize_pinecone

pc = initialize_pinecone()
cleanup_indexes(pc)
```

Or manually from the Pinecone console.

## Next Steps

1. Explore different embedding models (OpenAI, Cohere, HuggingFace)
2. Implement metadata filtering for advanced queries
3. Build a RAG application combining Pinecone with an LLM
4. Experiment with hybrid search (combining vector and keyword search)
5. Integrate with your application (Flask, FastAPI, etc.)
