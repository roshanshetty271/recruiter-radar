"""
AI Model Configuration Settings

Manages AI model configurations including:
- OpenAI model names for embeddings and chat completion
- Model parameters and settings
- AI service configurations
"""

from pydantic_settings import BaseSettings
from pydantic import validator, Field


class ModelSettings(BaseSettings):
    """Configuration for AI models and related parameters."""

    # OpenAI Model Configuration
    model_embedding_model_name: str = Field(
        "text-embedding-3-small", description="OpenAI model name for text embeddings."
    )
    model_chat_model_name: str = Field(
        "gpt-4o-mini", description="OpenAI model name for chat completions."
    )

    # Model Parameters
    model_embedding_dimensions: int = Field(
        1536, description="Default dimensions for the embedding model."
    )
    model_chat_temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Default temperature for chat completions."
    )
    model_chat_max_tokens: int = Field(
        400, gt=0, description="Default max tokens for chat completion response."
    )
    resume_snippet_max_chars_for_prompt: int = Field(
        2500,
        gt=0,
        description="Max characters of raw_resume_text to use in outreach prompt.",
    )

    # Search Configuration
    model_max_search_results: int = Field(
        5,
        gt=0,
        le=20,
        description="Default number of candidates to return in search results.",
    )
    model_similarity_threshold: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for search results (0.0 = no filtering).",
    )

    @validator("model_embedding_model_name")
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name."""
        valid_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]
        if v not in valid_models:
            raise ValueError(
                f"Embedding model must be one of: " f'{", ".join(valid_models)}'
            )
        return v

    @validator("model_chat_model_name")
    def validate_chat_model(cls, v: str) -> str:
        """Validate chat model name."""
        valid_models = ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]
        if v not in valid_models:
            raise ValueError(f'Chat model must be one of: {", ".join(valid_models)}')
        return v

    @validator("model_chat_temperature")
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is between 0 and 2."""
        if not (0.0 <= v <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @validator("model_max_search_results")
    def validate_max_results(cls, v: int) -> int:
        """Validate search results count."""
        if not (1 <= v <= 20):
            raise ValueError("Max search results must be between 1 and 20")
        return v

    # Convenience properties for cleaner access
    @property
    def embedding_model_name(self) -> str:
        return self.model_embedding_model_name

    @property
    def chat_model_name(self) -> str:
        return self.model_chat_model_name

    @property
    def embedding_dimensions(self) -> int:
        return self.model_embedding_dimensions

    @property
    def chat_temperature(self) -> float:
        return self.model_chat_temperature

    @property
    def chat_max_tokens(self) -> int:
        return self.model_chat_max_tokens

    @property
    def max_search_results(self) -> int:
        return self.model_max_search_results

    @property
    def similarity_threshold(self) -> float:
        return self.model_similarity_threshold

    @property
    def resume_snippet_chars(self) -> int:
        return self.resume_snippet_max_chars_for_prompt
