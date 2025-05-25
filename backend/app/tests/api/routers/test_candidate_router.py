import pytest
from typing import List, Optional, Dict, Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
)  # Patch is not used directly in this draft but good to have for other tests

from fastapi.testclient import TestClient
from fastapi import status  # For HTTP status codes

# Import your FastAPI app instance
from backend.app.main import app

# Import services to mock and Pydantic models for response validation
from backend.app.services.llm_service import LLMService, LLMServiceError
from backend.app.services.rag_service import RAGService

# Assuming RAGService might raise its own specific SearchOperationError or a more general RAGServiceError
from backend.app.services.rag_service import (
    SearchOperationError as RAGSearchOperationError,
    RAGServiceError,
)

# Import actual Pydantic models from app.models.api_models
# If these are not yet created, these imports would fail.
# For this conceptual step, we assume they exist as defined in BE-2.
try:
    from backend.app.models.api_models import (
        QueryResponseItem,
        SearchResponse,
        ErrorResponse,
        OutreachRequest,
        OutreachResponse,
        CandidateProfile,
    )
except ImportError:
    # Fallback placeholders if app.models.api_models or its contents are not yet created
    # This is just for the test file to be syntactically plausible if models are pending
    from pydantic import BaseModel, Field

    class QueryResponseItem(BaseModel):
        id: str
        name: str
        match_context: str
        skills: List[str]
        visa_status: Optional[str] = None
        location: Optional[str] = None
        experience_years: Optional[int] = None
        relevance_score: Optional[float] = None
        github_url: Optional[str] = None
        linkedin_url: Optional[str] = None

    class SearchResponse(BaseModel):
        count: int
        results: List[QueryResponseItem]

    class ErrorResponse(BaseModel):
        detail: str


# --- Mocked Service Instances (Module Level) ---
# These will be used by the override functions and reset by setup_method
mock_llm_service_instance = AsyncMock(spec=LLMService)
mock_rag_service_instance = AsyncMock(spec=RAGService)


# --- Dependency Override Functions (Module Level) ---
# These functions will be used by FastAPI's dependency injection override mechanism
def override_get_llm_service():
    return mock_llm_service_instance


def override_get_rag_service():
    return mock_rag_service_instance


@pytest.fixture(autouse=True)
def auto_apply_router_mocks_fixture():
    """
    Autouse, function-scoped fixture to apply dependency overrides for router endpoints.
    Ensures that router endpoints use our mocked service instances for each test function.
    """
    # Import here to ensure it's the actual dependency function from the app
    from backend.app.dependencies import get_llm_service, get_rag_service

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_llm_service] = override_get_llm_service
    app.dependency_overrides[get_rag_service] = override_get_rag_service

    yield  # Test runs here

    # Teardown: Restore original overrides
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():  # Function-scoped client
    """
    Provides a TestClient instance for each test function.
    The autouse fixture 'auto_apply_router_mocks_fixture' ensures that when
    TestClient(app) is called, the app already has the necessary overrides
    for router dependencies.
    """
    with TestClient(app) as c:
        yield c


class TestCandidateRouterQueryEndpoint:

    def setup_method(self):
        """Reset module-level mocks before each test method."""
        mock_llm_service_instance.reset_mock()
        mock_rag_service_instance.reset_mock()

        # Set a default successful embedding for LLM service for most tests
        mock_llm_service_instance.get_embedding.return_value = [0.1] * 1536
        mock_llm_service_instance.get_embedding.side_effect = None

        # Clear side effect for RAG service's similarity_search
        mock_rag_service_instance.similarity_search.side_effect = None

    def test_successful_search_basic_query(
        self, client: TestClient
    ):  # Use the client fixture
        # Arrange
        mock_query_embedding = [0.1] * 1536  # Aligns with setup_method default
        # mock_llm_service_instance.get_embedding.return_value = mock_query_embedding # Already set by default

        mock_rag_results = [
            {
                "id": "c001",
                "document": "Resume text for Alex...",
                "metadata": {
                    "name": "Alex Chen",
                    "skills": "Python,FastAPI",
                    "visa_status": "H1B",
                    "location": "SF",
                    "experience_years": 5,
                    "github_url": None,
                    "linkedin_url": None,
                },
                "distance": 0.1,
            },
            {
                "id": "c002",
                "document": "Resume text for Maria...",
                "metadata": {
                    "name": "Maria R",
                    "skills": "Python,AI",
                    "visa_status": "GC",
                    "location": "Austin",
                    "experience_years": 6,
                    "github_url": None,
                    "linkedin_url": None,
                },
                "distance": 0.2,
            },
        ]
        mock_rag_service_instance.similarity_search.return_value = (mock_rag_results, 2)

        # Act
        response = client.get("/api/v1/query?q=python developer&limit=5")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        print("Actual /query response JSON:", data)
        assert "final_count_after_post_filter" in data
        assert data["final_count_after_post_filter"] == 2
        assert "results" in data
        assert len(data["results"]) == 2
        result1 = data["results"][0]
        assert result1["candidate"]["id"] == "c001"
        assert result1["candidate"]["name"] == "Alex Chen"
        assert result1["candidate"]["raw_resume_text"] == "Resume text for Alex..."
        assert result1["candidate"]["skills"] == ["Python", "FastAPI"]
        assert result1["relevance_score"] == 0.1

        mock_llm_service_instance.get_embedding.assert_called_once_with(
            text="python developer"
        )
        mock_rag_service_instance.similarity_search.assert_called_once_with(
            query_embedding=mock_query_embedding, k=5, filters=None
        )

    def test_search_with_all_metadata_filters(self, client: TestClient):
        # Arrange
        mock_query_embedding = [0.2] * 1536
        mock_llm_service_instance.get_embedding.return_value = mock_query_embedding
        mock_rag_service_instance.similarity_search.return_value = (
            [
                {
                    "id": "c003",
                    "document": "Java dev resume...",
                    "metadata": {
                        "name": "David K",
                        "skills": "Java,Spring",
                        "visa_status": "USC",
                        "location": "NYC",
                        "experience_years": 7,
                        "github_url": "https://gh.com/dk",
                        "linkedin_url": "https://li.com/dk",
                    },
                    "distance": 0.3,
                }
            ],
            1,
        )
        # Act
        response = client.get(
            "/api/v1/query?q=java engineer&limit=3&visa_status=USC&location=NYC&min_experience=5&skills=java,spring"
        )
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        SearchResponse(**data)  # Validate response structure
        assert data["final_count_after_post_filter"] == 1
        assert data["results"][0]["candidate"]["name"] == "David K"
        assert data["results"][0]["candidate"]["github_url"] == "https://gh.com/dk"

        mock_llm_service_instance.get_embedding.assert_called_once_with(
            text="java engineer"
        )
        # The filters passed to RAGService should include skills_query as a list
        expected_filters = {
            "visa_status": "USC",
            "location": "NYC",
            "experience_years": {"$gte": 5},
            "skills_query": ["java", "spring"],
        }
        mock_rag_service_instance.similarity_search.assert_called_once_with(
            query_embedding=mock_query_embedding, k=3, filters=expected_filters
        )

    def test_search_query_param_validation_q_missing(self, client: TestClient):
        response = client.get("/api/v1/query")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any(
            err.get("type") == "missing" and err.get("loc") == ["query", "q"]
            for err in data["detail"]
        )

    def test_search_query_param_validation_q_too_short_if_min_length_is_set(
        self, client: TestClient
    ):
        # This test depends on Pydantic model validation for 'q' in the endpoint
        # Assuming min_length=3 for 'q' as per a common requirement
        response = client.get("/api/v1/query?q=hi")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any(
            err.get("type") == "string_too_short" and err.get("loc") == ["query", "q"]
            for err in data["detail"]
        )

    def test_search_query_param_validation_limit_invalid(self, client: TestClient):
        response_low = client.get("/api/v1/query?q=test&limit=0")  # limit < 1
        assert response_low.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data_low = response_low.json()
        assert "detail" in data_low
        assert isinstance(data_low["detail"], list)
        assert any(
            err.get("type") == "greater_than_equal"
            and err.get("loc") == ["query", "limit"]
            for err in data_low["detail"]
        )

        response_high = client.get(
            "/api/v1/query?q=test&limit=101"
        )  # limit > 50 (assuming max_limit=50)
        assert response_high.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data_high = response_high.json()
        assert "detail" in data_high
        assert isinstance(data_high["detail"], list)
        assert any(
            err.get("type") == "less_than_equal"
            and err.get("loc") == ["query", "limit"]
            for err in data_high["detail"]
        )

    def test_llm_service_get_embedding_raises_llm_service_error(
        self, client: TestClient
    ):
        # Arrange
        error_message = "Simulated LLM Service Error for embedding"
        mock_llm_service_instance.get_embedding.side_effect = LLMServiceError(
            error_message
        )

        # Act
        response = client.get("/api/v1/query?q=somequery")

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data
        ErrorResponse(**data["detail"])
        assert "Could not generate query embedding" in data["detail"]["message"]
        assert error_message in data["detail"]["message"]

    def test_llm_service_get_embedding_raises_value_error(self, client: TestClient):
        # Arrange
        error_message = "Empty query text provided to LLM embedding"
        mock_llm_service_instance.get_embedding.side_effect = ValueError(error_message)

        # Act
        # q is valid at API level, but service raises ValueError
        response = client.get("/api/v1/query?q=validapiquery")

        # Assert
        # The router should catch this ValueError from the service and return a 400 or 500
        # Based on BE-7 plan, it should be a 400 for ValueError from LLMService
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        ErrorResponse(**data["detail"])
        assert "Invalid query" in data["detail"]["message"]
        assert error_message in data["detail"]["message"]

    def test_rag_service_similarity_search_raises_rag_search_error(
        self, client: TestClient
    ):
        # Arrange
        mock_llm_service_instance.get_embedding.return_value = [0.1] * 1536
        mock_llm_service_instance.get_embedding.side_effect = None
        error_message = "Simulated RAG Search Error"
        mock_rag_service_instance.similarity_search.side_effect = (
            RAGSearchOperationError(error_message)
        )

        # Act
        response = client.get("/api/v1/query?q=somequery")

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data
        ErrorResponse(**data["detail"])
        assert "Candidate search failed" in data["detail"]["message"]
        assert error_message in data["detail"]["message"]

    def test_rag_service_similarity_search_raises_generic_rag_service_error(
        self, client: TestClient
    ):
        # Arrange
        mock_llm_service_instance.get_embedding.return_value = [0.1] * 1536
        mock_llm_service_instance.get_embedding.side_effect = None
        error_message = "Generic RAG Service Error"
        mock_rag_service_instance.similarity_search.side_effect = RAGServiceError(
            error_message
        )

        # Act
        response = client.get("/api/v1/query?q=somequery")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        ErrorResponse(**data["detail"])
        assert (
            "An internal error occurred with the RAG service during search"
            in data["detail"]["message"]
        )

    def test_rag_service_returns_empty_list(self, client: TestClient):
        # Arrange
        mock_llm_service_instance.get_embedding.return_value = [0.1] * 1536
        mock_llm_service_instance.get_embedding.side_effect = None
        mock_rag_service_instance.similarity_search.side_effect = None
        mock_rag_service_instance.similarity_search.return_value = (
            [],
            0,
        )  # Empty results, count 0

        # Act
        response = client.get("/api/v1/query?q=obscurequery")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        SearchResponse(**data)  # Validate response structure
        assert data["final_count_after_post_filter"] == 0
        assert data["results"] == []

    def test_skills_parameter_parsing_and_passing_to_rag_service(
        self, client: TestClient
    ):
        # Arrange
        mock_query_embedding = [0.3] * 1536
        mock_llm_service_instance.get_embedding.return_value = mock_query_embedding
        mock_rag_service_instance.similarity_search.return_value = ([], 0)

        # Act: skills with spaces and varied casing
        client.get("/api/v1/query?q=dev&skills=Python, react , Java, data science")

        # Assert
        mock_rag_service_instance.similarity_search.assert_called_once()
        call_args_list = mock_rag_service_instance.similarity_search.call_args_list
        # In Python 3.8+ call_args is a Call object, not a tuple. Use .kwargs
        # For older versions, it might be call_args[1] for kwargs

        # Check the 'filters' argument specifically
        called_filters = call_args_list[0].kwargs.get("filters")

        assert called_filters is not None
        assert "skills_query" in called_filters
        # Router should lowercase and strip whitespace from skills
        assert called_filters["skills_query"] == [
            "python",
            "react",
            "java",
            "data science",
        ]

    def test_relevance_score_calculation_or_passthrough(self, client: TestClient):
        # Arrange
        mock_query_embedding = [0.1] * 1536
        mock_llm_service_instance.get_embedding.return_value = mock_query_embedding
        mock_llm_service_instance.get_embedding.side_effect = None
        mock_rag_service_instance.similarity_search.side_effect = None

        # RAGService returns distances. Router is expected to map this to relevance_score.
        # For ChromaDB, smaller distance is better. A common way to convert to score is 1 - distance (if distance is 0-1)
        # Or simply pass distance if that's what frontend expects as "score".
        # Based on BE-7 plan, relevance_score is from distance. Let's assume direct mapping for now.
        mock_rag_results = [
            {
                "id": "c001",
                "document": "Doc1",
                "metadata": {"name": "N1", "skills": "S1"},
                "distance": 0.123,
            },
            {
                "id": "c002",
                "document": "Doc2",
                "metadata": {"name": "N2", "skills": "S2"},
                "distance": 0.456,
            },
        ]
        mock_rag_service_instance.similarity_search.return_value = (mock_rag_results, 2)

        # Act
        response = client.get("/api/v1/query?q=test")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        SearchResponse(**data)
        assert data["results"][0]["relevance_score"] == 0.123
        assert data["results"][1]["relevance_score"] == 0.456

    def test_example_query_placeholder(self, client: TestClient):
        # Arrange
        mock_query_embedding = [0.1] * 1536
        mock_llm_service_instance.get_embedding.return_value = mock_query_embedding
        mock_rag_service_instance.similarity_search.return_value = (
            [
                {
                    "id": "c001",
                    "document": "Resume text for Alex...",
                    "metadata": {
                        "name": "Alex Chen",
                        "skills": "Python,FastAPI",
                    },
                    "distance": 0.1,
                }
            ],
            1,
        )
        response = client.get("/api/v1/query?q=python")
        assert response.status_code == 200


class TestCandidateRouterGenerateOutreach:
    """Tests for the /candidates/{candidate_id}/generate-outreach endpoint."""

    def test_generate_outreach_success(self, client: TestClient):
        """Test successful outreach generation for a valid candidate and request."""
        candidate_id = "c001"  # Confirmed valid ID
        request_payload = OutreachRequest(
            job_role_title="Senior AI Developer",
            job_role_description="Develop and deploy cutting-edge AI solutions for enterprise clients. Lead a team of junior developers.",
            tone="enthusiastic and professional",
            company_context="A forward-thinking technology company leading innovation in the AI space. We value collaboration and continuous learning.",
            additional_instructions="Please emphasize their experience with cloud platforms.",
        )
        # Set up the mock to return a real CandidateProfile instance
        mock_rag_service_instance.get_candidate_details_by_id.return_value = (
            CandidateProfile(
                id="c001",
                name="Alex Chen",
                raw_resume_text="ALEX CHEN\nSoftware Engineer...",
                skills=["Python", "React", "PostgreSQL", "Docker"],
                experience_years=5,
                visa_status="H1B",
                location="San Francisco, CA",
                github_url="https://github.com/alexchen",
                linkedin_url="https://linkedin.com/in/alex-chen-dev",
            )
        )
        # Set up the mock to return a string for the outreach draft
        mock_llm_service_instance.generate_outreach_draft.return_value = (
            "Test outreach draft message"
        )

        response = client.post(
            f"/api/v1/candidates/{candidate_id}/generate-outreach",
            json=request_payload.model_dump(),
        )
        data = response.json()
        # Assert only on actual keys present in the response
        assert response.status_code == 200
        assert "draft_message" in data
        assert data["draft_message"] == "Test outreach draft message"
        assert data["candidate_name"] == "Alex Chen"
        assert data["candidate_id"] == candidate_id
        assert data["job_role_title"] == request_payload.job_role_title
        assert "generated_at" in data
        assert "generation_time_ms" in data
        assert "word_count" in data
        assert "character_count" in data
        assert data["tone_used"] == request_payload.tone
        assert isinstance(data["personalization_elements"], list)
        assert "confidence_score" in data

    def test_generate_outreach_candidate_not_found(self, client: TestClient):
        """Test outreach generation for a non-existent candidate ID."""
        candidate_id = "non_existent_candidate_id_123"
        request_payload = OutreachRequest(
            job_role_title="Test Role",
            job_role_description="Test Description",
            tone="formal",
        )
        # Set up the mock to raise ValueError as the real service would
        mock_rag_service_instance.get_candidate_details_by_id.side_effect = ValueError(
            f"Candidate with ID '{candidate_id}' not found."
        )

        response = client.post(
            f"/api/v1/candidates/{candidate_id}/generate-outreach",
            json=request_payload.model_dump(),
        )

        assert (
            response.status_code == 404
        ), f"Expected 404 Not Found, got {response.status_code}. Response: {response.text}"
        response_data = response.json()
        # Check inside 'detail' for error info
        assert "detail" in response_data
        detail = response_data["detail"]
        assert "error" in detail
        assert detail["error"] == "NotFoundError"
        assert "message" in detail
        assert candidate_id in detail["message"]

    def test_generate_outreach_invalid_request_payload(self, client: TestClient):
        """Test outreach generation with an invalid request payload (e.g., missing required fields)."""
        candidate_id = "c001"
        invalid_payload = {
            # Missing job_role_title, which is required by OutreachRequest
            "job_role_description": "A test description",
            "tone": "casual",
        }

        response = client.post(
            f"/api/v1/candidates/{candidate_id}/generate-outreach", json=invalid_payload
        )

        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.status_code}. Response: {response.text}"
        response_data = response.json()
        assert (
            "detail" in response_data
        )  # FastAPI validation errors are in response_data["detail"]
        # Check for a message indicating job_role_title is missing
        found_job_title_error = False
        for error in response_data.get("detail", []):
            if error.get("type") == "missing" and "job_role_title" in error.get(
                "loc", []
            ):
                found_job_title_error = True
                break
        assert (
            found_job_title_error
        ), "Error detail should indicate job_role_title is missing."

    # Consider adding a test for when the LLMService itself fails (e.g., OpenAI API key issue).
    # This would require mocking the llm_service.generate_outreach_draft to raise an LLMServiceError.
    # For an integration test, this might be complex if you don't want to actually hit OpenAI during tests.
    # A unit test for the router logic with a mocked service would be more appropriate for that.
    # For now, focusing on successful path and basic input validations.


# To run these tests, navigate to your project's root directory in the terminal and run:
# pytest backend/app/tests/api/routers/test_candidate_router.py
# Ensure you have pytest and httpx (TestClient dependency) installed in your environment.
# (e.g., pip install pytest httpx)
