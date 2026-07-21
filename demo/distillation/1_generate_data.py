"""
Step 1: Use Claude (teacher) to generate training data.
Run this once to build your dataset before fine-tuning.
"""
import json
import time
from pathlib import Path
import anthropic

client = anthropic.Anthropic()

# --- Define your task here ---
TASK_SYSTEM_PROMPT = """You are a senior software engineer and solutions architect with 15+ years of experience.
Given a software development task or requirement, provide a structured, actionable response covering:
- Analysis of the requirement or problem
- Recommended approach or solution with reasoning
- Key considerations (scalability, security, maintainability)
- Concrete implementation steps or code where relevant
Be precise, technical, and opinionated. Avoid vague advice."""

SEED_QUESTIONS = [
    # Requirements Analysis
    "Analyze this requirement: 'The system shall allow users to reset their password via email within 5 minutes.'",
    "What are the functional and non-functional requirements for a real-time chat feature in a SaaS app?",
    "Break down this user story into technical tasks: 'As a user, I want to export my data as CSV.'",
    "Identify ambiguities and missing details in: 'The app should be fast and support many users.'",
    "Convert this business requirement into acceptance criteria: 'Users must be able to log in securely.'",

    # Architecture & Design
    "Design a microservices architecture for an e-commerce platform handling 10k orders/day.",
    "What database schema would you design for a multi-tenant SaaS application?",
    "Compare REST vs GraphQL for a mobile app with complex nested data requirements.",
    "How would you design an event-driven system for order processing with guaranteed delivery?",
    "Design an API rate limiting system that supports per-user and per-endpoint limits.",

    # Code Review & Quality
    "Review this Python function for bugs, edge cases, and improvements:\ndef get_user(id):\n  return db.query('SELECT * FROM users WHERE id=' + id)",
    "What are the SOLID principle violations in a God class that handles auth, email, and payments?",
    "How would you refactor a 500-line function with nested conditionals into clean code?",
    "Identify security vulnerabilities in: user input directly concatenated into SQL queries.",
    "What code review checklist items matter most for a payment processing module?",

    # Testing Strategy
    "What testing strategy would you apply to a critical authentication service?",
    "Write test cases for a function that calculates shipping costs based on weight and destination.",
    "How do you test a distributed system where components communicate asynchronously?",
    "What's the difference between unit, integration, and e2e tests? When to use each?",
    "Design a load testing plan for an API expected to handle 1000 concurrent users.",

    # Technical Decisions
    "Should we use PostgreSQL or MongoDB for storing user activity logs? Justify the choice.",
    "How do you decide between building a feature in-house vs using a third-party library?",
    "What factors determine whether to use synchronous or asynchronous processing for a task?",
    "When should you introduce a message queue like Kafka vs direct API calls between services?",
    "How would you handle database migrations in a zero-downtime deployment pipeline?",
]


def generate_example(question: str, retry: int = 3) -> dict | None:
    """Teacher model (Sonnet) generates high-quality answer."""
    for attempt in range(retry):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",   # teacher model
                max_tokens=1024,
                system=TASK_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": question}],
            )
            return {
                "instruction": TASK_SYSTEM_PROMPT,
                "input": question,
                "output": response.content[0].text,
            }
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
    return None


def generate_variations(question: str) -> list[str]:
    """Use Claude to generate paraphrases → bigger dataset from fewer seeds."""
    response = client.messages.create(
        model="claude-haiku-4-5",   # cheap model for this meta-task
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"Generate 4 different ways to ask this software engineering question. Return as a JSON array of plain strings only.\n\nQuestion: {question}"
        }],
    )
    try:
        text = response.content[0].text
        start = text.find("[")
        end = text.rfind("]") + 1
        parsed = json.loads(text[start:end])
        # Ensure list of plain strings — haiku sometimes returns dicts
        return [v if isinstance(v, str) else str(list(v.values())[0]) for v in parsed if v]
    except Exception:
        return [question]


def main():
    output_path = Path(__file__).parent / "training_data.jsonl"
    examples = []

    print(f"Generating training data with Claude Sonnet (teacher)...")
    print(f"Seeds: {len(SEED_QUESTIONS)}, Output: {output_path}\n")

    for i, seed in enumerate(SEED_QUESTIONS):
        print(f"[{i+1}/{len(SEED_QUESTIONS)}] Seed: {seed[:60]}...")

        # Generate variations with Haiku (cheap)
        variations = generate_variations(seed)
        all_questions = [seed] + variations

        for question in all_questions:
            example = generate_example(question)
            if example:
                examples.append(example)
                print(f"  + Generated example ({len(examples)} total)")
            time.sleep(0.5)   # rate limit

    # Save as JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nDone. {len(examples)} examples saved to {output_path}")
    print(f"Estimated cost: ~${len(examples) * 0.003:.2f} (Sonnet pricing)")


if __name__ == "__main__":
    main()
