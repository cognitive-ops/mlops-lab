"""
DSPy RAG System with Custom Retriever using FAISS
This example demonstrates a more advanced RAG pipeline with a custom retriever
"""

import os
import json
import numpy as np
from typing import List, Optional
import dspy
from dspy import Module, ChainOfThought, Predict, LM


class FAISSRetriever(dspy.Retrieve):
    """Custom FAISS-based retriever for DSPy"""

    def __init__(self, corpus: List[str], k: int = 3):
        super().__init__(k=k)
        self.corpus = corpus
        self.embeddings = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """Initialize embeddings using sentence transformers"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("Install sentence-transformers: pip install sentence-transformers")
            return

        model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = model.encode(self.corpus)

    def forward(self, query: str, k: Optional[int] = None):
        """Retrieve similar documents"""
        if self.embeddings is None:
            return dspy.Prediction(passages=[])

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return dspy.Prediction(passages=[])

        k = k or self.k
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_embedding = model.encode(query)

        # Calculate similarity scores
        scores = np.dot(self.embeddings, query_embedding)
        top_k_indices = np.argsort(scores)[-k:][::-1]

        passages = [self.corpus[i] for i in top_k_indices]
        return dspy.Prediction(passages=passages)


class AdvancedRAGPipeline(Module):
    """Advanced RAG pipeline with custom retriever"""

    def __init__(self, retriever: dspy.Retrieve):
        super().__init__()
        self.retriever = retriever
        self.answer_generator = ChainOfThought(
            "context, question -> answer, confidence"
        )

    def forward(self, question: str):
        """Process question and generate answer"""
        # Retrieve relevant passages
        retrieved = self.retriever(question)
        context = "\n".join(retrieved.passages)

        # Generate answer with confidence
        prediction = self.answer_generator(context=context, question=question)

        return dspy.Prediction(
            question=question,
            context=retrieved.passages,
            answer=prediction.answer,
            confidence=prediction.confidence,
        )


def setup_dspy():
    """Initialize DSPy"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    lm = LM(model="openai/gpt-3.5-turbo", max_tokens=500)
    dspy.settings.configure(lm=lm)


def main():
    """Main execution"""
    setup_dspy()

    # Sample corpus
    corpus = [
        "Machine learning is a subset of artificial intelligence that focuses on learning from data.",
        "Deep learning uses neural networks with multiple layers to process information.",
        "Transfer learning allows models trained on one task to be applied to another task.",
        "Supervised learning requires labeled data for training the model.",
        "Unsupervised learning finds patterns in unlabeled data.",
        "Reinforcement learning uses rewards to train agents to make decisions.",
        "Natural language processing enables computers to understand human language.",
        "Computer vision allows machines to interpret visual information from images.",
        "Neural networks are inspired by biological neurons in the brain.",
        "Backpropagation is the algorithm used to train neural networks.",
    ]

    # Initialize retriever and pipeline
    retriever = FAISSRetriever(corpus, k=3)
    rag = AdvancedRAGPipeline(retriever)

    # Test questions
    questions = [
        "What is machine learning?",
        "How does transfer learning work?",
        "What are neural networks?",
    ]

    print("=" * 70)
    print("DSPy RAG System with FAISS Retriever")
    print("=" * 70)

    for question in questions:
        print(f"\n{'='*70}")
        print(f"Question: {question}")
        print("-" * 70)

        try:
            result = rag(question)
            print(f"\nAnswer: {result.answer}")
            print(f"\nConfidence: {result.confidence}")
            print(f"\nRetrieved Passages ({len(result.context)}):")
            for i, passage in enumerate(result.context, 1):
                print(f"  {i}. {passage}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
