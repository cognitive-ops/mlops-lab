"""
Complete DSPy RAG System with Document Loading and Vector Store
Production-ready example with document processing pipeline
"""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import dspy
from dspy import Module, ChainOfThought, Predict


class DocumentStore:
    """Simple in-memory document store"""

    def __init__(self):
        self.documents: Dict[str, str] = {}
        self.embeddings = None

    def add_documents(self, documents: List[Dict[str, str]]):
        """Add documents with ID and content"""
        for doc in documents:
            doc_id = doc.get("id", f"doc_{len(self.documents)}")
            self.documents[doc_id] = doc["content"]

    def add_from_json(self, json_path: str):
        """Load documents from JSON file"""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        with open(json_path, "r") as f:
            docs = json.load(f)
            self.add_documents(docs)

    def get_all_documents(self) -> List[str]:
        """Get all document contents"""
        return list(self.documents.values())


class VectorStore:
    """Vector store using semantic similarity"""

    def __init__(self, documents: List[str]):
        self.documents = documents
        self.embeddings = None
        self._build_embeddings()

    def _build_embeddings(self):
        """Build embeddings for documents"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("Warning: sentence-transformers not installed")
            return

        model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = model.encode(self.documents)

    def search(self, query: str, k: int = 3) -> List[str]:
        """Search for similar documents"""
        if self.embeddings is None:
            return self.documents[:k]

        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except ImportError:
            return self.documents[:k]

        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_embedding = model.encode(query)

        # Cosine similarity
        scores = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(scores)[-k:][::-1]

        return [self.documents[i] for i in top_indices]


class VectorStoreRetriever(dspy.Retrieve):
    """Retriever using vector store"""

    def __init__(self, vector_store: VectorStore, k: int = 3):
        super().__init__(k=k)
        self.vector_store = vector_store

    def forward(self, query: str, k: Optional[int] = None):
        k = k or self.k
        passages = self.vector_store.search(query, k=k)
        return dspy.Prediction(passages=passages)


class ProductionRAG(Module):
    """Production-ready RAG system"""

    def __init__(self, vector_store: VectorStore):
        super().__init__()
        self.retriever = VectorStoreRetriever(vector_store, k=3)
        self.answer_generator = ChainOfThought(
            "context, question -> answer, reasoning"
        )
        self.confidence_scorer = Predict(
            "context, question, answer -> confidence")

    def forward(self, question: str):
        """Generate answer with full metadata"""
        # Retrieve
        retrieved = self.retriever(question)
        context = "\n\n".join(retrieved.passages)

        # Generate
        prediction = self.answer_generator(context=context, question=question)

        # Score confidence
        try:
            confidence = self.confidence_scorer(
                context=context, question=question, answer=prediction.answer
            )
            confidence_score = confidence.confidence
        except:
            confidence_score = "unknown"

        return dspy.Prediction(
            question=question,
            answer=prediction.answer,
            reasoning=prediction.reasoning,
            confidence=confidence_score,
            context=retrieved.passages,
        )


class RAGEvaluator:
    """Evaluate RAG system performance"""

    def __init__(self, rag_system: ProductionRAG):
        self.rag = rag_system

    def evaluate(self, test_cases: List[Dict[str, str]]) -> Dict:
        """Evaluate on test cases"""
        results = {
            "total": len(test_cases),
            "successful": 0,
            "failed": 0,
            "details": [],
        }

        for test_case in test_cases:
            try:
                result = self.rag(test_case["question"])
                results["successful"] += 1
                results["details"].append(
                    {
                        "question": test_case["question"],
                        "answer": result.answer,
                        "confidence": result.confidence,
                        "status": "success",
                    }
                )
            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {
                        "question": test_case["question"],
                        "error": str(e),
                        "status": "failed",
                    }
                )

        return results


def setup_dspy():
    """Initialize DSPy"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    lm = dspy.LM(
        model="openai/gpt-3.5-turbo",
        max_tokens=500,
        temperature=0.5,
    )
    dspy.settings.configure(lm=lm)


def create_sample_documents() -> List[Dict[str, str]]:
    """Create sample documents for demonstration"""
    return [
        {
            "id": "ml_01",
            "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing algorithms that can access data and use it to learn for themselves.",
        },
        {
            "id": "ml_02",
            "content": "Supervised learning is a type of machine learning where the algorithm learns from labeled training data. The training data consists of input-output pairs, and the algorithm learns to map inputs to outputs.",
        },
        {
            "id": "ml_03",
            "content": "Unsupervised learning is used when we don't have labeled data. The algorithm tries to find hidden patterns or structures in the data without any predefined labels or categories.",
        },
        {
            "id": "nn_01",
            "content": "Neural networks are computing systems inspired by biological neural networks in animals' brains. They consist of interconnected nodes (neurons) that process and transmit information.",
        },
        {
            "id": "nn_02",
            "content": "Deep learning uses neural networks with multiple layers to learn representations of data. Each layer learns increasingly abstract features of the input data.",
        },
        {
            "id": "tl_01",
            "content": "Transfer learning is a technique where a model trained on one task is reused for a different but related task. This approach can significantly reduce training time and improve performance with limited data.",
        },
        {
            "id": "nlp_01",
            "content": "Natural language processing (NLP) is a subfield of AI that focuses on the interaction between computers and human language. It enables machines to understand, interpret, and generate human language.",
        },
        {
            "id": "cv_01",
            "content": "Computer vision is an interdisciplinary field that deals with how computers gain high-level understanding from digital images or videos. It aims to automate tasks that the human visual system can do.",
        },
    ]


def main():
    """Main execution"""
    print("=" * 80)
    print("Production-Ready DSPy RAG System")
    print("=" * 80)

    # Setup
    setup_dspy()

    # Create document store and load documents
    print("\n1. Loading documents...")
    doc_store = DocumentStore()
    documents = create_sample_documents()
    doc_store.add_documents(documents)
    print(f"   Loaded {len(documents)} documents")

    # Create vector store
    print("\n2. Creating vector store...")
    vector_store = VectorStore(doc_store.get_all_documents())
    print("   Vector store ready")

    # Create RAG system
    print("\n3. Initializing RAG system...")
    rag = ProductionRAG(vector_store)
    print("   RAG system initialized")

    # Test queries
    test_queries = [
        "What is machine learning?",
        "How do neural networks work?",
        "What is transfer learning?",
        "Explain the difference between supervised and unsupervised learning",
        "What is natural language processing?",
    ]

    print("\n" + "=" * 80)
    print("Running Queries")
    print("=" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Query {i}: {query}")
        print("─" * 80)

        try:
            result = rag(query)

            print(f"\nAnswer:\n{result.answer}")
            print(f"\nReasoning:\n{result.reasoning}")
            print(f"\nConfidence: {result.confidence}")
            print(f"\nSources: {len(result.context)} documents retrieved")

        except Exception as e:
            print(f"Error: {e}")

    # Evaluate
    print("\n" + "=" * 80)
    print("System Evaluation")
    print("=" * 80)

    evaluator = RAGEvaluator(rag)
    test_cases = [{"question": q} for q in test_queries]
    eval_results = evaluator.evaluate(test_cases)

    print(f"\nTotal: {eval_results['total']}")
    print(f"Successful: {eval_results['successful']}")
    print(f"Failed: {eval_results['failed']}")

    if eval_results["successful"] > 0:
        success_rate = (eval_results["successful"] /
                        eval_results["total"]) * 100
        print(f"Success Rate: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
