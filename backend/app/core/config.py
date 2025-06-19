"""
Main Configuration Module

Aggregates all configuration settings from different modules and provides
a unified settings instance for the application.

Usage:
    from app.core.config import settings

    # Access API settings
    openai_key = settings.openai_api_key

    # Access model settings
    model_name = settings.embedding_model_name

    # Access app settings
    data_path = settings.candidate_data_path
"""

from pathlib import Path
from pydantic import Field

from .api_config import APISettings
from .model_config import ModelSettings
from .app_config import AppSettings


class Settings(APISettings, ModelSettings, AppSettings):
    """
    Combined settings class that inherits from all configuration modules.

    This provides a single interface to access all application settings
    while maintaining modular organization of configuration categories.
    """

    # Upload Feature Settings
    max_uploads_per_session: int = Field(
        default=10, description="Maximum number of PDF uploads per session"
    )
    max_pdf_size_mb: int = Field(
        default=10, description="Maximum PDF file size in megabytes"
    )
    pdf_text_truncation_limit: int = Field(
        default=15000, description="Maximum characters to send to LLM for extraction"
    )
    session_expiry_hours: int = Field(
        default=48, description="Hours before a session expires"
    )

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.max_pdf_size_mb * 1024 * 1024

    # ETL Pipeline Settings
    enable_smart_chunking: bool = Field(
        default=False, description="Enable smart chunking for resume processing"
    )
    chunk_strategy: str = Field(
        default="simple_two_chunk",
        description="Chunking strategy: simple_two_chunk or semantic",
    )
    max_chunks_per_resume: int = Field(
        default=3, description="Maximum number of chunks per resume"
    )
    chunk_size_chars: int = Field(
        default=4000, description="Target size for each chunk in characters"
    )
    embedding_text_limit: int = Field(
        default=6000, description="Maximum characters for safe embedding generation"
    )

    # Chat Feature Settings
    max_chat_messages_per_session: int = Field(
        default=10, description="Maximum chat messages per session"
    )
    chat_temperature: float = Field(
        default=0.3,
        description="Temperature for chat query parsing (lower = more deterministic)",
    )
    chat_response_temperature: float = Field(
        default=0.7,
        description="Temperature for chat response generation (higher = more creative)",
    )
    enable_query_suggestions: bool = Field(
        default=True, description="Enable AI-generated query suggestions"
    )

    resume_chunk_overlap: int = Field(
        default=200, description="Overlap between resume text chunks"
    )

    class Config:
        # Construct path to .env file in the 'backend' directory, relative to this config file
        # config.py is in backend/app/core/, .env is in backend/
        # So, ../../.env from core/ should point to backend/.env
        # Corrected: Path(__file__).resolve().parent.parent.parent / ".env"
        # __file__ is config.py -> parent is core/ -> parent is app/ -> parent is backend/
        env_file_path = Path(__file__).resolve().parent.parent.parent / ".env"
        env_file = str(env_file_path)  # Pydantic expects a string path

        env_file_encoding = "utf-8"
        case_sensitive = False

        # Allow extra fields for flexibility
        extra = "forbid"  # Strict mode - no undefined fields

        # Custom title for OpenAPI docs
        title = "RecruiterRadar MVP Configuration"


# Global settings instance
settings = Settings()


# Convenience exports for backwards compatibility and easier imports
__all__ = ["Settings", "settings"]
