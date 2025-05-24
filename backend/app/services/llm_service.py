"""
Large Language Model Service

This service handles interactions with OpenAI's APIs, specifically:
- Text embeddings generation using the Embeddings API
- Error handling and retry logic for robustness
- Logging for debugging and monitoring

The service uses AsyncOpenAI for non-blocking API calls, making it suitable
for use within FastAPI's async framework.
"""

import logging
from typing import List
import asyncio

from openai import (
    AsyncOpenAI,
    APIError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
)
from fastapi import HTTPException, status

from backend.app.core.config import settings, Settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Custom exception for LLM Service errors."""

    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception


class EmbeddingGenerationError(LLMServiceError):
    """Raised when embedding generation fails after retries or due to a non-transient API error."""

    pass


class OpenAIConfigError(LLMServiceError):
    """Raised for OpenAI configuration issues (e.g., missing API key, invalid model name)."""

    pass


class LLMService:
    """
    Service class for interacting with Large Language Models.

    Currently handles:
    - Text embeddings generation via OpenAI's Embeddings API
    - Error handling with retry logic for transient failures
    - Proper logging for monitoring and debugging

    Future expansions:
    - Text generation via Chat Completions API (for outreach drafts)
    - Additional model providers if needed
    """

    def __init__(self, settings_obj: Settings):
        """
        Initialize the LLMService with OpenAI client configuration using settings object.

        Args:
            settings_obj: The application's global settings object.

        Raises:
            OpenAIConfigError: If essential OpenAI configurations are missing.
        """
        self.settings = settings_obj
        self.api_key = self.settings.openai_api_key
        self.embedding_model = self.settings.embedding_model_name
        self.chat_model = self.settings.chat_model_name

        if not self.api_key:
            logger.error("OpenAI API key is not configured in settings.")
            raise OpenAIConfigError(
                "OpenAI API key is required for LLMService. Please check configuration."
            )

        if not self.embedding_model:
            logger.error("Embedding model name is not configured in settings.")
            raise OpenAIConfigError(
                "Embedding model name is required for LLMService. Please check configuration."
            )

        if not self.chat_model:
            logger.warning(
                "Chat model name is not configured in settings. Text generation features might fail."
            )

        # Initialize the async OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(
            f"LLMService initialized with embedding model: {self.embedding_model}, chat model: {self.chat_model}"
        )

    async def get_embedding(
        self, text: str, attempt: int = 1, max_attempts: int = 3
    ) -> List[float]:
        """
        Generate a vector embedding for the given text.

        Uses OpenAI's Embeddings API to convert text into a high-dimensional
        vector representation suitable for similarity search and RAG applications.

        Args:
            text (str): The text to embed. Cannot be empty or whitespace-only.
            attempt (int): Current attempt number (for internal retry logic).
            max_attempts (int): Maximum number of retry attempts for transient errors.

        Returns:
            List[float]: The generated vector embedding.

        Raises:
            ValueError: If input text is empty, None, or whitespace-only.
            HTTPException: For various API errors (auth, rate limits, timeouts, etc.).

        Example:
            >>> llm_service = LLMService()
            >>> embedding = await llm_service.get_embedding("Hello, world!")
            >>> len(embedding)  # Should be 1536 for text-embedding-3-small
            1536
        """
        # Input validation
        if not text or not text.strip():
            logger.warning("get_embedding called with empty or whitespace-only text.")
            # For an invalid argument from the caller, ValueError is appropriate.
            raise ValueError("Input text for embedding cannot be empty.")

        # Log the request (with truncated text for privacy/readability)
        text_preview = text[:50] + "..." if len(text) > 50 else text
        logger.info(
            f"Requesting embedding (model: {self.embedding_model}, "
            f"attempt: {attempt}/{max_attempts}, text: '{text_preview}')"
        )

        try:
            # Make the API call to OpenAI's Embeddings endpoint
            response = await self.client.embeddings.create(
                input=text, model=self.embedding_model
            )

            # Extract the embedding vector from the response
            embedding = response.data[0].embedding

            logger.info(
                f"Embedding successfully generated (text: '{text_preview}', "
                f"dimension: {len(embedding)})"
            )

            return embedding

        except AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error: {e}", exc_info=True)
            # This is a configuration or setup issue.
            raise OpenAIConfigError(
                "OpenAI authentication failed. Please check API key configuration.",
                original_exception=e,
            )

        except RateLimitError as e:
            logger.warning(
                f"OpenAI Rate Limit Error (attempt {attempt}/{max_attempts}): {e}"
            )

            if attempt < max_attempts:
                # Progressive backoff: wait longer with each retry
                backoff_delay = 2**attempt  # 2, 4, 8 seconds
                logger.info(f"Retrying after {backoff_delay} seconds...")
                await asyncio.sleep(backoff_delay)
                return await self.get_embedding(text, attempt + 1, max_attempts)
            else:
                logger.error(
                    "OpenAI API rate limit exceeded after multiple retries.",
                    exc_info=True,
                )
                raise EmbeddingGenerationError(
                    "OpenAI API rate limit exceeded after multiple retries.",
                    original_exception=e,
                )

        except (APITimeoutError, APIConnectionError) as e:
            logger.warning(
                f"OpenAI API Connection/Timeout Error (attempt {attempt}/{max_attempts}): {e}"
            )

            if attempt < max_attempts:
                # Progressive backoff for connection issues
                backoff_delay = 2**attempt
                logger.info(f"Retrying after {backoff_delay} seconds...")
                await asyncio.sleep(backoff_delay)
                return await self.get_embedding(text, attempt + 1, max_attempts)
            else:
                logger.error(
                    "OpenAI API connection/timeout issue after multiple retries.",
                    exc_info=True,
                )
                raise EmbeddingGenerationError(
                    "OpenAI API connection/timeout issue after multiple retries.",
                    original_exception=e,
                )

        except BadRequestError as e:
            logger.error(
                f"OpenAI Bad Request Error (possibly input too long or invalid model): {e}",
                exc_info=True,
            )
            # This could be due to bad input from the user of this service or an issue with the model.
            # For ingest_data.py, this is a critical failure for that piece of text.
            raise EmbeddingGenerationError(
                f"Invalid request to OpenAI API: {e.message if hasattr(e, 'message') else str(e)}",
                original_exception=e,
            )

        except APIError as e:  # Catch other OpenAI API errors
            logger.error(f"Generic OpenAI API Error: {e}", exc_info=True)
            raise EmbeddingGenerationError(
                f"OpenAI API service error: {e.message if hasattr(e, 'message') else str(e)}",
                original_exception=e,
            )

        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error in get_embedding: {e}", exc_info=True)
            # This is an unexpected internal error in this service.
            raise LLMServiceError(
                f"An unexpected error occurred while generating embeddings: {str(e)}",
                original_exception=e,
            )

    # Future method placeholder for text generation
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using OpenAI's Chat Completions API.

        This method will be implemented in a future feature (BE-4) for
        generating personalized outreach messages.

        Args:
            prompt (str): The text prompt for generation.
            **kwargs: Additional parameters for the generation API.

        Returns:
            str: The generated text.

        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        raise NotImplementedError(
            "Text generation will be implemented in Feature BE-4: "
            "LLM Service - Text Generation Functionality"
        )


# Example usage and testing function (can be removed in production)
async def _test_llm_service():
    """
    Simple test function to verify LLMService functionality.
    This function can be used for manual testing during development.
    """
    try:
        # Ensure global settings are imported and used for instantiation
        from backend.app.core.config import settings as global_settings

        llm_service = LLMService(settings_obj=global_settings)

        # Test embedding generation
        test_text = "This is a test sentence for embedding generation."
        embedding = await llm_service.get_embedding(test_text)

        print(f"✅ Embedding generated successfully!")
        print(f"   Text: '{test_text}'")
        print(f"   Embedding dimension: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")

    except Exception as e:
        print(f"❌ Test failed: {e}")


# Allow running this module directly for testing
if __name__ == "__main__":
    import asyncio

    # Ensure settings are loaded if running directly for testing
    from backend.app.core.config import settings as global_settings_for_direct_run

    asyncio.run(_test_llm_service())
