import logging
from typing import List, Optional, Dict, Any
import time  # For search_time_ms
import datetime  # For error timestamp

from fastapi import APIRouter, Depends, Query, HTTPException, status

# Import the official Pydantic models
from backend.app.models.api_models import (
    QueryResponseItem,
    SearchResponse,
    ErrorResponse,
    CandidateProfile,  # For constructing the nested candidate object
)

from backend.app.services.llm_service import LLMService, LLMServiceError
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
        None, description="Comma-separated skills to filter by"
    ),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
):
    """Search for candidate profiles based on query and filters."""
    start_time = time.time()  # Start timer for search_time_ms
    request_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(
        f"Received search query: '{q}' with limit: {limit}, filters: visa='{visa_status}', loc='{location}', exp>='{min_experience}', skills='{skills}'"
    )

    current_filters_applied: Dict[str, Any] = {}
    if visa_status:
        current_filters_applied["visa_status"] = visa_status
    if location:
        current_filters_applied["location"] = location
    if min_experience is not None:
        current_filters_applied["min_experience"] = min_experience
    if skills:
        current_filters_applied["skills"] = [
            s.strip().lower() for s in skills.split(",") if s.strip()
        ]

    try:
        query_embedding = await llm_service.get_embedding(text=q)
    except LLMServiceError as e:
        logger.error(f"LLMService error during query embedding: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(  # Use the imported ErrorResponse model
                error="ServiceError",
                message=f"Could not generate query embedding: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(),
        )
    except ValueError as e:
        logger.warning(f"Invalid query text for embedding or processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="ValueError",
                message=f"Invalid query: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(),
        )

    metadata_filters_for_rag: Dict[str, Any] = {}
    if visa_status:
        metadata_filters_for_rag["visa_status"] = visa_status
    if location:
        metadata_filters_for_rag["location"] = location
    if min_experience is not None:
        metadata_filters_for_rag["experience_years"] = {"$gte": min_experience}
    if skills:
        metadata_filters_for_rag["skills_query"] = current_filters_applied["skills"]

    try:
        retrieved_candidates_data = await rag_service.similarity_search(
            query_embedding=query_embedding,
            k=limit,
            filters=metadata_filters_for_rag if metadata_filters_for_rag else None,
        )
    except SearchOperationError as e:
        logger.error(f"RAGService search operation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="SearchError",
                message=f"Candidate search failed: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(),
        )
    except RAGServiceError as e:
        logger.error(f"General RAGService error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="InternalSearchError",
                message="An internal error occurred with the search service.",
                timestamp=request_timestamp,
            ).model_dump(),
        )
    except ValueError as e:  # Catch ValueErrors from RAG service as well
        logger.error(f"ValueError during RAGService search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="SearchValueError",
                message=f"Search processing error: {str(e)}",
                timestamp=request_timestamp,
            ).model_dump(),
        )

    response_items: List[QueryResponseItem] = []
    for cand_data in retrieved_candidates_data:
        try:
            meta = cand_data.get("metadata", {})
            # Ensure skills are processed correctly into a list
            skills_str = meta.get("skills", "")
            skills_list = (
                [s.strip() for s in skills_str.split(",") if s.strip()]
                if isinstance(skills_str, str)
                else []
            )

            # Construct the nested CandidateProfile model
            # Ensure all *required* fields for CandidateProfile are present and from the correct source.
            # `raw_resume_text` comes from the main document retrieved by Chroma.
            # Other fields come from `meta` (metadata stored alongside the vector).
            candidate_profile_data = {
                "id": str(cand_data.get("id")),
                "name": str(meta.get("name", "N/A")),
                "raw_resume_text": str(cand_data.get("document", "")),
                "skills": skills_list,
                # experience_years must be an int and is required by CandidateProfile
                "experience_years": int(
                    meta.get("experience_years", 0)
                ),  # Default to 0 if missing/None
                "visa_status": meta.get("visa_status"),
                "location": meta.get("location"),
                "github_url": meta.get("github_url"),
                "linkedin_url": meta.get("linkedin_url"),
            }

            # Filter out None values for optional fields if HttpUrl doesn't handle None well when parsing
            # Pydantic HttpUrl should handle None, so this might not be strictly necessary
            # but can prevent issues if meta.get returns an explicit None that trips validation.
            candidate_profile_data = {
                k: v
                for k, v in candidate_profile_data.items()
                if v is not None
                or k in ["id", "name", "raw_resume_text", "skills", "experience_years"]
            }

            candidate_profile = CandidateProfile(**candidate_profile_data)

            response_items.append(
                QueryResponseItem(
                    candidate=candidate_profile,
                    relevance_score=cand_data.get(
                        "distance", 0.0
                    ),  # Assuming distance is used for score
                    # match_reasons and highlighted_text can be populated if logic exists, else defaults
                    match_reasons=[],  # Placeholder
                    highlighted_text=None,  # Placeholder
                )
            )
        except Exception as e:
            logger.error(
                f"Error mapping candidate data (ID: {cand_data.get('id')}) to QueryResponseItem: {e}",
                exc_info=True,
            )

    end_time = time.time()
    search_time_ms = (end_time - start_time) * 1000

    logger.info(
        f"Search successful. Returning {len(response_items)} candidates in {search_time_ms:.2f}ms."
    )
    return SearchResponse(
        query=q,
        results=response_items,
        total_results=len(response_items),
        search_time_ms=search_time_ms,
        filters_applied=current_filters_applied if current_filters_applied else None,
        # suggestions=None # Placeholder for now
    )
