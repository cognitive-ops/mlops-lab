"""
RAG (Retrieval-Augmented Generation) with LangChain
This example demonstrates how to build a RAG system using LangChain
"""

import os
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

# Set up API keys (if using OpenAI instead of Ollama)
# os.environ["OPENAI_API_KEY"] = "your-openai-key"

def create_vector_store_from_documents(documents_path):
    """
    Load documents, split them, and create a vector store
    """
    print("📚 Loading documents...")
    
    # Load documents from directory
    loader = DirectoryLoader(
        documents_path,
        glob="**/*.txt",
        loader_cls=TextLoader
    )
    documents = loader.load()
    print(f"Loaded {len(documents)} documents")
    
    # Split documents into chunks
    print("✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")
    
    # Create embeddings using HuggingFace (free, local)
    print("🔢 Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    # Create vector store
    print("💾 Creating vector store...")
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Save vector store for later use
    vector_store.save_local("faiss_index")
    print("✅ Vector store created and saved!")
    
    return vector_store

def load_existing_vector_store():
    """
    Load an existing vector store
    """
    print("📂 Loading existing vector store...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    vector_store = FAISS.load_local(
        "faiss_index", 
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("✅ Vector store loaded!")
    return vector_store

def create_rag_chain(vector_store, use_ollama=True):
    """
    Create a RAG chain with retrieval and generation
    """
    print("🔗 Creating RAG chain...")
    
    # Choose LLM
    if use_ollama:
        # Use Ollama (free, local) - Make sure Ollama is installed
        # Install: https://ollama.ai/
        # Run: ollama pull llama3.2
        llm = Ollama(model="llama3.2", temperature=0.7)
        print("Using Ollama with llama3.2 model")
    else:
        # Use OpenAI (requires API key and billing)
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        print("Using OpenAI with gpt-4o-mini model")
    
    # Create custom prompt template
    template = """Use the following pieces of context to answer the question at the end. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    
    Context: {context}
    
    Question: {question}
    
    Answer:"""
    
    PROMPT = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    # Create retrieval chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    
    print("✅ RAG chain created!")
    return qa_chain

def query_rag_system(qa_chain, question):
    """
    Query the RAG system
    """
    print(f"\n❓ Question: {question}")
    print("🔍 Searching and generating answer...\n")
    
    result = qa_chain.invoke({"query": question})
    
    print(f"💬 Answer: {result['result']}\n")
    print("📄 Source Documents:")
    for i, doc in enumerate(result['source_documents'], 1):
        print(f"\n--- Source {i} ---")
        print(f"Content: {doc.page_content[:200]}...")
        print(f"Metadata: {doc.metadata}")
    
    return result

def main():
    """
    Main function to run the RAG system
    """
    print("🚀 LangChain RAG System\n")
    
    # Example usage - choose one:
    
    # Option 1: Create new vector store from documents
    # Uncomment if you have documents to index
    # documents_path = "./data"  # Path to your documents
    # vector_store = create_vector_store_from_documents(documents_path)
    
    # Option 2: Load existing vector store
    try:
        vector_store = load_existing_vector_store()
    except Exception as e:
        print(f"❌ Error loading vector store: {e}")
        print("💡 Creating a sample vector store...")
        
        # Create sample documents for demo
        from langchain_core.documents import Document
        sample_docs = [
            Document(
                page_content="LangChain is a framework for developing applications powered by language models. It was created by Harrison Chase in 2022.",
                metadata={"source": "langchain_info.txt"}
            ),
            Document(
                page_content="RAG (Retrieval-Augmented Generation) combines information retrieval with text generation. It retrieves relevant documents and uses them as context for generating answers.",
                metadata={"source": "rag_info.txt"}
            ),
            Document(
                page_content="FAISS (Facebook AI Similarity Search) is a library for efficient similarity search and clustering of dense vectors. It's commonly used for vector databases.",
                metadata={"source": "faiss_info.txt"}
            ),
        ]
        
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        vector_store = FAISS.from_documents(sample_docs, embeddings)
        vector_store.save_local("faiss_index")
        print("✅ Sample vector store created!")
    
    # Create RAG chain
    # Set use_ollama=False to use OpenAI (requires API key and billing)
    qa_chain = create_rag_chain(vector_store, use_ollama=True)
    
    # Example queries
    questions = [
        "What is LangChain?",
        "Explain RAG in simple terms",
        "What is FAISS used for?",
    ]
    
    for question in questions:
        query_rag_system(qa_chain, question)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
