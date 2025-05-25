# backend/app/tests/services/test_llm_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Optional

# Assuming your project structure allows these imports
# Adjust paths if necessary based on your project's root and how pytest discovers tests
from backend.app.services.llm_service import (
    LLMService,
    TextGenerationError,
    OpenAIConfigError,
    # EmbeddingGenerationError, # Not directly tested here but good to have if LLMService.__init__ is more complex
    # LLMServiceError
)
from backend.app.models.candidate import CandidateProfile
from backend.app.core.config import Settings  # For creating mock settings
from backend.app.core.model_config import (
    ModelSettings,
)  # For instantiating within Settings if that's your setup

# If openai library itself is used for error types in asserts
from openai import RateLimitError, BadRequestError, APIError, AuthenticationError

pytestmark = pytest.mark.asyncio


class TestLLMServiceGenerateOutreachDraft:

    @pytest.fixture
    def mock_model_settings(self):
        """Reusable mock for ModelSettings."""
        model_settings = MagicMock(spec=ModelSettings)
        model_settings.model_chat_model_name = "gpt-4o-mini"
        model_settings.model_chat_temperature = 0.7
        model_settings.model_chat_max_tokens = 400
        # Small for easier testing of truncation, ensure this matches what LLMService __init__ expects
        model_settings.resume_snippet_max_chars_for_prompt = 200
        model_settings.model_embedding_model_name = (
            "text-embedding-3-small"  # Needed for LLMService init
        )
        return model_settings

    @pytest.fixture
    def mock_settings(self, mock_model_settings):
        """Reusable mock for the main Settings, embedding ModelSettings."""
        settings = MagicMock(spec=Settings)
        settings.openai_api_key = "test_sk_key"

        # Align with LLMService.__init__ expectations
        settings.embedding_model_name = mock_model_settings.model_embedding_model_name
        settings.chat_model_name = mock_model_settings.model_chat_model_name

        # These are the direct attributes LLMService __init__ uses from the main settings object
        settings.model_chat_temperature = mock_model_settings.model_chat_temperature
        settings.model_chat_max_tokens = mock_model_settings.model_chat_max_tokens
        settings.resume_snippet_max_chars_for_prompt = (
            mock_model_settings.resume_snippet_max_chars_for_prompt
        )
        return settings

    @pytest.fixture
    def mock_candidate(self):
        # Create a consistent mock CandidateProfile
        # Ensure all fields used by generate_outreach_draft are present and valid
        candidate_data = {
            "id": "c001",
            "name": "Test User",
            "raw_resume_text": "This is a short resume text. "
            + "Longer text for truncation " * 20,  # To test truncation
            "skills": ["Python", "FastAPI", "Testing"],
            "experience_years": 5,
            "visa_status": "US Citizen",
            "location": "Testville, USA",
            "linkedin_url": "https://linkedin.com/in/testuser",
            "github_url": "https://github.com/testuser",
        }
        return CandidateProfile.model_validate(candidate_data)

    @pytest.fixture
    def llm_service(self, mock_settings):
        # Patch the AsyncOpenAI client within the LLMService instance for all tests in this class
        # The patch target should be where AsyncOpenAI is looked up when LLMService is initialized.
        # If LLMService imports it as `from openai import AsyncOpenAI`, then 'backend.app.services.llm_service.AsyncOpenAI' is correct.
        with patch(
            "backend.app.services.llm_service.AsyncOpenAI"
        ) as mock_async_openai_constructor:
            # Configure the mock constructor to return an AsyncMock instance for the client
            mock_client_instance = AsyncMock()
            mock_async_openai_constructor.return_value = mock_client_instance

            service = LLMService(settings_obj=mock_settings)
            # The service.client will now be mock_client_instance
            return service

    async def test_successful_draft_generation_with_all_inputs(
        self, llm_service, mock_candidate, mock_settings
    ):
        """Test successful draft generation when all optional inputs are provided."""
        mock_openai_response = AsyncMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock()
        mock_openai_response.choices[0].message.content = (
            "Generated outreach draft text."
        )
        mock_openai_response.choices[0].finish_reason = "stop"

        # Ensure the client instance on the service is the one we mock methods on
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        job_details = {
            "job_role_title": "Senior Python Developer",
            "job_role_description": "Develop awesome Python apps.",
            "tone": "enthusiastic and professional",
            "company_context": "A fast-growing tech company.",
            "additional_instructions": "Mention their FastAPI skill.",
        }

        result = await llm_service.generate_outreach_draft(
            candidate=mock_candidate, **job_details
        )

        assert result == "Generated outreach draft text."
        llm_service.client.chat.completions.create.assert_called_once()

        # Basic check on call args (more detailed checks in specific prompt tests)
        call_args = llm_service.client.chat.completions.create.call_args
        assert call_args is not None
        passed_messages = call_args.kwargs["messages"]
        assert any(
            mock_candidate.name in msg["content"]
            for msg in passed_messages
            if msg["role"] == "user"
        )
        assert any(
            job_details["job_role_title"] in msg["content"]
            for msg in passed_messages
            if msg["role"] == "user"
        )
        assert call_args.kwargs["model"] == mock_settings.chat_model_name
        assert call_args.kwargs["temperature"] == mock_settings.model_chat_temperature
        assert call_args.kwargs["max_tokens"] == mock_settings.model_chat_max_tokens

    async def test_successful_draft_generation_with_minimal_optional_inputs(
        self, llm_service, mock_candidate, mock_settings
    ):
        """Test successful draft generation when optional inputs are None."""
        mock_openai_response = AsyncMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock()
        mock_openai_response.choices[0].message.content = "Minimal draft text."
        mock_openai_response.choices[0].finish_reason = "stop"

        llm_service.client.chat.completions.create.return_value = mock_openai_response

        job_details = {
            "job_role_title": "Junior Developer",
            "job_role_description": None,
            "tone": "friendly",  # Tone is technically not optional in the method signature as designed
            "company_context": None,
            "additional_instructions": None,
        }

        result = await llm_service.generate_outreach_draft(
            candidate=mock_candidate, **job_details
        )

        assert result == "Minimal draft text."
        llm_service.client.chat.completions.create.assert_called_once()
        call_args = llm_service.client.chat.completions.create.call_args
        assert call_args is not None
        passed_messages_str = "".join(
            msg["content"] for msg in call_args.kwargs["messages"]
        )

        # Check that placeholders for None values are not present or are handled gracefully
        # This depends on how your prompt string construction handles None values.
        # For example, if "Key aspects of the role: None" would appear, this test might need refinement
        # based on actual prompt output. For now, we assume they are just omitted.
        assert (
            "Key aspects of the role:" not in passed_messages_str
            or "Key aspects of the role: None" not in passed_messages_str
        )  # A bit loose, refine
        assert "Context about our company/team:" not in passed_messages_str
        assert (
            "Additional specific instructions for this draft:"
            not in passed_messages_str
        )
        assert call_args.kwargs["model"] == mock_settings.chat_model_name
        assert call_args.kwargs["temperature"] == mock_settings.model_chat_temperature
        assert call_args.kwargs["max_tokens"] == mock_settings.model_chat_max_tokens

    async def test_prompt_construction_includes_all_details(
        self,
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
        mock_settings: MagicMock,
    ):
        """
        Tests that the prompt constructed includes all necessary details
        from candidate, job, tone, context, and instructions.
        """
        # Arrange
        mock_openai_response = AsyncMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock()
        mock_openai_response.choices[0].message.content = "Detailed prompt test draft."
        mock_openai_response.choices[0].finish_reason = "stop"
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        job_role_title = "Senior AI Engineer"
        job_role_description = "Build cutting-edge AI models."
        tone = "formal and direct"
        company_context = "A leading AI research lab."
        additional_instructions = "Emphasize research background."

        # Act
        await llm_service.generate_outreach_draft(
            candidate=mock_candidate,
            job_role_title=job_role_title,
            job_role_description=job_role_description,
            tone=tone,
            company_context=company_context,
            additional_instructions=additional_instructions,
        )

        # Assert
        llm_service.client.chat.completions.create.assert_called_once()
        call_args = llm_service.client.chat.completions.create.call_args

        assert call_args is not None
        messages = call_args.kwargs["messages"]

        # Check System Message
        assert messages[0]["role"] == "system"
        # A more robust check for system message content:
        expected_system_content_parts = [
            "expert recruitment assistant",
            "RecruiterRadar",
            "draft a concise",
            "engaging, and personalized outreach message",
            "Highlight the candidate's relevant skills and experience",
            "connect it to the target job role",
            "Maintain the specified tone",
            "only the body of the outreach message",
            "without any preamble or subject line",
        ]
        for part in expected_system_content_parts:
            assert part in messages[0]["content"]

        # Check User Message Content
        user_message_content = messages[1]["content"]
        assert messages[1]["role"] == "user"

        # Using f-strings for clarity and direct value checking
        assert (
            f"- Name: {mock_candidate.name}" in user_message_content
        )  # Adjusted from "Candidate Name:"
        assert (
            f"- Key Skills (from profile): {', '.join(mock_candidate.skills)}"
            in user_message_content
        )
        assert (
            f"- Years of Experience: {mock_candidate.experience_years}"
            in user_message_content
        )
        assert f"- Target Job Role: {job_role_title}" in user_message_content
        assert (
            f"- Key aspects of the role: {job_role_description}" in user_message_content
        )
        assert (
            f"Desired tone for the outreach message: {tone}." in user_message_content
        )  # Added period
        assert (
            f"- Context about our company/team: {company_context}"
            in user_message_content
        )
        assert (
            f"Additional specific instructions for this draft: {additional_instructions}"
            in user_message_content
        )

        # Check for presence of (part of) the resume snippet
        # This assumes the prompt structure around the snippet from LLMService.
        # A more specific test for truncation (test_raw_resume_text_truncation_logic) will handle length.
        assert "Relevant excerpt from candidate's resume:" in user_message_content
        assert (
            mock_candidate.raw_resume_text[:50] in user_message_content
        )  # Check a prefix of the resume

        # Check for key task instructions
        assert "Draft a personalized outreach message directly" in user_message_content
        assert f"to {mock_candidate.name}" in user_message_content
        assert "Address the candidate by their first name" in user_message_content
        assert "clear call to action" in user_message_content
        assert "Output only the body of the message" in user_message_content

        # Verify API call parameters
        assert call_args.kwargs["model"] == mock_settings.chat_model_name
        assert call_args.kwargs["temperature"] == mock_settings.model_chat_temperature
        assert call_args.kwargs["max_tokens"] == mock_settings.model_chat_max_tokens

    async def test_raw_resume_text_truncation_logic(
        self,
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
        mock_settings: MagicMock,
    ):
        """
        Tests that raw_resume_text is correctly truncated in the prompt
        based on settings.resume_snippet_max_chars_for_prompt.
        """
        # Arrange
        # mock_settings fixture already sets resume_snippet_max_chars_for_prompt to 200
        # mock_candidate fixture has raw_resume_text much longer than 200 chars

        mock_openai_response = (
            AsyncMock()
        )  # Basic mock, we only care about the prompt input
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock()
        mock_openai_response.choices[0].message.content = "Truncation test draft."
        mock_openai_response.choices[0].finish_reason = "stop"
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        # Act
        await llm_service.generate_outreach_draft(
            candidate=mock_candidate,
            job_role_title="Test Role for Truncation",
            job_role_description="Test Desc for Truncation",  # Provided a value
            tone="neutral",
            company_context=None,
            additional_instructions=None,
        )

        # Assert
        llm_service.client.chat.completions.create.assert_called_once()
        call_args = llm_service.client.chat.completions.create.call_args
        assert call_args is not None

        user_message_content = call_args.kwargs["messages"][1]["content"]

        start_marker = "Relevant excerpt from candidate's resume:\n---\n"
        end_marker = "\n---"

        start_index = user_message_content.find(start_marker)
        assert (
            start_index != -1
        ), f"Resume snippet start marker ('{start_marker.strip()}') not found in prompt"

        snippet_start_in_prompt = start_index + len(start_marker)
        snippet_end_in_prompt = user_message_content.find(
            end_marker, snippet_start_in_prompt
        )
        assert (
            snippet_end_in_prompt != -1
        ), f"Resume snippet end marker ('{end_marker.strip()}') not found in prompt after start marker"

        actual_snippet_in_prompt = user_message_content[
            snippet_start_in_prompt:snippet_end_in_prompt
        ]

        expected_max_len_from_settings = (
            mock_settings.resume_snippet_max_chars_for_prompt
        )

        # The actual snippet in the prompt should be the original text up to expected_max_len_from_settings,
        # followed by "..."
        # So, its length will be expected_max_len_from_settings + 3 (for "...")
        # However, if the original text is SHORTER than expected_max_len_from_settings,
        # then it won't be truncated and won't have "..."

        if len(mock_candidate.raw_resume_text) > expected_max_len_from_settings:
            assert actual_snippet_in_prompt.endswith("...")
            # The content part of the snippet (before "...") should be exactly the truncated part
            content_part_of_snippet = actual_snippet_in_prompt[:-3]  # Remove "..."
            assert (
                content_part_of_snippet
                == mock_candidate.raw_resume_text[:expected_max_len_from_settings]
            )
            assert len(actual_snippet_in_prompt) == expected_max_len_from_settings + 3
        else:
            # If raw_resume_text is shorter than the limit, it should be used as is, without "..."
            assert not actual_snippet_in_prompt.endswith("...")
            assert actual_snippet_in_prompt == mock_candidate.raw_resume_text
            assert len(actual_snippet_in_prompt) == len(mock_candidate.raw_resume_text)

        # Example for checking logger (optional, requires patching logger on the service or globally for the module)
        # with patch.object(llm_service_logger, 'debug') as mock_logger_debug: # Assuming llm_service_logger is the logger instance used in llm_service.py
        #     await llm_service.generate_outreach_draft(...) # Re-run or structure test to capture log
        #     if len(mock_candidate.raw_resume_text) > expected_max_len_from_settings:
        #         mock_logger_debug.assert_any_call(
        #             f"Truncated raw_resume_text for candidate {mock_candidate.id} to ~{expected_max_len_from_settings} chars for prompt."
        #         )

    # 3. Handling OpenAI API errors (RateLimitError with retry, BadRequestError, ContentFilter, Length)
    #    - test_handles_openai_rate_limit_error_with_retry_and_success
    #    - test_raises_text_generation_error_after_max_rate_limit_retries

    @patch("backend.app.services.llm_service.asyncio.sleep", new_callable=AsyncMock)
    async def test_handles_openai_rate_limit_error_with_retry_and_success(
        self,
        mock_sleep: AsyncMock,
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
    ):
        """
        Tests that the service retries on RateLimitError and succeeds on a subsequent attempt.
        """
        # Arrange
        # Simulate RateLimitError on the first call, then a successful response
        successful_response = AsyncMock()
        successful_response.choices = [MagicMock()]
        successful_response.choices[0].message = MagicMock()
        successful_response.choices[0].message.content = "Success after retry!"
        successful_response.choices[0].finish_reason = "stop"

        # The side_effect list will be consumed by sequential calls
        llm_service.client.chat.completions.create.side_effect = [
            RateLimitError(
                message="Simulated Rate Limit Error",
                response=MagicMock(),  # Mock response object for the error
                body=None,
            ),
            successful_response,
        ]

        job_details = {
            "job_role_title": "Retry Role",
            "job_role_description": "Testing retries",
            "tone": "patient",
            "company_context": None,
            "additional_instructions": None,
        }

        # Act
        result = await llm_service.generate_outreach_draft(
            candidate=mock_candidate,
            **job_details,
            # LLMService internally handles default attempts (max_attempts=3)
        )

        # Assert
        assert result == "Success after retry!"
        assert (
            llm_service.client.chat.completions.create.call_count == 2
        )  # First call failed, second succeeded
        mock_sleep.assert_called_once()  # Check that asyncio.sleep was called for backoff

    @patch("backend.app.services.llm_service.asyncio.sleep", new_callable=AsyncMock)
    async def test_raises_text_generation_error_after_max_rate_limit_retries(
        self,
        mock_sleep: AsyncMock,
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
    ):
        """
        Tests that TextGenerationError is raised after exhausting max retries for RateLimitError.
        """
        # Arrange
        # Simulate RateLimitError on all attempts (LLMService defaults to max_attempts=3)
        llm_service.client.chat.completions.create.side_effect = RateLimitError(
            message="Persistent Rate Limit Error", response=MagicMock(), body=None
        )

        job_details = {
            "job_role_title": "Max Retry Role",
            "job_role_description": "Testing max retries",
            "tone": "persistent",
            "company_context": None,
            "additional_instructions": None,
        }

        # Act & Assert
        with pytest.raises(
            TextGenerationError, match="OpenAI API rate limit exceeded."
        ):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate, **job_details
            )

        # Default max_attempts in generate_outreach_draft is 3
        assert llm_service.client.chat.completions.create.call_count == 3
        # Sleep should be called twice (after 1st fail, after 2nd fail)
        assert mock_sleep.call_count == 2
        # Check backoff delays if desired:
        expected_sleep_calls = [call(2), call(4)]  # 2**1, 2**2
        mock_sleep.assert_has_calls(expected_sleep_calls, any_order=False)

    #    - test_handles_openai_bad_request_error_context_length_exceeded
    #    - test_handles_openai_bad_request_error_other
    #    - test_handles_openai_authentication_error
    #    - test_handles_generic_openai_api_error

    async def test_handles_openai_bad_request_error_context_length_exceeded(
        self, llm_service: LLMService, mock_candidate: CandidateProfile
    ):
        """
        Tests handling of BadRequestError specifically for context_length_exceeded.
        """
        # Arrange
        error_message = "Context length exceeded"
        # Simulate the structure of the error body OpenAI might return for this
        error_body = {
            "error": {
                "code": "context_length_exceeded",
                "message": "This model's maximum context length is X tokens...",
            }
        }
        mock_http_response = MagicMock()
        mock_http_response.status_code = 400  # Example status code

        llm_service.client.chat.completions.create.side_effect = BadRequestError(
            message=error_message,
            response=mock_http_response,  # Pass a mock HTTP response
            body=error_body,
        )

        job_details = {
            "job_role_title": "Context Test Role",
            "job_role_description": "Testing context length error",
            "tone": "concise",
            "company_context": None,
            "additional_instructions": None,
        }

        # Act & Assert
        expected_detail_match = (
            "Prompt combined with max_tokens exceeds the model's context window."
        )
        with pytest.raises(TextGenerationError, match=expected_detail_match):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate, **job_details
            )

        llm_service.client.chat.completions.create.assert_called_once()

    async def test_handles_openai_bad_request_error_other(
        self, llm_service: LLMService, mock_candidate: CandidateProfile
    ):
        """
        Tests handling of a generic BadRequestError (not context length related).
        """
        # Arrange
        original_error_message = "Some other bad request from OpenAI."
        mock_http_response = MagicMock()
        mock_http_response.status_code = 400

        llm_service.client.chat.completions.create.side_effect = BadRequestError(
            message=original_error_message,
            response=mock_http_response,
            body={
                "error": {
                    "message": original_error_message,
                    "type": "invalid_request_error",
                }
            },  # Example body
        )

        job_details = {
            "job_role_title": "Bad Req Role",
            "tone": "neutral",
        }  # Minimal details

        # Act & Assert
        expected_detail_match = f"Invalid request to OpenAI API for chat completion: {original_error_message}"
        with pytest.raises(TextGenerationError, match=expected_detail_match):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate,
                job_role_title=job_details["job_role_title"],
                job_role_description=None,  # Explicitly None
                tone=job_details["tone"],
                company_context=None,
                additional_instructions=None,
            )
        llm_service.client.chat.completions.create.assert_called_once()

    async def test_handles_openai_authentication_error(
        self, llm_service: LLMService, mock_candidate: CandidateProfile
    ):
        """
        Tests handling of AuthenticationError, expecting OpenAIConfigError.
        """
        # Arrange
        mock_http_response = MagicMock()
        mock_http_response.status_code = 401

        llm_service.client.chat.completions.create.side_effect = AuthenticationError(
            message="Invalid API Key", response=mock_http_response, body=None
        )

        job_details = {"job_role_title": "Auth Test Role", "tone": "neutral"}

        # Act & Assert
        with pytest.raises(
            OpenAIConfigError, match="OpenAI authentication failed. Check API key."
        ):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate,
                job_role_title=job_details["job_role_title"],
                job_role_description=None,
                tone=job_details["tone"],
                company_context=None,
                additional_instructions=None,
            )
        llm_service.client.chat.completions.create.assert_called_once()

    async def test_handles_generic_openai_api_error(
        self, llm_service: LLMService, mock_candidate: CandidateProfile
    ):
        """
        Tests handling of a generic APIError from OpenAI.
        """
        # Arrange
        original_error_message = "A generic API error occurred."
        # mock_http_response = MagicMock()
        # mock_http_response.status_code = 500  # Example status

        llm_service.client.chat.completions.create.side_effect = APIError(
            message=original_error_message, request=MagicMock(), body=None
        )

        job_details = {"job_role_title": "Generic API Error Role", "tone": "neutral"}

        # Act & Assert
        expected_detail_match = (
            f"OpenAI API service error for chat completion: {original_error_message}"
        )
        with pytest.raises(TextGenerationError, match=expected_detail_match):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate,
                job_role_title=job_details["job_role_title"],
                job_role_description=None,
                tone=job_details["tone"],
                company_context=None,
                additional_instructions=None,
            )
        llm_service.client.chat.completions.create.assert_called_once()

    #    - test_handles_text_generation_stopped_by_content_filter
    #    - test_handles_text_generation_stopped_by_length (check logger.warning)
    #    - test_raises_text_generation_error_on_empty_llm_response

    async def test_handles_text_generation_stopped_by_content_filter(
        self, llm_service: LLMService, mock_candidate: CandidateProfile
    ):
        """
        Tests that TextGenerationError is raised if OpenAI stops due to content filter.
        """
        # Arrange
        mock_openai_response = AsyncMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock(content=None)
        mock_openai_response.choices[0].finish_reason = "content_filter"
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        job_details = {"job_role_title": "Content Filter Test", "tone": "neutral"}

        # Act & Assert
        with pytest.raises(
            TextGenerationError,
            match="Generated content was flagged by OpenAI's content filter.",
        ):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate,
                job_role_title=job_details["job_role_title"],
                job_role_description=None,
                tone=job_details["tone"],
                company_context=None,
                additional_instructions=None,
            )
        llm_service.client.chat.completions.create.assert_called_once()

    @patch("backend.app.services.llm_service.logger", new_callable=MagicMock)
    async def test_handles_text_generation_stopped_by_length(
        self,
        mock_logger: MagicMock,
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
        mock_settings: MagicMock,
    ):
        """
        Tests that a warning is logged if OpenAI stops due to length (max_tokens).
        The method should still return the truncated content.
        """
        # Arrange
        partial_content = "This is partially generated text due to length..."
        mock_openai_response = AsyncMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock(content=partial_content)
        mock_openai_response.choices[0].finish_reason = "length"
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        job_details = {"job_role_title": "Length Stop Test", "tone": "neutral"}

        # Act
        result = await llm_service.generate_outreach_draft(
            candidate=mock_candidate,
            job_role_title=job_details["job_role_title"],
            job_role_description=None,
            tone=job_details["tone"],
            company_context=None,
            additional_instructions=None,
        )

        # Assert
        assert result == partial_content.strip()  # LLMService strips the result
        llm_service.client.chat.completions.create.assert_called_once()

        expected_log_message_part = (
            f"Text generation for candidate {mock_candidate.id} truncated due to max_tokens "
            f"({llm_service.default_chat_max_tokens})."
        )

        called_with_expected_message = False
        for call_args_list in mock_logger.warning.call_args_list:
            args, _ = call_args_list
            if args and expected_log_message_part in args[0]:
                called_with_expected_message = True
                break
        assert (
            called_with_expected_message
        ), f"Expected log warning containing '{expected_log_message_part}' was not found."

    @pytest.mark.parametrize("empty_content_value", [None, "", "   "])
    async def test_raises_text_generation_error_on_empty_llm_response(
        self,
        empty_content_value: Optional[str],
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
    ):
        """
        Tests that TextGenerationError is raised if OpenAI returns None, empty, or whitespace-only content.
        """
        # Arrange
        mock_openai_response = AsyncMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message = MagicMock(content=empty_content_value)
        mock_openai_response.choices[0].finish_reason = "stop"
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        job_details = {"job_role_title": "Empty Response Test", "tone": "neutral"}

        # Act & Assert
        with pytest.raises(
            TextGenerationError,
            match="LLM returned empty or whitespace-only content for outreach draft.",
        ):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate,
                job_role_title=job_details["job_role_title"],
                job_role_description=None,
                tone=job_details["tone"],
                company_context=None,
                additional_instructions=None,
            )
        llm_service.client.chat.completions.create.assert_called_once()

    # 4. Handling invalid/edge case inputs to the method itself
    #    - test_raises_value_error_if_candidate_is_none
    #    - test_raises_value_error_if_job_role_title_is_empty_or_whitespace

    async def test_raises_value_error_if_candidate_is_none(
        self, llm_service: LLMService
    ):
        """
        Tests that a ValueError is raised if the candidate object is None.
        """
        # Arrange
        job_details = {
            "job_role_title": "Test Role",
            "job_role_description": "A role.",
            "tone": "neutral",
            "company_context": None,
            "additional_instructions": None,
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="Candidate profile and job role title are required."
        ):
            await llm_service.generate_outreach_draft(
                candidate=None, **job_details  # Passing None for candidate
            )

        llm_service.client.chat.completions.create.assert_not_called()

    @pytest.mark.parametrize("empty_job_title", ["", "   "])
    async def test_raises_value_error_if_job_role_title_is_empty_or_whitespace(
        self,
        empty_job_title: str,
        llm_service: LLMService,
        mock_candidate: CandidateProfile,
    ):
        """
        Tests that a ValueError is raised if job_role_title is empty or whitespace.
        """
        # Arrange
        job_details = {
            "job_role_title": empty_job_title,
            "job_role_description": "A role.",
            "tone": "neutral",
            "company_context": None,
            "additional_instructions": None,
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="Candidate profile and job role title are required."
        ):
            await llm_service.generate_outreach_draft(
                candidate=mock_candidate, **job_details
            )

        llm_service.client.chat.completions.create.assert_not_called()
