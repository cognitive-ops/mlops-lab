# Quick Start Guide - DSPy RAG System

## 5-Minute Setup

### 1. Install Dependencies
```bash
cd demo/dspy
pip install -r requirements.txt
```

### 2. Set OpenAI API Key
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Run a Demo
```bash
# Simple RAG
python dspy_rag_simple.py

# RAG with FAISS Retriever
python dspy_rag_with_retriever.py

# Optimized RAG with Multi-hop Reasoning
python dspy_rag_optimized.py

# Production-Ready System
python dspy_rag_production.py
```

## What Each Script Does

| Script | Complexity | Best For | Key Features |
|--------|-----------|----------|--------------|
| `dspy_rag_simple.py` | ⭐ Low | Learning basics | Built-in Retrieve, ChainOfThought |
| `dspy_rag_with_retriever.py` | ⭐⭐ Medium | Custom retrieval | FAISS, Embeddings, Confidence scoring |
| `dspy_rag_optimized.py` | ⭐⭐⭐ High | Advanced reasoning | Multi-hop, Validation, Complex chains |
| `dspy_rag_production.py` | ⭐⭐⭐⭐ Advanced | Real applications | Document store, Evaluation, Error handling |

## Understanding DSPy Basics

### 1. Modules
```python
class MyRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.answer = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        passages = self.retrieve(question).passages
        return self.answer(context=passages, question=question)
```

### 2. Signatures
Define what LM should do:
```python
# Input -> Output specification
qa = dspy.ChainOfThought("context, question -> answer, confidence")
result = qa(context="...", question="...")
```

### 3. Retrieve
Built-in document retrieval:
```python
retriever = dspy.Retrieve(k=3)
passages = retriever("search query").passages  # Returns top 3 passages
```

### 4. ChainOfThought
Reasoning with intermediate steps:
```python
cot = dspy.ChainOfThought("input -> output")
result = cot(input="What is 2+2?")
# Includes reasoning explanation
```

## Common Patterns

### Pattern 1: Basic QA
```python
class BasicQA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.qa = dspy.ChainOfThought("question -> answer")
    
    def forward(self, question):
        return self.qa(question=question)
```

### Pattern 2: RAG
```python
class RAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.qa = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.qa(context=context, question=question)
```

### Pattern 3: Multi-step Reasoning
```python
class MultiStep(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step1 = dspy.ChainOfThought("input -> intermediate")
        self.step2 = dspy.ChainOfThought("intermediate -> output")
    
    def forward(self, input_text):
        step1_result = self.step1(input=input_text)
        return self.step2(intermediate=step1_result.intermediate)
```

## API Key Setup

### Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key

### Set in Environment

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-..."
# Verify
echo $env:OPENAI_API_KEY
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-...
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-..."
# Verify
echo $OPENAI_API_KEY
```

**Python (quick test):**
```python
import os
os.environ['OPENAI_API_KEY'] = 'sk-...'
```

## Troubleshooting

### Issue: OPENAI_API_KEY not set
**Solution:** Make sure to set the environment variable before running the script.

### Issue: sentence-transformers not found
**Solution:** Install full requirements:
```bash
pip install -r requirements.txt
```

### Issue: Module not found errors
**Solution:** Run from the correct directory:
```bash
cd demo/dspy
python dspy_rag_simple.py
```

### Issue: FAISS import error
**Solution:** Install FAISS:
```bash
pip install faiss-cpu
```

## Next Steps

1. **Modify the corpus**: Edit the sample documents in `dspy_rag_production.py`
2. **Add your own data**: Use `DocumentStore.add_from_json()` to load custom data
3. **Optimize prompts**: Use DSPy compilers to improve performance
4. **Add evaluation**: Implement metrics to measure RAG quality
5. **Deploy**: Integrate RAG with your application

## Resources

- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy Examples](https://github.com/stanfordnlp/dspy/tree/main/examples)
- [OpenAI API Docs](https://platform.openai.com/docs/)
- [RAG Paper](https://arxiv.org/abs/2005.11401)

## Example: Minimal RAG in 10 Lines

```python
import dspy
import os

# Setup
dspy.settings.configure(lm=dspy.OpenAI(model=\"gpt-3.5-turbo\"))

# Define RAG
class RAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.qa = dspy.ChainOfThought(\"context, question -> answer\")
    def forward(self, q): 
        return self.qa(context=self.retrieve(q).passages, question=q)

# Use
rag = RAG()
print(rag(\"What is machine learning?\").answer)
```

That's it! You now have a working RAG system with DSPy.
