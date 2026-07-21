"""
Optimized DSPy RAG System with Multi-hop Reasoning
This example demonstrates advanced DSPy features for complex RAG tasks
"""

import os
from typing import List, Optional
import dspy
from dspy import Module, ChainOfThought, Predict, LM


class MultiHopRAGPipeline(Module):
    """Multi-hop RAG pipeline that breaks down complex questions"""

    def __init__(self, num_passages: int = 3, num_hops: int = 2):
        super().__init__()
        self.num_passages = num_passages
        self.num_hops = num_hops

        # Initialize retrievers and generators
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.decompose = Predict("question -> subquestions")
        self.answer_generator = ChainOfThought(
            "context, question, subquestion_answers -> answer"
        )

    def forward(self, question: str):
        """Multi-hop reasoning forward pass"""
        # Decompose question into subquestions
        decomposition = self.decompose(question=question)
        subquestions = decomposition.subquestions.split("|")

        # Retrieve context for each subquestion
        all_contexts = []
        subquestion_answers = []

        for subq in subquestions[: self.num_hops]:
            subq = subq.strip()
            if subq:
                # Retrieve relevant passages
                retrieved = self.retrieve(subq)
                all_contexts.extend(retrieved.passages)

                # You can add intermediate reasoning here
                subquestion_answers.append(f"Subquestion: {subq}")

        # Combine all retrieved context
        combined_context = "\n".join(all_contexts)

        # Generate final answer
        prediction = self.answer_generator(
            context=combined_context,
            question=question,
            subquestion_answers="\n".join(subquestion_answers),
        )

        return dspy.Prediction(
            question=question,
            subquestions=subquestions,
            context=all_contexts,
            answer=prediction.answer,
        )


class RAGWithValidation(Module):
    """RAG pipeline with answer validation"""

    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.answer_generator = ChainOfThought(
            "context, question -> answer, is_supported"
        )
        self.validator = Predict("context, question, answer -> is_valid")

    def forward(self, question: str):
        """Generate answer with validation"""
        # Retrieve context
        retrieved = self.retrieve(question)
        context = "\n".join(retrieved.passages)

        # Generate answer
        prediction = self.answer_generator(context=context, question=question)

        # Validate answer
        validation = self.validator(
            context=context, question=question, answer=prediction.answer
        )

        return dspy.Prediction(
            question=question,
            answer=prediction.answer,
            is_supported=prediction.is_supported,
            is_valid=validation.is_valid,
            context=retrieved.passages,
        )


class SimpleQAProgram(Module):
    """Simple QA program using DSPy signatures"""

    def __init__(self):
        super().__init__()
        # Use built-in QA signature
        self.qa = ChainOfThought("context, question -> answer")

    def forward(self, question: str, context: str):
        return self.qa(context=context, question=question)


def setup_dspy():
    """Initialize DSPy with OpenAI"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    lm = LM(
        model="openai/gpt-3.5-turbo",
        max_tokens=1000,
        temperature=0.7,
    )
    dspy.settings.configure(lm=lm)
    return lm


def demo_simple_qa():
    """Demonstrate simple QA"""
    print("\n" + "=" * 70)
    print("Demo 1: Simple QA with Context")
    print("=" * 70)

    qa = SimpleQAProgram()
    context = """
    Machine learning is a subset of artificial intelligence that enables 
    systems to learn and improve from experience without being explicitly programmed. 
    It focuses on developing algorithms that can access data and use it to learn for themselves.
    """
    question = "What is machine learning?"

    result = qa(question=question, context=context)
    print(f"\nQuestion: {question}")
    print(f"Answer: {result.answer}")


def demo_multi_hop():
    """Demonstrate multi-hop reasoning"""
    print("\n" + "=" * 70)
    print("Demo 2: Multi-hop Reasoning RAG")
    print("=" * 70)

    rag = MultiHopRAGPipeline(num_passages=2, num_hops=2)
    question = "How do neural networks and transfer learning relate to each other?"

    print(f"\nQuestion: {question}")
    print("Processing multi-hop reasoning...")

    try:
        result = rag(question)
        print(f"\nSubquestions: {', '.join(result.subquestions[:2])}")
        print(f"Answer: {result.answer}")
    except Exception as e:
        print(f"Note: This demo requires retrieval setup. Error: {e}")


def demo_validation():
    """Demonstrate RAG with validation"""
    print("\n" + "=" * 70)
    print("Demo 3: RAG with Answer Validation")
    print("=" * 70)

    rag = RAGWithValidation()
    question = "What is the capital of France?"

    print(f"\nQuestion: {question}")
    print("Generating and validating answer...")

    try:
        result = rag(question)
        print(f"Answer: {result.answer}")
        print(f"Answer Supported by Context: {result.is_supported}")
        print(f"Answer Valid: {result.is_valid}")
    except Exception as e:
        print(f"Note: This demo requires retrieval setup. Error: {e}")


def main():
    """Main execution"""
    setup_dspy()

    # Run demos
    demo_simple_qa()
    demo_multi_hop()
    demo_validation()

    print("\n" + "=" * 70)
    print("DSPy RAG Examples Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
