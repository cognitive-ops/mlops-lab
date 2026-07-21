"""
Qdrant Vector Database Demo
This example demonstrates how to use Qdrant for semantic search and similarity matching.
Run docker-compose up -d first to start a local Qdrant instance.
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np

# Load environment variables from .env file
load_dotenv()


def initialize_client(url=None, api_key=None):
    """Initialize Qdrant client"""
    if url is None:
        url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    if api_key is None:
        api_key = os.environ.get("QDRANT_API_KEY") or None

    return QdrantClient(url=url, api_key=api_key)


def create_collection(client, collection_name="demo-collection", dimension=384, distance=Distance.COSINE):
    """Create a new Qdrant collection (recreates if it already exists)"""
    if client.collection_exists(collection_name):
        print(f"Collection '{collection_name}' already exists. Recreating...")
        client.delete_collection(collection_name)

    print(f"Creating collection '{collection_name}'...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dimension, distance=distance),
    )
    print(f"Collection '{collection_name}' is ready!")
    return collection_name


def upsert_vectors(client, collection_name, vectors, payloads=None, ids=None):
    """Insert or update vectors in the collection"""
    if payloads is None:
        payloads = [{} for _ in range(len(vectors))]
    if ids is None:
        ids = list(range(len(vectors)))

    points = [
        PointStruct(id=id_, vector=vector.tolist(), payload=payload)
        for id_, vector, payload in zip(ids, vectors, payloads)
    ]

    client.upsert(collection_name=collection_name, points=points, wait=True)
    print(f"Upserted {len(vectors)} vectors into '{collection_name}'")


def search_similar_vectors(client, collection_name, query_vector, top_k=5, query_filter=None):
    """Search for similar vectors"""
    return client.query_points(
        collection_name=collection_name,
        query=query_vector.tolist(),
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    ).points


def basic_example():
    """Basic Qdrant workflow example"""
    print("=" * 50)
    print("Qdrant Basic Example")
    print("=" * 50)

    client = initialize_client()

    dimension = 8  # Small dimension for demo
    collection_name = create_collection(client, "demo-basic", dimension=dimension)

    num_vectors = 10
    vectors = np.random.rand(num_vectors, dimension).astype("float32")
    payloads = [
        {"text": f"Sample document {i}", "category": f"cat-{i % 3}"}
        for i in range(num_vectors)
    ]

    upsert_vectors(client, collection_name, vectors, payloads)

    print("\nQuerying for similar vectors...")
    query_vector = np.random.rand(dimension).astype("float32")
    results = search_similar_vectors(client, collection_name, query_vector, top_k=3)

    print("\nTop 3 similar vectors:")
    for point in results:
        print(f"  ID: {point.id}, Score: {point.score:.4f}, Payload: {point.payload}")

    return client


def text_embedding_example():
    """Example using sentence embeddings for semantic search"""
    print("\n" + "=" * 50)
    print("Qdrant Text Embedding Example")
    print("=" * 50)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers not installed. Install with: pip install sentence-transformers")
        return

    client = initialize_client()

    print("Loading sentence transformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    dimension = 384  # Dimension for all-MiniLM-L6-v2

    collection_name = create_collection(client, "demo-text", dimension=dimension)

    documents = [
        "Artificial intelligence is transforming industries",
        "Machine learning models require large datasets",
        "Deep learning uses neural networks with multiple layers",
        "Natural language processing enables computers to understand text",
        "Computer vision helps machines interpret images",
        "Python is a popular programming language for data science",
        "Cloud computing provides scalable infrastructure",
        "Database systems store and manage data efficiently",
    ]

    print("Generating embeddings...")
    embeddings = model.encode(documents)

    payloads = [{"text": doc, "index": i} for i, doc in enumerate(documents)]
    upsert_vectors(client, collection_name, embeddings, payloads)

    queries = [
        "Who is the CEO of Apple?",
        "What language is best for data science?",
        "Tell me about neural networks",
    ]

    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        query_embedding = model.encode([query])[0]
        results = search_similar_vectors(client, collection_name, query_embedding, top_k=3)

        for i, point in enumerate(results, 1):
            print(f"  {i}. Score: {point.score:.4f}")
            print(f"     Text: {point.payload['text']}")

    return client


def filtered_search_example():
    """Example using payload filters to scope a search"""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    print("\n" + "=" * 50)
    print("Qdrant Filtered Search Example")
    print("=" * 50)

    client = initialize_client()

    dimension = 8
    collection_name = create_collection(client, "demo-filter", dimension=dimension)

    categories = ["products", "users", "articles"]
    vectors, payloads, ids = [], [], []
    for cat_idx, category in enumerate(categories):
        for i in range(5):
            vectors.append(np.random.rand(dimension).astype("float32"))
            payloads.append({"category": category, "id": i})
            ids.append(cat_idx * 5 + i)

    upsert_vectors(client, collection_name, np.array(vectors), payloads, ids)

    query_vector = np.random.rand(dimension).astype("float32")

    for category in categories:
        results = search_similar_vectors(
            client,
            collection_name,
            query_vector,
            top_k=2,
            query_filter=Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            ),
        )
        print(f"\nTop 2 matches in '{category}':")
        for point in results:
            print(f"  ID: {point.id}, Score: {point.score:.4f}")

    return client


def cleanup_collections(client, prefix="demo-"):
    """Delete all demo collections"""
    print("\n" + "=" * 50)
    print("Cleaning up demo collections...")
    print("=" * 50)

    demo_collections = [
        c.name for c in client.get_collections().collections if c.name.startswith(prefix)
    ]

    for name in demo_collections:
        print(f"Deleting collection: {name}")
        client.delete_collection(name)

    print("Cleanup complete!")


def main():
    """Run all examples"""
    try:
        client = basic_example()
        text_embedding_example()
        filtered_search_example()

        # Optional: Cleanup (comment out if you want to keep the collections)
        # cleanup_collections(client)

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
