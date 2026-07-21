# DSPy RAG System

This directory contains sample implementations of Retrieval-Augmented Generation (RAG) systems using **DSPy** from Databricks.

## What is DSPy?

DSPy is a framework for optimizing language model pipelines. It provides:
- **Modular abstractions** for composing LM calls
- **Automatic optimization** of prompts and weights
- **Declarative programming** for AI systems
- Built-in support for **retrieval-augmented generation**

## Project Structure

### 1. **dspy_rag_simple.py**
Simple RAG pipeline using DSPy's built-in components.
```bash
python dspy_rag_simple.py
```

**Features:**
- Basic question-answering with retrieval
- Uses OpenAI's API
- Simple ChainOfThought reasoning

### 2. **dspy_rag_with_retriever.py**
Advanced RAG with custom FAISS retriever.
```bash
python dspy_rag_with_retriever.py
```

**Features:**
- Custom FAISS-based document retriever
- Semantic similarity search
- Multiple document retrieval
- Confidence scoring
- Sentence transformer embeddings

### 3. **dspy_rag_optimized.py**
Optimized RAG with multi-hop reasoning and validation.
```bash
python dspy_rag_optimized.py
```

**Features:**
- Multi-hop question decomposition
- Answer validation
- Complex reasoning chains
- Multiple demo scenarios

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key
- Virtual environment (recommended)

### Installation

1. **Create virtual environment:**
```bash
python -m venv dspy-env
source dspy-env/bin/activate  # On Windows: dspy-env\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**
```bash
export OPENAI_API_KEY="your-api-key-here"
# Or on Windows (PowerShell):
# $env:OPENAI_API_KEY="your-api-key-here"
```

## Usage Examples

### Basic RAG
```python
import dspy
from dspy_rag_simple import RAGPipeline, setup_dspy

# Setup
setup_dspy()

# Create and use pipeline
rag = RAGPipeline(num_passages=3)
result = rag("What is machine learning?")
print(result.answer)
```

### Custom Retriever
```python
from dspy_rag_with_retriever import FAISSRetriever, AdvancedRAGPipeline

# Prepare corpus
corpus = [
    "Machine learning is...",
    "Deep learning uses...",
    # ... more documents
]

# Create retriever and pipeline
retriever = FAISSRetriever(corpus, k=3)
rag = AdvancedRAGPipeline(retriever)
result = rag("What is machine learning?")
```

### Multi-hop Reasoning
```python
from dspy_rag_optimized import MultiHopRAGPipeline

rag = MultiHopRAGPipeline(num_passages=3, num_hops=2)
result = rag("How do neural networks relate to transfer learning?")
```

## Key DSPy Concepts

### 1. **Modules**
Reusable components that encapsulate LM calls:
```python
class MyRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.answer = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.answer(context=context, question=question)
```

### 2. **Signatures**
Declarative interfaces for LM behavior:
```python
# Define what the model should do
answer_generator = dspy.ChainOfThought("context, question -> answer")

# Use it
prediction = answer_generator(context="...", question="...")
```

### 3. **ChainOfThought**
Reasoning pattern with intermediate steps:
```python
cot = dspy.ChainOfThought("question -> answer")
result = cot(question="What is 2+2?")
# Includes reasoning steps
```

### 4. **Retrieve**
Built-in retrieval component:
```python
retriever = dspy.Retrieve(k=3)
passages = retriever("search query").passages
```

## Advanced Features

### Prompt Optimization
DSPy can automatically optimize prompts:
```python
from dspy.teleprompt import BootstrapFewShot

# Compile program with few-shot examples
compiler = BootstrapFewShot()
optimized_rag = compiler.compile(rag, trainset=examples)
```

### Custom Retrievers
Implement your own retriever:
```python
class CustomRetriever(dspy.Retrieve):
    def forward(self, query):
        # Your retrieval logic
        passages = retrieve_documents(query)
        return dspy.Prediction(passages=passages)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `dspy-ai` | Core DSPy framework |
| `openai` | OpenAI API integration |
| `sentence-transformers` | Semantic embeddings |
| `faiss-cpu` | Vector similarity search |
| `numpy` | Numerical operations |
| `python-dotenv` | Environment management |

## Troubleshooting

### "OPENAI_API_KEY not set"
Set your API key:
```bash
export OPENAI_API_KEY="sk-..."
```

### "sentence-transformers not found"
Install the full requirements:
```bash
pip install -r requirements.txt
```

### Retriever returns empty results
Check that:
1. Corpus is properly initialized
2. Query is not empty
3. Embeddings are computed correctly

## Resources

- [DSPy Documentation](https://github.com/stanfordnlp/dspy)
- [DSPy Guides](https://github.com/stanfordnlp/dspy/tree/main/examples)
- [RAG Best Practices](https://python.langchain.com/docs/modules/data_connection/retrieval_augmented_generation/)
- [OpenAI API Docs](https://platform.openai.com/docs/)

## Next Steps

1. **Expand corpus**: Add more documents for better retrieval
2. **Tune parameters**: Adjust `k` (number of passages), temperature, etc.
3. **Prompt optimization**: Use DSPy compilers to automatically optimize prompts
4. **Add evaluation**: Measure RAG quality with metrics like BLEU, ROUGE
5. **Production deployment**: Integrate with your application

## License

MIT
