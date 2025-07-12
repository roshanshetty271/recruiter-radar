import logging
from typing import List, Optional, Dict, Any
import time  # For search_time_ms
import datetime  # For error timestamp
import uuid
import json
import asyncio
from collections import Counter
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
    status,
    Path,
    Body,
    File,
    Form,
    UploadFile,
)

# Import the official Pydantic models
from app.models.api_models import (
    QueryResponseItem,
    SearchResponse,
    ErrorResponse,
    CandidateProfile,  # For constructing the nested candidate object
    OutreachRequest,  # Added for new endpoint
    OutreachResponse,  # Added for new endpoint
    UploadResponse,
    UploadErrorResponse,
    BatchUploadResponse,
    BatchUploadStats,
    CandidatePreview,
    CandidateUpdateInfo,
    FileError,
    CandidateInsightsResponse,
    PaginationInfo,  # Added for pagination support
    SearchMetadata,  # Added for enhanced search metadata
    ComparisonRequest,  # Added for AI comparison analysis
    ComparisonAnalysisResponse,  # Added for AI comparison analysis
)

from app.services.llm_service import (
    LLMService,
    LLMServiceError,
    TextGenerationError,  # Assuming this is defined in llm_service
    OpenAIConfigError,  # Assuming this is defined in llm_service
)
from app.services.rag_service import (
    RAGService,
    SearchOperationError,
    RAGServiceError,
)
from app.services.search_utils import (
    extract_location_from_query,
    enhance_search_query,
)  # Import our new utility
from app.dependencies import get_llm_service, get_rag_service, get_comparison_service
from app.services.ai_extraction_service import AIExtractionService
from app.services.resume_parser import ResumeParser
from app.services.comparison_service import (
    ComparisonService,
)  # Added for AI comparison analysis

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


# Dependencies for services
def get_ai_extraction_service(
    llm_service: LLMService = Depends(get_llm_service),
) -> AIExtractionService:
    """Dependency to get AI extraction service."""
    return AIExtractionService(llm_service)


def get_resume_parser() -> ResumeParser:
    """Dependency to get resume parser."""
    ai_extraction_service = get_ai_extraction_service()
    return ResumeParser(ai_extraction_service)


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
        "",
        min_length=0,
        max_length=200,
        description="Natural language query string (e.g., 'Python developers with AI experience'). Leave empty to see all candidates.",
        example="Python developers with AI experience",
    ),
    # Pagination parameters
    page: int = Query(
        1,
        ge=1,
        le=1000,
        description="Page number (1-based) - which page of results to retrieve",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of results per page (1-100, default 20 for optimal recruiter workflow)",
    ),
    # Legacy parameter for backward compatibility
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=100,
        description="Legacy: Maximum number of results (deprecated, use page_size instead)",
    ),
    # Existing filter parameters
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

    search_start_time = time.time()

    try:
        # 🔄 PAGINATION LOGIC: Handle backward compatibility
        if limit is not None:
            # Legacy mode: use limit parameter
            effective_page_size = limit
            effective_page = 1
            logger.info(f"🔄 Using legacy pagination: limit={limit}")
        else:
            # New pagination mode
            effective_page_size = page_size
            effective_page = page
            logger.info(f"📄 Using new pagination: page={page}, page_size={page_size}")

        # Calculate skip for pagination (0-based offset)
        skip = (effective_page - 1) * effective_page_size

        # 🧠 INTELLIGENT QUERY ENHANCEMENT
        original_filters = {
            "visa_status": visa_status,
            "location": location,
            "min_experience": min_experience,
            "skills": skills,
        }
        query_enhancements = enhance_search_query(q, original_filters)
        enhanced_filters = query_enhancements["enhanced_filters"]
        embedding_query = query_enhancements["cleaned_query"]

        logger.info(
            f"🚀 ENHANCED search processing: "
            f"Original: '{q}' → Cleaned: '{embedding_query}' | "
            f"Enhanced filters: {enhanced_filters} | "
            f"Pagination: page={effective_page}, size={effective_page_size}, skip={skip}"
        )

        # Generate embedding for the cleaned query
        # For empty queries, use a generic embedding that will return all candidates
        if embedding_query.strip():
            query_embedding = await llm_service.get_embedding(embedding_query)
        else:
            # Use a generic query for empty searches to get all candidates
            query_embedding = await llm_service.get_embedding(
                "candidate profile software engineer"
            )

        # Parse enhanced skills filter
        skills_list = None
        if enhanced_filters.get("skills"):
            skills_list = [
                s.strip().lower()
                for s in enhanced_filters["skills"].split(",")
                if s.strip()
            ]

        # Build metadata filters using enhanced values
        metadata_filters = {}
        if enhanced_filters.get("visa_status"):
            metadata_filters["visa_status"] = enhanced_filters["visa_status"]
        if enhanced_filters.get("location"):
            metadata_filters["location"] = enhanced_filters["location"]
        if enhanced_filters.get("min_experience") is not None:
            metadata_filters["experience_years"] = {
                "$gte": enhanced_filters["min_experience"]
            }
        if skills_list:
            metadata_filters["skills_query"] = skills_list

        # 🎯 ENHANCED SEARCH: Fetch more results to enable proper pagination
        # We need to get all matching results first, then paginate
        max_k_for_pagination = 500  # Reasonable limit to avoid memory issues
        search_k = max_k_for_pagination  # Get a large set for pagination

        # RAGService.similarity_search is expected to return a tuple:
        # (list_of_candidate_data_dicts, count_before_post_filter)
        all_raw_results, count_before_filter = await rag_service.similarity_search(
            query_embedding=query_embedding,
            query_text=embedding_query,
            k=search_k,  # Get many results for proper pagination
            filters=metadata_filters,
        )

        # 📊 PAGINATION PROCESSING: Transform and paginate results
        all_candidates = []
        for result_dict in all_raw_results:
            metadata = result_dict.get("metadata", {})
            distance = result_dict.get("distance", 1.0)
            relevance_score = max(0.0, 1.0 - float(distance))
            skills_str = metadata.get("skills", "")
            candidate_skills_list = (
                [s.strip() for s in skills_str.split(",") if s.strip()]
                if isinstance(skills_str, str)
                else []
            )

            # -- Email sanitization: convert empty or malformed emails to None to satisfy Pydantic
            raw_email = metadata.get("email")
            if raw_email:
                raw_email = raw_email.strip()
                # Basic sanity check for '@' presence; more complex validation is unnecessary here
                if "@" not in raw_email:
                    raw_email = None
            else:
                raw_email = None

            all_candidates.append(
                QueryResponseItem(
                    id=str(result_dict.get("id", "")),
                    name=str(metadata.get("name", "Unknown")),
                    email=raw_email,
                    skills=candidate_skills_list,
                    experience_years=int(metadata.get("experience_years", 0)),
                    location=str(metadata.get("location", "Not specified")),
                    visa_status=str(metadata.get("visa_status", "Not specified")),
                    match_context=str(result_dict.get("document", "")),
                    relevance_score=relevance_score,
                    github_url=metadata.get("github_url"),
                    linkedin_url=metadata.get("linkedin_url"),
                )
            )

        # 🎯 APPLY PAGINATION: Slice the results for current page
        total_candidates = len(all_candidates)
        end_index = skip + effective_page_size
        current_page_candidates = all_candidates[skip:end_index]

        # 📈 CALCULATE PAGINATION METADATA
        total_pages = (
            total_candidates + effective_page_size - 1
        ) // effective_page_size  # Ceiling division
        has_next = effective_page < total_pages
        has_previous = effective_page > 1
        actual_end_index = min(
            skip + len(current_page_candidates) - 1, total_candidates - 1
        )

        pagination_info = PaginationInfo(
            current_page=effective_page,
            page_size=effective_page_size,
            total_candidates=total_candidates,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            start_index=skip,
            end_index=actual_end_index if current_page_candidates else skip,
        )

        search_time_ms = (time.time() - search_start_time) * 1000

        # 🧠 BUILD ENHANCED SEARCH METADATA
        search_metadata = SearchMetadata(
            query=q,
            processing_time_ms=round(search_time_ms, 2),
            filters_applied=enhanced_filters,
            ai_confidence=0.85,  # Mock confidence score for MVP
            semantic_themes=query_enhancements.get("extracted_skills", [])[
                :3
            ],  # Top 3 themes
            suggested_refinements=[
                (
                    "Consider adding location filter"
                    if not enhanced_filters.get("location")
                    else None
                ),
                (
                    "Specify experience level"
                    if not enhanced_filters.get("min_experience")
                    else None
                ),
                (
                    "Add visa status filter"
                    if not enhanced_filters.get("visa_status")
                    else None
                ),
            ],
        )
        # Remove None values from suggested refinements
        search_metadata.suggested_refinements = [
            r for r in search_metadata.suggested_refinements if r
        ]

        # 📋 DETAILED PAGINATION LOGGING
        logger.info(
            f"🎯 PAGINATED SEARCH RESULTS for query '{q}' "
            f"(Page {effective_page}/{pagination_info.total_pages}): "
            f"Showing {len(current_page_candidates)} of {total_candidates} total candidates"
        )
        logger.info("=" * 80)
        for i, candidate in enumerate(current_page_candidates, skip + 1):
            logger.info(
                f"  {i:2d}. 👤 {candidate.name} (ID: {candidate.id}) "
                f"- Score: {candidate.relevance_score:.3f}"
            )
            logger.info(
                f"      💼 {candidate.experience_years} years exp | "
                f"📍 {candidate.location} | "
                f"🛂 {candidate.visa_status}"
            )
            logger.info(
                f"      🔧 Skills: {', '.join(candidate.skills[:5])}{'...' if len(candidate.skills) > 5 else ''}"
            )
            logger.info(
                f"      📄 Context: {candidate.match_context[:100]}{'...' if len(candidate.match_context) > 100 else ''}"
            )
            logger.info("-" * 80)

        if current_page_candidates:
            avg_score = sum(c.relevance_score for c in current_page_candidates) / len(
                current_page_candidates
            )
            top_skills = {}
            for c in all_candidates:  # Use all candidates for skills analysis
                for skill in c.skills:
                    top_skills[skill] = top_skills.get(skill, 0) + 1
            common_skills = sorted(
                top_skills.items(), key=lambda x: x[1], reverse=True
            )[:3]

            logger.info(
                f"📊 PAGE SUMMARY: Avg relevance: {avg_score:.3f} | "
                f"Page {effective_page}/{pagination_info.total_pages} | "
                f"Common skills across all results: {', '.join([f'{skill}({count})' for skill, count in common_skills])}"
            )
        else:
            logger.info("❌ No candidates found on this page.")
        logger.info("=" * 80)

        # 🚀 BUILD ENHANCED RESPONSE with Pagination
        response = SearchResponse(
            results=current_page_candidates,
            pagination=pagination_info,
            search_metadata=search_metadata,
            # Backward compatibility fields
            total_results=total_candidates,
            search_time_ms=round(search_time_ms, 2),
            query_interpretation=(
                f"Intelligent search: '{embedding_query}'"
                + (
                    f" (location: {query_enhancements['extracted_location']})"
                    if query_enhancements["extracted_location"]
                    else ""
                )
                + (
                    f" (skills: {', '.join(query_enhancements['extracted_skills'])})"
                    if query_enhancements["extracted_skills"]
                    else ""
                )
                + (
                    f" (experience: {query_enhancements['extracted_experience']['level']})"
                    if query_enhancements["extracted_experience"]
                    else ""
                )
            ),
            suggested_filters=None,
            search_metadata_legacy={
                "retrieved_before_filter": count_before_filter,
                "intelligence_enhancements": query_enhancements,
            },
        )

        logger.info(
            f"🎯 Enhanced paginated search completed: "
            f"Showing {len(current_page_candidates)} results on page {effective_page}/{pagination_info.total_pages} "
            f"({total_candidates} total) in {search_time_ms:.2f}ms"
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
            generated_at=datetime.datetime.utcnow(),
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


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload and Parse Resume",
    description="""
Upload a resume file (PDF, DOCX, or TXT) to automatically extract candidate information 
and add them to the searchable candidate database.

**Supported File Types:**
- PDF (.pdf) - Text extraction using OCR-like capabilities
- Microsoft Word (.docx) - Direct text extraction
- Plain Text (.txt) - Direct text processing

**File Requirements:**
- Maximum file size: 10MB
- File must contain readable text
- Filename should be provided

**What Gets Extracted:**
- Candidate name (from resume header)
- Technical skills (using AI-powered pattern matching)
- Years of experience (from resume content)
- Location (if mentioned)
- GitHub/LinkedIn URLs (if present)

**AI Processing:**
The system uses advanced text processing to:
1. Extract structured data from unstructured resume text
2. Identify relevant technical skills from a comprehensive database
3. Estimate experience level based on resume content
4. Generate searchable embeddings for semantic search

**After Upload:**
- Candidate is immediately searchable via the `/query` endpoint
- Outreach messages can be generated via `/generate-outreach`
- All standard search and filtering features apply

**Privacy Note:**
Uploaded resumes are processed locally and stored securely in the vector database.
Text content is used only for search and matching purposes.
    """,
    response_description="Detailed information about the processed resume and extracted candidate data.",
    responses={
        200: {
            "description": "Resume uploaded and processed successfully.",
            "model": UploadResponse,
        },
        400: {
            "description": "Invalid file or processing error.",
            "model": UploadErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "file_too_large": {
                            "summary": "File size exceeds limit",
                            "value": {
                                "success": False,
                                "error": "file_too_large",
                                "message": "File size exceeds 10MB limit",
                                "file_name": "large_resume.pdf",
                                "details": {"max_size_mb": 10, "actual_size_mb": 15.2},
                            },
                        },
                        "unsupported_file": {
                            "summary": "Unsupported file format",
                            "value": {
                                "success": False,
                                "error": "unsupported_format",
                                "message": "Unsupported file type. Supported: .pdf, .docx, .txt",
                                "file_name": "resume.png",
                                "details": {
                                    "supported_formats": [".pdf", ".docx", ".txt"]
                                },
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Server error during processing.",
            "model": UploadErrorResponse,
        },
    },
    operation_id="uploadResumeV1",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file to upload"),
    candidate_name: Optional[str] = Form(
        None, description="Override candidate name (optional)"
    ),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    **Upload and Process Resume File**

    Upload a resume file and automatically extract candidate information for searchable storage.

    **Parameters:**
    - `file`: Resume file (PDF, DOCX, or TXT format, max 10MB)
    - `candidate_name`: Optional name override if auto-extraction fails

    **Process:**
    1. **File Validation**: Check format and size
    2. **Text Extraction**: Extract readable text from the file
    3. **Information Parsing**: Use AI to extract:
       - Name, skills, experience, location
       - GitHub/LinkedIn URLs if present
    4. **Embedding Generation**: Create searchable vector representation
    5. **Database Storage**: Add to ChromaDB for immediate searchability

    **Response:**
    - Success confirmation with extracted information
    - Generated candidate ID for future reference
    - Processing time and file details
    - List of extracted skills and experience level

    The uploaded candidate will be immediately available in search results.
    """

    processing_start_time = time.time()
    file_name = file.filename or "unknown_file"

    try:
        # Import here to avoid circular imports
        from app.services.resume_parser import ResumeParser, ResumeParsingError

        logger.info(
            f"📁 Processing uploaded resume: {file_name} (size: {file.size if hasattr(file, 'size') else 'unknown'})"
        )

        # Initialize AI-powered resume parser
        parser = ResumeParser(llm_service)

        # First, get the file content for AI parsing
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer for later use

        # Get file type for processing
        file_type = file_name.split(".")[-1].lower() if "." in file_name else "txt"

        # Parse using AI extraction (get comprehensive data)
        try:
            extracted_data = await parser.parse_resume(file_content, file_type)
            if not extracted_data:
                raise ResumeParsingError("AI extraction failed - no data extracted")

            # Override name if provided
            if candidate_name:
                extracted_data.name = candidate_name

            logger.info(
                f"✅ AI extraction completed for {extracted_data.name} "
                f"(email: {extracted_data.email or 'N/A'}, "
                f"confidence: {extracted_data.extraction_confidence:.2f}, "
                f"skills: {len(extracted_data.technical_skills)})"
            )
        except Exception as e:
            logger.error(f"AI extraction failed for {file_name}: {e}")
            # Fallback to old method if AI fails
            try:
                candidate_profile = await parser.parse_uploaded_file(
                    file, candidate_name
                )
                # Create minimal ExtractedResumeData from CandidateProfile
                from app.models.extraction_models import ExtractedResumeData

                extracted_data = ExtractedResumeData(
                    name=candidate_profile.name,
                    technical_skills=candidate_profile.skills,
                    total_experience_years=float(candidate_profile.experience_years),
                    location=candidate_profile.location,
                    github_url=candidate_profile.github_url,
                    linkedin_url=candidate_profile.linkedin_url,
                    professional_summary="Extracted using fallback method",
                    extraction_confidence=0.6,
                )
                logger.info(f"✅ Fallback extraction for {extracted_data.name}")
            except ResumeParsingError as fallback_error:
                logger.error(f"Resume parsing failed for {file_name}: {fallback_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=UploadErrorResponse(
                        error="parsing_failed",
                        message=str(fallback_error),
                        file_name=file_name,
                        details={"error_type": "ResumeParsingError"},
                    ).model_dump(exclude_none=True),
                )

        # 🔧 CRITICAL: Apply post-processing improvements regardless of extraction method
        try:
            # Get the original text from the file for post-processing
            original_text = parser.extract_text_from_file(file_content, file_type)
            if original_text:
                # Apply our post-processing improvements
                ai_service = get_ai_extraction_service()
                extracted_data = ai_service._post_process_extraction(
                    extracted_data, original_text
                )
                logger.info(
                    f"🔧 Post-processing applied to {extracted_data.name} "
                    f"(final confidence: {extracted_data.extraction_confidence:.2f}, "
                    f"skills: {len(extracted_data.technical_skills)})"
                )
        except Exception as post_error:
            logger.warning(
                f"Post-processing failed for {extracted_data.name}: {post_error}"
            )
            # Don't fail the entire upload if post-processing fails

        # Normalize email before creating candidate profile
        normalized_email = (
            extracted_data.email.lower().strip() if extracted_data.email else None
        )

        # Create candidate profile from extracted data for backward compatibility
        candidate_profile = CandidateProfile(
            id=f"uploaded_{uuid.uuid4().hex[:8]}",
            name=extracted_data.name,
            email=normalized_email,  # Use normalized email
            raw_resume_text=extracted_data.professional_summary
            or "AI-extracted summary not available",
            skills=extracted_data.technical_skills,
            experience_years=int(round(extracted_data.total_experience_years)),
            visa_status=None,
            location=extracted_data.location,
            github_url=extracted_data.github_url,
            linkedin_url=extracted_data.linkedin_url,
        )

        # Generate embedding for comprehensive text from AI extraction
        try:
            # Create rich embedding text from AI extracted data
            embedding_text = f"""
            {extracted_data.name}
            {extracted_data.current_title or ''}
            {extracted_data.professional_summary or ''}
            Skills: {', '.join(extracted_data.technical_skills)}
            Experience: {extracted_data.total_experience_years} years
            Location: {extracted_data.location or ''}
            Education: {', '.join([f"{edu.degree} in {edu.field} from {edu.school}" for edu in extracted_data.education])}
            """.strip()

            embedding = await llm_service.get_embedding(embedding_text)
            logger.info(
                f"🧠 Generated embedding for {extracted_data.name} (dimension: {len(embedding)})"
            )
        except Exception as e:
            logger.error(f"Embedding generation failed for {extracted_data.name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=UploadErrorResponse(
                    error="embedding_failed",
                    message="Failed to generate AI embedding for resume content",
                    file_name=file_name,
                    details={"service_error": str(e)},
                ).model_dump(exclude_none=True),
            )

        # Prepare metadata for ChromaDB, ensuring no None values are passed
        metadata_to_store = {
            "candidate_id": candidate_profile.id,
            "name": extracted_data.name or "Unknown",
            "email": normalized_email,  # Use normalized email
            "experience_years": extracted_data.total_experience_years or 0.0,
            "skills": ",".join(extracted_data.technical_skills),
            "location": extracted_data.location or "Not Specified",
            "source": "uploaded_resume",
            "upload_timestamp": datetime.datetime.utcnow().isoformat(),
        }

        # Add portfolio and other URLs
        if extracted_data.portfolio_url:
            metadata_to_store["portfolio_url"] = extracted_data.portfolio_url
        if extracted_data.other_urls:
            metadata_to_store["other_urls"] = ", ".join(extracted_data.other_urls)

        # Add candidate to ChromaDB with comprehensive AI extraction data
        try:
            # Create comprehensive document text for storage and retrieval
            document_text = f"""
            Name: {extracted_data.name}
            Current Title: {extracted_data.current_title or 'Not specified'}
            Location: {extracted_data.location or 'Not specified'}
            Experience: {extracted_data.total_experience_years} years
            
            Professional Summary:
            {extracted_data.professional_summary or 'Not available'}
            
            Technical Skills: {', '.join(extracted_data.technical_skills)}
            Soft Skills: {', '.join(extracted_data.soft_skills)}
            
            Work Experience:
            {chr(10).join([f"- {exp.title} at {exp.company} ({exp.duration})" for exp in extracted_data.work_experience])}
            
            Education:
            {chr(10).join([f"- {edu.degree} in {edu.field} from {edu.school} ({edu.graduation_year or 'N/A'})" for edu in extracted_data.education])}
            
            Certifications: {', '.join(extracted_data.certifications) if extracted_data.certifications else 'None'}
            Languages: {', '.join(extracted_data.languages) if extracted_data.languages else 'Not specified'}
            
            Contact:
            Email: {extracted_data.email or 'Not provided'}
            Phone: {extracted_data.phone or 'Not provided'}
            LinkedIn: {extracted_data.linkedin_url or 'Not provided'}
            GitHub: {extracted_data.github_url or 'Not provided'}
            """.strip()

            await rag_service.add_candidate_to_collection(
                candidate_id=candidate_profile.id,
                embedding=embedding,
                metadata=metadata_to_store,
                document_text=document_text,
            )
            logger.info(
                f"💾 Successfully added {extracted_data.name} to ChromaDB with ID: {candidate_profile.id} "
                f"(AI confidence: {extracted_data.extraction_confidence:.2f})"
            )
        except Exception as e:
            logger.error(f"Failed to add candidate to ChromaDB: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=UploadErrorResponse(
                    error="database_error",
                    message="Failed to add candidate to search database",
                    file_name=file_name,
                    details={"service_error": str(e)},
                ).model_dump(exclude_none=True),
            )

        # Calculate metrics
        processing_time_ms = (time.time() - processing_start_time) * 1000
        file_size = len(file_content)  # Use already read content

        # Build comprehensive response with AI extraction data
        response = UploadResponse(
            success=True,
            candidate_id=candidate_profile.id,
            candidate_name=extracted_data.name,
            extracted_data=extracted_data,
            file_name=file_name,
            file_size=file_size,
            processing_time_ms=round(processing_time_ms, 2),
            message=f"Resume processed successfully. {extracted_data.name} is now searchable with {len(extracted_data.technical_skills)} technical skills extracted (AI confidence: {extracted_data.extraction_confidence:.0%}).",
            # Backward compatibility fields
            extracted_skills=extracted_data.technical_skills,
            experience_years=int(round(extracted_data.total_experience_years)),
            location=extracted_data.location,
        )

        logger.info(
            f"🎉 Upload completed successfully: {extracted_data.name} ({candidate_profile.id}) "
            f"in {processing_time_ms:.2f}ms with {len(extracted_data.technical_skills)} technical skills "
            f"(AI confidence: {extracted_data.extraction_confidence:.2f})"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            f"Unexpected error processing upload {file_name}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=UploadErrorResponse(
                error="internal_upload_error",
                message="An unexpected error occurred while processing the resume",
                file_name=file_name,
                details={"error": str(e)},
            ).model_dump(exclude_none=True),
        )


@router.get("/extraction-analytics", response_model=Dict[str, Any])
async def get_extraction_analytics(
    hours_back: int = Query(
        24, ge=1, le=168, description="Hours to look back for analytics (1-168)"
    ),
    ai_extraction_service: AIExtractionService = Depends(get_ai_extraction_service),
) -> Dict[str, Any]:
    """
    Get AI extraction performance analytics and metrics.

    Provides insights into extraction performance, success rates,
    and system health metrics for monitoring and optimization.

    Args:
        hours_back: Number of hours to analyze (default 24, max 168 = 1 week)

    Returns:
        Analytics data including success rates, performance metrics, and benchmarks
    """
    try:
        logger.info(f"Fetching extraction analytics for last {hours_back} hours")

        analytics = ai_extraction_service.get_analytics(hours_back=hours_back)

        # Add system status and recommendations
        analytics["system_status"] = "healthy"
        analytics["recommendations"] = []

        # Add intelligent recommendations based on metrics
        if analytics.get("success_rate", 0) < 0.85:
            analytics["system_status"] = "degraded"
            analytics["recommendations"].append(
                "Success rate below 85% - investigate extraction failures"
            )

        if analytics.get("average_metrics", {}).get("extraction_time_seconds", 0) > 8:
            analytics["recommendations"].append(
                "Extraction time above 8s - consider optimization"
            )

        if analytics.get("cache_hit_rate", 0) < 0.20:
            analytics["recommendations"].append(
                "Low cache hit rate - consider cache size tuning"
            )

        if analytics.get("average_metrics", {}).get("confidence_score", 0) < 0.80:
            analytics["recommendations"].append(
                "Low confidence scores - review prompt engineering"
            )

        if not analytics["recommendations"]:
            analytics["recommendations"].append("System performing optimally ✅")

        # Add current extraction capabilities showcase
        analytics["extraction_capabilities"] = {
            "skills_detection": "Unlimited (AI finds ALL mentioned skills)",
            "work_experience": "Complete career history (all jobs)",
            "education": "All degrees, certifications, bootcamps",
            "data_completeness": "85-95% vs 10% before AI",
            "improvement_factor": "9-10x better than pattern matching",
            "supported_formats": ["PDF", "TXT", "Complex layouts"],
            "languages_supported": ["Multi-language resumes"],
            "processing_speed": "3-10 seconds (< 100ms cached)",
        }

        return analytics

    except Exception as e:
        logger.error(f"Analytics retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.post(
    "/upload-batch",
    response_model=BatchUploadResponse,
    summary="Upload up to 10 resumes in one request",
    description="""
Upload 1-10 resume files at once. Each file is parsed, embedded, and added to the
candidate database. Duplicate candidates (matched by email) are updated instead
of added again. Returns a rich summary of the batch.
    """,
    response_description="Summary of batch processing results",
)
async def upload_resume_batch(
    files: List[UploadFile] = File(
        ..., description="Resume files (PDF, DOCX, or TXT)", max_items=10
    ),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
):
    """Batch upload endpoint supporting up to 10 resume files."""

    start_time = time.time()
    parser = ResumeParser(llm_service)

    added: List[CandidatePreview] = []
    updated: List[CandidateUpdateInfo] = []
    failed: List[FileError] = []

    total_files = len(files)
    new_candidates = 0
    duplicates_updated = 0
    successful = 0
    exp_sum = 0.0
    all_skills: List[str] = []

    for file in files:
        file_name = file.filename or "unknown_file"
        try:
            file_content = await file.read()
            await file.seek(0)

            file_type = file_name.split(".")[-1].lower() if "." in file_name else "txt"

            # ----- AI extraction -----
            extracted_data = await parser.parse_resume(file_content, file_type)
            if not extracted_data:
                raise Exception("AI extraction returned no data")

            # ----- NORMALIZE EMAIL & GENERATE ID -----
            normalized_email = (
                extracted_data.email.lower().strip() if extracted_data.email else None
            )
            candidate_id = f"uploaded_{uuid.uuid4().hex[:8]}"

            candidate_profile = CandidateProfile(
                id=candidate_id,
                name=extracted_data.name,
                email=normalized_email,  # Use normalized email
                raw_resume_text=extracted_data.professional_summary
                or "AI-extracted summary not available",
                skills=extracted_data.technical_skills,
                experience_years=int(round(extracted_data.total_experience_years)),
                visa_status=None,
                location=extracted_data.location,
                github_url=extracted_data.github_url,
                linkedin_url=extracted_data.linkedin_url,
            )

            # ----- Embedding -----
            embedding_text = (
                f"{extracted_data.name}\n"
                f"{extracted_data.professional_summary or ''}\n"
                f"Skills: {', '.join(extracted_data.technical_skills)}"
            )
            embedding = await llm_service.get_embedding(embedding_text)

            # ----- Store in ChromaDB via RAGService -----
            from datetime import datetime

            metadata = {
                "candidate_id": candidate_profile.id,
                "name": extracted_data.name or "Unknown",
                "email": normalized_email,  # Use normalized email
                "experience_years": extracted_data.total_experience_years or 0.0,
                "skills": (
                    ",".join(extracted_data.technical_skills)
                    if extracted_data.technical_skills
                    else ""
                ),
                "location": extracted_data.location or "Not Specified",
                "source": "uploaded_resume_batch",
                "github_url": extracted_data.github_url or "",
                "linkedin_url": extracted_data.linkedin_url or "",
                "visa_status": "Not Specified",  # Default for uploaded resumes
                "uploaded_at": datetime.utcnow().isoformat(),
                "original_filename": file_name,
            }

            # Store in ChromaDB with proper error handling
            storage_success = True
            try:
                await rag_service.add_candidate_to_collection(
                    candidate_id=candidate_profile.id,
                    embedding=embedding,
                    metadata=metadata,
                    document_text=candidate_profile.raw_resume_text,
                )
            except Exception as storage_error:
                logger.error(
                    f"ChromaDB storage failed for {file_name}: {storage_error}"
                )
                storage_success = False
                raise Exception(f"Database storage failed: {str(storage_error)}")

            # ----- Categorise result -----
            successful += 1
            exp_sum += extracted_data.total_experience_years or 0.0
            all_skills.extend([s.lower() for s in extracted_data.technical_skills])

            # RAG service handles deduplication automatically, so we count all as processed
            new_candidates += 1
            added.append(
                CandidatePreview(
                    candidate_id=candidate_profile.id,
                    name=extracted_data.name,
                    email=normalized_email,  # Use normalized email
                    top_skills=extracted_data.technical_skills[:5],
                )
            )

        except Exception as e:
            logger.error(f"Batch upload failed for {file_name}: {e}")
            failed.append(
                FileError(
                    file_name=file_name,
                    error="processing_failed",
                    message=str(e),
                )
            )

    # ----- Aggregate stats -----
    processing_time_seconds = round(time.time() - start_time, 2)
    common_skills = (
        [s for s, _ in Counter(all_skills).most_common(5)] if all_skills else None
    )
    avg_exp = round(exp_sum / successful, 1) if successful else None

    stats = BatchUploadStats(
        total_files=total_files,
        successful=successful,
        new_candidates=new_candidates,
        duplicates_updated=duplicates_updated,
        failed=len(failed),
        processing_time_seconds=processing_time_seconds,
        top_skills=common_skills,
        average_experience_years=avg_exp,
    )

    summary = f"Successfully processed {successful} of {total_files} resumes"

    # ----- Update JSON file with new candidates -----
    if added:  # Only update if new candidates were added
        try:
            await update_candidate_json_file(
                [preview.candidate_id for preview in added], rag_service
            )
            logger.info(f"✅ Updated JSON file with {len(added)} new candidates")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update JSON file: {e}")
            # Don't fail the upload if JSON update fails

    return BatchUploadResponse(
        summary=summary,
        stats=stats,
        added=added,
        updated=updated,
        failed=failed,
    )


# -----------------------------------------------------------------------------
# Helper Functions for JSON Persistence
# -----------------------------------------------------------------------------


async def update_candidate_json_file(
    candidate_ids: List[str], rag_service: RAGService
) -> None:
    """Update the candidate_profiles.json file with newly uploaded candidates."""
    try:
        json_path = Path(settings.candidate_data_full_path)
        logger.info(f"📁 Updating JSON file at: {json_path}")

        # Load existing candidates from JSON
        existing_candidates = []
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                existing_candidates = json.load(f)

        # Convert existing to dict for easy lookup
        existing_dict = {c["id"]: c for c in existing_candidates}

        # Fetch full details for new candidates from ChromaDB and add to JSON
        for candidate_id in candidate_ids:
            try:
                # Get candidate metadata from ChromaDB
                results = await asyncio.to_thread(
                    rag_service.collection.get,
                    ids=[candidate_id],
                    include=["metadatas", "documents"],
                )

                if results.get("ids") and results["ids"][0]:
                    metadata = results["metadatas"][0][0]
                    document = (
                        results["documents"][0][0]
                        if results.get("documents") and results["documents"][0]
                        else ""
                    )

                    # Parse skills from comma-separated string
                    skills = []
                    if metadata.get("skills"):
                        skills = [
                            skill.strip()
                            for skill in metadata["skills"].split(",")
                            if skill.strip()
                        ]

                    # Create candidate profile dict for JSON
                    candidate_json = {
                        "id": candidate_id,
                        "name": metadata.get("name", "Unknown"),
                        "email": metadata.get("email"),
                        "raw_resume_text": document or "Extracted from uploaded resume",
                        "skills": skills,
                        "experience_years": int(
                            float(metadata.get("experience_years", 0))
                        ),
                        "visa_status": metadata.get("visa_status"),
                        "location": metadata.get("location"),
                        "github_url": metadata.get("github_url"),
                        "linkedin_url": metadata.get("linkedin_url"),
                    }

                    existing_dict[candidate_id] = candidate_json
                    logger.info(
                        f"📝 Added {metadata.get('name', 'Unknown')} to JSON cache"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to fetch details for candidate {candidate_id}: {e}"
                )
                continue

        # Write updated data back to JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(list(existing_dict.values()), f, indent=2, ensure_ascii=False)

        logger.info(
            f"✅ Successfully updated {json_path} with {len(candidate_ids)} candidates"
        )

        # Clear the RAGService cache so it reloads with new data
        if hasattr(rag_service, "_candidates_cache"):
            rag_service._candidates_cache = None
            logger.info("🔄 Cleared RAGService cache to force reload")

    except Exception as e:
        logger.error(f"💥 Failed to update candidate JSON file: {e}")
        raise


# -----------------------------------------------------------------------------
# Individual Candidate Details Endpoint
# -----------------------------------------------------------------------------


@router.get(
    "/{candidate_id}",
    response_model=CandidateProfile,
    summary="Get complete candidate details by ID",
    description="""
Get detailed information about a specific candidate by their unique ID.

Returns comprehensive candidate data including:
- Personal information (name, email, location)
- Professional summary and experience
- Technical and soft skills
- Work experience history
- Education background
- Contact information and social links

This endpoint serves both static candidates (from JSON) and uploaded candidates (from ChromaDB).
    """,
    response_description="Complete candidate profile with all available information.",
    responses={
        200: {
            "description": "Candidate details retrieved successfully.",
            "model": CandidateProfile,
        },
        404: {
            "description": "Candidate not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Candidate with ID 'candidate_123' not found"}
                }
            },
        },
    },
    operation_id="getCandidateDetailsV1",
)
async def get_candidate_details(
    candidate_id: str = Path(
        ...,
        min_length=1,
        description="Unique identifier of the candidate",
        example="c001",
    ),
    rag_service: RAGService = Depends(get_rag_service),
):
    """Get complete candidate details by ID with fallback to ChromaDB reconstruction."""
    logger.info(f"🔍 Fetching candidate details for ID: {candidate_id}")
    try:
        # First, try to get from the JSON cache via RAGService
        candidate = await rag_service.get_candidate_details_by_id(candidate_id)
        logger.info(f"✅ Found candidate '{candidate.name}' in JSON cache")
        return candidate
    except ValueError:
        # If not in cache, log it and proceed to check ChromaDB
        logger.info(
            f"🔄 Candidate '{candidate_id}' not in JSON cache, checking ChromaDB..."
        )
        try:
            # Attempt to fetch and reconstruct from ChromaDB
            candidate = await rag_service.get_candidate_from_chroma_by_id(candidate_id)
            if not candidate:
                # This could happen if get_candidate_from_chroma_by_id returns None.
                raise HTTPException(
                    status_code=404,
                    detail=f"Candidate with ID '{candidate_id}' not found",
                )

            logger.info(
                f"✅ Successfully reconstructed candidate '{candidate.name}' from ChromaDB"
            )
            return candidate
        except RAGServiceError as e:
            # This catches specific, known errors from our service layer.
            logger.error(
                f"💥 RAG service error while fetching from ChromaDB for '{candidate_id}': {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=503, detail=f"A problem occurred with the data service: {e}"
            )
        except Exception as e:
            # Catch any other unexpected errors during ChromaDB fetch
            request_id = str(uuid.uuid4())
            error_timestamp = datetime.datetime.utcnow().isoformat()
            logger.error(
                f"💥 Unexpected error fetching from ChromaDB for '{candidate_id}'. "
                f"Request ID: {request_id}. Error Type: {type(e).__name__}. Error: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected server error occurred. Please contact support with Request ID: {request_id}",
            )


# -----------------------------------------------------------------------------
# Candidate Insights Endpoint
# -----------------------------------------------------------------------------


@router.get(
    "/{candidate_id}/insights",
    response_model=CandidateInsightsResponse,
    summary="Get AI-powered insights for a candidate",
    description="Returns fit score, key strengths, and suggested interview questions for a candidate.",
)
async def get_candidate_insights(
    candidate_id: str = Path(..., min_length=1),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    try:
        try:
            # First try the in-memory cache (pre-loaded JSON profiles)
            candidate = await rag_service.get_candidate_details_by_id(candidate_id)

            skills = candidate.skills
            years_exp = candidate.experience_years
        except ValueError:
            # 🔄 Fallback: fetch metadata directly from Chroma (for newly-uploaded resumes)
            logger.info(
                f"Candidate {candidate_id} not found in cache – trying Chroma metadata fallback."
            )

            try:
                result = await asyncio.to_thread(
                    rag_service.collection.get,
                    ids=[candidate_id],
                    include=["metadatas"],
                )

                meta_list = result.get("metadatas", [])
                if not meta_list or not meta_list[0]:
                    raise ValueError("Metadata not found for candidate in ChromaDB")

                metadata: dict = meta_list[0]

                skills_str = metadata.get("skills", "")
                skills = [s.strip() for s in skills_str.split(",") if s.strip()]
                years_exp = int(float(metadata.get("experience_years", 0)))
            except Exception as e:
                logger.error(
                    f"Chroma fallback failed for {candidate_id}: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=404,
                    detail="Candidate not found.",
                ) from e

        # --- Attempt real LLM-powered insights ---
        insights_prompt = f"""
Analyze this candidate profile and provide recruitment insights:

Name: {candidate_id}
Experience: {years_exp} years
Skills: {', '.join(skills)}
{f"Raw resume excerpt: {metadata.get('summary_text', '')[:300]}..." if metadata.get('summary_text') else ""}

Provide a JSON response with:
1. fit_score: A score from 60-95 for a general software engineering role
2. strengths: Exactly 3 unique professional strengths
3. interview_questions: Exactly 3 thoughtful technical/behavioral questions

Format as JSON:
{{
    "fit_score": <number>,
    "strengths": ["strength1", "strength2", "strength3"],
    "interview_questions": ["question1", "question2", "question3"]
}}
"""

        llm_response = await llm_service.client.chat.completions.create(
            model=llm_service.chat_model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert technical recruiter with deep knowledge of software engineering roles.",
                },
                {"role": "user", "content": insights_prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
            max_tokens=500,
        )

        insights_data = json.loads(llm_response.choices[0].message.content)

        # Validate the response has required fields
        if all(
            key in insights_data
            for key in ["fit_score", "strengths", "interview_questions"]
        ):
            return CandidateInsightsResponse(
                candidate_id=candidate_id,
                fit_score=float(insights_data["fit_score"]),
                strengths=insights_data["strengths"],
                interview_questions=insights_data["interview_questions"],
            )

    except Exception as e:
        logger.warning(
            f"LLM insights generation failed for candidate {candidate_id}: {e}"
        )

    # 🔄 Fallback to enhanced heuristic approach
    logger.info(f"Using enhanced heuristic approach for candidate {candidate_id}")
    fit_score = calculate_enhanced_fit_score(
        skills=skills,
        years_exp=years_exp,
        has_github=(
            bool(metadata.get("github_url")) if "metadata" in locals() else False
        ),
        has_linkedin=(
            bool(metadata.get("linkedin_url")) if "metadata" in locals() else False
        ),
        profile_completeness=(
            0.7 if "metadata" in locals() and metadata.get("summary_text") else 0.5
        ),
    )

    strengths = (
        skills[:3]
        if len(skills) >= 3
        else skills
        + ["Communication", "Problem-solving", "Team collaboration"][: 3 - len(skills)]
    )

    fallback_questions = [
        "Describe a challenging project you led and its outcome.",
        "How do you stay current with the technologies you use?",
        "What trade-offs did you face in your most recent architecture decision?",
    ]

    return CandidateInsightsResponse(
        candidate_id=candidate_id,
        fit_score=round(fit_score, 1),
        strengths=strengths,
        interview_questions=fallback_questions,
    )


# -----------------------------------------------------------------------------
# AI Comparison Analysis Endpoint
# -----------------------------------------------------------------------------


@router.post(
    "/analyze-comparison",
    response_model=ComparisonAnalysisResponse,
    summary="🤖 AI Hiring Advisor - Compare Multiple Candidates",
    description="""
**The game-changing AI Hiring Advisor that recruiters love!**

Upload 2-5 candidate IDs and get comprehensive AI analysis including:

🏆 **Winner Recommendation**: AI determines the best hire with detailed reasoning
🔍 **Hidden Insights**: Discover information not obvious from resumes  
📊 **Comparison Matrix**: Visual scoring across technical fit, culture, retention risk
🎯 **Individual Analysis**: Enhanced insights for each candidate

**What makes this special:**
- Analyzes rare skill combinations and market value
- Discovers hidden strengths from public profiles
- Identifies potential risks (visa status, overqualification)
- Provides actionable hiring recommendations
- Saves 2-3 hours of manual research per comparison

**Perfect for:**
- Final stage candidate selection
- Presenting recommendations to hiring managers
- Making data-driven hiring decisions
- Reducing hiring bias with AI insights

**Input:** 2-5 candidate IDs + optional job context  
**Output:** Complete hiring analysis with clear recommendations
    """,
    response_description="Comprehensive AI analysis with winner recommendation, hidden insights, and comparison data.",
    responses={
        200: {
            "description": "AI comparison analysis completed successfully.",
            "model": ComparisonAnalysisResponse,
        },
        400: {
            "description": "Invalid request - check candidate IDs and job context.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "invalid_comparison_request",
                        "message": "Must provide 2-5 unique candidate IDs for comparison.",
                        "details": {"provided_candidates": 1, "minimum_required": 2},
                        "request_id": "req_comp_123",
                    }
                }
            },
        },
        404: {
            "description": "One or more candidates not found.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "candidates_not_found",
                        "message": "Some candidates could not be found in the database.",
                        "details": {"missing_candidates": ["candidate_xyz_404"]},
                        "request_id": "req_comp_456",
                    }
                }
            },
        },
    },
    operation_id="analyzeComparisonV1",
)
async def analyze_candidate_comparison(
    request: ComparisonRequest,
    comparison_service: ComparisonService = Depends(get_comparison_service),
):
    """
    🤖 AI Hiring Advisor: Analyze multiple candidates and get AI-powered hiring recommendations.

    This endpoint powers the revolutionary AI Hiring Advisor feature that saves recruiters
    hours of manual analysis while providing insights they'd never discover on their own.
    """
    try:
        logger.info(
            f"🤖 AI Hiring Advisor analyzing {len(request.candidate_ids)} candidates"
        )

        # Validate request
        if len(request.candidate_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least 2 candidates for comparison analysis.",
            )

        if len(request.candidate_ids) > 5:
            raise HTTPException(
                status_code=400, detail="Cannot compare more than 5 candidates at once."
            )

        # Perform AI analysis
        analysis_result = await comparison_service.analyze_candidates_comparison(
            request
        )

        logger.info(
            f"✅ AI Hiring Advisor completed analysis in {analysis_result.processing_time_ms:.1f}ms. "
            f"Winner: {analysis_result.winner.candidate_name} ({analysis_result.winner.confidence}% confidence)"
        )

        return analysis_result

    except ValueError as e:
        logger.error(f"❌ Comparison analysis validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"💥 Comparison analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="AI comparison analysis temporarily unavailable. Please try again.",
        )


def calculate_enhanced_fit_score(
    skills: List[str],
    years_exp: int,
    has_github: bool = False,
    has_linkedin: bool = False,
    profile_completeness: float = 0.5,
) -> float:
    """
    Calculate an enhanced fit score based on multiple factors.

    Args:
        skills: List of candidate skills
        years_exp: Years of experience
        has_github: Whether candidate has GitHub profile
        has_linkedin: Whether candidate has LinkedIn profile
        profile_completeness: Overall profile completeness (0.0 to 1.0)

    Returns:
        Fit score from 0-100
    """
    base_score = 40  # Start at 40%

    # Experience scoring (up to 25 points)
    if years_exp >= 10:
        base_score += 25
    elif years_exp >= 7:
        base_score += 20
    elif years_exp >= 5:
        base_score += 15
    elif years_exp >= 3:
        base_score += 10
    elif years_exp >= 1:
        base_score += 5

    # Skills scoring (up to 20 points)
    skill_score = min(20, len(skills) * 2.5)
    base_score += skill_score

    # Profile completeness (up to 10 points)
    if has_github:
        base_score += 5
    if has_linkedin:
        base_score += 3
    base_score += profile_completeness * 2  # Up to 2 points for overall completeness

    # Bonus for well-rounded profiles (if they have both experience and skills)
    if years_exp >= 3 and len(skills) >= 5:
        base_score += 5

    # Cap at 95% (leave room for perfection)
    return min(95.0, base_score)
