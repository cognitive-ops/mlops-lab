"""
Simple DSPy RAG System using OpenAI
This example demonstrates a basic RAG pipeline using DSPy
"""

import os
import dspy
from typing import List
from dspy import ChainOfThought, LM


class SimplifiedRAGPipeline(dspy.Module):
    """Simplified RAG pipeline using DSPy without retriever"""

    def __init__(self):
        super().__init__()
        # Use ChainOfThought for answer generation
        self.generate_answer = ChainOfThought("question -> answer")

    def forward(self, question: str):
        """Forward pass: generate answer"""
        # Generate answer
        prediction = self.generate_answer(question=question)
        return dspy.Prediction(answer=prediction.answer)


def setup_dspy():
    """Initialize DSPy with OpenAI LLM"""
    lm = LM(
        model="openai/gpt-3.5-turbo",
        max_tokens=500,
    )
    dspy.settings.configure(lm=lm)
    return lm


def main():
    """Main execution"""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Setup DSPy
    setup_dspy()

    # Create RAG pipeline
    rag = SimplifiedRAGPipeline()

    # Example questions
    questions = [
        "Who is Maria Ozawa?",
        "How does transfer learning work?",
        "What are neural networks?",
    ]

    # Process questions
    print("=" * 50)
    print("DSPy RAG System - Simple Example")
    print("=" * 50)

    for question in questions:
        print(f"\nQuestion: {question}")
        print("-" * 50)

        try:
            result = rag(question)
            print(f"Answer: {result.answer}")
        except Exception as e:
            print(f"Error processing question: {e}")


if __name__ == "__main__":
    main()
