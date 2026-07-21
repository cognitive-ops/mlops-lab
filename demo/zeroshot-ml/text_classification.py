"""
Zero-Shot Text Classification Example
Uses BART model for zero-shot classification without any training data
"""

from transformers import pipeline
import json


def zero_shot_text_classification():
    """
    Classify text into predefined categories without training examples
    """
    # Initialize the zero-shot classification pipeline
    classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli"
    )

    # Sample texts to classify
    texts = [
        "I absolutely love this new restaurant! The food was amazing.",
        "This product stopped working after one week. Very disappointed.",
        "The weather today is quite pleasant with some clouds.",
        "I just finished reading an incredible book about artificial intelligence."
    ]

    # Define candidate labels - what we want to classify into
    candidate_labels = ["positive sentiment", "negative sentiment", "neutral"]

    print("=" * 60)
    print("ZERO-SHOT TEXT CLASSIFICATION")
    print("=" * 60)

    results = []
    for text in texts:
        print(f"\nText: {text}")
        result = classifier(text, candidate_labels)

        # Display results
        print(f"Classification Results:")
        for label, score in zip(result["labels"], result["scores"]):
            print(f"  - {label}: {score:.4f}")

        results.append({
            "text": text,
            "predictions": [
                {"label": label, "score": float(score)}
                for label, score in zip(result["labels"], result["scores"])
            ]
        })

    return results


def zero_shot_intent_classification():
    """
    Classify user intents without training examples
    """
    classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli"
    )

    # User queries
    queries = [
        "Can you book me a flight to Paris?",
        "What's the weather like tomorrow?",
        "How do I reset my password?",
        "Tell me a joke"
    ]

    # Intent labels
    intents = [
        "booking request",
        "weather inquiry",
        "technical support",
        "entertainment",
        "general information"
    ]

    print("\n" + "=" * 60)
    print("ZERO-SHOT INTENT CLASSIFICATION")
    print("=" * 60)

    results = []
    for query in queries:
        print(f"\nQuery: {query}")
        result = classifier(query, intents)

        print(
            f"Detected Intent: {result['labels'][0]} (confidence: {result['scores'][0]:.4f})")

        results.append({
            "query": query,
            "intent": result["labels"][0],
            "confidence": float(result["scores"][0])
        })

    return results


def zero_shot_nli_classification():
    """
    Natural Language Inference (NLI) - determine if premise entails hypothesis
    """
    classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli"
    )

    # Premise to evaluate
    premise = "A woman is cooking in the kitchen."

    # Hypotheses to test
    hypotheses = [
        "A person is in the kitchen",
        "A man is cooking",
        "Someone is cooking food"
    ]

    print("\n" + "=" * 60)
    print("ZERO-SHOT NATURAL LANGUAGE INFERENCE")
    print("=" * 60)
    print(f"\nPremise: {premise}\n")

    results = []
    for hypothesis in hypotheses:
        result = classifier(premise, [hypothesis])
        entailment_score = result["scores"][0]

        print(f"Hypothesis: {hypothesis}")
        print(f"Entailment Score: {entailment_score:.4f}")
        print(
            f"Relationship: {'ENTAILS' if entailment_score > 0.5 else 'DOES NOT ENTAIL'}\n")

        results.append({
            "hypothesis": hypothesis,
            "entailment_score": float(entailment_score)
        })

    return results


def main():
    """Run all zero-shot classification examples"""
    print("\n" + "=" * 60)
    print("ZERO-SHOT LEARNING DEMONSTRATION")
    print("=" * 60)

    # Run classification examples
    text_results = zero_shot_text_classification()
    intent_results = zero_shot_intent_classification()
    nli_results = zero_shot_nli_classification()

    # Save results to JSON
    all_results = {
        "text_classification": text_results,
        "intent_classification": intent_results,
        "nli_classification": nli_results
    }

    with open("text_classification_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 60)
    print("Results saved to text_classification_results.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
