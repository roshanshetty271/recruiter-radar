import logging
from typing import List, Optional, Dict, Any
import time  # For search_time_ms
import datetime  # For error timestamp

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path, Body

# Import the official Pydantic models
from backend.app.models.api_models import (
    QueryResponseItem,
    SearchResponse,
    ErrorResponse,
    CandidateProfile,  # For constructing the nested candidate object
    OutreachRequest,  # Added for new endpoint
    OutreachResponse,  # Added for new endpoint
)

from backend.app.services.llm_service import (
    LLMService,
    LLMServiceError,
    TextGenerationError,  # Assuming this is defined in llm_service
    OpenAIConfigError,  # Assuming this is defined in llm_service
)
from backend.app.services.rag_service import (
    RAGService,
    SearchOperationError,
    RAGServiceError,
)
from backend.app.dependencies import get_llm_service, get_rag_service

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid request parameters or body",
        },
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service temporarily unavailable"},
    },
)


@router.get(
    "/query",
    response_model=SearchResponse,
    summary="Search candidates using AI and keyword filters",
    description="""
Search for candidates using natural language queries powered by semantic search, combined with precise metadata filters.

The search engine understands context and meaning, not just keywords. For example:
- "Python developers who've worked with AI and live in California"
- "Senior full-stack engineers with cloud platform experience, preferably AWS or GCP"
- "Software engineers with a background in fintech, open to remote work"

**Supported Filters**:
- `limit`: Number of results (default 10, max 50).
- `visa_status`: e.g., "US Citizen", "H1B", "Green Card".
- `location`: e.g., "San Francisco, CA", "Remote".
- `min_experience`: Minimum years of experience (integer).
- `skills`: Comma-separated list of required skills (e.g., "Python,FastAPI,Docker").

**Response includes**:
- Ranked list of candidates.
- Relevance scores and context snippets.
- Search performance metrics.
    """,
    response_description="A list of matching candidate profiles ranked by relevance, along with search metadata.",
    responses={
        200: {
            "description": "Search executed successfully. Returns a list of candidates.",
            "model": SearchResponse,
        },
        400: {
            "description": "Invalid query parameters provided.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "invalid_query_parameter",
                        "message": "Query parameter 'q' must be at least 3 characters long.",
                        "details": {"parameter": "q", "value": "AI"},
                        "request_id": "req_123xyz",
                    }
                }
            },
        },
    },
    operation_id="searchCandidatesV1",
)
async def search_candidates(
    q: str = Query(
        ...,
        min_length=3,
        max_length=200,
        description="Natural language query string (e.g., 'Python developers with AI experience')",
        example="Python developers with AI experience",
    ),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of results to return (1-50)"
    ),
    visa_status: Optional[str] = Query(
        None,
        description="Filter by candidate's visa status (e.g., 'US Citizen', 'H1B')",
        example="US Citizen",
    ),
    location: Optional[str] = Query(
        None,
        description="Filter by candidate's location (e.g., 'San Francisco, CA', 'Remote')",
        example="San Francisco",
    ),
    min_experience: Optional[int] = Query(
        None,
        ge=0,
        le=50,
        description="Minimum years of professional experience required",
    ),
    skills: Optional[str] = Query(
        None,
        description="Comma-separated list of required skills (e.g., 'Python,FastAPI,Docker')",
        example="Python,FastAPI,Docker",
    ),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    **Search for Candidates using Natural Language and Filters**

    This endpoint allows for powerful semantic search across candidate profiles,
    enhanced by specific filters for skills, experience, location, and visa status.

    - **Query (`q`)**: Your primary search term. Be descriptive!
        - _Example_: "Show me senior software engineers in New York with Java and Spring Boot experience who have worked on financial trading systems."
    - **Limit (`limit`)**: Controls pagination.
        - _Default_: 10
    - **Filters**: Apply these to narrow down results precisely.
        - `skills`: "Java,Spring Boot,Microservices"
        - `location`: "New York, NY"
        - `min_experience`: 5
        - `visa_status`: "Green Card"

    The API will return a ranked list of candidates, including snippets from their resume
    that match your query (match_context) and a relevance_score (0.0 to 1.0).
    """

    # Start timing for metrics
    search_start_time = time.time()

    try:
        # Step 1: Generate embedding for the query
        logger.info(
            f"Processing search query: '{q}' with limit={limit}, filters: {{visa_status:'{visa_status}', location:'{location}', min_experience:{min_experience}, skills:'{skills}'}}"
        )
        query_embedding = await llm_service.get_embedding(q)

        # Step 2: Parse skills filter if provided
        skills_list = None
        if skills:
            skills_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
            logger.debug(f"Parsed skills filter: {skills_list}")

        # Step 3: Build metadata filters for ChromaDB
        metadata_filters = {}
        if visa_status:
            metadata_filters["visa_status"] = visa_status
        if location:
            metadata_filters["location"] = location
        if min_experience is not None:
            metadata_filters["experience_years"] = {"$gte": min_experience}
        if skills_list:
            metadata_filters["skills_query"] = skills_list

        # Step 4: Perform similarity search
        # RAGService.similarity_search is expected to return a tuple:
        # (list_of_candidate_data_dicts, count_before_post_filter)
        raw_results_tuples, count_before_filter = await rag_service.similarity_search(
            query_embedding=query_embedding,
            k=limit,  # The RAG service will handle fetching more if needed for post-filtering
            filters=metadata_filters,
        )

        # Step 5: Transform results to API response format
        candidates = []
        for result_dict in raw_results_tuples:
            # Extract metadata
            metadata = result_dict.get("metadata", {})

            # Calculate relevance score from distance (ChromaDB returns smaller distances for better matches)
            distance = result_dict.get(
                "distance", 1.0
            )  # Default to 1.0 (0 relevance) if not present
            relevance_score = max(
                0.0, 1.0 - float(distance)
            )  # Ensure float conversion and 0-1 range

            # Parse skills from comma-separated string in metadata
            skills_str = metadata.get("skills", "")
            candidate_skills_list = (
                [s.strip() for s in skills_str.split(",") if s.strip()]
                if isinstance(skills_str, str)
                else []
            )

            candidates.append(
                QueryResponseItem(
                    id=str(result_dict.get("id", "")),  # Ensure ID is string
                    name=str(metadata.get("name", "Unknown")),  # Ensure name is string
                    skills=candidate_skills_list,
                    experience_years=int(
                        metadata.get("experience_years", 0)
                    ),  # Ensure int
                    location=str(
                        metadata.get("location", "Not specified")
                    ),  # Ensure string
                    visa_status=str(
                        metadata.get("visa_status", "Not specified")
                    ),  # Ensure string
                    match_context=str(
                        result_dict.get("document", "")
                    ),  # raw_resume_text from ChromaDB
                    relevance_score=relevance_score,  # Already validated by QueryResponseItem
                    github_url=metadata.get("github_url"),  # Already optional str
                    linkedin_url=metadata.get("linkedin_url"),  # Already optional str
                )
            )

        # Calculate search time
        search_time_ms = (time.time() - search_start_time) * 1000

        # Build response with enhanced metadata
        response = SearchResponse(
            results=candidates,
            total_results=len(
                candidates
            ),  # This should be final_count_after_post_filter from RAG if available
            # For now, it's just the length of the processed list
            search_time_ms=round(search_time_ms, 2),
            # Future enhancements - set to None for MVP
            query_interpretation=f"Searched for: '{q}' with filters: {metadata_filters if metadata_filters else 'None'}",
            suggested_filters=None,  # TODO: Add smart filter suggestions
            search_metadata={"retrieved_before_filter": count_before_filter},
        )

        logger.info(
            f"Search completed: {len(candidates)} results in {search_time_ms:.2f}ms. Count before filter: {count_before_filter}"
        )
        return response

    except ValueError as e:
        # Handle LLMService ValueError (e.g., empty query after processing)
        logger.warning(f"Invalid query value: {str(e)} for query: '{q}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="invalid_query_value", message=str(e), details={"query": q}
            ).model_dump(exclude_none=True),
        )
    except LLMServiceError as e:
        logger.error(
            f"LLMService error during search for query '{q}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="llm_service_error",
                message="AI embedding service temporarily unavailable.",
                details={"service_issue": str(e)},
            ).model_dump(exclude_none=True),
        )
    except SearchOperationError as e:
        logger.error(
            f"SearchOperationError during search for query '{q}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="search_service_error",
                message="Candidate search service temporarily unavailable.",
                details={"operation_issue": str(e)},
            ).model_dump(exclude_none=True),
        )
    except Exception as e:
        logger.error(
            f"Unexpected search error for query '{q}': {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_search_error",
                message="An unexpected error occurred during candidate search.",
                request_id=f"req_{int(time.time())}",
            ).model_dump(exclude_none=True),
        )


@router.post(
    "/{candidate_id}/generate-outreach",
    response_model=OutreachResponse,
    summary="Generate AI-Personalized Outreach Message",
    description="""
Craft a highly personalized recruitment message for a specific candidate using advanced AI.

Our AI analyzes the candidate's professional background, skills, and experience against
the provided job role details to generate a compelling and engaging outreach message.
This helps in significantly increasing response rates.

**Provide:**
- `candidate_id`: The unique ID of the target candidate.
- `job_role_title`: Title of the position.
- `job_role_description` (Optional): Detailed description for better personalization.
- `tone` (Optional): Desired tone (e.g., "professional and friendly", "enthusiastic and direct").
- `company_context` (Optional): Brief info about your company culture.
- `additional_instructions` (Optional): Specific points to emphasize.

**Note**: The ability to request multiple message variations with different tones is planned for v1.1!
    """,
    response_description="The generated personalized outreach message along with metadata.",
    responses={
        200: {
            "description": "Outreach message generated successfully.",
            "model": OutreachResponse,
        },
        404: {
            "description": "The specified candidate ID was not found.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "candidate_not_found",
                        "message": "Candidate with ID 'candidate_abc_123' not found.",
                        "details": {"candidate_id": "candidate_abc_123"},
                        "request_id": "req_456uvw",
                    }
                }
            },
        },
        400: {
            "description": "Invalid request data provided for outreach generation.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "invalid_outreach_request",
                        "message": "Job role title cannot be empty.",
                        "details": {"field": "job_role_title"},
                        "request_id": "req_789def",
                    }
                }
            },
        },
    },
    operation_id="generateCandidateOutreachV1",
)
async def generate_outreach(
    *,
    candidate_id: str = Path(
        ...,
        min_length=1,
        description="Unique identifier of the candidate for whom to generate outreach.",
        example="candidate_001_dev_python_senior",
    ),
    request: OutreachRequest,
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    **Generate AI-Personalized Outreach Message for a Candidate**

    Takes a `candidate_id` and an `OutreachRequest` body to produce a tailored
    message using an LLM, enriched with the candidate's profile details.

    - **`candidate_id`**: Path parameter, the ID of the candidate.
    - **Request Body (`OutreachRequest`)**:
        - `job_role_title` (required): "Senior Software Engineer"
        - `job_role_description`: "Seeking a skilled engineer to lead..."
        - `tone`: "professional and direct"
        - `company_context`: "We are a fast-paced Series C startup..."
        - `additional_instructions`: "Highlight their experience with microservices."

    The response includes the `draft_message`, metrics like `word_count`, `generation_time_ms`,
    and `personalization_elements` identified by the AI.
    """

    generation_start_time = time.time()

    try:
        # Step 1: Retrieve candidate details
        logger.info(
            f"Generating outreach for candidate: {candidate_id}, Job: '{request.job_role_title}', Tone: '{request.tone}'"
        )
        candidate = await rag_service.get_candidate_details_by_id(candidate_id)

        if not candidate:
            logger.warning(
                f"Candidate with ID '{candidate_id}' not found for outreach generation."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="candidate_not_found",
                    message=f"Candidate with ID '{candidate_id}' not found.",
                    details={"candidate_id": candidate_id},
                ).model_dump(exclude_none=True),
            )

        # Step 2: Log if variations requested (future feature)
        if request.generate_variations:
            logger.info(
                "Variations requested but not yet implemented for candidate ID {candidate_id}. "
                "Generating single draft with requested tone: {request.tone}."
            )

        # Step 3: Generate outreach draft (MVP: single draft only)
        draft = await llm_service.generate_outreach_draft(
            candidate=candidate,
            job_role_title=request.job_role_title,
            job_role_description=request.job_role_description,
            tone=request.tone,
            company_context=request.company_context,
            additional_instructions=request.additional_instructions,
        )

        # Step 4: Calculate metrics
        word_count = len(draft.split())
        character_count = len(draft)
        generation_time_ms = (time.time() - generation_start_time) * 1000

        # Step 5: Extract personalization elements (simple implementation for MVP)
        personalization_elements = []

        # Check for years of experience mention
        if str(candidate.experience_years) in draft:
            personalization_elements.append(
                f"{candidate.experience_years} years experience"
            )

        # Check for skills mentioned
        mentioned_skills = [
            skill for skill in candidate.skills if skill.lower() in draft.lower()
        ]
        if mentioned_skills:
            personalization_elements.extend(
                [f"{skill} expertise" for skill in mentioned_skills[:2]]
            )

        # Check for location mention
        if candidate.location and candidate.location.lower() in draft.lower():
            personalization_elements.append(f"Based in {candidate.location}")

        # Step 6: Build response (with future-ready fields)
        response = OutreachResponse(
            draft_message=draft,
            candidate_name=candidate.name,
            candidate_id=candidate_id,
            job_role_title=request.job_role_title,
            generated_at=datetime.utcnow(),
            generation_time_ms=round(generation_time_ms, 2),
            word_count=word_count,
            character_count=character_count,
            tone_used=request.tone,
            personalization_elements=(
                personalization_elements if personalization_elements else None
            ),
            variations=None,  # Will be populated in v1.1 with BE-11
            total_variations_generated=1,
            recommended_variation_index=None,
        )

        logger.info(
            f"Outreach generated for {candidate_id}: {word_count} words in {generation_time_ms:.2f}ms. Tone: {request.tone}"
        )

        # Log performance metrics for monitoring
        if generation_time_ms > 2000:
            logger.warning(
                f"Potentially slow outreach generation: {generation_time_ms:.2f}ms for candidate {candidate_id}, job '{request.job_role_title}'"
            )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except (TextGenerationError, LLMServiceError) as e:
        logger.error(
            f"LLM service error during outreach for {candidate_id}, job '{request.job_role_title}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="llm_service_error",
                message="AI text generation service temporarily unavailable.",
                details={"service_issue": str(e)},
            ).model_dump(exclude_none=True),
        )
    except RAGServiceError as e:
        logger.error(
            f"RAGService error during outreach for {candidate_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="data_access_error",
                message="Error accessing candidate data for outreach.",
                details={"service_issue": str(e)},
            ).model_dump(exclude_none=True),
        )
    except Exception as e:
        logger.error(
            f"Unexpected error generating outreach for {candidate_id}, job '{request.job_role_title}': {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_outreach_error",
                message="An unexpected error occurred while generating the outreach message.",
                request_id=f"req_{int(time.time())}",
            ).model_dump(exclude_none=True),
        )
