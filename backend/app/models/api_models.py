"""
API Models for RecruiterRadar

These Pydantic models define the API contract between frontend and backend.
Designed with future extensibility in mind while supporting MVP functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator, model_validator
from .candidate import CandidateProfile


# ============= Outreach Models =============


class OutreachVariation(BaseModel):
    """Single outreach message variation (Future feature)"""

    tone: str = Field(..., description="Tone used for this variation")
    draft_message: str = Field(..., description="The generated outreach message")
    word_count: int = Field(..., description="Number of words in the message")
    character_count: int = Field(..., description="Number of characters in the message")
    personalization_score: Optional[float] = Field(
        None, ge=0, le=1, description="AI-assessed personalization level (0-1)"
    )


class OutreachRequest(BaseModel):
    """Request model for generating outreach messages"""

    job_role_title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the job role",
        example="Senior Python Developer",
    )
    job_role_description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed job description",
        example="Lead our AI initiatives and mentor junior developers...",
    )
    tone: str = Field(
        "professional and friendly",
        max_length=50,
        description="Tone for the message",
        example="professional and friendly",
    )
    company_context: Optional[str] = Field(
        None,
        max_length=1000,
        description="Company culture and context",
        example="Series B AI startup with strong engineering culture",
    )
    additional_instructions: Optional[str] = Field(
        None,
        max_length=500,
        description="Special personalization instructions",
        example="Emphasize remote work flexibility",
    )

    # Future-ready fields (not used in MVP backend logic)
    generate_variations: bool = Field(
        False, description="Generate multiple variations (coming soon)"
    )
    custom_tones: Optional[List[str]] = Field(
        None,
        max_items=5,
        description="Custom tone list (coming soon)",
        example=["professional", "enthusiastic", "casual"],
    )

    @validator("job_role_title")
    def validate_job_role_title_not_empty(cls, v):
        """Ensure job role title is meaningful."""
        if not v or not v.strip():
            raise ValueError("Job role title cannot be empty")
        return v.strip()

    @validator("tone")
    def validate_tone_not_empty(cls, v):
        """Ensure tone is not empty."""
        if not v or not v.strip():
            raise ValueError("Tone cannot be empty")
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "job_role_title": "Senior Python Developer",
                "job_role_description": "Lead our AI initiatives",
                "tone": "professional and friendly",
                "company_context": "YC-backed startup disrupting recruiting",
                "additional_instructions": "Mention their RAG experience",
                "generate_variations": False,
            }
        }


class OutreachResponse(BaseModel):
    """Response model for outreach generation"""

    # Core MVP fields
    draft_message: str = Field(..., description="Primary outreach message")
    candidate_name: str = Field(..., description="Name of the candidate")
    candidate_id: str = Field(..., description="Unique candidate identifier")
    job_role_title: str = Field(..., description="Target job role")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    generation_time_ms: float = Field(
        ..., description="Time taken to generate in milliseconds"
    )
    word_count: int = Field(..., description="Number of words in the message")
    character_count: int = Field(..., description="Number of characters in the message")
    tone_used: str = Field(..., description="Tone used for generation")
    personalization_elements: Optional[List[str]] = Field(
        None,
        description="Key personalization elements identified in the message",
        example=[
            "5 years Python experience",
            "FAANG background",
            "Open source contributor",
        ],
    )

    # Future-ready fields (will be None/defaults in MVP)
    variations: Optional[List[OutreachVariation]] = Field(
        None, description="Alternative message variations with different tones"
    )
    total_variations_generated: int = Field(
        1, description="Total number of variations generated"
    )
    recommended_variation_index: Optional[int] = Field(
        None, description="AI-recommended best variation (0-based index)"
    )

    class Config:
        schema_extra = {
            "example": {
                "draft_message": "Hi Sarah,\\n\\nYour 5 years of experience building Python applications...",
                "candidate_name": "Sarah Chen",
                "candidate_id": "candidate_001",
                "job_role_title": "Senior Python Developer",
                "generated_at": "2024-01-15T10:30:00Z",
                "generation_time_ms": 1456.23,
                "word_count": 156,
                "character_count": 892,
                "tone_used": "professional and friendly",
                "personalization_elements": [
                    "5 years Python experience",
                    "AI/ML background",
                ],
                "variations": None,
                "total_variations_generated": 1,
                "recommended_variation_index": None,
            }
        }


# ============= Search/Query Models =============


class QueryResponseItem(BaseModel):
    """Individual candidate in search results"""

    id: str = Field(..., description="Unique candidate identifier")
    name: str = Field(..., description="Candidate's full name")
    skills: List[str] = Field(..., description="List of candidate's skills")
    experience_years: int = Field(..., description="Years of experience")
    location: str = Field(..., description="Candidate's location")
    visa_status: str = Field(..., description="Visa/work authorization status")
    match_context: str = Field(
        ...,
        description="Relevant excerpt from resume showing why they match",
        example="...5 years developing scalable Python applications using FastAPI...",
    )
    relevance_score: float = Field(
        ..., ge=0, le=1, description="Relevance score (0-1) based on query match"
    )
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")

    @validator("relevance_score")
    def round_relevance_score(cls, v):
        """Round relevance score to 3 decimal places"""
        return round(v, 3)


class SearchResponse(BaseModel):
    """Response model for candidate search"""

    results: List[QueryResponseItem] = Field(
        ..., description="List of matching candidates"
    )
    total_results: int = Field(..., ge=0, description="Total number of results found")
    search_time_ms: float = Field(
        ..., description="Time taken for search in milliseconds"
    )

    # Enhanced fields for better UX
    query_interpretation: Optional[str] = Field(
        None,
        description="How the system interpreted the query (future feature)",
        example="Searching for: Python developers with 5+ years experience",
    )
    suggested_filters: Optional[Dict[str, Any]] = Field(
        None, description="Suggested filters based on query (future feature)"
    )
    search_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional search insights (future feature)"
    )

    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "id": "candidate_001",
                        "name": "Sarah Chen",
                        "skills": ["Python", "FastAPI", "Machine Learning"],
                        "experience_years": 5,
                        "location": "San Francisco, CA",
                        "visa_status": "US Citizen",
                        "match_context": "5 years developing Python applications...",
                        "relevance_score": 0.945,
                        "github_url": "https://github.com/sarahchen",
                        "linkedin_url": "https://linkedin.com/in/sarahchen",
                    }
                ],
                "total_results": 42,
                "search_time_ms": 156.7,
                "query_interpretation": None,
                "suggested_filters": None,
                "search_metadata": None,
            }
        }


# ============= Error Models =============


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

    class Config:
        schema_extra = {
            "example": {
                "error": "not_found",
                "message": "Candidate with ID 'candidate_999' not found",
                "details": {"candidate_id": "candidate_999"},
                "request_id": "req_123456",
            }
        }


# Query parameters model for search endpoint
class SearchQueryParams(BaseModel):
    """
    Model for search query parameters.

    Used to validate and structure search parameters from query strings.
    """

    q: str = Field(
        ...,
        description="Search query string",
        min_length=1,
        max_length=500,
        example="Python developer with FastAPI experience",
    )

    limit: Optional[int] = Field(
        10, description="Maximum number of results to return", ge=1, le=50, example=10
    )

    min_score: Optional[float] = Field(
        None,
        description="Minimum relevance score threshold (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        example=0.3,
    )

    skills_filter: Optional[List[str]] = Field(
        None,
        description="Filter results by specific skills",
        example=["Python", "FastAPI"],
    )

    @validator("q")
    def validate_query_not_empty(cls, v):
        """Ensure query is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()

    class Config:
        """Pydantic configuration for SearchQueryParams."""

        json_schema_extra = {
            "example": {
                "q": "Python developer with FastAPI experience",
                "limit": 10,
                "min_score": 0.3,
                "skills_filter": ["Python", "FastAPI"],
            }
        }


# ============= Chat Models (NEW) =============


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(
        ...,
        max_length=500,
        description="User's chat message/query",
        example="Show me Python developers with 5+ years experience",
    )

    # For future V2 - conversation history
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Previous messages in conversation (V2 feature)",
        example=[
            {"role": "user", "content": "Show me Python developers"},
            {"role": "assistant", "content": "I found 5 Python developers..."},
        ],
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    ai_message: str = Field(
        ...,
        description="AI's conversational response",
        example="I found 3 Python developers with 5+ years of experience. Here are the top matches:",
    )

    candidates: List[Dict[str, Any]] = Field(
        ...,
        description="List of matching candidates with full details",
        example=[
            {
                "id": "upload_device123_abc",
                "name": "Sarah Chen",
                "title": "Senior Python Developer",
                "skills": ["Python", "Django", "AWS"],
                "location": "San Francisco, CA",
                "experience_years": 6,
                "match_context": "Strong Python background with Django expertise...",
                "relevance_score": 0.95,
            }
        ],
    )

    query_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about how the query was processed",
        example={
            "parsed_filters": {"skills": ["Python"], "experience_years": {"$gte": 5}},
            "candidates_found": 3,
            "search_type": "filtered",
        },
    )

    remaining_messages: int = Field(
        ..., ge=0, description="Remaining chat messages for this session", example=7
    )

    processing_time_ms: int = Field(
        ..., ge=0, description="Time taken to process the chat request", example=1234
    )

    suggestions: Optional[List[str]] = Field(
        None,
        description="Suggested follow-up queries",
        example=[
            "Try: 'with Django experience'",
            "Try: 'in San Francisco'",
            "Try: 'who know AWS'",
        ],
    )

    # Bulletproof assistant fields
    source: Optional[str] = Field(
        None,
        description="Source of the response (assistant/fallback/emergency_fallback)",
        example="assistant",
    )

    response_time: Optional[float] = Field(
        None,
        description="Response time in seconds",
        example=2.45,
    )

    @model_validator(mode="before")
    @classmethod
    def ensure_candidate_fields_have_safe_defaults(cls, values):
        """Ensure all candidate fields have safe defaults."""
        candidates = values.get("candidates", [])

        for candidate in candidates:
            # Ensure required fields exist with safe defaults
            candidate.setdefault("id", f"candidate_{hash(str(candidate))}")
            candidate.setdefault("name", "Unknown Candidate")
            candidate.setdefault("title", "Unknown Role")
            candidate.setdefault("location", "Location not specified")
            candidate.setdefault("experience_years", 0)
            candidate.setdefault("relevance_score", 0.0)
            candidate.setdefault("match_score", candidate.get("relevance_score", 0.0))
            candidate.setdefault("visa_status", "Not specified")

            # Handle skills conversion FIRST, then set default
            skills = candidate.get("skills")
            if isinstance(skills, str):
                # Convert string to list (split by comma)
                candidate["skills"] = [
                    s.strip() for s in skills.split(",") if s.strip()
                ]
            elif isinstance(skills, list):
                # Already a list, keep as-is
                candidate["skills"] = skills
            else:
                # None, empty, or other invalid type - set to empty list
                candidate["skills"] = []

        return values


class BulletproofChatResponse(BaseModel):
    """Internal response model for bulletproof chat with detailed metadata"""

    ai_message: str = Field(..., description="AI's conversational response")
    candidates: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of matching candidates"
    )
    source: str = Field(
        ..., description="Source of the response (real_rag/fallback/cache/etc)"
    )
    response_time: float = Field(..., description="Response time in seconds")
    remaining_messages: int = Field(..., description="Remaining messages for session")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    success: bool = Field(
        default=True, description="Whether the operation was successful"
    )
