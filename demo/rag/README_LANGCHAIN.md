# LangChain RAG System

A complete Retrieval-Augmented Generation (RAG) system built with LangChain.

## 🎯 Features

- 📚 Document loading from multiple formats (TXT, PDF, DOCX)
- ✂️ Intelligent text chunking
- 🔢 Free local embeddings (HuggingFace)
- 💾 FAISS vector store for efficient similarity search
- 🤖 Support for both Ollama (free, local) and OpenAI
- 🔍 Semantic search and answer generation

## 📦 Installation

### Option 1: Install in WSL (Recommended)

```bash
# Activate conda environment
conda activate ai

# Install LangChain dependencies
pip install -r requirements_langchain.txt

# Install Ollama (for free local LLM)
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2
```

### Option 2: Install in PowerShell

```powershell
# Activate conda environment
conda activate ai

# Install dependencies
pip install -r requirements_langchain.txt

# Install Ollama from: https://ollama.ai/download
# Then run: ollama pull llama3.2
```

## 🚀 Quick Start

### 1. Basic Usage with Sample Data

```bash
cd /mnt/d/work/acme/backbone-mlops/demo/rag
conda activate ai
python langchain_rag.py
```

This will:
- Create sample documents
- Build a vector store
- Run example queries

### 2. Use Your Own Documents

Create a `data` directory and add your documents:

```bash
mkdir data
# Add your .txt, .pdf, or .docx files to data/
```

Then modify `langchain_rag.py`:

```python
# Uncomment these lines in main():
documents_path = "./data"
vector_store = create_vector_store_from_documents(documents_path)
```

### 3. Interactive Query

```python
from langchain_rag import create_rag_chain, load_existing_vector_store, query_rag_system

# Load vector store
vector_store = load_existing_vector_store()

# Create RAG chain
qa_chain = create_rag_chain(vector_store, use_ollama=True)

# Ask questions
query_rag_system(qa_chain, "Your question here?")
```

## 🔧 Configuration

### Using Ollama (Free, Local)

```python
qa_chain = create_rag_chain(vector_store, use_ollama=True)
```

**Requirements:**
- Install Ollama: https://ollama.ai/
- Pull a model: `ollama pull llama3.2`
- No API key needed!

### Using OpenAI

```python
qa_chain = create_rag_chain(vector_store, use_ollama=False)
```

**Requirements:**
- Set environment variable: `export OPENAI_API_KEY="sk-..."`
- Or add to `.env` file
- Requires billing setup at https://platform.openai.com/account/billing

## 📁 Project Structure

```
rag/
├── langchain_rag.py              # Main RAG implementation
├── requirements_langchain.txt     # Python dependencies
├── README_LANGCHAIN.md           # This file
├── data/                         # Your documents (create this)
│   ├── document1.txt
│   ├── document2.pdf
│   └── ...
└── faiss_index/                  # Vector store (auto-generated)
    ├── index.faiss
    └── index.pkl
```

## 💡 Key Components

### 1. Document Loading
```python
from langchain_community.document_loaders import DirectoryLoader, TextLoader

loader = DirectoryLoader("./data", glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()
```

### 2. Text Splitting
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(documents)
```

### 3. Embeddings (Local, Free)
```python
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

### 4. Vector Store
```python
from langchain_community.vectorstores import FAISS

vector_store = FAISS.from_documents(chunks, embeddings)
vector_store.save_local("faiss_index")
```

### 5. RAG Chain
```python
from langchain.chains import RetrievalQA

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vector_store.as_retriever(),
    return_source_documents=True
)
```

## 🔍 How RAG Works

```
1. User Question
   ↓
2. Convert question to embedding
   ↓
3. Search vector store for similar chunks
   ↓
4. Retrieve top K relevant chunks
   ↓
5. Combine chunks with question as prompt
   ↓
6. Send to LLM for answer generation
   ↓
7. Return answer + source documents
```

## 🎨 Advanced Usage

### Custom Prompt Template

```python
from langchain.prompts import PromptTemplate

template = """You are a helpful AI assistant. Use the context below to answer.

Context: {context}
Question: {question}

Answer in detail:"""

PROMPT = PromptTemplate(
    template=template,
    input_variables=["context", "question"]
)
```

### Adjust Retrieval Parameters

```python
# Retrieve more/fewer documents
retriever = vector_store.as_retriever(
    search_kwargs={"k": 5}  # Retrieve top 5 documents
)

# Use different search type
retriever = vector_store.as_retriever(
    search_type="mmr",  # Maximal Marginal Relevance
    search_kwargs={"k": 3, "fetch_k": 10}
)
```

### Load Different Document Types

```python
from langchain_community.document_loaders import PDFLoader, Docx2txtLoader

# PDF
pdf_loader = PDFLoader("document.pdf")

# Word Document
docx_loader = Docx2txtLoader("document.docx")
```

## 🐛 Troubleshooting

### Import Errors
```bash
pip install --upgrade langchain langchain-community langchain-core
```

### Ollama Connection Error
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

### Out of Memory
```python
# Reduce chunk size
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,  # Smaller chunks
    chunk_overlap=50
)
```

## 📊 Performance Tips

1. **Use GPU for embeddings** (if available):
   ```python
   embeddings = HuggingFaceEmbeddings(
       model_kwargs={'device': 'cuda'}
   )
   ```

2. **Batch processing for large documents**:
   ```python
   vector_store = FAISS.from_documents(
       chunks[:100]  # Process in batches
   )
   ```

3. **Cache vector store** to avoid reprocessing:
   ```python
   vector_store.save_local("faiss_index")
   ```

## 🔗 Resources

- **LangChain Docs**: https://python.langchain.com/
- **Ollama Models**: https://ollama.ai/library
- **FAISS**: https://github.com/facebookresearch/faiss
- **Sentence Transformers**: https://www.sbert.net/

## 📝 Example Queries

```python
questions = [
    "What is the main topic of the documents?",
    "Summarize the key points",
    "What are the recommendations mentioned?",
    "Compare X and Y from the documents",
]

for question in questions:
    result = query_rag_system(qa_chain, question)
```

## 🌟 Next Steps

1. **Add more document types** (PDF, DOCX, HTML)
2. **Implement chat history** for conversational RAG
3. **Add evaluation metrics** for answer quality
4. **Deploy as API** using FastAPI
5. **Create web interface** with Streamlit

## 💰 Cost Comparison

| Option | Cost | Speed | Privacy |
|--------|------|-------|---------|
| Ollama (Local) | Free | Fast | 100% Private |
| OpenAI GPT-4o-mini | ~$0.15/1M tokens | Very Fast | API-based |
| OpenAI GPT-4 | ~$10/1M tokens | Fast | API-based |

## 🤝 Contributing

Feel free to extend this RAG system with:
- More LLM providers (Anthropic, Cohere, etc.)
- Different vector stores (Chroma, Pinecone, Weaviate)
- Enhanced retrieval strategies (HyDE, Multi-query)
- Evaluation frameworks

---

**Happy RAG Building! 🚀**
