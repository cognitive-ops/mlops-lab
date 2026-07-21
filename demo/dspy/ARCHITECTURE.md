# DSPy RAG System Architecture

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY INPUT                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      QUERY PREPROCESSING                            │
│  • Text cleaning                                                    │
│  • Token counting                                                   │
│  • Validation                                                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT RETRIEVAL (VECTOR STORE)               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Query Embedding (Sentence Transformers)                    │  │
│  │  ↓                                                            │  │
│  │  Semantic Similarity Search                                 │  │
│  │  ↓                                                            │  │
│  │  Top-K Document Retrieval (FAISS)                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTEXT ASSEMBLY                              │
│  • Combine retrieved documents                                     │
│  • Format for LLM input                                            │
│  • Token limit management                                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM PROCESSING (OpenAI)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  DSPy Module (e.g., ChainOfThought)                         │  │
│  │  ↓                                                            │  │
│  │  Signature Definition                                        │  │
│  │  ↓                                                            │  │
│  │  Prompt Generation                                           │  │
│  │  ↓                                                            │  │
│  │  LLM API Call (gpt-3.5-turbo / gpt-4)                      │  │
│  │  ↓                                                            │  │
│  │  Response Parsing                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     POST-PROCESSING                                │
│  • Answer extraction                                               │
│  • Confidence scoring                                              │
│  • Source attribution                                              │
│  • Validation                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STRUCTURED OUTPUT                               │
│  • Answer text                                                    │
│  • Confidence score                                               │
│  • Source documents                                               │
│  • Reasoning steps                                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────┐
│   DOCUMENTS │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ DOCUMENT STORE       │
│ • JSON              │
│ • CSV               │
│ • Text              │
│ • Web               │
│ • PDF               │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ EMBEDDING GENERATION │
│ (Sentence Trans.)    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ VECTOR STORE (FAISS) │
└──────┬───────────────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
    INDEXING          QUERY SEARCH
    (Offline)          (Online)
                         │
                         ▼
                    RETRIEVED DOCS
                         │
                         ▼
                    RAG PIPELINE
```

## Module Hierarchy

```
dspy.Module
│
├── SimpleQAProgram
│   └── Uses: ChainOfThought("question -> answer")
│
├── RAGPipeline
│   ├── retrieve: dspy.Retrieve(k=3)
│   └── generate_answer: ChainOfThought
│
├── AdvancedRAGPipeline
│   ├── retriever: FAISSRetriever
│   └── answer_generator: ChainOfThought
│
├── MultiHopRAGPipeline
│   ├── retrieve: dspy.Retrieve()
│   ├── decompose: Predict()
│   └── answer_generator: ChainOfThought()
│
├── RAGWithValidation
│   ├── retrieve: dspy.Retrieve()
│   ├── answer_generator: ChainOfThought()
│   └── validator: Predict()
│
└── ProductionRAG
    ├── retriever: VectorStoreRetriever
    ├── answer_generator: ChainOfThought()
    └── confidence_scorer: Predict()
```

## Component Relationships

```
┌─────────────────────────────────────────┐
│         DSPy Module                     │
│  (Base class for all RAG components)    │
└────────────┬────────────────────────────┘
             │
    ┌────────┴────────┬────────────────────┐
    │                 │                    │
    ▼                 ▼                    ▼
┌─────────┐    ┌──────────────┐    ┌─────────────┐
│Retrieve │    │ChainOfThought│    │  Predict    │
│         │    │              │    │             │
│K=3      │    │Reasoning +   │    │Prediction   │
│Top docs │    │Answer        │    │Only         │
└─────────┘    └──────────────┘    └─────────────┘
    ▲                 ▲                    ▲
    │                 │                    │
    └─────────────────┴────────────────────┘
             Uses
             │
             ▼
    ┌────────────────────┐
    │  Signature Objects │
    │  (I/O Spec)        │
    │                    │
    │ Declares input &   │
    │ output fields      │
    └────────────────────┘
```

## Data Processing Pipeline

```
Input Documents
      │
      ▼
┌──────────────────────┐
│  Data Integration    │
│  - from_json_file    │
│  - from_csv_file     │
│  - from_web_url      │
│  - from_directory    │
│  - from_pdf_file     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  DocumentStore       │
│  - add_documents()   │
│  - get_documents()   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  VectorStore         │
│  - build_embeddings()│
│  - search()          │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  VectorStoreRetriever│
│  (dspy.Retrieve)     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  RAG Pipeline        │
│  - retrieve docs     │
│  - generate answer   │
│  - score confidence  │
└──────┬───────────────┘
       │
       ▼
Output (Answer + Sources)
```

## Query Processing Flow

```
Query: "What is machine learning?"
│
├─ STEP 1: Query Embedding
│  └─ Embed query using SentenceTransformer
│     └─ Dense vector (384-dim)
│
├─ STEP 2: Similarity Search
│  └─ Find similar docs in FAISS index
│     └─ Cosine similarity scores
│
├─ STEP 3: Retrieve Top-K
│  └─ Select top 3 documents
│     └─ ["ML is...", "ML uses...", "ML learns..."]
│
├─ STEP 4: Format Context
│  └─ Combine docs for LLM
│     └─ "Doc1: ML is...\nDoc2: ML uses...\nDoc3: ML learns..."
│
├─ STEP 5: Build Prompt
│  └─ Create DSPy prompt
│     └─ "Context: ...\nQuestion: What is machine learning?\nAnswer:"
│
├─ STEP 6: LLM Call
│  └─ Send to OpenAI API
│     └─ gpt-3.5-turbo processes
│
├─ STEP 7: Parse Response
│  └─ Extract answer + reasoning
│     └─ answer="...", reasoning="..."
│
├─ STEP 8: Score Confidence
│  └─ Validate answer against context
│     └─ confidence="high"
│
└─ STEP 9: Return Result
   └─ Final output with sources
      └─ Prediction(answer, reasoning, confidence, sources)
```

## System Stack

```
┌─────────────────────────────────────────┐
│         APPLICATION LAYER               │
│  (Your code using RAG system)           │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         DSPy FRAMEWORK LAYER            │
│  • Modules                              │
│  • Signatures                           │
│  • ChainOfThought                       │
│  • Retrieve                             │
│  • Predict                              │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      RAG COMPONENTS LAYER               │
│  • DocumentStore                        │
│  • VectorStore                          │
│  • VectorStoreRetriever                 │
│  • ProductionRAG                        │
│  • RAGEvaluator                         │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      EMBEDDING & SEARCH LAYER           │
│  • SentenceTransformers                 │
│  • FAISS                                │
│  • NumPy                                │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         LLM API LAYER                   │
│  • OpenAI API                           │
│  • gpt-3.5-turbo                        │
│  • gpt-4 (optional)                     │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│       EXTERNAL SERVICES                 │
│  • OpenAI LLM Service                   │
│  • Internet (for web content)           │
└─────────────────────────────────────────┘
```

## File Dependency Graph

```
requirements.txt
    │
    ├── dspy-ai ────┐
    ├── openai ─────┼─► dspy_rag_*.py (all implementations)
    ├── sentence-transformers ─┐
    └── faiss-cpu ────────────┬┼──► dspy_rag_with_retriever.py
                              ││
                              ├─► dspy_rag_optimized.py
                              │
                              └──► dspy_rag_production.py

config.py ──────────────────────► All implementations
.env.example ─────► config.py

test_rag_system.py ──┐
                     ├─► All implementations (for testing)
data_integration.py ─┘

README.md ────────────► Documentation
QUICKSTART.md ────────► Documentation  
IMPLEMENTATION_GUIDE.md ──► Documentation
CHEATSHEET.md ────────► Documentation
SETUP_COMPLETE.md ────► Documentation
```

## Performance Characteristics

```
Component        │ Speed    │ Quality  │ Cost
─────────────────┼──────────┼──────────┼────────
Query Embedding  │ ⚡⚡⚡    │ ⭐⭐⭐  │ Free
FAISS Search     │ ⚡⚡⚡    │ ⭐⭐⭐  │ Free
gpt-3.5-turbo    │ ⚡⚡⚡    │ ⭐⭐    │ $
gpt-4            │ ⚡⚡     │ ⭐⭐⭐  │ $$$
```

---

This architecture provides:
- **Modularity**: Each component is independent
- **Scalability**: Easy to replace components
- **Performance**: Optimized retrieval and generation
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Custom components can be added
