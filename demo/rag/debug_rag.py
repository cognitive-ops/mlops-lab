#!/usr/bin/env python3
"""
Debug version of RAG application with step-by-step execution and error handling.
"""

import sys
import traceback
from typing import List, TypedDict


def debug_step(step_name: str, func, *args, **kwargs):
    """Execute a function with debug information."""
    print(f"\n🔧 DEBUG: Starting {step_name}...")
    try:
        result = func(*args, **kwargs)
        print(f"✅ DEBUG: {step_name} completed successfully")
        return result
    except Exception as e:
        print(f"❌ DEBUG: {step_name} failed: {str(e)}")
        traceback.print_exc()
        return None


def test_imports():
    """Test all required imports."""
    print("Testing imports...")

    try:
        from typing_extensions import List, TypedDict
        print("✅ typing_extensions imported")
    except ImportError as e:
        print(f"❌ typing_extensions failed: {e}")
        return False

    try:
        from langgraph.graph import START, StateGraph
        print("✅ langgraph imported")
    except ImportError as e:
        print(f"❌ langgraph failed: {e}")
        return False

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        print("✅ langchain_text_splitters imported")
    except ImportError as e:
        print(f"❌ langchain_text_splitters failed: {e}")
        return False

    try:
        from langchain_core.documents import Document
        print("✅ langchain_core.documents imported")
    except ImportError as e:
        print(f"❌ langchain_core.documents failed: {e}")
        return False

    try:
        from langchain_community.document_loaders import WebBaseLoader
        print("✅ langchain_community imported")
    except ImportError as e:
        print(f"❌ langchain_community failed: {e}")
        return False

    try:
        import bs4
        print("✅ bs4 imported")
    except ImportError as e:
        print(f"❌ bs4 failed: {e}")
        return False

    try:
        from langchain_core.vectorstores import InMemoryVectorStore
        print("✅ langchain_core.vectorstores imported")
    except ImportError as e:
        print(f"❌ langchain_core.vectorstores failed: {e}")
        return False

    try:
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        print("✅ langchain_openai imported")
    except ImportError as e:
        print(f"❌ langchain_openai failed: {e}")
        return False

    return True


def test_models():
    """Test model initialization."""
    import os
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_core.vectorstores import InMemoryVectorStore

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set. Please set it:")
        print("export OPENAI_API_KEY='your-api-key'")
        return None, None, None

    try:
        print("Initializing ChatOpenAI...")
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
        print("✅ ChatOpenAI initialized")

        print("Initializing OpenAI embeddings...")
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        print("✅ Embeddings initialized")

        print("Initializing vector store...")
        vector_store = InMemoryVectorStore(embeddings)
        print("✅ Vector store initialized")

        return llm, embeddings, vector_store

    except Exception as e:
        print(f"❌ Model initialization failed: {e}")
        return None, None, None


def test_document_processing():
    """Test document processing with simple text."""
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    print("Testing document processing...")

    # Create simple test document
    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science that aims to create 
    intelligent machines that can perform tasks typically requiring human intelligence. 
    These tasks include learning, reasoning, problem-solving, perception, and language understanding.
    
    Machine Learning is a subset of AI that focuses on the development of algorithms 
    that can learn and make predictions or decisions without being explicitly programmed 
    for every scenario.
    """

    doc = Document(page_content=sample_text, metadata={"source": "test_doc"})
    print(f"✅ Created document with {len(doc.page_content)} characters")

    # Test text splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=50)
    chunks = text_splitter.split_documents([doc])
    print(f"✅ Split into {len(chunks)} chunks")

    return chunks


def test_rag_retrieve_function(vector_store, chunks):
    """Test the retrieve function."""
    from langchain_core.documents import Document

    print("Testing document indexing and retrieval...")

    # Add documents to vector store
    vector_store.add_documents(chunks)
    print(f"✅ Added {len(chunks)} documents to vector store")

    # Test similarity search
    query = "What is artificial intelligence?"
    results = vector_store.similarity_search(query, k=2)
    print(f"✅ Retrieved {len(results)} results for query: '{query}'")

    for i, doc in enumerate(results):
        print(f"  Result {i+1}: {doc.page_content[:100]}...")

    return results


def main():
    """Main debug function."""
    print("🐛 RAG DEBUG SESSION STARTED")
    print("=" * 50)

    # Step 1: Test imports
    if not debug_step("Import Testing", test_imports):
        print("❌ Import testing failed. Please install missing packages:")
        print("pip install langchain langchain-openai langchain-community langgraph beautifulsoup4")
        return

    # Step 2: Test models
    llm, embeddings, vector_store = debug_step(
        "Model Initialization", test_models)
    if not all([llm, embeddings, vector_store]):
        print("❌ Model initialization failed. Check your OpenAI API key.")
        return

    # Step 3: Test document processing
    chunks = debug_step("Document Processing", test_document_processing)
    if not chunks:
        print("❌ Document processing failed.")
        return

    # Step 4: Test RAG retrieval
    results = debug_step(
        "RAG Retrieval", test_rag_retrieve_function, vector_store, chunks)
    if not results:
        print("❌ RAG retrieval failed.")
        return

    # Step 5: Test LLM generation
    def test_generation():
        context = "\n\n".join([doc.page_content for doc in results])
        question = "What is artificial intelligence?"

        prompt = f"""You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.

Question: {question}

Context: {context}

Answer:"""

        response = llm.invoke(prompt)
        print(f"✅ Generated response: {response.content[:200]}...")
        return response

    debug_step("LLM Generation", test_generation)

    print("\n🎉 RAG DEBUG SESSION COMPLETED SUCCESSFULLY!")
    print("=" * 50)


if __name__ == "__main__":
    main()
