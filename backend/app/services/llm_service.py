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
