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
from typing import List, Optional, Dict, Any
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
from backend.app.models.candidate import CandidateProfile

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Custom exception for LLM Service errors."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


class EmbeddingGenerationError(LLMServiceError):
    """Raised when embedding generation fails after retries or due to a non-transient API error."""

    pass


class OpenAIConfigError(LLMServiceError):
    """Raised for OpenAI configuration issues (e.g., missing API key, invalid model name)."""

    pass


class TextGenerationError(LLMServiceError):
    """Raised when text generation fails after retries or due to a non-transient API error."""

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
        self.chat_model_name = self.settings.chat_model_name

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

        if not self.chat_model_name:
            logger.error("Chat model name is not configured in settings.")
            raise OpenAIConfigError(
                "Chat model name is required for text generation features."
            )

        self.default_chat_temperature = self.settings.model_chat_temperature
        self.default_chat_max_tokens = self.settings.model_chat_max_tokens
        self.resume_snippet_max_chars_for_prompt = (
            self.settings.resume_snippet_max_chars_for_prompt
        )

        # Initialize the async OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(
            f"LLMService initialized with embedding model: {self.embedding_model}, chat model: {self.chat_model_name}, "
            f"Default Temp: {self.default_chat_temperature}, Default Chat Max Tokens: {self.default_chat_max_tokens}, "
            f"Resume Snippet Chars: {self.resume_snippet_max_chars_for_prompt}"
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
            EmbeddingGenerationError: For API errors after retries or non-transient issues.
            OpenAIConfigError: For configuration-related issues.

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
                f"Invalid request to OpenAI API for embeddings: {e.message if hasattr(e, 'message') else str(e)}",
                original_exception=e,
            )

        except APIError as e:  # Catch other OpenAI API errors
            logger.error(f"Generic OpenAI API Error for embeddings: {e}", exc_info=True)
            raise EmbeddingGenerationError(
                f"OpenAI API service error for embeddings: {e.message if hasattr(e, 'message') else str(e)}",
                original_exception=e,
            )

        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error in get_embedding: {e}", exc_info=True)
            # This is an unexpected internal error in this service.
            raise LLMServiceError(
                f"An unexpected error occurred while generating embeddings: {str(e)}",
                original_exception=e,
            )

    async def generate_outreach_draft(
        self,
        candidate: CandidateProfile,
        job_role_title: str,
        job_role_description: Optional[str],
        tone: str,
        company_context: Optional[str],
        additional_instructions: Optional[str],
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> str:
        """
        Generates a personalized outreach message draft for a candidate using OpenAI's Chat Completions API.

        Args:
            candidate: The CandidateProfile object.
            job_role_title: The target job role title.
            job_role_description: Optional detailed description of the job role.
            tone: Desired tone for the message.
            company_context: Optional context about the company or team.
            additional_instructions: Optional specific instructions for the LLM.
            attempt: Current attempt number for retries (internal use).
            max_attempts: Maximum number of retry attempts for transient errors.

        Returns:
            The generated outreach message string.

        Raises:
            ValueError: If essential inputs like candidate or job_role_title are missing.
            TextGenerationError: If text generation fails after retries or for non-retryable API errors.
            OpenAIConfigError: If chat model or API key configuration is missing/invalid.
        """
        if not candidate or not job_role_title or not job_role_title.strip():
            logger.warning(
                "generate_outreach_draft called with missing candidate or job_role_title."
            )
            raise ValueError("Candidate profile and job role title are required.")

        resume_snippet = candidate.raw_resume_text[
            : self.resume_snippet_max_chars_for_prompt
        ]
        if len(candidate.raw_resume_text) > self.resume_snippet_max_chars_for_prompt:
            resume_snippet += "..."
            logger.debug(
                f"Truncated raw_resume_text for candidate {candidate.id} to ~{self.resume_snippet_max_chars_for_prompt} chars for prompt."
            )

        system_message_content = (
            "You are an expert recruitment assistant for 'RecruiterRadar'. Your task is to draft a concise, "
            "engaging, and personalized outreach message to a potential candidate for a specific job role. "
            "Highlight the candidate's relevant skills and experience found in their resume text, "
            "and clearly connect it to the target job role. Maintain the specified tone. The output should be "
            "only the body of the outreach message, ready to be sent, without any preamble or subject line."
        )

        prompt_parts = [
            f"Please draft an outreach message based on the following information:",
            f"## Candidate Information:",
            f"- Name: {candidate.name}",
            f"- Key Skills (from profile): {', '.join(candidate.skills) if candidate.skills else 'Not explicitly listed'}",
            f"- Years of Experience: {candidate.experience_years if candidate.experience_years is not None else 'Not specified'}",  # Handle potential None
            f"- Relevant excerpt from candidate's resume:\n---\n{resume_snippet}\n---",
            f"\n## Job Information:",
            f"- Target Job Role: {job_role_title}",
        ]
        if job_role_description:
            prompt_parts.append(f"- Key aspects of the role: {job_role_description}")
        if company_context:
            prompt_parts.append(f"- Context about our company/team: {company_context}")

        prompt_parts.append(f"Desired tone for the outreach message: {tone}.")

        if additional_instructions:
            prompt_parts.append(
                f"Additional specific instructions for this draft: {additional_instructions}"
            )

        prompt_parts.append(
            f"\n## Your Task:\n"
            f"Draft a personalized outreach message directly to {candidate.name} for the {job_role_title} position. "
            "1. Address the candidate by their first name. "
            "2. Briefly introduce yourself (as a recruiter from RecruiterRadar or the hiring company if context provided). "
            "3. Clearly state the job role. "
            "4. Specifically mention 1-2 key qualifications or experiences from their resume excerpt that make them a strong potential fit for this role, connecting these to the job. "
            "5. Briefly highlight what might be exciting or beneficial for them in this role or at the company. "
            "6. Maintain the specified tone throughout the message. "
            "7. Keep the entire message concise and engaging (e.g., 3-4 short paragraphs, ideally under 200 words). "
            "8. End with a clear call to action (e.g., inviting them for a brief, exploratory chat to share more details). "
            "9. Output only the body of the message. Do not include a subject line or any text before or after the message itself."
        )
        user_prompt_content = "\n\n".join(prompt_parts)

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": user_prompt_content},
        ]

        logger.info(
            f"Requesting chat completion (model: {self.chat_model_name}, "
            f"temp: {self.default_chat_temperature}, max_tokens: {self.default_chat_max_tokens}, "
            f"attempt: {attempt}/{max_attempts}) for candidate: {candidate.id}, role: {job_role_title}"
        )
        logger.debug(f"System message for {candidate.id}:\n{system_message_content}")
        logger.debug(
            f"User prompt for {candidate.id} (first 200 chars):\n{user_prompt_content[:200]}..."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=messages,
                temperature=self.default_chat_temperature,
                max_tokens=self.default_chat_max_tokens,
            )

            generated_text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            if finish_reason == "content_filter":
                logger.warning(
                    f"Text generation for candidate {candidate.id} stopped by content filter."
                )
                raise TextGenerationError(
                    "Generated content was flagged by OpenAI's content filter.",
                    original_exception=None,
                )

            if finish_reason == "length":
                logger.warning(
                    f"Text generation for candidate {candidate.id} truncated due to max_tokens ({self.default_chat_max_tokens}). Consider increasing max_tokens or refining prompt for conciseness if output is incomplete."
                )

            if not generated_text or not generated_text.strip():
                logger.warning(
                    f"OpenAI returned empty or whitespace-only content for candidate {candidate.id}."
                )
                raise TextGenerationError(
                    "LLM returned empty or whitespace-only content for outreach draft.",
                    original_exception=None,
                )

            logger.info(
                f"Outreach draft successfully generated for candidate {candidate.id}."
            )
            return generated_text.strip()

        except AuthenticationError as e:
            logger.error(
                f"OpenAI Authentication Error in generate_outreach_draft: {e}",
                exc_info=True,
            )
            raise OpenAIConfigError(
                "OpenAI authentication failed. Check API key.", original_exception=e
            )
        except RateLimitError as e:
            logger.warning(
                f"OpenAI Rate Limit Error in generate_outreach_draft (attempt {attempt}/{max_attempts}): {e}"
            )
            if attempt < max_attempts:
                backoff_delay = 2**attempt
                logger.info(
                    f"Retrying generate_outreach_draft after {backoff_delay} seconds..."
                )
                await asyncio.sleep(backoff_delay)
                return await self.generate_outreach_draft(
                    candidate,
                    job_role_title,
                    job_role_description,
                    tone,
                    company_context,
                    additional_instructions,
                    attempt + 1,
                    max_attempts,
                )
            else:
                logger.error(
                    "OpenAI API rate limit exceeded after multiple retries in generate_outreach_draft.",
                    exc_info=True,
                )
                raise TextGenerationError(
                    "OpenAI API rate limit exceeded.", original_exception=e
                )
        except (APITimeoutError, APIConnectionError) as e:
            logger.warning(
                f"OpenAI API Connection/Timeout Error in generate_outreach_draft (attempt {attempt}/{max_attempts}): {e}"
            )
            if attempt < max_attempts:
                backoff_delay = 2**attempt
                logger.info(
                    f"Retrying generate_outreach_draft after {backoff_delay} seconds..."
                )
                await asyncio.sleep(backoff_delay)
                return await self.generate_outreach_draft(
                    candidate,
                    job_role_title,
                    job_role_description,
                    tone,
                    company_context,
                    additional_instructions,
                    attempt + 1,
                    max_attempts,
                )
            else:
                logger.error(
                    "OpenAI API connection/timeout issue after multiple retries in generate_outreach_draft.",
                    exc_info=True,
                )
                raise TextGenerationError(
                    "OpenAI API connection/timeout issue.", original_exception=e
                )
        except BadRequestError as e:
            err_body = e.body
            err_detail = str(e)  # Default to full error string
            error_code = None
            if (
                isinstance(err_body, dict)
                and "error" in err_body
                and isinstance(err_body["error"], dict)
            ):  # Safely access nested error code
                error_code = err_body["error"].get("code")

            if error_code == "context_length_exceeded":
                err_detail = "Prompt combined with max_tokens exceeds the model's context window. Try reducing resume snippet length or max_tokens."
                logger.error(
                    f"OpenAI Context Length Exceeded in generate_outreach_draft: {err_detail}",
                    exc_info=True,
                )
            else:  # Log the full error if it's not context length
                logger.error(
                    f"OpenAI Bad Request Error in generate_outreach_draft (code: {error_code}): {str(e)}",
                    exc_info=True,
                )
            raise TextGenerationError(
                f"Invalid request to OpenAI API for chat completion: {err_detail}",
                original_exception=e,
            )
        except APIError as e:
            logger.error(
                f"Generic OpenAI API Error in generate_outreach_draft: {e}",
                exc_info=True,
            )
            raise TextGenerationError(
                f"OpenAI API service error for chat completion: {str(e)}",
                original_exception=e,
            )
        except TextGenerationError:
            # Allow service-level errors to propagate without re-wrapping
            raise
        except LLMServiceError:
            # Allow service-level errors to propagate without re-wrapping
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in generate_outreach_draft for candidate {candidate.id}: {e}",
                exc_info=True,
            )
            raise LLMServiceError(
                f"An unexpected error occurred during text generation: {str(e)}",
                original_exception=e,
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
        print("--- Testing Embedding Generation ---")
        test_text = "This is a test sentence for embedding generation."
        embedding = await llm_service.get_embedding(test_text)

        print(f"✅ Embedding generated successfully!")
        print(f"   Text: '{test_text}'")
        print(f"   Embedding dimension: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")

        # Test outreach draft generation
        print("\n--- Testing Outreach Draft Generation ---")
        # Create a dummy CandidateProfile instance for testing
        # Ensure all required fields for CandidateProfile are provided.
        # Check your app.models.candidate.CandidateProfile for exact fields.
        # Assuming 'email' is also a required field for CandidateProfile as an example.
        dummy_candidate_data = {
            "id": "test001",
            "name": "Test Candidate",
            "email": "test.candidate@example.com",  # Assuming email is required
            "summary_text": "A skilled professional with diverse experience.",  # Assuming summary_text is required
            "raw_resume_text": "Detailed resume: Skilled in Python and AI. Also worked with Java and Cloud technologies. Looking for a challenging role.",
            "skills": ["Python", "AI", "Java", "Cloud"],
            "experience_years": 5,
            "visa_status": "Eligible",  # Example value
            "location": "Testville, TS",  # Example value
            # Add any other non-optional fields that your CandidateProfile model might have.
            # For example, if 'education_level' is required:
            # "education_level": "Master's Degree"
        }
        # Validate and create the model instance
        # If your CandidateProfile has optional fields with defaults, they'll be applied.
        # If fields are optional and not provided, they'll be None (or their default_factory if set).
        test_candidate = CandidateProfile.model_validate(dummy_candidate_data)

        draft = await llm_service.generate_outreach_draft(
            candidate=test_candidate,
            job_role_title="Senior AI Developer",
            job_role_description="Develop and deploy cutting-edge AI solutions for enterprise clients. Lead a team of junior developers.",
            tone="professional yet enthusiastic",
            company_context="A forward-thinking technology company leading innovation in the AI space. We value collaboration and continuous learning.",
            additional_instructions="Highlight their cloud experience as it's a plus for this role. Keep the message under 180 words.",
        )
        print(f"✅ Outreach draft generated successfully!")
        print(f"Draft:\n{draft}")

    except OpenAIConfigError as e_cfg:
        print(f"❌ Test failed due to LLMService configuration issue: {e_cfg}")
    except LLMServiceError as e_llm:
        print(f"❌ Test failed due to an LLMService operational error: {e_llm}")
    except Exception as e:
        print(f"❌ Test failed with an unexpected error: {e}")
        import traceback

        traceback.print_exc()


# Allow running this module directly for testing
if __name__ == "__main__":
    import asyncio

    # Ensure settings are loaded if running directly for testing
    from backend.app.core.config import settings as global_settings_for_direct_run

    asyncio.run(_test_llm_service())
