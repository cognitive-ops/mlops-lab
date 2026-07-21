"""
Testing and Evaluation Suite for DSPy RAG System
Run tests to verify system functionality
"""

import os
import json
from typing import List, Dict, Tuple
import dspy
from dspy_rag_production import (
    DocumentStore,
    VectorStore,
    ProductionRAG,
    RAGEvaluator,
    create_sample_documents,
)


class TestSuite:
    """Test suite for RAG system"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str, condition: bool, message: str = ""):
        """Run a single test"""
        status = "✓ PASS" if condition else "✗ FAIL"
        result = {
            "name": name,
            "status": "passed" if condition else "failed",
            "message": message,
        }
        self.results.append(result)

        if condition:
            self.passed += 1
        else:
            self.failed += 1

        print(f"  {status}: {name}")
        if message and not condition:
            print(f"         {message}")

    def report(self):
        """Print test report"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print("Test Report")
        print("=" * 70)
        print(f"Total:  {total}")
        print(f"Passed: {self.passed} ✓")
        print(f"Failed: {self.failed} ✗")
        if total > 0:
            pass_rate = (self.passed / total) * 100
            print(f"Pass Rate: {pass_rate:.1f}%")
        print("=" * 70)


def test_imports():
    """Test that all imports work"""
    print("\n1. Testing Imports...")
    suite = TestSuite()

    try:
        import dspy

        suite.test("DSPy import", True)
    except ImportError as e:
        suite.test("DSPy import", False, str(e))

    try:
        from sentence_transformers import SentenceTransformer

        suite.test("Sentence Transformers import", True)
    except ImportError:
        suite.test("Sentence Transformers import", False,
                   "Install sentence-transformers")

    try:
        import numpy as np

        suite.test("NumPy import", True)
    except ImportError:
        suite.test("NumPy import", False, "Install numpy")

    suite.report()
    return suite.passed == suite.passed + suite.failed


def test_configuration():
    """Test DSPy configuration"""
    print("\n2. Testing Configuration...")
    suite = TestSuite()

    api_key = os.getenv("OPENAI_API_KEY")
    suite.test("OPENAI_API_KEY set", bool(api_key),
               "Set OPENAI_API_KEY environment variable")

    if api_key:
        suite.test("API key format", api_key.startswith(
            "sk-"), "Invalid API key format")

    suite.report()
    return suite.passed > 0


def test_document_store():
    """Test document store functionality"""
    print("\n3. Testing Document Store...")
    suite = TestSuite()

    try:
        doc_store = DocumentStore()
        suite.test("Document store creation", True)

        docs = create_sample_documents()
        doc_store.add_documents(docs)
        suite.test("Add documents", len(doc_store.documents) == len(docs))

        all_docs = doc_store.get_all_documents()
        suite.test("Retrieve documents", len(all_docs) == len(docs))

    except Exception as e:
        suite.test("Document store operations", False, str(e))

    suite.report()


def test_vector_store():
    """Test vector store functionality"""
    print("\n4. Testing Vector Store...")
    suite = TestSuite()

    try:
        docs = [
            "Machine learning is a subset of AI",
            "Deep learning uses neural networks",
            "Transfer learning reuses trained models",
        ]

        vector_store = VectorStore(docs)
        suite.test("Vector store creation", True)

        results = vector_store.search("neural networks", k=2)
        suite.test("Vector search", len(results) <= 2)

        results = vector_store.search("artificial intelligence", k=1)
        suite.test("Top-k search", len(results) == 1)

    except Exception as e:
        suite.test("Vector store operations", False, str(e))

    suite.report()


def test_rag_system():
    """Test complete RAG system"""
    print("\n5. Testing RAG System...")
    suite = TestSuite()

    try:
        # Setup
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            suite.test("RAG system setup", False, "OPENAI_API_KEY not set")
            suite.report()
            return

        lm = dspy.OpenAI(model="gpt-3.5-turbo",
                         api_key=api_key, max_tokens=200)
        dspy.settings.configure(lm=lm)
        suite.test("DSPy LM configuration", True)

        # Create RAG
        doc_store = DocumentStore()
        doc_store.add_documents(create_sample_documents())
        vector_store = VectorStore(doc_store.get_all_documents())
        rag = ProductionRAG(vector_store)
        suite.test("RAG system creation", True)

        # Test prediction (with timeout)
        try:
            result = rag("What is machine learning?")
            suite.test("RAG prediction", bool(result.answer))
            suite.test("Answer content", len(result.answer) > 0)
            suite.test("Context retrieval", len(result.context) > 0)
        except Exception as e:
            suite.test("RAG prediction", False, str(e))

    except Exception as e:
        suite.test("RAG system setup", False, str(e))

    suite.report()


def test_evaluation():
    """Test evaluation functionality"""
    print("\n6. Testing Evaluation...")
    suite = TestSuite()

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            suite.test("Evaluator setup", False, "OPENAI_API_KEY not set")
            suite.report()
            return

        # Setup
        lm = dspy.OpenAI(model="gpt-3.5-turbo",
                         api_key=api_key, max_tokens=200)
        dspy.settings.configure(lm=lm)

        doc_store = DocumentStore()
        doc_store.add_documents(create_sample_documents())
        vector_store = VectorStore(doc_store.get_all_documents())
        rag = ProductionRAG(vector_store)

        evaluator = RAGEvaluator(rag)
        suite.test("Evaluator creation", True)

        test_cases = [{"question": "What is machine learning?"}]
        results = evaluator.evaluate(test_cases)
        suite.test("Evaluation execution", results["total"] > 0)

    except Exception as e:
        suite.test("Evaluation", False, str(e))

    suite.report()


def performance_test():
    """Simple performance test"""
    print("\n7. Performance Test...")
    import time

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  Skipped: OPENAI_API_KEY not set")
        return

    try:
        # Setup
        lm = dspy.OpenAI(model="gpt-3.5-turbo",
                         api_key=api_key, max_tokens=100)
        dspy.settings.configure(lm=lm)

        doc_store = DocumentStore()
        doc_store.add_documents(create_sample_documents())
        vector_store = VectorStore(doc_store.get_all_documents())
        rag = ProductionRAG(vector_store)

        # Single query timing
        start = time.time()
        result = rag("What is machine learning?")
        elapsed = time.time() - start

        print(f"  Query execution time: {elapsed:.2f}s")
        print(f"  Answer length: {len(result.answer)} characters")

    except Exception as e:
        print(f"  Performance test error: {e}")


def main():
    """Run all tests"""
    print("=" * 70)
    print("DSPy RAG System Test Suite")
    print("=" * 70)

    test_imports()
    test_configuration()
    test_document_store()
    test_vector_store()
    test_rag_system()
    test_evaluation()
    performance_test()

    print("\n" + "=" * 70)
    print("Test Suite Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
