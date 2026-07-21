# DSPy RAG Cheatsheet

## Installation & Setup

```bash
# 1. Install dependencies
cd demo/dspy
pip install -r requirements.txt

# 2. Set API key
export OPENAI_API_KEY="your-key-here"

# 3. Run test to verify
python test_rag_system.py
```

## Minimal RAG in 3 Steps

```python
import dspy

# 1. Configure LLM
dspy.settings.configure(lm=dspy.OpenAI(model="gpt-3.5-turbo"))

# 2. Define RAG
class RAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.qa = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.qa(context=context, question=question)

# 3. Use it
rag = RAG()
print(rag("What is machine learning?").answer)
```

## Common Patterns

### Pattern 1: Simple Question Answering
```python
class QA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict("question -> answer")
    
    def forward(self, question):
        return self.predict(question=question)
```

### Pattern 2: RAG (Retrieve + Generate)
```python
class RAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.answer = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.answer(context=context, question=question)
```

### Pattern 3: Multi-hop (Step-by-step reasoning)
```python
class MultiHop(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.step1 = dspy.ChainOfThought("context, question -> reasoning")
        self.step2 = dspy.ChainOfThought("reasoning, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        step1 = self.step1(context=context, question=question)
        return self.step2(reasoning=step1.reasoning, question=question)
```

### Pattern 4: Custom Retriever
```python
class CustomRetriever(dspy.Retrieve):
    def __init__(self, documents, k=3):
        super().__init__(k=k)
        self.documents = documents
    
    def forward(self, query):
        # Your search logic here
        results = [doc for doc in self.documents if query in doc][:self.k]
        return dspy.Prediction(passages=results)

class RAGWithCustom(dspy.Module):
    def __init__(self, documents):
        super().__init__()
        self.retrieve = CustomRetriever(documents)
        self.answer = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.answer(context=context, question=question)
```

## DSPy Components Reference

| Component | Purpose | Example |
|-----------|---------|---------|
| `dspy.Module` | Base class for RAG components | `class MyRAG(dspy.Module)` |
| `dspy.Predict` | Simple LM call | `dspy.Predict("input -> output")` |
| `dspy.ChainOfThought` | Reasoning with steps | `dspy.ChainOfThought("q -> a")` |
| `dspy.Retrieve` | Document retrieval | `dspy.Retrieve(k=3)` |
| `dspy.OpenAI` | OpenAI integration | `dspy.OpenAI(model="...")` |
| `dspy.Signature` | Custom I/O spec | `class MySig(dspy.Signature)` |

## Configuration

```python
import dspy

# Set up LLM
lm = dspy.OpenAI(
    model="gpt-3.5-turbo",
    api_key="sk-...",
    max_tokens=500,
    temperature=0.7
)

dspy.settings.configure(lm=lm)

# Settings available
dspy.settings.lm        # Current LM
dspy.settings.rm        # Current retriever module
dspy.settings.trace_history  # Trace execution
```

## Signatures Explained

A signature is a declarative spec for what an LM should do:

```python
# Format: input_field -> output_field
signature = "question -> answer"

# With descriptions
signature = """
question: The user's question
---
answer: A helpful answer
"""

# Multiple fields
signature = "question, context -> answer, confidence"

# Custom class
class MySignature(dspy.Signature):
    """Your task description"""
    input1 = dspy.InputField(desc="What this field contains")
    input2 = dspy.InputField(desc="Another input")
    output1 = dspy.OutputField(desc="What to output")
```

## Predictions & Results

```python
# Basic prediction
qa = dspy.ChainOfThought("question -> answer")
result = qa(question="What is AI?")

# Access outputs
print(result.answer)        # The generated answer
print(result.reasoning)     # Intermediate reasoning
print(result['answer'])     # Alternative access

# Iterate predictions
for key, value in result.items():
    print(f"{key}: {value}")

# Convert to dict
result_dict = result.toDict()
```

## Debugging & Inspection

```python
# Enable tracing
dspy.settings.trace_history = []

# Run with trace
result = my_rag(question)

# Inspect execution
for step in dspy.settings.trace_history:
    print(f"Step: {step}")

# Debug individual components
retriever = dspy.Retrieve(k=3)
retrieved = retriever("my query")
print(retrieved.passages)  # See what was retrieved

# LM inspection
lm = dspy.settings.lm
lm.inspect_history()  # See recent calls
```

## Custom Signatures

```python
class QuestionAnswering(dspy.Signature):
    """Answer questions given context."""
    
    context = dspy.InputField(desc="May contain relevant facts")
    question = dspy.InputField()
    answer = dspy.OutputField(desc="Often between 1-5 sentences")

class Summarization(dspy.Signature):
    """Summarize a document."""
    
    document = dspy.InputField(desc="The document to summarize")
    summary = dspy.OutputField(desc="A 1-3 sentence summary")

# Use custom signatures
predict_qa = dspy.ChainOfThought(QuestionAnswering)
summary = dspy.ChainOfThought(Summarization)
```

## Error Handling

```python
class RobustRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.answer = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        try:
            context = self.retrieve(question).passages
            if not context:
                return dspy.Prediction(answer="No relevant documents found")
            
            result = self.answer(context=context, question=question)
            return result
        except Exception as e:
            return dspy.Prediction(answer=f"Error: {str(e)}")
```

## Performance Optimization

```python
# Faster responses
lm = dspy.OpenAI(
    model="gpt-3.5-turbo",
    max_tokens=100,        # Shorter responses
    temperature=0.5        # More consistent
)

# Better quality (slower)
lm = dspy.OpenAI(
    model="gpt-4",
    max_tokens=1000,
    temperature=0.7
)

# Caching for repeated queries
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_predict(question):
    return rag(question)
```

## Testing RAG System

```python
# Unit test
def test_rag():
    rag = RAG()
    result = rag("What is AI?")
    assert result.answer is not None
    assert len(result.answer) > 0

# Integration test
def test_rag_end_to_end():
    documents = ["AI is...", "ML is..."]
    rag = RAGWithCustom(documents)
    result = rag("Tell me about AI")
    assert "AI" in result.answer.lower()

# Evaluation test
from dspy.evaluate.evaluate import Evaluate

def metric(example, pred, trace=None):
    return len(pred.answer) > 0

evaluator = Evaluate(dsrs=test_set, metric=metric, num_threads=10)
score = evaluator(rag)
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not set` | `export OPENAI_API_KEY="sk-..."` |
| `No module named dspy` | `pip install dspy-ai` |
| Empty retrieved results | Increase `k`, check corpus |
| Low quality answers | Use gpt-4, increase k, improve documents |
| Timeout errors | Increase timeout, reduce max_tokens |
| Out of memory | Reduce corpus size, use batching |

## Running Examples

```bash
# From demo/dspy directory

# Simple example
python dspy_rag_simple.py

# With custom retriever
python dspy_rag_with_retriever.py

# Advanced reasoning
python dspy_rag_optimized.py

# Production system
python dspy_rag_production.py

# Run tests
python test_rag_system.py
```

## Key Files

| File | Purpose | Complexity |
|------|---------|-----------|
| `dspy_rag_simple.py` | Getting started | ⭐ |
| `dspy_rag_with_retriever.py` | Custom retrieval | ⭐⭐ |
| `dspy_rag_optimized.py` | Advanced patterns | ⭐⭐⭐ |
| `dspy_rag_production.py` | Production ready | ⭐⭐⭐⭐ |
| `test_rag_system.py` | Validation suite | ⭐⭐ |
| `config.py` | Configuration | ⭐ |

## Resources

- **DSPy GitHub**: https://github.com/stanfordnlp/dspy
- **DSPy Docs**: https://github.com/stanfordnlp/dspy/tree/main/docs
- **Examples**: https://github.com/stanfordnlp/dspy/tree/main/examples
- **RAG Paper**: https://arxiv.org/abs/2005.11401

## Quick Reference

```python
# Import
import dspy

# Configure
dspy.settings.configure(lm=dspy.OpenAI(model="gpt-3.5-turbo"))

# Create component
class MyModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.component = dspy.ChainOfThought("input -> output")
    
    def forward(self, **kwargs):
        return self.component(**kwargs)

# Use
module = MyModule()
result = module(input="test")
print(result.output)
```

---

**Happy RAGing with DSPy! 🚀**
