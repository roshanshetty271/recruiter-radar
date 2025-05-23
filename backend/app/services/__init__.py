"""
Services Package

This package contains service layer implementations for various business logic
components of the RecruiterRadar MVP application.

Services:
- LLMService: Handles Large Language Model operations (embeddings, text generation)
"""

from .llm_service import LLMService

__all__ = ["LLMService"]
