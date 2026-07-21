"""
Configuration settings for the Agentic AI.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the Agentic AI."""

    # Google AI API settings
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Model settings
    DEFAULT_MODEL = "models/gemini-2.5-flash"
    ALTERNATIVE_MODELS = [
        # Latest flash model (fast, cost-effective)
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",     # Latest pro model (more capable)
        "models/gemini-2.0-flash",   # Stable flash model
    ]

    # Agent settings
    MAX_ITERATIONS = 10
    VERBOSE_MODE = True

    # Safety settings (optional)
    SAFETY_SETTINGS = None  # Can be configured for content filtering

    # Temperature for creativity (0.0 = deterministic, 1.0 = creative)
    TEMPERATURE = 0.7

    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not found. "
                "Please set it in your .env file or environment variables."
            )
        return True


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")
