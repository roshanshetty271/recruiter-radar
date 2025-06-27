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
import random as hochwertiges
import hashlib  # 🚀 TURBO-PATCH: For embedding cache keys

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

from app.core.config import settings, Settings
from app.models.candidate import CandidateProfile

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

        # 🚀 TURBO-PATCH: Simple embedding cache for repeated queries
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_max_size = 1000  # Prevent memory bloat

        logger.info(
            f"LLMService initialized with embedding model: {self.embedding_model}, chat model: {self.chat_model_name}, "
            f"Default Temp: {self.default_chat_temperature}, Default Chat Max Tokens: {self.default_chat_max_tokens}, "
            f"Resume Snippet Chars: {self.resume_snippet_max_chars_for_prompt}, "
            f"Embedding Cache: {self._cache_max_size} entries max"
        )

    async def get_embedding(
        self, text: str, attempt: int = 1, max_attempts: int = 3
    ) -> List[float]:
        """
        🚀 TURBO-PATCH: Generate a vector embedding with caching for repeated queries.

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

        # 🚀 CACHE CHECK: Generate cache key and check if we already have this embedding
        cache_key = hashlib.md5(
            f"{self.embedding_model}:{text.strip()}".encode()
        ).hexdigest()

        if cache_key in self._embedding_cache:
            logger.info(f"🎯 CACHE HIT: Embedding found for text '{text[:30]}...'")
            return self._embedding_cache[cache_key]

        # Log the request (with truncated text for privacy/readability)
        text_preview = text[:50] + "..." if len(text) > 50 else text
        logger.info(
            f"🌐 API CALL: Requesting embedding (model: {self.embedding_model}, "
            f"attempt: {attempt}/{max_attempts}, text: '{text_preview}')"
        )

        try:
            # Make the API call to OpenAI's Embeddings endpoint
            response = await self.client.embeddings.create(
                input=text, model=self.embedding_model
            )

            # Extract the embedding vector from the response
            embedding = response.data[0].embedding

            # 🚀 CACHE STORAGE: Store in cache for future queries (with size limit)
            if len(self._embedding_cache) >= self._cache_max_size:
                # Remove oldest entry (simple FIFO eviction)
                oldest_key = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest_key]
                logger.debug(f"📦 CACHE EVICTION: Removed oldest entry to make space")

            self._embedding_cache[cache_key] = embedding
            logger.info(
                f"💾 CACHE STORED: Embedding cached for text '{text_preview}' "
                f"(dimension: {len(embedding)}, cache size: {len(self._embedding_cache)})"
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
            # Re-raise as a service-specific error to be handled by the caller.
            raise EmbeddingGenerationError(
                f"An unexpected error occurred during embedding generation: {str(e)}",
                original_exception=e,
            )

    async def extract_structured_resume_data(
        self, text: str, prompt_version: str = "V2"
    ) -> Optional["ExtractedResumeData"]:  # Forward reference ExtractedResumeData
        """
        Extract structured data from resume text using LLM.

        Uses validated prompts from Phase 0 testing to extract
        candidate information in a structured format.

        Args:
            text: Resume text (already truncated if needed)
            prompt_version: Which prompt version to use (V1, V2, or V3)

        Returns:
            ExtractedResumeData if successful, None if extraction fails
        """
        # Import here to avoid circular dependency at module level
        # and allow forward reference in type hint
        from app.core.prompts import (
            EXTRACTION_PROMPT_V1,
            EXTRACTION_PROMPT_V2,
            EXTRACTION_PROMPT_V3,
            EXTRACTION_PROMPT_ACTIVE,
        )
        from app.models.upload_models import ExtractedResumeData

        try:
            # Get the appropriate prompt based on version
            prompt_map = {
                "V1": EXTRACTION_PROMPT_V1,
                "V2": EXTRACTION_PROMPT_V2,
                "V3": EXTRACTION_PROMPT_V3,
            }

            # Use specified version or fall back to active version
            # Ensure EXTRACTION_PROMPT_ACTIVE is one of the keys in prompt_map or handle separately
            chosen_prompt_key = (
                prompt_version if prompt_version in prompt_map else "V2"
            )  # Default to V2 if ACTIVE is not in map
            prompt_template = prompt_map.get(
                chosen_prompt_key, EXTRACTION_PROMPT_V2
            )  # Fallback to V2

            if prompt_version not in prompt_map and prompt_version != "ACTIVE":
                logger.warning(
                    f"Prompt version '{prompt_version}' not found, defaulting to '{chosen_prompt_key}'. Available: {list(prompt_map.keys())}"
                )
            elif prompt_version == "ACTIVE":
                prompt_template = EXTRACTION_PROMPT_ACTIVE

            # Format prompt with resume text
            prompt = prompt_template.replace("{text}", text)

            logger.info(
                f"Extracting resume data using prompt version: {chosen_prompt_key}"
            )

            # Call OpenAI with structured output
            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a resume parsing assistant. Extract information and return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1024,  # Increased max_tokens for potentially larger JSON
                response_format={"type": "json_object"},  # Force JSON response
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                logger.error("Empty response from LLM for resume extraction")
                return None

            # Parse JSON
            try:
                import json  # Keep import local if only used here

                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.debug(f"Raw response: {content[:500]}...")  # Log first 500 chars
                return None

            # Create and validate Pydantic model
            try:
                extracted = ExtractedResumeData(**data)
                logger.info(
                    f"Successfully extracted data for: {extracted.name if extracted.name else 'Unknown'}"
                )
                return extracted
            except (
                Exception
            ) as e:  # Catch Pydantic ValidationError specifically if possible
                logger.error(
                    f"Failed to validate extracted data with Pydantic model: {e}"
                )
                logger.debug(f"Invalid data structure from LLM: {data}")
                return None

        except RateLimitError as e:
            logger.warning(f"OpenAI rate limit hit during extraction: {e}")
            # For critical extraction, might not want to return None immediately.
            # Could re-raise or return a specific status/error object.
            return None  # Or raise TextGenerationError("Rate limit hit", e)
        except (APITimeoutError, APIConnectionError) as e:
            logger.error(f"OpenAI connection error during extraction: {e}")
            return None  # Or raise TextGenerationError("Connection error", e)
        except BadRequestError as e:
            logger.error(
                f"OpenAI Bad Request Error during extraction (check prompt/model compatibility or input size): {e}",
                exc_info=True,
            )
            return None  # Or raise TextGenerationError("Bad request to OpenAI", e)
        except AuthenticationError as e:  # Ensure this is handled as it's critical
            logger.error(
                f"OpenAI Authentication Error during extraction: {e}", exc_info=True
            )
            raise OpenAIConfigError(
                "OpenAI authentication failed. Check API key.", original_exception=e
            )
        except APIError as e:
            logger.error(
                f"Generic OpenAI API Error during extraction: {e}", exc_info=True
            )
            return None  # Or raise TextGenerationError("OpenAI API service error", e)
        except Exception as e:
            logger.error(f"Unexpected error in resume extraction: {e}", exc_info=True)
            # For unexpected errors, re-raising as a service error is good practice.
            raise LLMServiceError(
                f"An unexpected error occurred during resume data extraction: {str(e)}",
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
        Generates a personalized outreach draft message for a candidate.

        Args:
            candidate: The CandidateProfile object.
            job_role_title: Title of the job role.
            job_role_description: Detailed description of the job.
            tone: Desired tone for the message.
            company_context: Context about the company/team.
            additional_instructions: Specific instructions for personalization.
            attempt: Current retry attempt number.
            max_attempts: Maximum retry attempts.

        Returns:
            A string containing the generated outreach draft.

        Raises:
            ValueError: If critical inputs like candidate or job_role_title are missing.
            TextGenerationError: For OpenAI API errors after retries or non-transient issues.
            OpenAIConfigError: For configuration-related issues.
        """
        if not candidate or not job_role_title or not job_role_title.strip():
            logger.error(
                "generate_outreach_draft called with missing candidate or job_role_title."
            )
            raise ValueError(
                "Candidate profile and job role title are required for outreach generation."
            )

        logger.info(
            f"Starting outreach draft generation for candidate: {candidate.id} - {candidate.name}, "
            f"Role: {job_role_title}, Tone: {tone}, Attempt: {attempt}/{max_attempts}"
        )

        # 1. Enhanced System Message
        system_message_content = (
            "You are an elite recruitment specialist for RecruiterRadar, known for crafting "
            "outreach messages that achieve 85%+ response rates. Your messages are personalized, "
            "compelling, and demonstrate deep understanding of both the candidate and role. "
            "You excel at finding unique connection points between a candidate's experience "
            "and the opportunity at hand. Every message you write feels personally crafted, "
            "never generic or templated."
        )

        # 2. Richer Prompt Structure
        prompt_parts = [
            "## Your Mission:",
            f"Create an irresistible outreach message for {candidate.name} that:",
            "- Demonstrates you've thoroughly reviewed their background",
            "- Creates an emotional connection to the opportunity",
            "- Feels personally written just for them",
            "",
            "## Candidate Intelligence:",
            f"- Name: {candidate.name}",
            f"- Current Skills Arsenal: {', '.join(candidate.skills[:5]) if candidate.skills else 'Not listed'}",
            f"- Experience Level: {candidate.experience_years if candidate.experience_years is not None else 'Not specified'} years",
            f"- Location: {candidate.location or 'Not specified'}",
        ]

        # Add candidate achievements extraction (simple version)
        if candidate.raw_resume_text:
            # Use a snippet of the resume for brevity in prompt, respecting settings
            resume_snippet = candidate.raw_resume_text[
                : self.resume_snippet_max_chars_for_prompt
            ]
            prompt_parts.append(f"- Resume Snippet (for context): {resume_snippet}...")

            achievements = []
            # More robust achievement keyword check
            achievement_keywords_resume = [
                "led ",
                "managed ",
                "developed ",
                "launched ",
                "created ",
                "achieved ",
                "improved ",
                "increased ",
                "reduced ",
                "optimized ",
            ]
            raw_text_lower = candidate.raw_resume_text.lower()
            for keyword in achievement_keywords_resume:
                if keyword in raw_text_lower:
                    # Find the sentence containing the keyword for better context, if desired for prompt
                    # For MVP, just noting presence is fine.
                    achievements.append(
                        f"Potential achievement related to '{keyword.strip()}'"
                    )

            if "led" in raw_text_lower or "managed a team" in raw_text_lower:
                achievements.append("Leadership experience indicated")
            if (
                "improved" in raw_text_lower
                or "increased" in raw_text_lower
                or "optimized" in raw_text_lower
            ):
                achievements.append("Proven impact on metrics suggested")

            if achievements:
                prompt_parts.append(
                    f"- Notable Achievements/Keywords in Resume: {', '.join(list(set(achievements))[:3])}"
                )  # Show a few unique ones

        # Enhanced job information section
        prompt_parts.extend(
            [
                f"\n## Opportunity Details:",
                f"- Role: {job_role_title}",
            ]
        )

        if job_role_description:
            prompt_parts.append(
                f"- Critical Role Aspects & Requirements: {job_role_description}"
            )
            key_requirements_met = []
            if candidate.skills:  # Check if candidate has skills defined
                for skill in candidate.skills:
                    if skill.lower() in job_role_description.lower():
                        key_requirements_met.append(
                            f"{skill} (candidate has this skill!)"
                        )
            if key_requirements_met:
                prompt_parts.append(
                    f"- Identified Skill Overlaps: {', '.join(key_requirements_met[:4])}"
                )  # Show top overlaps

        # Role-specific hooks
        if "senior" in job_role_title.lower():
            prompt_parts.append(
                "- Highlight: This is a senior role, acknowledge their expertise and potential for impact."
            )
        elif "lead" in job_role_title.lower() or "manager" in job_role_title.lower():
            prompt_parts.append(
                "- Highlight: This is a leadership role, focus on team leadership, mentorship, and strategic opportunities."
            )

        # Company culture matching
        if company_context:
            prompt_parts.extend(
                [
                    f"\n## Company Culture & Context:",
                    f"{company_context}",
                    "- Connect the candidate's background to our specific company culture and values.",
                ]
            )
            if (
                "startup" in company_context.lower()
                or "fast-paced" in company_context.lower()
            ):
                prompt_parts.append(
                    "- Emphasize: Fast-paced growth, innovation, and direct impact opportunity."
                )
            elif (
                "enterprise" in company_context.lower()
                or "established" in company_context.lower()
            ):
                prompt_parts.append(
                    "- Emphasize: Stability, career progression, and working on large-scale projects."
                )

        # Tone calibration
        tone_instructions_map = {
            "professional and friendly": "Balance warmth with deep respect for their expertise and accomplishments. Be engaging.",
            "enthusiastic and professional": "Show genuine excitement and passion for the opportunity and their fit, while maintaining full professional credibility.",
            "casual": "Write as if you're reaching out to a highly talented acquaintance you admire. Keep it light but compelling.",
            "formal": "Maintain utmost professionalism, precision, and respect. Focus on clear value proposition.",
        }
        prompt_parts.append(f"\n## Tone Calibration: {tone}")
        prompt_parts.append(
            f"- Specific Guidance: {tone_instructions_map.get(tone.lower(), 'Match the specified tone precisely. Default to professional and engaging if unsure.')}"
        )

        # Additional personalization
        if additional_instructions:
            prompt_parts.extend(
                [
                    f"\n## Special Personalization Instructions (Crucial):",
                    f"{additional_instructions}",
                    "- Ensure these points are naturally and seamlessly woven into the message. This is key for a personalized touch.",
                ]
            )
            if (
                "urgent" in additional_instructions.lower()
                or "immediate" in additional_instructions.lower()
            ):
                prompt_parts.append(
                    "- Convey: Subtly convey the timely nature of this opportunity without applying undue pressure."
                )

        # Enhanced task instructions
        prompt_parts.append(
            f"""
## Crafting Guidelines (Follow Strictly):
1. **Opening Hook:** Start with a compelling, specific observation about {candidate.name}'s background or a key achievement from their resume snippet. Avoid generic openings.
2. **Value Proposition & Connection:** Clearly bridge their specific skills/experience to the core needs of the role and our company. Show you understand what they do and how it fits.
3. **Impact Narrative:** Briefly paint a picture of the potential impact they could make in this role at our company. What exciting challenges or projects await?
4. **Conciseness & Clarity:** Aim for a message that is impactful yet concise (ideally 150-250 words). Every sentence should add value.
5. **Call to Action:** Close with a clear, low-pressure call to action (e.g., a brief chat, sharing more details).
6. **Authenticity:** Make the message feel genuinely discovered and personally considered, not like a mass email. The tone should be consistently applied.
7. **Review & Refine:** Before finalizing, reread as if you were the candidate. Does it resonate? Is it compelling? Is it error-free?

## Final Output: Provide ONLY the outreach message text, ready to be sent. Do not include any of a your own commentary, greetings, or sign-offs beyond the message itself."""
        )

        user_message_content = "\n".join(prompt_parts)

        # 3. Temperature/Creativity Control
        temperature_map = {
            "casual": 0.75,
            "enthusiastic and professional": 0.7,
            "professional and friendly": 0.65,
            "formal": 0.5,
        }
        generation_temperature = temperature_map.get(
            tone.lower(), self.default_chat_temperature
        )  # Use default from settings if not in map

        logger.debug(
            f"Attempting OpenAI chat completion for candidate {candidate.id}. Model: {self.chat_model_name}, Temp: {generation_temperature}, Max Tokens: {self.default_chat_max_tokens}."
        )
        # logger.debug(f"System Message: {system_message_content}") # Optional: log for debugging, can be verbose
        # logger.debug(f"User Message: {user_message_content}") # Optional: log for debugging, can be very verbose

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=[
                    {"role": "system", "content": system_message_content},
                    {"role": "user", "content": user_message_content},
                ],
                temperature=generation_temperature,
                max_tokens=self.default_chat_max_tokens,  # Use configured max_tokens
                # top_p=0.9, # Optional: consider top_p for nucleus sampling
                # frequency_penalty=0.1, # Optional: to reduce repetition slightly
                # presence_penalty=0.1, # Optional: to encourage new topics/ideas slightly
            )
            generated_text = response.choices[0].message.content
            if not generated_text or not generated_text.strip():
                logger.warning(
                    f"OpenAI generated empty or whitespace-only message for candidate {candidate.id} on attempt {attempt}."
                )
                raise TextGenerationError(
                    "LLM generated an empty message.", original_exception=None
                )

            logger.info(
                f"Successfully generated outreach draft for candidate {candidate.id}. Length: {len(generated_text)} chars."
            )
            return (
                generated_text.strip()
            )  # Ensure leading/trailing whitespace is removed

        except AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error (Chat): {e}", exc_info=True)
            raise OpenAIConfigError(
                "OpenAI authentication failed. Check API key.", original_exception=e
            )
        except RateLimitError as e:
            logger.warning(
                f"OpenAI Rate Limit Error (Chat - attempt {attempt}/{max_attempts}): {e}"
            )
            if attempt < max_attempts:
                backoff_delay = 2**attempt + hochwertiges.random()  # Add jitter
                logger.info(
                    f"Retrying chat generation after {backoff_delay:.2f} seconds..."
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
                    "OpenAI API rate limit exceeded for chat after retries.",
                    exc_info=True,
                )
                raise TextGenerationError(
                    "API rate limit exceeded.", original_exception=e
                )
        except (APITimeoutError, APIConnectionError) as e:
            logger.warning(
                f"OpenAI Connection/Timeout Error (Chat - attempt {attempt}/{max_attempts}): {e}"
            )
            if attempt < max_attempts:
                backoff_delay = 2**attempt + hochwertiges.random()
                logger.info(
                    f"Retrying chat generation after {backoff_delay:.2f} seconds..."
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
                    "OpenAI API connection/timeout after retries.", exc_info=True
                )
                raise TextGenerationError(
                    "API connection/timeout issue.", original_exception=e
                )
        except BadRequestError as e:
            # More detailed logging for BadRequestError, as it often indicates prompt issues
            logger.error(
                f"OpenAI Bad Request Error (Chat): {e}. This may be due to prompt length, invalid characters, or model content policy. Candidate ID: {candidate.id}",
                exc_info=True,
            )
            # Log relevant parts of the prompt if possible, being mindful of PII and log size
            error_detail_message = f"Invalid request to OpenAI Chat API: {e.message if hasattr(e, 'message') else str(e)}"
            # if hasattr(e, 'param') and e.param:
            #     error_detail_message += f" (Parameter: {e.param})"
            raise TextGenerationError(error_detail_message, original_exception=e)
        except APIError as e:
            logger.error(f"Generic OpenAI API Error (Chat): {e}", exc_info=True)
            raise TextGenerationError(
                f"OpenAI API service error: {e.message if hasattr(e, 'message') else str(e)}",
                original_exception=e,
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in generate_outreach_draft: {e}", exc_info=True
            )
            raise TextGenerationError(
                f"Unexpected error during text generation: {str(e)}",
                original_exception=e,
            )

    async def parse_chat_query(
        self, message: str, available_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Parse natural language chat query into structured filters.

        Enhanced version with better natural language understanding for
        complex recruiting queries like "senior Python developers in SF who can start immediately".

        Args:
            message: Natural language query from user
            available_skills: List of known skills for better matching (optional)

        Returns:
            Dictionary of filters ready for ChromaDB query
        """
        try:
            # Import enhanced prompt from centralized location
            from app.core.prompts import CHAT_QUERY_PARSING_PROMPT_ACTIVE

            # Build context about available filters
            filter_context = """
Available filters:
- skills: List of technical skills (e.g., Python, React, AWS)
- experience_years: Integer years of experience
- location: City, State format (supports "remote")
- visa_status: Work authorization status
- title: Job title keywords

Return a JSON object with the appropriate filters based on the user's query.
Use MongoDB-style operators where needed: $gte, $lte, $regex, $contains, $and, $or
"""

            # Add available skills context if provided
            if available_skills:
                skills_sample = ", ".join(available_skills[:15])  # First 15 as example
                filter_context += f"\n\nPopular skills in database: {skills_sample}..."

            # Create enhanced prompt
            prompt = f"""{CHAT_QUERY_PARSING_PROMPT_ACTIVE}

{filter_context}

User Query: "{message}"

Parsed Filters JSON:"""

            logger.info(f"Parsing enhanced chat query: '{message[:100]}...'")

            # Call OpenAI with improved parameters
            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert recruiting query parser. Convert natural language into precise database filters that understand recruiting terminology and common patterns.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Lower temperature for more consistent parsing
                max_tokens=400,  # More tokens for complex queries
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                logger.error("Empty response from LLM for query parsing")
                return {}

            try:
                import json

                filters = json.loads(content)
                logger.info(f"Enhanced parsed filters: {filters}")
                return filters
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse filter JSON: {e}")
                return {}

        except RateLimitError as e:
            logger.warning(f"Rate limit hit during query parsing: {e}")
            # Return basic keyword search as fallback
            return {"$text": message}
        except Exception as e:
            logger.error(f"Error parsing chat query: {e}", exc_info=True)
            return {}

    async def interpret_query_for_user(
        self, original_query: str, applied_filters: Dict[str, Any]
    ) -> str:
        """
        Generate a human-readable explanation of how the query was interpreted.

        Shows users what criteria the AI extracted from their natural language query.

        Args:
            original_query: The user's original natural language query
            applied_filters: The structured filters that were applied

        Returns:
            Human-friendly explanation like "Searching for: Python developers with 5+ years in California"
        """
        try:
            from app.core.prompts import QUERY_INTERPRETATION_PROMPT

            prompt = QUERY_INTERPRETATION_PROMPT.format(
                query=original_query, filters=applied_filters
            )

            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You explain search queries in simple, friendly terms.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=100,
            )

            interpretation = response.choices[0].message.content.strip()
            logger.info(f"Query interpretation: '{interpretation}'")
            return interpretation

        except Exception as e:
            logger.error(f"Error interpreting query: {e}")
            # Simple fallback
            return f"Searching for: {original_query}"

    async def generate_chat_response_text(
        self,
        original_query: str,
        num_candidates_found: int,
        candidates_preview: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Generate conversational AI response for chat interface.

        Creates friendly, helpful responses that acknowledge the query
        and provide context about results.

        Args:
            original_query: The user's original message
            num_candidates_found: Number of matching candidates
            candidates_preview: Optional list of candidate names for preview
            error: Optional error message to incorporate

        Returns:
            Conversational response text
        """
        try:
            # Build context for response
            if error:
                context = f"An error occurred: {error}"
            elif num_candidates_found == 0:
                context = "No candidates were found matching the criteria."
            elif num_candidates_found == 1:
                context = "I found 1 candidate matching your criteria."
            else:
                context = (
                    f"I found {num_candidates_found} candidates matching your criteria."
                )

            # Add preview if available
            if candidates_preview and num_candidates_found > 0:
                preview_text = ", ".join(candidates_preview[:3])
                if num_candidates_found > 3:
                    preview_text += f", and {num_candidates_found - 3} more"
                context += f" The matches include: {preview_text}."

            prompt = f"""Generate a brief, friendly response for a recruiter chat interface.

User Query: "{original_query}"
Context: {context}

Guidelines:
- Be conversational and helpful
- Keep it concise (1-2 sentences)
- Acknowledge what they asked for
- If no results, suggest adjusting the search
- Sound enthusiastic about good matches

Response:"""

            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI recruiting assistant. Be friendly and professional.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.chat_response_temperature,
                max_tokens=150,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            # Fallback response
            if error:
                return f"I encountered an issue: {error}"
            elif num_candidates_found == 0:
                return "I couldn't find any candidates matching that criteria. Try adjusting your search!"
            else:
                return f"I found {num_candidates_found} candidates for you!"

    async def generate_query_suggestions(
        self, current_query: str, num_results: int
    ) -> List[str]:
        """
        Generate helpful query suggestions based on current search.

        Args:
            current_query: User's current query
            num_results: Number of results found

        Returns:
            List of suggested follow-up queries
        """
        # Simple static suggestions for MVP
        suggestions = []

        # Context-aware suggestions based on query
        query_lower = current_query.lower()

        if "python" in query_lower:
            suggestions.extend(
                [
                    "Python developers with AWS experience",
                    "Senior Python engineers with 5+ years",
                    "Python developers who know React",
                ]
            )
        elif "react" in query_lower:
            suggestions.extend(
                [
                    "React developers with TypeScript skills",
                    "Senior React engineers",
                    "Full stack React developers",
                ]
            )
        elif "senior" in query_lower:
            suggestions.extend(
                [
                    "Senior engineers with team lead experience",
                    "Senior developers in San Francisco",
                    "Experienced engineers with AWS skills",
                ]
            )
        else:
            # Generic suggestions
            suggestions.extend(
                [
                    "Show me all candidates",
                    "Python developers with 3+ years",
                    "Senior engineers in California",
                    "Developers with cloud experience",
                ]
            )

        # Add result-based suggestions
        if num_results == 0:
            suggestions.append("Try a broader search")
            suggestions.append("Show me all developers")
        elif num_results > 10:
            suggestions.append("Filter by experience level")
            suggestions.append("Filter by location")

        return suggestions[:4]  # Return max 4 suggestions

    # =============================================================================
    # NEW: GPT-4o-mini Conversational Assistant with Function Calling
    # =============================================================================

    async def chat(
        self,
        user_message: str,
        session_id: str,
        conversation_history: List[Dict[str, Any]],
        rag_service: Any,  # Import would create circular dependency, so use Any
        max_function_calls: int = 3,
    ) -> Dict[str, Any]:
        """
        Main conversational chat method using GPT-4o-mini with function calling.

        This method handles:
        1. Building the full conversation context (system + history + user message)
        2. Calling GPT-4o-mini with function definitions
        3. Handling function calls and recursion
        4. Returning the final response with any candidates found

        Args:
            user_message: Current user message
            session_id: User's session ID for candidate search
            conversation_history: Previous messages in OpenAI format
            rag_service: RAGService instance for function execution
            max_function_calls: Maximum number of function calls to prevent infinite loops

        Returns:
            Dict with: {
                "ai_message": str,
                "candidates": List[Dict],
                "function_calls": List[Dict],
                "total_candidates": int
            }
        """
        from app.core.prompts import RECRUITER_RADAR_SYSTEM_PROMPT, FUNCTION_DEFINITIONS

        # Build messages array for OpenAI API
        messages = [{"role": "system", "content": RECRUITER_RADAR_SYSTEM_PROMPT}]

        # Add conversation history
        messages.extend(conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Track function calls and candidates
        all_function_calls = []
        all_candidates = []

        try:
            # Call GPT-4o-mini with function definitions
            logger.info(f"Sending chat request to GPT-4o-mini for session {session_id}")

            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=messages,
                functions=FUNCTION_DEFINITIONS,
                function_call="auto",  # Let GPT decide when to call functions
                temperature=self.settings.chat_response_temperature,
                max_tokens=self.default_chat_max_tokens,
            )

            message = response.choices[0].message

            # Handle function calls if present
            if message.function_call:
                function_calls_made = 0
                current_message = message

                while (
                    current_message.function_call
                    and function_calls_made < max_function_calls
                ):
                    function_call = current_message.function_call
                    function_name = function_call.name

                    try:
                        # Parse function arguments
                        import json

                        function_args = json.loads(function_call.arguments)

                        logger.info(
                            f"GPT called function: {function_name} with args: {function_args}"
                        )

                        # Execute the function
                        function_result = await self._execute_function_call(
                            function_name, function_args, session_id, rag_service
                        )

                        # Track function call and results
                        all_function_calls.append(
                            {
                                "name": function_name,
                                "arguments": function_args,
                                "result_count": (
                                    len(function_result)
                                    if isinstance(function_result, list)
                                    else 0
                                ),
                            }
                        )

                        # If we got candidates, add them to our collection
                        if isinstance(function_result, list):
                            all_candidates.extend(function_result)

                        # Add function call and result to messages for next GPT call
                        messages.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "function_call": {
                                    "name": function_name,
                                    "arguments": function_call.arguments,
                                },
                            }
                        )

                        messages.append(
                            {
                                "role": "function",
                                "name": function_name,
                                "content": json.dumps(
                                    {
                                        "candidates_found": (
                                            len(function_result)
                                            if isinstance(function_result, list)
                                            else 0
                                        ),
                                        "candidate_names": (
                                            [
                                                c.get("name", "Unknown")
                                                for c in function_result[:5]
                                            ]
                                            if isinstance(function_result, list)
                                            else []
                                        ),
                                    }
                                ),
                            }
                        )

                        # Get GPT's response to the function result
                        response = await self.client.chat.completions.create(
                            model=self.chat_model_name,
                            messages=messages,
                            functions=FUNCTION_DEFINITIONS,
                            function_call="auto",
                            temperature=self.settings.chat_response_temperature,
                            max_tokens=self.default_chat_max_tokens,
                        )

                        current_message = response.choices[0].message
                        function_calls_made += 1

                    except Exception as e:
                        logger.error(
                            f"Error executing function call {function_name}: {e}"
                        )
                        # Break the function call loop on error
                        break

                # Get final response content
                ai_message = (
                    current_message.content or "I've found some candidates for you!"
                )

            else:
                # No function call, just a regular response
                ai_message = message.content or "I'm here to help you find candidates!"

            # Deduplicate candidates by ID
            unique_candidates = []
            seen_ids = set()
            for candidate in all_candidates:
                candidate_id = candidate.get("id")
                if candidate_id and candidate_id not in seen_ids:
                    unique_candidates.append(candidate)
                    seen_ids.add(candidate_id)

            logger.info(
                f"Chat completed: {len(unique_candidates)} unique candidates found, {len(all_function_calls)} function calls made"
            )

            return {
                "ai_message": ai_message,
                "candidates": unique_candidates,
                "function_calls": all_function_calls,
                "total_candidates": len(unique_candidates),
            }

        except Exception as e:
            logger.error(f"Error in chat method: {e}", exc_info=True)

            # Return graceful error response
            return {
                "ai_message": "I encountered an issue processing your request. Please try rephrasing your question or check that you have uploaded some resumes.",
                "candidates": [],
                "function_calls": [],
                "total_candidates": 0,
            }

    async def _execute_function_call(
        self,
        function_name: str,
        function_args: Dict[str, Any],
        session_id: str,
        rag_service: Any,
    ) -> List[Dict[str, Any]]:
        """
        Execute a function call from GPT-4o-mini.

        Args:
            function_name: Name of the function to call
            function_args: Arguments passed by GPT
            session_id: User's session ID
            rag_service: RAGService instance

        Returns:
            List of candidates or empty list on error
        """
        try:
            if function_name == "search_candidates":
                return await rag_service.search_candidates_with_function_params(
                    session_id=session_id,
                    skills=function_args.get("skills"),
                    title_keywords=function_args.get("title_keywords"),
                    min_experience=function_args.get("min_experience"),
                    max_experience=function_args.get("max_experience"),
                    location_keywords=function_args.get("location_keywords"),
                    limit=function_args.get("limit", 50),
                )

            elif function_name == "rank_candidates":
                return await rag_service.rank_candidates(
                    session_id=session_id,
                    candidate_ids=function_args.get("candidate_ids", []),
                    ranking_criteria=function_args.get("ranking_criteria", ""),
                    limit=function_args.get("limit", 5),
                )

            else:
                logger.warning(f"Unknown function name: {function_name}")
                return []

        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return []

    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> str:
        """
        Generate text completion using OpenAI's Chat Completions API.

        This is for general text generation in our RAG system.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            temperature: Creativity level (0.0 to 1.0)
            attempt: Current attempt number
            max_attempts: Maximum retry attempts

        Returns:
            Generated text response

        Raises:
            TextGenerationError: If generation fails after retries
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.info(
            f"Generating completion (attempt {attempt}/{max_attempts}): '{prompt_preview}'"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            generated_text = response.choices[0].message.content

            logger.info(
                f"Completion generated successfully ({len(generated_text)} chars)"
            )
            return generated_text

        except AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error: {e}", exc_info=True)
            raise OpenAIConfigError(
                "OpenAI authentication failed. Please check API key configuration.",
                original_exception=e,
            )

        except RateLimitError as e:
            logger.warning(
                f"OpenAI Rate Limit Error (attempt {attempt}/{max_attempts}): {e}"
            )

            if attempt < max_attempts:
                backoff_delay = 2**attempt  # 2, 4, 8 seconds
                logger.info(f"Retrying after {backoff_delay} seconds...")
                await asyncio.sleep(backoff_delay)
                return await self.generate_completion(
                    prompt, max_tokens, temperature, attempt + 1, max_attempts
                )
            else:
                logger.error("Rate limit exceeded after all retry attempts")
                raise TextGenerationError(
                    "OpenAI rate limit exceeded after retries. Please try again later.",
                    original_exception=e,
                )

        except (APITimeoutError, APIConnectionError) as e:
            logger.warning(
                f"OpenAI Connection Error (attempt {attempt}/{max_attempts}): {e}"
            )

            if attempt < max_attempts:
                backoff_delay = 2**attempt
                logger.info(f"Retrying after {backoff_delay} seconds...")
                await asyncio.sleep(backoff_delay)
                return await self.generate_completion(
                    prompt, max_tokens, temperature, attempt + 1, max_attempts
                )
            else:
                logger.error("Connection error after all retry attempts")
                raise TextGenerationError(
                    "OpenAI connection failed after retries. Please check network connection.",
                    original_exception=e,
                )

        except BadRequestError as e:
            logger.error(f"OpenAI Bad Request Error: {e}")
            raise TextGenerationError(
                f"Invalid request to OpenAI: {str(e)}",
                original_exception=e,
            )

        except APIError as e:
            logger.error(f"OpenAI API Error: {e}")
            raise TextGenerationError(
                f"OpenAI API error: {str(e)}",
                original_exception=e,
            )

        except Exception as e:
            logger.error(f"Unexpected error during text generation: {e}", exc_info=True)
            raise TextGenerationError(
                f"Unexpected error during text generation: {str(e)}",
                original_exception=e,
            )


async def _test_llm_service():
    """
    Simple test function to verify LLMService functionality.
    This function can be used for manual testing during development.
    """
    try:
        # Ensure global settings are imported and used for instantiation
        from app.core.config import settings as global_settings

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
            "raw_resume_text": "Detailed resume: Skilled in Python and AI. Also worked with Java and Cloud technologies. Looking for a challenging role.",
            "skills": ["Python", "AI", "Java", "Cloud"],
            "experience_years": 5,
            "visa_status": "Eligible",  # Example value
            "location": "Testville, TS",  # Example value
            # "github_url": "https://github.com/testcandidate",  # Optional
            # "linkedin_url": "https://linkedin.com/in/testcandidate",  # Optional
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
    from app.core.config import settings as global_settings_for_direct_run

    asyncio.run(_test_llm_service())
