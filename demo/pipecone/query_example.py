"""
Simple example to query Pinecone vector database
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import numpy as np

# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# List available indexes
print("Available indexes:")
for idx in pc.list_indexes():
    print(f"  - {idx.name}")

# Connect to an existing index (change this to your index name)
index_name = "demo-text"  # or "demo-basic", "demo-namespace"

try:
    index = pc.Index(index_name)
    print(f"\nConnected to index: {index_name}")
    
    # Get index stats
    stats = index.describe_index_stats()
    print(f"Index stats: {stats}")
    
    # Example 1: Query with a random vector (for demo-basic index)
    if index_name == "demo-basic":
        print("\n--- Example 1: Random Vector Query ---")
        query_vector = np.random.rand(8).astype('float32')  # dimension = 8
        
        results = index.query(
            vector=query_vector.tolist(),
            top_k=3,
            include_metadata=True
        )
        
        print(f"Top 3 similar vectors:")
        for match in results['matches']:
            print(f"  ID: {match['id']}")
            print(f"  Score: {match['score']:.4f}")
            print(f"  Metadata: {match.get('metadata', {})}")
            print()
    
    # Example 2: Query with text (for demo-text index)
    elif index_name == "demo-text":
        print("\n--- Example 2: Text Query ---")
        
        # Load the same model used to create embeddings
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Your search query
        query_text = "Who is Maria Ozawa?"
        
        # Convert query to vector
        query_vector = model.encode([query_text])[0]
        
        # Search
        results = index.query(
            vector=query_vector.tolist(),
            top_k=5,
            include_metadata=True
        )
        
        print(f"Query: '{query_text}'")
        print(f"\nTop {len(results['matches'])} similar documents:")
        for i, match in enumerate(results['matches'], 1):
            print(f"\n{i}. Score: {match['score']:.4f}")
            print(f"   Text: {match['metadata'].get('text', 'N/A')}")
    
    # Example 3: Query with namespace (for demo-namespace index)
    elif index_name == "demo-namespace":
        print("\n--- Example 3: Namespace Query ---")
        query_vector = np.random.rand(8).astype('float32')
        
        namespace = "products"  # or "users", "articles"
        
        results = index.query(
            vector=query_vector.tolist(),
            namespace=namespace,
            top_k=3,
            include_metadata=True
        )
        
        print(f"Querying namespace: '{namespace}'")
        print(f"Top 3 matches:")
        for match in results['matches']:
            print(f"  ID: {match['id']}, Score: {match['score']:.4f}")
    
    # Example 4: Query with metadata filter
    print("\n--- Example 4: Query with Filter ---")
    try:
        if index_name == "demo-text":
            model = SentenceTransformer('all-MiniLM-L6-v2')
            query_vector = model.encode(["technology"])[0]
        else:
            query_vector = np.random.rand(8 if index_name != "demo-text" else 384).astype('float32')
        
        results = index.query(
            vector=query_vector.tolist(),
            top_k=5,
            include_metadata=True,
            filter={"index": {"$gte": 0}}  # Adjust filter based on your metadata
        )
        
        print(f"Filtered results: {len(results['matches'])} matches")
        for match in results['matches']:
            print(f"  ID: {match['id']}, Score: {match['score']:.4f}")
    except Exception as e:
        print(f"Filter query not applicable: {e}")

except Exception as e:
    print(f"Error: {e}")
    print(f"\nMake sure the index '{index_name}' exists.")
    print("Run 'python pinecone_demo.py' first to create demo indexes.")
