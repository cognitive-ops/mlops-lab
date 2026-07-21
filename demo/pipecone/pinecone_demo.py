"""
Pinecone Vector Database Demo
This example demonstrates how to use Pinecone for semantic search and similarity matching.
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import time
import numpy as np

# Load environment variables from .env file
load_dotenv()


def initialize_pinecone(api_key=None):
    """Initialize Pinecone client"""
    if api_key is None:
        api_key = os.environ.get("PINECONE_API_KEY")
    
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    
    pc = Pinecone(api_key=api_key)
    return pc


def create_index(pc, index_name="demo-index", dimension=384, metric="cosine"):
    """Create a new Pinecone index"""
    # Check if index already exists
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if index_name in existing_indexes:
        print(f"Index '{index_name}' already exists. Deleting...")
        pc.delete_index(index_name)
        time.sleep(1)
    
    # Create new index
    print(f"Creating index '{index_name}'...")
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )
    
    # Wait for index to be ready
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)
    
    print(f"Index '{index_name}' is ready!")
    return pc.Index(index_name)


def upsert_vectors(index, vectors, metadata=None):
    """Insert or update vectors in the index"""
    if metadata is None:
        metadata = [{} for _ in range(len(vectors))]
    
    # Prepare vectors for upsert
    upsert_data = [
        (f"vec-{i}", vector.tolist(), meta) 
        for i, (vector, meta) in enumerate(zip(vectors, metadata))
    ]
    
    # Upsert vectors
    index.upsert(vectors=upsert_data)
    print(f"Upserted {len(vectors)} vectors")


def query_similar_vectors(index, query_vector, top_k=5, include_metadata=True):
    """Query for similar vectors"""
    results = index.query(
        vector=query_vector.tolist(),
        top_k=top_k,
        include_metadata=include_metadata
    )
    return results


def basic_example():
    """Basic Pinecone workflow example"""
    print("=" * 50)
    print("Pinecone Basic Example")
    print("=" * 50)
    
    # 1. Initialize Pinecone
    pc = initialize_pinecone()
    
    # 2. Create index
    dimension = 8  # Small dimension for demo
    index = create_index(pc, index_name="demo-basic", dimension=dimension)
    
    # 3. Create sample vectors
    num_vectors = 10
    vectors = np.random.rand(num_vectors, dimension).astype('float32')
    
    # Create metadata
    metadata = [
        {"text": f"Sample document {i}", "category": f"cat-{i % 3}"}
        for i in range(num_vectors)
    ]
    
    # 4. Upsert vectors
    upsert_vectors(index, vectors, metadata)
    
    # Give it a moment to process
    time.sleep(2)
    
    # 5. Query similar vectors
    print("\nQuerying for similar vectors...")
    query_vector = np.random.rand(dimension).astype('float32')
    results = query_similar_vectors(index, query_vector, top_k=3)
    
    print(f"\nTop 3 similar vectors:")
    for match in results['matches']:
        print(f"  ID: {match['id']}, Score: {match['score']:.4f}, Metadata: {match.get('metadata', {})}")
    
    # 6. Get index stats
    stats = index.describe_index_stats()
    print(f"\nIndex stats: {stats}")
    
    return pc, index


def text_embedding_example():
    """Example using sentence embeddings for semantic search"""
    print("\n" + "=" * 50)
    print("Pinecone Text Embedding Example")
    print("=" * 50)
    
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers not installed. Install with: pip install sentence-transformers")
        return
    
    # 1. Initialize Pinecone
    pc = initialize_pinecone()
    
    # 2. Load embedding model
    print("Loading sentence transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    dimension = 384  # Dimension for all-MiniLM-L6-v2
    
    # 3. Create index
    index = create_index(pc, index_name="demo-text", dimension=dimension)
    
    # 4. Sample documents
    documents = [
        "Artificial intelligence is transforming industries",
        "Machine learning models require large datasets",
        "Deep learning uses neural networks with multiple layers",
        "Natural language processing enables computers to understand text",
        "Computer vision helps machines interpret images",
        "Python is a popular programming language for data science",
        "Cloud computing provides scalable infrastructure",
        "Database systems store and manage data efficiently",
        "Maria Ozawa is a well-known actress",
    ]
    
    # 5. Generate embeddings
    print("Generating embeddings...")
    embeddings = model.encode(documents)
    
    # 6. Prepare metadata
    metadata = [{"text": doc, "index": i} for i, doc in enumerate(documents)]
    
    # 7. Upsert to Pinecone
    upsert_data = [
        (f"doc-{i}", embedding.tolist(), meta)
        for i, (embedding, meta) in enumerate(zip(embeddings, metadata))
    ]
    index.upsert(vectors=upsert_data)
    print(f"Upserted {len(documents)} document embeddings")
    
    # Give it a moment to process
    time.sleep(2)
    
    # 8. Query with natural language
    queries = [
        "How do computers understand images?",
        "What language is best for data science?",
        "Tell me about neural networks"
    ]
    
    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        query_embedding = model.encode([query])[0]
        results = query_similar_vectors(index, query_embedding, top_k=3)
        
        for i, match in enumerate(results['matches'], 1):
            print(f"  {i}. Score: {match['score']:.4f}")
            print(f"     Text: {match['metadata']['text']}")
    
    return pc, index


def namespace_example():
    """Example using namespaces to organize vectors"""
    print("\n" + "=" * 50)
    print("Pinecone Namespace Example")
    print("=" * 50)
    
    # 1. Initialize Pinecone
    pc = initialize_pinecone()
    
    # 2. Create index
    dimension = 8
    index = create_index(pc, index_name="demo-namespace", dimension=dimension)
    
    # 3. Upsert vectors to different namespaces
    namespaces = ["products", "users", "articles"]
    
    for namespace in namespaces:
        vectors = np.random.rand(5, dimension).astype('float32')
        metadata = [{"namespace": namespace, "id": i} for i in range(5)]
        
        upsert_data = [
            (f"{namespace}-{i}", vector.tolist(), meta)
            for i, (vector, meta) in enumerate(zip(vectors, metadata))
        ]
        
        index.upsert(vectors=upsert_data, namespace=namespace)
        print(f"Upserted 5 vectors to namespace '{namespace}'")
    
    # Give it a moment to process
    time.sleep(2)
    
    # 4. Query specific namespace
    query_vector = np.random.rand(dimension).astype('float32')
    
    for namespace in namespaces:
        results = index.query(
            vector=query_vector.tolist(),
            namespace=namespace,
            top_k=2,
            include_metadata=True
        )
        print(f"\nTop 2 matches in '{namespace}' namespace:")
        for match in results['matches']:
            print(f"  ID: {match['id']}, Score: {match['score']:.4f}")
    
    # 5. Get stats by namespace
    stats = index.describe_index_stats()
    print(f"\nNamespace stats: {stats}")
    
    return pc, index


def cleanup_indexes(pc):
    """Delete all demo indexes"""
    print("\n" + "=" * 50)
    print("Cleaning up demo indexes...")
    print("=" * 50)
    
    demo_indexes = [idx.name for idx in pc.list_indexes() if idx.name.startswith("demo-")]
    
    for index_name in demo_indexes:
        print(f"Deleting index: {index_name}")
        pc.delete_index(index_name)
    
    print("Cleanup complete!")


def main():
    """Run all examples"""
    try:
        # Run basic example
        pc, _ = basic_example()
        
        # Run text embedding example
        text_embedding_example()
        
        # Run namespace example
        namespace_example()
        
        # Optional: Cleanup (comment out if you want to keep the indexes)
        # cleanup_indexes(pc)
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
