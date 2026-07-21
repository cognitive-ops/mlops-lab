# LangChain RAG Environment Setup

This directory contains a complete LangChain RAG (Retrieval-Augmented Generation) implementation with multiple examples.

## Environment Setup

### Option 1: Using Conda (Recommended)

```bash
# Create the conda environment
conda env create -f environment.yml

# Activate the environment
conda activate langchain-rag
```

### Option 2: Using pip with virtual environment

```bash
# Create virtual environment
python -m venv langchain-rag-env

# Activate virtual environment
# On Windows (WSL/Linux):
source langchain-rag-env/bin/activate
# On Windows (PowerShell):
# langchain-rag-env\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Set up your API keys before running the code:

```bash
# Required for OpenAI (both LLM and embeddings)
export OPENAI_API_KEY="your-openai-api-key"

# Optional: LangSmith for monitoring
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-langsmith-api-key"
```

## Running the Code

```bash
# Make sure you're in the rag directory
cd backbone-mlops/demo/rag

# Run the examples
python rag.py
```

## What's Included

The `rag.py` file contains several examples:

1. **Simple Chat Example** - Basic LLM interaction
2. **Document Processing Example** - Text splitting and document handling
3. **Chain Example** - Sequential LLM calls
4. **RAG Example** - Full retrieval-augmented generation pipeline

## Dependencies Explained

- **langchain**: Core LangChain framework
- **langchain-openai**: OpenAI integration for LLM and embeddings
- **langchain-community**: Community integrations (WebBaseLoader)
- **langgraph**: Graph-based workflow orchestration
- **openai**: OpenAI GPT model integration
- **beautifulsoup4**: HTML parsing for web content
- **tiktoken**: OpenAI tokenization

## Troubleshooting

1. **Import errors**: Make sure you've activated the correct environment
2. **API key errors**: Verify your API keys are set correctly
3. **Network errors**: Ensure internet connection for web scraping and API calls
4. **Model access**: Verify you have access to the specified OpenAI models (GPT-3.5-turbo, text-embedding-ada-002)