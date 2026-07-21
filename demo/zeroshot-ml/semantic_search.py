"""
Zero-Shot Semantic Search Example
Uses embeddings for semantic search without training
"""

import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
import json


def get_embeddings(texts, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """
    Get embeddings for texts using a pre-trained model
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    # Tokenize and encode
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )

    # Get embeddings
    with torch.no_grad():
        model_output = model(**encoded)

    # Use mean pooling
    embeddings = mean_pooling(
        model_output,
        encoded['attention_mask']
    )

    return embeddings


def mean_pooling(model_output, attention_mask):
    """Mean Pooling - Take attention mask into account for correct averaging"""
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(
        -1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return torch.nn.functional.cosine_similarity(a, b)


def zero_shot_semantic_search():
    """
    Perform semantic search without training
    """
    # Corpus of documents to search
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Python is a popular programming language",
        "Machine learning is a subset of artificial intelligence",
        "The Eiffel Tower is located in Paris",
        "A cat sat on the mat",
        "Deep learning uses neural networks",
        "France is known for wine and cheese",
        "Dogs are loyal pets",
        "Natural language processing helps computers understand text",
        "Artificial intelligence is transforming industries"
    ]

    # Query
    query = "programming and machine learning"

    print("=" * 60)
    print("ZERO-SHOT SEMANTIC SEARCH")
    print("=" * 60)
    print(f"\nQuery: {query}\n")

    # Get embeddings for documents and query
    all_texts = documents + [query]
    embeddings = get_embeddings(all_texts)

    query_embedding = embeddings[-1:, :]
    document_embeddings = embeddings[:-1, :]

    # Calculate similarities
    similarities = cosine_similarity(query_embedding, document_embeddings)[0]

    # Sort by similarity
    sorted_indices = torch.argsort(similarities, descending=True)

    print("Top Results:\n")
    results = []
    for rank, idx in enumerate(sorted_indices[:5], 1):
        doc = documents[idx]
        score = similarities[idx].item()
        print(f"{rank}. [{score:.4f}] {doc}")

        results.append({
            "rank": rank,
            "document": doc,
            "similarity": float(score)
        })

    return results


def zero_shot_duplicate_detection():
    """
    Detect similar/duplicate texts using embeddings
    """
    texts = [
        "I love machine learning and deep learning",
        "I enjoy learning about machine learning",
        "Python is a great programming language",
        "Python is an excellent programming language",
        "What time is the meeting?",
        "When is the meeting scheduled?"
    ]

    print("\n" + "=" * 60)
    print("ZERO-SHOT DUPLICATE DETECTION")
    print("=" * 60)

    # Get embeddings
    embeddings = get_embeddings(texts)

    # Calculate similarity matrix
    similarity_matrix = torch.nn.functional.cosine_similarity(
        embeddings.unsqueeze(1),
        embeddings.unsqueeze(0),
        dim=2
    )

    print("\nSimilarity Matrix:\n")
    print("Texts:")
    for i, text in enumerate(texts):
        print(f"  {i}: {text}")

    print("\nSimilarity Scores (threshold > 0.7 = potential duplicates):\n")

    duplicates = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            score = similarity_matrix[i][j].item()
            if score > 0.7:
                print(f"[{score:.4f}] Text {i} <-> Text {j}")
                duplicates.append({
                    "text_1": texts[i],
                    "text_2": texts[j],
                    "similarity": float(score)
                })

    return duplicates


def zero_shot_clustering():
    """
    Cluster texts without labeled training data
    """
    documents = [
        "Machine learning is revolutionizing AI",
        "Deep neural networks learn from data",
        "Paris is the capital of France",
        "The Eiffel Tower attracts millions of tourists",
        "Python programming language is popular",
        "JavaScript is used for web development"
    ]

    print("\n" + "=" * 60)
    print("ZERO-SHOT TEXT CLUSTERING")
    print("=" * 60)

    # Get embeddings
    embeddings = get_embeddings(documents)

    # Simple clustering using K-means-like approach
    # For simplicity, we'll use a threshold-based clustering
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler

    # Prepare data
    embeddings_np = embeddings.cpu().numpy()
    scaler = StandardScaler()
    embeddings_scaled = scaler.fit_transform(embeddings_np)

    # Cluster
    clustering = DBSCAN(eps=0.3, min_samples=1).fit(embeddings_scaled)
    labels = clustering.labels_

    print("\nClusters:\n")
    results = []
    for cluster_id in sorted(set(labels)):
        cluster_docs = [documents[i]
                        for i in range(len(documents)) if labels[i] == cluster_id]
        print(f"Cluster {cluster_id}:")
        for doc in cluster_docs:
            print(f"  - {doc}")
        print()

        results.append({
            "cluster_id": int(cluster_id),
            "documents": cluster_docs
        })

    return results


def main():
    """Run all semantic search examples"""
    print("\n" + "=" * 60)
    print("ZERO-SHOT SEMANTIC SEARCH DEMONSTRATION")
    print("=" * 60)

    search_results = zero_shot_semantic_search()
    duplicate_results = zero_shot_duplicate_detection()
    clustering_results = zero_shot_clustering()

    # Save results
    all_results = {
        "semantic_search": search_results,
        "duplicate_detection": duplicate_results,
        "clustering": clustering_results
    }

    with open("semantic_search_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 60)
    print("Results saved to semantic_search_results.json")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # Try importing required libraries
        try:
            from sklearn.cluster import DBSCAN
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            print("Installing scikit-learn for clustering example...")
            import subprocess
            subprocess.check_call(["pip", "install", "scikit-learn"])

        main()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        print("  pip install scikit-learn")
