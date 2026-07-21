# DSPy RAG System - Implementation Summary

## What You Have

A complete, production-ready Retrieval-Augmented Generation (RAG) system using **DSPy** from Databricks with multiple examples from beginner to advanced.

## Files Overview

### 📚 Documentation
- **README.md** - Complete reference guide with concepts and examples
- **QUICKSTART.md** - 5-minute setup and basic patterns
- **requirements.txt** - All dependencies

### 🔧 Core Implementation Files

#### 1. **dspy_rag_simple.py** (Beginner)
**What:** Basic RAG using DSPy built-in components
```python
rag = RAGPipeline(num_passages=3)
result = rag("What is machine learning?")
```
**Key Classes:**
- `RAGPipeline` - Simple retrieve + generate pattern

**Learn:** Basic DSPy usage, Retrieve component, ChainOfThought

---

#### 2. **dspy_rag_with_retriever.py** (Intermediate)
**What:** Advanced RAG with custom FAISS retriever
```python
retriever = FAISSRetriever(corpus, k=3)
rag = AdvancedRAGPipeline(retriever)
```
**Key Classes:**
- `FAISSRetriever` - Custom retriever with semantic search
- `AdvancedRAGPipeline` - With confidence scoring

**Learn:** Custom retrievers, semantic embeddings, confidence prediction

---

#### 3. **dspy_rag_optimized.py** (Advanced)
**What:** Multi-hop reasoning and validation patterns
```python
rag = MultiHopRAGPipeline(num_passages=3, num_hops=2)
```
**Key Classes:**
- `MultiHopRAGPipeline` - Question decomposition and multi-step reasoning
- `RAGWithValidation` - Answer validation
- `SimpleQAProgram` - Basic QA signature

**Learn:** Complex reasoning chains, validation, decomposition

---

#### 4. **dspy_rag_production.py** (Production)
**What:** Enterprise-ready RAG with document management
```python
doc_store = DocumentStore()
doc_store.add_documents(documents)
vector_store = VectorStore(doc_store.get_all_documents())
rag = ProductionRAG(vector_store)
```
**Key Classes:**
- `DocumentStore` - Document management
- `VectorStore` - Vector embeddings and search
- `VectorStoreRetriever` - Integration with DSPy
- `ProductionRAG` - Full RAG system
- `RAGEvaluator` - System evaluation

**Learn:** Production patterns, document processing, evaluation

---

### 🧪 Testing & Config
- **test_rag_system.py** - Comprehensive test suite
- **config.py** - Configuration management
- **.env.example** - Environment template

## Quick Start (5 Minutes)

### 1. Install
```bash
cd demo/dspy
pip install -r requirements.txt
```

### 2. Configure
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"
```

### 3. Run
```bash
# Start with production example (most complete)
python dspy_rag_production.py
```

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         Query/Question Input            │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   Document Retrieval (Vector Store)     │
│   - Semantic similarity search          │
│   - Top-K passage retrieval             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  LLM Processing (DSPy ChainOfThought)   │
│   - Context integration                 │
│   - Reasoning generation                │
│   - Answer synthesis                    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   Answer + Metadata Output              │
│   - Final answer                        │
│   - Confidence score                    │
│   - Source documents                    │
└─────────────────────────────────────────┘
```

## Key DSPy Concepts Used

### 1. **Modules**
Reusable components:
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
Input-output specifications:
```python
# Specifies: given context and question, produce answer
qa = dspy.ChainOfThought("context, question -> answer")
```

### 3. **Retrieve**
Document retrieval:
```python
retriever = dspy.Retrieve(k=3)  # Get top 3 documents
passages = retriever("query").passages
```

### 4. **ChainOfThought**
Reasoning with intermediate steps:
```python
cot = dspy.ChainOfThought("question -> answer")
# Produces: question, reasoning, answer
```

## Workflow Comparison

| Task | Simple | With Retriever | Optimized | Production |
|------|--------|---|---|---|
| Basic QA | ✓ | ✓ | ✓ | ✓ |
| Custom Retrieval | ✗ | ✓ | ✓ | ✓ |
| Multi-hop | ✗ | ✗ | ✓ | ✓ |
| Document Store | ✗ | ✗ | ✗ | ✓ |
| Evaluation | ✗ | ✗ | ✗ | ✓ |
| Error Handling | Basic | Basic | Basic | Full |

## Configuration

All settings in `config.py`:
```python
DEFAULT_MODEL = "gpt-3.5-turbo"      # LLM to use
DEFAULT_MAX_TOKENS = 500              # Max output length
DEFAULT_K = 3                         # Number of documents to retrieve
EMBEDDING_MODEL = "all-MiniLM-L6-v2" # Embedding model
```

Environment variables in `.env`:
```bash
OPENAI_API_KEY=sk-...
VERBOSE=False
```

## Running Tests

```bash
python test_rag_system.py
```

Tests:
1. ✓ Import validation
2. ✓ Configuration check
3. ✓ Document store functionality
4. ✓ Vector store operations
5. ✓ Full RAG system
6. ✓ Evaluation framework
7. ✓ Performance profiling

## Common Use Cases

### Use Case 1: Document Q&A
```python
from dspy_rag_production import DocumentStore, VectorStore, ProductionRAG

docs = [{"content": "..."}, {"content": "..."}]
doc_store = DocumentStore()
doc_store.add_documents(docs)
vector_store = VectorStore(doc_store.get_all_documents())
rag = ProductionRAG(vector_store)

answer = rag("Your question here").answer
```

### Use Case 2: Web Content Q&A
```python
# Fetch web content
import requests
from bs4 import BeautifulSoup

url = "https://example.com/article"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
content = soup.get_text()

# Use with RAG
docs = [{"content": content}]
# ... rest as above
```

### Use Case 3: Custom Reasoning
```python
class CustomRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=5)
        self.reason = dspy.ChainOfThought("docs, query -> reasoning, answer")
    
    def forward(self, query):
        docs = self.retrieve(query).passages
        return self.reason(docs=docs, query=query)
```

## Advanced Features

### Prompt Optimization
```python
from dspy.teleprompt import BootstrapFewShot

compiler = BootstrapFewShot()
optimized_rag = compiler.compile(rag, trainset=examples)
```

### Custom Evaluators
```python
class CustomEvaluator:
    def metric(self, gold_answer, pred_answer):
        # Your metric logic
        return score
```

### Multi-Provider Support
Switch between providers:
```python
# OpenAI
lm = dspy.OpenAI(model="gpt-4")

# Anthropic (if configured)
lm = dspy.LM('claude-3-opus')

# Local models
lm = dspy.Local(model_path="...")
```

## Extending the System

### Add Custom Retriever
```python
class CustomRetriever(dspy.Retrieve):
    def forward(self, query):
        # Your retrieval logic
        passages = your_search_function(query)
        return dspy.Prediction(passages=passages)
```

### Add Custom Signature
```python
class CustomSignature(dspy.Signature):
    """Your custom task description"""
    input_field = dspy.InputField(desc="Input description")
    output_field = dspy.OutputField(desc="Output description")
```

## Performance Tips

1. **Reduce max_tokens** for faster responses
2. **Increase k** in retriever for better context (increases latency)
3. **Use cheaper model** (gpt-3.5-turbo vs gpt-4)
4. **Cache embeddings** for repeated queries
5. **Batch queries** when possible

## Troubleshooting

| Problem | Solution |
|---------|----------|
| API Key error | Set `OPENAI_API_KEY` environment variable |
| No responses | Check `DEFAULT_MAX_TOKENS` setting |
| Slow retrieval | Reduce number of documents or use better indexing |
| Memory issues | Use FAISS GPU indexing or reduce corpus size |
| Low quality answers | Add more/better documents or increase `k` |

## Next Steps

1. **Integrate documents**: Add your own data to DocumentStore
2. **Optimize prompts**: Use DSPy compilers to improve results
3. **Evaluate**: Run test_rag_system.py to validate setup
4. **Deploy**: Package as API for your application
5. **Monitor**: Track performance and quality metrics

## Resources

- **DSPy Docs**: https://github.com/stanfordnlp/dspy
- **RAG Paper**: https://arxiv.org/abs/2005.11401
- **OpenAI API**: https://platform.openai.com/docs/
- **LLM Best Practices**: https://lilianweng.github.io/posts/2023-10-25-llm-rag/

## Summary

You now have a complete RAG system with:
- ✓ 4 progressively complex implementations
- ✓ Production-ready code with error handling
- ✓ Custom vector store and document management
- ✓ Evaluation framework
- ✓ Comprehensive testing suite
- ✓ Full documentation

Start with `dspy_rag_production.py` and customize from there!
