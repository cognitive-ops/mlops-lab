"""
RAG (Retrieval-Augmented Generation) using Qdrant as the vector store.
Run docker-compose up -d first to start a local Qdrant instance.
Requires ANTHROPIC_API_KEY for the generation step.
"""

import argparse
import os
import uuid
from dotenv import load_dotenv
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic

from qdrant_demo import initialize_client, create_collection, upsert_vectors, search_similar_vectors

load_dotenv()

COLLECTION_NAME = "rag-demo"
EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384
CHUNK_ID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")

DOCUMENTS = [
    "Qdrant is a vector database optimized for storing and searching high-dimensional embeddings.",
    "Retrieval-Augmented Generation (RAG) combines a retriever with an LLM to ground answers in real documents.",
    "Sentence transformers convert text into dense vector embeddings that capture semantic meaning.",
    "Cosine similarity measures the angle between two vectors and is commonly used for semantic search.",
    "Docker Compose lets you define and run multi-container applications with a single YAML file.",
    "LangChain provides abstractions for building LLM applications, including RAG pipelines.",
]


def index_documents(client, embedder, documents=DOCUMENTS):
    """Embed documents and upsert them into the Qdrant collection"""
    create_collection(client, COLLECTION_NAME, dimension=EMBED_DIM, distance=Distance.COSINE)
    embeddings = embedder.encode(documents)
    payloads = [{"text": doc} for doc in documents]
    upsert_vectors(client, COLLECTION_NAME, embeddings, payloads)


def ensure_collection(client, collection_name=COLLECTION_NAME, dimension=EMBED_DIM, distance=Distance.COSINE):
    """Create the collection only if it doesn't already exist (won't wipe existing data)"""
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dimension, distance=distance),
        )


def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    """Split text into overlapping chunks of roughly chunk_size characters"""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start = end - chunk_overlap
    return chunks


def index_document_file(client, embedder, file_path, chunk_size=1000, chunk_overlap=200, batch_size=64):
    """Chunk a large text/markdown file and upsert it into Qdrant in batches"""
    ensure_collection(client)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"'{file_path}': {len(chunks)} chunks")

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        embeddings = embedder.encode(batch)
        payloads = [
            {"text": chunk, "source": file_path, "chunk_index": batch_start + i}
            for i, chunk in enumerate(batch)
        ]
        ids = [
            str(uuid.uuid5(CHUNK_ID_NAMESPACE, f"{file_path}:{batch_start + i}"))
            for i in range(len(batch))
        ]
        upsert_vectors(client, COLLECTION_NAME, embeddings, payloads, ids)
        print(f"  upserted {batch_start + len(batch)}/{len(chunks)}")


def retrieve(client, embedder, question, top_k=3):
    """Embed the question and fetch the most relevant chunks from Qdrant"""
    query_vector = embedder.encode(question)
    results = search_similar_vectors(client, COLLECTION_NAME, query_vector, top_k=top_k)
    return [point.payload["text"] for point in results]


def generate(llm, question, context_chunks):
    """Call the LLM with retrieved context to answer the question"""
    context = "\n\n".join(context_chunks)
    prompt = f"""Use the following context to answer the question. If the answer isn't in the context, say you don't know. Keep it to 2-3 sentences.

Context:
{context}

Question: {question}

Answer:"""

    response = llm.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def rag_query(client, embedder, llm, question, top_k=3):
    """Full RAG pipeline: retrieve then generate"""
    context_chunks = retrieve(client, embedder, question, top_k=top_k)
    answer = generate(llm, question, context_chunks)
    return answer, context_chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Path to a large .txt/.md file to chunk and index")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--query", help="Ask a question against the indexed content instead of running the demo questions")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY in your environment or .env file")

    client = initialize_client()
    embedder = SentenceTransformer(EMBED_MODEL)
    llm = Anthropic()

    if args.file:
        index_document_file(client, embedder, args.file, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    else:
        print("Indexing documents into Qdrant...")
        index_documents(client, embedder)

    questions = [args.query] if args.query else [
        "What is Qdrant and what is it used for?",
       
    ]

    for question in questions:
        answer, context_chunks = rag_query(client, embedder, llm, question)
        print(f"\n--- Question: {question} ---")
        print("Retrieved context:")
        for chunk in context_chunks:
            print(f"  - {chunk}")
        print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
