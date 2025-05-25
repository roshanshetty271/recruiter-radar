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
router = APIRouter()


@router.get(
    "/query",
    response_model=SearchResponse,  # Uses the imported SearchResponse
    summary="Search for candidates using natural language and optional filters",
    tags=["Candidates"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
        400: {"model": ErrorResponse, "description": "Bad request"},
    },
)
async def query_candidates(
    q: str = Query(
        ..., min_length=3, max_length=300, description="Natural language search query"
    ),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
    visa_status: Optional[str] = Query(None, description="Filter by visa status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    min_experience: Optional[int] = Query(
        None, ge=0, le=50, description="Minimum years of experience"
    ),
    skills: Optional[str] = Query(
        None, description='Comma-separated skills to filter by (e.g., "python,fastapi")'
    ),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    Search for candidate profiles based on a natural language query and various filters.

    Returns a list of matching candidates with relevance scores, search metadata,
    and performance insights.
    """
    start_time = time.time()  # Start timer
    request_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(
        f"Received search query: '{q}' with limit: {limit}, filters: visa='{visa_status}', loc='{location}', exp>='{min_experience}', skills='{skills}'"
    )

    # Prepare filters_applied for response and metadata_filters_for_rag for RAG service
    current_filters_applied: Dict[str, Any] = {}
    metadata_filters_for_rag: Dict[str, Any] = {}
    original_query_terms_list: List[str] = list(
        set(q.lower().split())
    )  # Basic extraction from query

    if visa_status:
        current_filters_applied["visa_status"] = visa_status
        metadata_filters_for_rag["visa_status"] = visa_status
    if location:
        current_filters_applied["location"] = location
        metadata_filters_for_rag["location"] = location
    if min_experience is not None:
        current_filters_applied["min_experience"] = min_experience
        metadata_filters_for_rag["experience_years"] = {"$gte": min_experience}

    parsed_skills_query: Optional[List[str]] = None
    if skills:
        parsed_skills_query = [
            s.strip().lower() for s in skills.split(",") if s.strip()
        ]
        if parsed_skills_query:
            current_filters_applied["skills_query"] = parsed_skills_query
            metadata_filters_for_rag["skills_query"] = parsed_skills_query
            original_query_terms_list.extend(parsed_skills_query)
            original_query_terms_list = list(
                set(original_query_terms_list)
            )  # Deduplicate

    try:
        query_embedding = await llm_service.get_embedding(text=q)
    except LLMServiceError as e:
        logger.error(f"LLMService error during query embedding: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="LLMServiceError",
                message=f"Could not generate query embedding: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )
    except ValueError as e:  # From LLM service if text is invalid
        logger.warning(f"Invalid query text for embedding: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="InvalidQueryInput",
                message=f"Invalid query input: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )

    try:
        retrieved_candidates_data, count_before_post_filter = (
            await rag_service.similarity_search(
                query_embedding=query_embedding,
                k=limit,
                filters=metadata_filters_for_rag if metadata_filters_for_rag else None,
            )
        )
    except SearchOperationError as e:
        logger.error(f"RAGService search operation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="SearchOperationError",
                message=f"Candidate search failed during operation: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )
    except RAGServiceError as e:
        logger.error(f"General RAGService error during search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="RAGServiceSearchError",
                message=f"An internal error occurred with the RAG service during search: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )
    except ValueError as e:  # From RAG service if inputs are invalid
        logger.error(
            f"ValueError during RAGService search processing: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="SearchInputError",
                message=f"Invalid input for search processing: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )

    response_items: List[QueryResponseItem] = []
    for cand_data in retrieved_candidates_data:
        try:
            meta = cand_data.get("metadata", {})
            skills_str = meta.get("skills", "")
            skills_list = (
                [s.strip() for s in skills_str.split(",") if s.strip()]
                if isinstance(skills_str, str)
                else []
            )

            raw_resume_for_context = str(cand_data.get("document", ""))

            candidate_profile_data = {
                "id": str(cand_data.get("id")),
                "name": str(meta.get("name", "N/A")),
                "raw_resume_text": raw_resume_for_context,
                "skills": skills_list,
                "experience_years": int(meta.get("experience_years", 0)),
                "visa_status": meta.get("visa_status"),
                "location": meta.get("location"),
                "github_url": meta.get("github_url"),
                "linkedin_url": meta.get("linkedin_url"),
                # Ensure all required fields of CandidateProfile are present
            }
            # Filter out None values only for optional fields of CandidateProfile
            candidate_profile_data_cleaned = {
                k: v for k, v in candidate_profile_data.items() if v is not None
            }
            # Ensure required fields that might have been Nulled out (like name if N/A was used) are re-added if Pydantic needs them
            # This part needs care based on CandidateProfile definition
            # For MVP, assuming meta fields are generally present or defaults are acceptable.
            if (
                "name" not in candidate_profile_data_cleaned
                and "name" in candidate_profile_data
            ):
                candidate_profile_data_cleaned["name"] = candidate_profile_data[
                    "name"
                ]  # Keep 'N/A' if that's the default
            if (
                "experience_years" not in candidate_profile_data_cleaned
                and "experience_years" in candidate_profile_data
            ):
                candidate_profile_data_cleaned["experience_years"] = (
                    candidate_profile_data["experience_years"]
                )  # Keep 0 default
            if (
                "raw_resume_text" not in candidate_profile_data_cleaned
                and "raw_resume_text" in candidate_profile_data
            ):
                candidate_profile_data_cleaned["raw_resume_text"] = (
                    candidate_profile_data["raw_resume_text"]
                )  # Keep "" default
            if (
                "id" not in candidate_profile_data_cleaned
                and "id" in candidate_profile_data
            ):
                candidate_profile_data_cleaned["id"] = candidate_profile_data["id"]
            if (
                "skills" not in candidate_profile_data_cleaned
                and "skills" in candidate_profile_data
            ):
                candidate_profile_data_cleaned["skills"] = candidate_profile_data[
                    "skills"
                ]

            candidate_profile = CandidateProfile(**candidate_profile_data_cleaned)

            response_items.append(
                QueryResponseItem(
                    candidate=candidate_profile,
                    relevance_score=round(
                        cand_data.get("distance", 0.0), 4
                    ),  # Chroma gives distance, closer to 0 is better. Assuming score is 1-distance or similar transformation if needed by frontend. For now, pass distance.
                    match_context=raw_resume_for_context,  # Populating match_context
                )
            )
        except Exception as e:
            logger.error(
                f"Error mapping candidate data (ID: {cand_data.get('id')}) to QueryResponseItem: {e}",
                exc_info=True,
            )
            # Optionally, skip this candidate and continue, or re-raise if critical

    processing_time_ms = (time.time() - start_time) * 1000

    # Construct query interpretation notes
    interpretation_parts = [f"Searched for: '{q}'"]
    if parsed_skills_query:
        interpretation_parts.append(
            f"Filtered by skills: {', '.join(parsed_skills_query)}"
        )
    if location:
        interpretation_parts.append(f"Location: {location}")
    if visa_status:
        interpretation_parts.append(f"Visa Status: {visa_status}")
    if min_experience is not None:
        interpretation_parts.append(f"Min Experience: {min_experience} years")
    query_interpretation_str = ". ".join(interpretation_parts) + "."

    final_results_count = len(response_items)

    logger.info(
        f"Search successful. Before post-filter: {count_before_post_filter}. After post-filter & k-limit: {final_results_count}. Time: {processing_time_ms:.2f}ms."
    )
    return SearchResponse(
        query=q,
        original_query_terms=(
            original_query_terms_list if original_query_terms_list else None
        ),
        results=response_items,
        retrieved_count_before_post_filter=count_before_post_filter,
        final_count_after_post_filter=final_results_count,
        processing_time_ms=round(processing_time_ms, 2),
        query_interpretation_notes=query_interpretation_str,
        filters_applied=current_filters_applied if current_filters_applied else None,
        # suggestions=["Try adding a location filter?", "Broaden your skill search?"] # Example suggestions
    )


@router.post(
    "/candidates/{candidate_id}/generate-outreach",
    response_model=OutreachResponse,
    summary="Generate AI-powered personalized outreach message",
    description="Generate a personalized outreach message for a specific candidate using AI. "
    "The message will be tailored based on the candidate's profile and the job requirements.",
    tags=["Candidates", "AI Generation"],
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Candidate not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NotFoundError",
                        "message": "Candidate with ID 'xyz' not found",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        422: {"model": ErrorResponse, "description": "Invalid request data"},
        503: {
            "model": ErrorResponse,
            "description": "AI service temporarily unavailable",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def generate_outreach(
    candidate_id: str = Path(
        ...,
        min_length=1,
        max_length=100,
        description="Unique identifier of the candidate",
        example="candidate_001",
    ),
    request: OutreachRequest = Body(...),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> OutreachResponse:
    """
    Generate a personalized outreach message for a candidate.

    This endpoint combines candidate profile data with job requirements to create
    a compelling, personalized outreach message using AI.
    """
    endpoint_start_time = time.time()
    request_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(
        f"Outreach generation request - Candidate ID: {candidate_id}, "
        f"Role: {request.job_role_title}, Tone: {request.tone}"
    )

    try:
        # Step 1: Fetch candidate details
        logger.debug(f"Fetching candidate profile for ID: {candidate_id}")
        candidate = await rag_service.get_candidate_details_by_id(candidate_id)

        # Step 2: Generate outreach draft
        logger.debug(
            f"Generating outreach for {candidate.name} - {request.job_role_title}"
        )

        generation_start_time = time.time()
        draft_message = await llm_service.generate_outreach_draft(
            candidate=candidate,
            job_role_title=request.job_role_title,
            job_role_description=request.job_role_description,
            tone=request.tone,
            company_context=request.company_context,
            additional_instructions=request.additional_instructions,
        )
        generation_time_ms = (time.time() - generation_start_time) * 1000

        # Step 3: Extract personalization elements (simple version for MVP)
        personalization_elements = []

        # Add years of experience if available and mentioned
        if candidate.experience_years is not None:  # Check if not None
            exp_str = str(candidate.experience_years)
            # Check if number itself or number + "year" is in draft
            if exp_str in draft_message or (exp_str + " year") in draft_message:
                personalization_elements.append(
                    f"{candidate.experience_years} years experience"
                )

        # Add top 3 skills mentioned
        if candidate.skills:
            for skill in candidate.skills[:3]:  # Iterate through first 3 skills
                if skill.lower() in draft_message.lower():  # Case-insensitive check
                    personalization_elements.append(f"{skill} expertise")

        # Add location if mentioned
        if candidate.location and candidate.location.lower() in draft_message.lower():
            personalization_elements.append(f"Located in {candidate.location}")

        # Step 4: Calculate metrics
        word_count = len(draft_message.split())
        character_count = len(draft_message)

        logger.info(
            f"Successfully generated {word_count}-word outreach for {candidate.name} "
            f"in {generation_time_ms:.2f}ms (total endpoint time: {(time.time() - endpoint_start_time) * 1000:.2f}ms)"
        )

        return OutreachResponse(
            draft_message=draft_message,
            candidate_name=candidate.name,
            candidate_id=candidate_id,  # Return candidate_id in response as per model
            job_role_title=request.job_role_title,
            generated_at=request_timestamp,
            generation_time_ms=round(generation_time_ms, 2),
            word_count=word_count,
            character_count=character_count,
            tone_used=request.tone,
            personalization_elements=list(
                set(personalization_elements)
            ),  # Deduplicate, just in case
            confidence_score=None,  # Future enhancement, explicitly None
        )

    except ValueError as e:
        # Candidate not found from RAGService
        logger.warning(f"Candidate not found for ID '{candidate_id}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="NotFoundError",
                message=str(e),  # Use the message from ValueError
                details={"candidate_id": candidate_id},
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )

    except TextGenerationError as e:  # Specific error from LLMService
        logger.error(
            f"LLM Text generation failed for candidate {candidate_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="TextGenerationError",
                message=f"AI text generation service failed: {str(e)}",
                details={"retry_after_seconds": 30},  # Example detail
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )

    except OpenAIConfigError as e:  # Specific error from LLMService for config issues
        logger.error(
            f"OpenAI configuration error during outreach generation: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="AIConfigurationError",
                message=f"AI service configuration error: {str(e)}. Please contact support.",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )
    except LLMServiceError as e:  # Catch any other general LLMServiceError
        logger.error(
            f"General LLMService error for candidate {candidate_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="LLMServiceUnavailable",
                message=f"AI service is currently unavailable: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )
    except (
        RAGServiceError
    ) as e:  # Catch errors from RAG cache loading if not caught by ValueError
        logger.error(
            f"RAGService error during outreach generation for candidate {candidate_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="DataServiceError",
                message=f"Could not retrieve candidate data: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )

    except Exception as e:
        # Unexpected errors
        request_id = (
            f"req_{int(time.time())}_{candidate_id[:8]}"  # More specific request ID
        )
        logger.error(
            f"Unexpected error in generate_outreach (Req ID: {request_id}): {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="InternalServerError",
                message="An unexpected internal error occurred. Please try again later.",
                details={"request_id": request_id},
                timestamp=request_timestamp,
            ).model_dump(exclude_none=True),
        )
