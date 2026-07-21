"""
Integration examples for DSPy RAG with real data sources
"""

import os
import json
import requests
from typing import List, Dict
from dspy_rag_production import DocumentStore


class DataIntegration:
    """Integration with various data sources"""

    @staticmethod
    def from_json_file(file_path: str) -> List[Dict]:
        """Load documents from JSON file

        Expected format:
        [
            {"id": "doc1", "content": "..."},
            {"id": "doc2", "content": "..."}
        ]
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r") as f:
            return json.load(f)

    @staticmethod
    def from_text_file(file_path: str, chunk_size: int = 500) -> List[Dict]:
        """Load documents from text file with chunking

        Args:
            file_path: Path to text file
            chunk_size: Size of each chunk in characters
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into chunks
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i: i + chunk_size]
            if chunk.strip():
                chunks.append(
                    {"id": f"chunk_{i//chunk_size}", "content": chunk}
                )

        return chunks

    @staticmethod
    def from_csv_file(file_path: str, content_column: str = "content") -> List[Dict]:
        """Load documents from CSV file

        Args:
            file_path: Path to CSV file
            content_column: Name of column containing document text
        """
        import csv

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if content_column in row:
                    documents.append(
                        {"id": f"csv_row_{i}", "content": row[content_column]}
                    )

        return documents

    @staticmethod
    def from_web_url(url: str) -> List[Dict]:
        """Load documents from web page

        Args:
            url: URL to fetch content from
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "Install beautifulsoup4: pip install beautifulsoup4")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch URL: {e}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip()
                  for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return [{"id": url, "content": text}]

    @staticmethod
    def from_markdown_file(file_path: str) -> List[Dict]:
        """Load documents from Markdown file (preserves structure)

        Args:
            file_path: Path to Markdown file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by headings to create logical chunks
        chunks = []
        current_chunk = ""

        for line in content.split("\n"):
            if line.startswith("#") and current_chunk.strip():
                chunks.append({"id": f"md_{len(chunks)}",
                              "content": current_chunk})
                current_chunk = line
            else:
                current_chunk += "\n" + line

        if current_chunk.strip():
            chunks.append({"id": f"md_{len(chunks)}",
                          "content": current_chunk})

        return chunks

    @staticmethod
    def from_pdf_file(file_path: str) -> List[Dict]:
        """Load documents from PDF file

        Args:
            file_path: Path to PDF file
        """
        try:
            import PyPDF2
        except ImportError:
            raise ImportError("Install PyPDF2: pip install PyPDF2")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        documents = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                documents.append(
                    {"id": f"pdf_page_{page_num}", "content": text}
                )

        return documents

    @staticmethod
    def from_directory(directory_path: str, file_pattern: str = "*.txt") -> List[Dict]:
        """Load documents from all files in a directory

        Args:
            directory_path: Path to directory
            file_pattern: Pattern for files to load (e.g., "*.txt", "*.md")
        """
        from pathlib import Path

        if not os.path.isdir(directory_path):
            raise ValueError(f"Not a directory: {directory_path}")

        documents = []
        path = Path(directory_path)

        for file_path in path.glob(file_pattern):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(
                        {
                            "id": f"{file_path.name}",
                            "content": content,
                        }
                    )
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

        return documents


class RAGDataPipeline:
    """Complete pipeline for data loading and RAG"""

    def __init__(self):
        self.doc_store = DocumentStore()
        self.data_integration = DataIntegration()

    def load_from_source(self, source_type: str, source_path: str, **kwargs):
        """Load documents from specified source"""
        print(f"Loading documents from {source_type}: {source_path}")

        if source_type == "json":
            documents = self.data_integration.from_json_file(source_path)
        elif source_type == "text":
            chunk_size = kwargs.get("chunk_size", 500)
            documents = self.data_integration.from_text_file(
                source_path, chunk_size=chunk_size
            )
        elif source_type == "csv":
            content_column = kwargs.get("content_column", "content")
            documents = self.data_integration.from_csv_file(
                source_path, content_column=content_column
            )
        elif source_type == "web":
            documents = self.data_integration.from_web_url(source_path)
        elif source_type == "markdown":
            documents = self.data_integration.from_markdown_file(source_path)
        elif source_type == "pdf":
            documents = self.data_integration.from_pdf_file(source_path)
        elif source_type == "directory":
            pattern = kwargs.get("pattern", "*.txt")
            documents = self.data_integration.from_directory(
                source_path, pattern)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        self.doc_store.add_documents(documents)
        print(f"Loaded {len(documents)} documents")
        return self

    def get_documents(self) -> List[str]:
        """Get all loaded documents"""
        return self.doc_store.get_all_documents()

    def get_store(self) -> DocumentStore:
        """Get document store"""
        return self.doc_store


# Example usage demonstrations
def demo_usage():
    """Demonstrate various data sources"""
    import dspy
    from dspy_rag_production import VectorStore, ProductionRAG

    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return

    lm = dspy.OpenAI(model="gpt-3.5-turbo", api_key=api_key)
    dspy.settings.configure(lm=lm)

    # Example 1: Load from JSON
    print("\n" + "=" * 70)
    print("Example 1: Loading from JSON")
    print("=" * 70)

    # Create sample JSON file
    sample_json = [
        {"id": "1", "content": "Machine learning is a subset of AI"},
        {"id": "2", "content": "Deep learning uses neural networks"},
    ]

    with open("sample_docs.json", "w") as f:
        json.dump(sample_json, f)

    pipeline = RAGDataPipeline()
    pipeline.load_from_source("json", "sample_docs.json")

    docs = pipeline.get_documents()
    vector_store = VectorStore(docs)
    rag = ProductionRAG(vector_store)

    result = rag("What is machine learning?")
    print(f"Answer: {result.answer}\n")

    # Cleanup
    os.remove("sample_docs.json")

    # Example 2: Load from text with chunking
    print("\n" + "=" * 70)
    print("Example 2: Loading from Text File")
    print("=" * 70)

    sample_text = """
    Artificial Intelligence (AI) is the simulation of human intelligence by machines.
    Machine Learning (ML) is a subset of AI that focuses on learning from data.
    Deep Learning is a subset of ML that uses neural networks with multiple layers.
    """

    with open("sample.txt", "w") as f:
        f.write(sample_text)

    pipeline = RAGDataPipeline()
    pipeline.load_from_source("text", "sample.txt", chunk_size=100)

    docs = pipeline.get_documents()
    print(f"Created {len(docs)} chunks from text")

    # Cleanup
    os.remove("sample.txt")

    # Example 3: Load from directory
    print("\n" + "=" * 70)
    print("Example 3: Loading from Directory")
    print("=" * 70)

    # Create sample files
    os.makedirs("sample_docs", exist_ok=True)
    with open("sample_docs/doc1.txt", "w") as f:
        f.write("This is document 1")
    with open("sample_docs/doc2.txt", "w") as f:
        f.write("This is document 2")

    pipeline = RAGDataPipeline()
    pipeline.load_from_source("directory", "sample_docs", pattern="*.txt")

    docs = pipeline.get_documents()
    print(f"Loaded {len(docs)} files from directory")

    # Cleanup
    import shutil

    shutil.rmtree("sample_docs")

    # Example 4: Load from web
    print("\n" + "=" * 70)
    print("Example 4: Loading from Web URL (requires internet)")
    print("=" * 70)
    print("Note: In production, replace URL with your actual content")
    print("Example: pipeline.load_from_source('web', 'https://example.com')")


if __name__ == "__main__":
    # Only run demo if API key is set
    if os.getenv("OPENAI_API_KEY"):
        demo_usage()
    else:
        print("Skipping demo - OPENAI_API_KEY not set")
        print("\nAvailable methods:")
        print("- from_json_file(path)")
        print("- from_text_file(path, chunk_size=500)")
        print("- from_csv_file(path, content_column='content')")
        print("- from_web_url(url)")
        print("- from_markdown_file(path)")
        print("- from_pdf_file(path)")
        print("- from_directory(path, pattern='*.txt')")
