"""
Pydantic models for API request and response structures.

This module defines all the models used for FastAPI endpoint request bodies,
response bodies, and error handling in the RecruiterRadar MVP.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, validator
from .candidate import CandidateProfile


class OutreachRequest(BaseModel):
    """
    Request model for generating personalized outreach messages.

    Used by the /generate_outreach endpoint to specify candidate and job details
    for LLM-powered draft generation.
    """

    candidate_id: str = Field(
        ...,
        description="Unique identifier of the candidate to generate outreach for",
        example="candidate_001",
    )

    job_role: str = Field(
        ...,
        description="Target job role/position for the outreach",
        example="Senior Python Developer",
    )

    company_name: Optional[str] = Field(
        None, description="Name of the hiring company", example="TechCorp Inc."
    )

    additional_context: Optional[str] = Field(
        None,
        description="Additional context or requirements for the outreach message",
        example="Remote work opportunity, equity compensation",
    )

    tone: Optional[str] = Field(
        "professional",
        description="Desired tone for the outreach message",
        example="friendly",
    )

    @validator("job_role")
    def validate_job_role_not_empty(cls, v):
        """Ensure job role is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Job role cannot be empty")
        return v.strip()

    @validator("tone")
    def validate_tone(cls, v):
        """Validate tone is one of allowed values."""
        if v:
            allowed_tones = ["professional", "friendly", "casual", "formal"]
            if v.lower() not in allowed_tones:
                raise ValueError(f"Tone must be one of: {', '.join(allowed_tones)}")
            return v.lower()
        return "professional"

    class Config:
        """Pydantic configuration for OutreachRequest."""

        json_schema_extra = {
            "example": {
                "candidate_id": "candidate_001",
                "job_role": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "additional_context": "Remote work opportunity with equity compensation",
                "tone": "professional",
            }
        }


class OutreachResponse(BaseModel):
    """
    Response model for generated outreach messages.

    Contains the AI-generated outreach draft and metadata about the generation process.
    """

    candidate_id: str = Field(
        ...,
        description="ID of the candidate the outreach was generated for",
        example="candidate_001",
    )

    candidate_name: str = Field(
        ..., description="Name of the candidate", example="Alex Johnson"
    )

    job_role: str = Field(
        ...,
        description="Target job role used in generation",
        example="Senior Python Developer",
    )

    outreach_draft: str = Field(
        ...,
        description="Generated personalized outreach message",
        example="Hi Alex, I came across your profile and was impressed by your experience...",
    )

    key_highlights: List[str] = Field(
        default_factory=list,
        description="Key candidate highlights mentioned in the outreach",
        example=[
            "5 years Python experience",
            "FastAPI expertise",
            "Cloud technologies",
        ],
    )

    generated_at: str = Field(
        ...,
        description="Timestamp when the outreach was generated (ISO format)",
        example="2024-01-15T10:30:00Z",
    )

    class Config:
        """Pydantic configuration for OutreachResponse."""

        json_schema_extra = {
            "example": {
                "candidate_id": "candidate_001",
                "candidate_name": "Alex Johnson",
                "job_role": "Senior Python Developer",
                "outreach_draft": "Hi Alex,\n\nI hope this message finds you well. I came across your profile and was impressed by your 5 years of experience in Python development, particularly your expertise with FastAPI and cloud technologies. We have an exciting Senior Python Developer opportunity at TechCorp Inc. that I believe would be a great match for your background.\n\nWould you be interested in learning more about this role? I'd love to schedule a brief call to discuss the details.\n\nBest regards,\n[Your Name]",
                "key_highlights": [
                    "5 years Python experience",
                    "FastAPI expertise",
                    "Cloud technologies",
                ],
                "generated_at": "2024-01-15T10:30:00Z",
            }
        }


class QueryResponseItem(BaseModel):
    """
    Model for individual candidate search results.

    Represents a single candidate match with relevance score and key information.
    """

    candidate: CandidateProfile = Field(
        ..., description="Complete candidate profile information"
    )

    relevance_score: float = Field(
        ...,
        description="Similarity/relevance score for the search query (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        example=0.85,
    )

    match_reasons: List[str] = Field(
        default_factory=list,
        description="Specific reasons why this candidate matched the query",
        example=["Python expertise", "5 years experience", "FastAPI skills"],
    )

    highlighted_text: Optional[str] = Field(
        None,
        description="Relevant text excerpt from candidate's profile",
        example="Senior Software Engineer with 5 years of experience in Python...",
    )

    class Config:
        """Pydantic configuration for QueryResponseItem."""

        json_schema_extra = {
            "example": {
                "candidate": {
                    "id": "candidate_001",
                    "name": "Alex Johnson",
                    "summary_text": "Senior Software Engineer with 5 years of experience...",
                    "raw_resume_text": "Alex Johnson\nSenior Software Engineer...",
                    "skills": ["Python", "FastAPI", "React"],
                    "experience_years": 5,
                },
                "relevance_score": 0.85,
                "match_reasons": [
                    "Python expertise",
                    "5 years experience",
                    "FastAPI skills",
                ],
                "highlighted_text": "Senior Software Engineer with 5 years of experience in Python and FastAPI",
            }
        }


class SearchResponse(BaseModel):
    """
    Complete response model for candidate search queries.

    Contains search results, metadata, and query information.
    """

    query: str = Field(
        ...,
        description="Original search query submitted",
        example="Python developer with FastAPI experience",
    )

    results: List[QueryResponseItem] = Field(
        default_factory=list,
        description="List of matching candidates ordered by relevance",
    )

    total_results: int = Field(
        ..., description="Total number of candidates found", ge=0, example=5
    )

    search_time_ms: float = Field(
        ...,
        description="Time taken to execute the search in milliseconds",
        ge=0,
        example=245.7,
    )

    filters_applied: Optional[Dict[str, Any]] = Field(
        None,
        description="Any filters that were applied to the search",
        example={"min_experience": 3, "skills": ["Python"]},
    )

    suggestions: Optional[List[str]] = Field(
        None,
        description="Suggested alternative search terms if results are limited",
        example=["Try 'backend developer'", "Consider 'full-stack engineer'"],
    )

    class Config:
        """Pydantic configuration for SearchResponse."""

        json_schema_extra = {
            "example": {
                "query": "Python developer with FastAPI experience",
                "results": [
                    {
                        "candidate": {
                            "id": "candidate_001",
                            "name": "Alex Johnson",
                            "skills": ["Python", "FastAPI", "React"],
                        },
                        "relevance_score": 0.85,
                        "match_reasons": ["Python expertise", "FastAPI skills"],
                    }
                ],
                "total_results": 1,
                "search_time_ms": 245.7,
                "filters_applied": None,
                "suggestions": None,
            }
        }


class ErrorResponse(BaseModel):
    """
    Standardized error response model for all API endpoints.

    Provides consistent error information across the RecruiterRadar API.
    """

    error: str = Field(
        ..., description="Error type or category", example="ValidationError"
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        example="The provided candidate ID was not found",
    )

    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details or context",
        example={"candidate_id": "invalid_id", "field": "candidate_id"},
    )

    timestamp: str = Field(
        ...,
        description="Timestamp when the error occurred (ISO format)",
        example="2024-01-15T10:30:00Z",
    )

    request_id: Optional[str] = Field(
        None,
        description="Unique identifier for the request (for debugging)",
        example="req_12345",
    )

    class Config:
        """Pydantic configuration for ErrorResponse."""

        json_schema_extra = {
            "example": {
                "error": "NotFoundError",
                "message": "Candidate with ID 'candidate_999' was not found",
                "details": {
                    "candidate_id": "candidate_999",
                    "available_candidates": 50,
                },
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_12345",
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
