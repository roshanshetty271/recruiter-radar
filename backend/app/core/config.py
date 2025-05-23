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

from .api_config import APISettings
from .model_config import ModelSettings
from .app_config import AppSettings


class Settings(APISettings, ModelSettings, AppSettings):
    """
    Combined settings class that inherits from all configuration modules.

    This provides a single interface to access all application settings
    while maintaining modular organization of configuration categories.
    """

    class Config:
        env_file = ".env"
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
