"""
Configuration and utilities for DSPy RAG system
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for DSPy RAG"""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Model settings
    DEFAULT_MODEL = "gpt-3.5-turbo"
    DEFAULT_MAX_TOKENS = 500
    DEFAULT_TEMPERATURE = 0.5

    # Retrieval settings
    DEFAULT_K = 3  # Number of documents to retrieve
    DEFAULT_CHUNK_SIZE = 500  # Document chunk size
    DEFAULT_OVERLAP = 100  # Chunk overlap

    # Vector store settings
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    VECTOR_DIMENSION = 384  # For all-MiniLM-L6-v2

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not set. Please set it in .env or environment variables."
            )
        return True


class Logger:
    """Simple logger for debugging"""

    VERBOSE = os.getenv("VERBOSE", "False").lower() == "true"

    @classmethod
    def log(cls, message: str, level: str = "INFO"):
        if cls.VERBOSE:
            print(f"[{level}] {message}")

    @classmethod
    def error(cls, message: str):
        print(f"[ERROR] {message}")

    @classmethod
    def debug(cls, message: str):
        cls.log(message, "DEBUG")

    @classmethod
    def info(cls, message: str):
        cls.log(message, "INFO")


def setup_environment():
    """Setup environment for RAG system"""
    Config.validate()
    Logger.info("Environment validated")


def get_api_key(provider: str = "openai") -> str:
    """Get API key for specified provider"""
    if provider == "openai":
        return Config.OPENAI_API_KEY
    elif provider == "anthropic":
        return Config.ANTHROPIC_API_KEY
    else:
        raise ValueError(f"Unknown provider: {provider}")


if __name__ == "__main__":
    setup_environment()
    print("Configuration loaded successfully!")
