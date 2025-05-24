"""
API Configuration Settings

Manages external API configurations including:
- OpenAI API credentials
- CORS settings for FastAPI
- External service endpoints
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator


class APISettings(BaseSettings):
    """Configuration for external APIs and CORS settings."""

    # OpenAI API Configuration
    api_openai_api_key: str

    # CORS Configuration for FastAPI
    api_backend_cors_origins: List[str] = [
        "http://localhost:3000",  # React dev server default
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://localhost:3001",  # Alternative React port
    ]

    @validator("api_openai_api_key")
    def validate_openai_api_key(cls, v: str) -> str:
        """Validate OpenAI API key format."""
        if not v:
            raise ValueError("OpenAI API key is required")
        if not v.startswith("sk-"):
            raise ValueError('OpenAI API key must start with "sk-"')
        if len(v) < 20:  # Minimum reasonable length
            raise ValueError("OpenAI API key appears to be too short")
        return v

    @validator("api_backend_cors_origins")
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Validate CORS origins format."""
        for origin in v:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(
                    f"CORS origin must start with http:// or https://: {origin}"
                )
        return v

    # Convenience properties for cleaner access
    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key."""
        return self.api_openai_api_key

    @property
    def backend_cors_origins(self) -> List[str]:
        """Get CORS origins."""
        return self.api_backend_cors_origins
