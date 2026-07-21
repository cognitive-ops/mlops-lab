from typing_extensions import List, TypedDict
from langgraph.graph import START, StateGraph
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
# from langchain import hub  # Commented out due to import issues
import bs4
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass(
        "Enter API key for OpenAI: ")

try:
    # Initialize OpenAI GPT model
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",  # You can change to "gpt-4" or "gpt-4o" for better performance
        temperature=0.7
    )
    # Using OpenAI embedding model
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    vector_store = InMemoryVectorStore(embeddings)
except Exception as e:
    print(f"Error initializing OpenAI models: {str(e)}")
    print("Please ensure you have a valid OpenAI API key with sufficient credits")
    raise


# Load and chunk contents of the blog
loader = WebBaseLoader(
    web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("post-content", "post-title", "post-header")
        )
    ),
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200)
all_splits = text_splitter.split_documents(docs)

# Index chunks
_ = vector_store.add_documents(documents=all_splits)

# Define prompt for question-answering
# Custom RAG prompt template (replacing hub.pull due to import issues)


def create_rag_prompt(question: str, context: str) -> str:
    """Create a RAG prompt with question and context"""
    return f"""You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.

Question: {question}

Context: {context}

Answer:"""


# Define state for application
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# Define application steps


def retrieve(state: State):
    print(f"🔧 DEBUG: Starting retrieval for question: '{state['question']}'")
    try:
        retrieved_docs = vector_store.similarity_search(state["question"])
        print(f"✅ DEBUG: Retrieved {len(retrieved_docs)} documents")
        for i, doc in enumerate(retrieved_docs):
            print(f"   Document {i+1}: {doc.page_content[:100]}...")
        return {"context": retrieved_docs}
    except Exception as e:
        print(f"❌ DEBUG: Retrieval failed: {e}")
        raise


def generate(state: State):
    print(f"🔧 DEBUG: Starting generation for question: '{state['question']}'")
    try:
        docs_content = "\n\n".join(
            doc.page_content for doc in state["context"])
        print(
            f"✅ DEBUG: Combined context length: {len(docs_content)} characters")

        prompt_text = create_rag_prompt(state["question"], docs_content)
        print(
            f"✅ DEBUG: Created prompt, length: {len(prompt_text)} characters")

        response = llm.invoke(prompt_text)
        print(f"✅ DEBUG: Generated response: {response.content[:200]}...")
        return {"answer": response.content}
    except Exception as e:
        print(f"❌ DEBUG: Generation failed: {e}")
        raise


# Compile application and test
graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()


# Simple LangChain examples
def simple_chat_example():
    """Simple chat example with LangChain"""
    print("=== Simple Chat Example ===")

    # Simple chat without RAG
    simple_prompt = "What is artificial intelligence? Explain in 2-3 sentences."
    response = llm.invoke(simple_prompt)
    print(f"Question: {simple_prompt}")
    print(f"Answer: {response.content}")
    print()


def rag_example():
    """RAG example using the graph we built"""
    print("=== RAG Example ===")

    # Test the RAG system
    question = "What are the key components of an AI agent?"
    print(f"Question: {question}")

    # Run the graph
    result = graph.invoke({"question": question})
    print(f"Answer: {result['answer']}")
    print()

    # Show retrieved context
    print("Retrieved context chunks:")
    for i, doc in enumerate(result['context']):
        print(f"Chunk {i+1}: {doc.page_content[:200]}...")
    print()


def chain_example():
    """Example of creating a simple chain using basic LangChain functionality"""
    print("=== Simple LLM Chain Example ===")

    # Create simple prompts
    topics = [
        "What is machine learning and how does it work?",
        "Explain natural language processing in simple terms.",
        "What are the main types of artificial intelligence?"
    ]

    for topic in topics:
        print(f"Question: {topic}")
        response = llm.invoke(topic)
        print(f"Answer: {response.content}")
        print("-" * 50)
        print()


def document_processing_example():
    """Example of document processing with LangChain"""
    print("=== Document Processing Example ===")

    # Create a simple document
    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science that aims to create 
    intelligent machines that can perform tasks typically requiring human intelligence. 
    These tasks include learning, reasoning, problem-solving, perception, and language understanding.
    
    Machine Learning is a subset of AI that focuses on the development of algorithms 
    that can learn and make predictions or decisions without being explicitly programmed 
    for every scenario.
    """

    # Create a document object
    doc = Document(page_content=sample_text, metadata={"source": "sample_doc"})

    # Split the document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=50
    )
    chunks = text_splitter.split_documents([doc])

    print(f"Original document length: {len(sample_text)} characters")
    print(f"Number of chunks created: {len(chunks)}")
    print("\nChunks:")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk.page_content.strip()}")
        print()


def main():
    """Main function to run all examples"""
    print("🤖 LangChain Examples\n")
    print("🔧 DEBUG: Starting main execution...")

    try:
        print("🔧 DEBUG: Running simple chat example...")
        # Run simple chat
        simple_chat_example()

        print("🔧 DEBUG: Running document processing example...")
        # Run document processing example
        document_processing_example()

        print("🔧 DEBUG: Running chain example...")
        # Run chain example
        chain_example()

        print("🔧 DEBUG: Running RAG example...")
        # Run RAG example (requires internet connection)
        print("📡 Note: RAG example requires internet connection to load web content")
        rag_example()

        print("✅ DEBUG: All examples completed successfully!")

    except Exception as e:
        print(f"❌ DEBUG: Error running examples: {str(e)}")
        print("Make sure you have valid API keys and internet connection")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
