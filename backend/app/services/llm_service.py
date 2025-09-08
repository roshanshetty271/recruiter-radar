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

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Custom exception for LLM Service errors."""

    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception


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

    def __init__(self, api_key: str = None, embedding_model_name: str = None):
        """
        Initialize the LLMService with OpenAI client configuration.

        Args:
            api_key (str, optional): OpenAI API key. If None, uses settings.
            embedding_model_name (str, optional): Embedding model name. If None, uses settings.

        Raises:
            ValueError: If API key is not provided or found in settings.
        """
        # Use provided values or fall back to settings, but check for empty strings
        if api_key is not None:
            if not api_key.strip():
                raise ValueError("OpenAI API key cannot be empty.")
            self.api_key = api_key
        else:
            self.api_key = settings.openai_api_key

        if embedding_model_name is not None:
            if not embedding_model_name.strip():
                raise ValueError("Embedding model name cannot be empty.")
            self.embedding_model = embedding_model_name
        else:
            self.embedding_model = settings.embedding_model_name

        if not self.api_key:
            logger.error("OpenAI API key is not configured.")
            raise ValueError("OpenAI API key is required for LLMService.")

        if not self.embedding_model:
            logger.error("Embedding model name is not configured.")
            raise ValueError("Embedding model name is required for LLMService.")

        # Initialize the async OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(
            f"LLMService initialized with embedding model: {self.embedding_model}"
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI authentication failed. Please check API key configuration.",
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
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="OpenAI API rate limit exceeded after multiple retries.",
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
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="OpenAI API connection/timeout issue after multiple retries.",
                )

        except BadRequestError as e:
            logger.error(
                f"OpenAI Bad Request Error (possibly input too long): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request to OpenAI API: {e.message if hasattr(e, 'message') else str(e)}",
            )

        except APIError as e:
            logger.error(f"Generic OpenAI API Error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API service temporarily unavailable.",
            )

        except Exception as e:
            logger.error(f"Unexpected error in get_embedding: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while generating embeddings.",
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
        llm_service = LLMService()

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

    asyncio.run(_test_llm_service())
