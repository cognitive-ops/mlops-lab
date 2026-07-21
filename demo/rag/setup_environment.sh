#!/bin/bash

# LangChain RAG Environment Setup Script
# This script automates the conda environment creation and setup

set -e  # Exit on any error

echo "🚀 Setting up LangChain RAG Environment..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed. Please install Anaconda or Miniconda first."
    exit 1
fi

# Create conda environment
echo "📦 Creating conda environment 'langchain-rag'..."
conda env create -f environment.yml

echo "✅ Environment created successfully!"

# Provide activation instructions
echo ""
echo "🎯 To activate the environment, run:"
echo "   conda activate langchain-rag"
echo ""
echo "🔑 Don't forget to set your API key:"
echo "   export OPENAI_API_KEY='your-openai-api-key'"
echo ""
echo "🏃 To run the examples:"
echo "   python rag.py"
echo ""
echo "📚 For more information, see README.md"