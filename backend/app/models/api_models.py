"""
Pydantic models for API request and response structures.

This module defines all the models used for FastAPI endpoint request bodies,
response bodies, and error handling in the RecruiterRadar MVP.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, validator
from .candidate import CandidateProfile


class OutreachRequest(BaseModel):
    """Request model for generating personalized outreach messages."""

    job_role_title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Target job role/position title",
        example="Senior Python Developer",
    )

    job_role_description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Detailed description of the job role and key requirements",
        example="Build scalable microservices using FastAPI, design RESTful APIs, mentor junior developers",
    )

    tone: str = Field(
        "professional and friendly",
        min_length=1,
        max_length=50,
        description="Desired tone for the outreach message",
        example="enthusiastic and professional",
    )

    company_context: Optional[str] = Field(
        None,
        max_length=500,
        description="Context about the company/team culture",
        example="Fast-growing AI startup in Boston with a casual, innovation-focused culture",
    )

    additional_instructions: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional instructions for personalization",
        example="Emphasize remote work flexibility and equity compensation",
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
        """Pydantic configuration for OutreachRequest."""

        json_schema_extra = {
            "example": {
                "job_role_title": "Senior Python Developer",
                "job_role_description": "Looking for an experienced Python developer to lead our backend team, focusing on building scalable microservices using FastAPI and PostgreSQL. You will also be responsible for designing RESTful APIs and mentoring junior developers.",
                "tone": "enthusiastic and professional",
                "company_context": "We are a Series B startup revolutionizing the fintech space with a casual, innovation-focused culture.",
                "additional_instructions": "Please emphasize their experience with cloud platforms and RAG systems, and mention our remote work flexibility and equity compensation.",
            }
        }


class OutreachResponse(BaseModel):
    """Response model for generated outreach messages with rich metadata."""

    draft_message: str = Field(
        ...,
        description="Generated personalized outreach message",
        example="Hi Alex,\n\nI came across your profile and was truly impressed...",
    )

    candidate_name: str = Field(
        ..., description="Name of the candidate", example="Alex Johnson"
    )

    candidate_id: str = Field(
        ..., description="ID of the candidate", example="candidate_001"
    )

    job_role_title: str = Field(
        ...,
        description="Target job role used in generation",
        example="Senior Python Developer",
    )

    generated_at: str = Field(
        ..., description="ISO timestamp of generation", example="2024-01-15T10:30:00Z"
    )

    generation_time_ms: float = Field(
        ...,
        description="Time taken to generate the message in milliseconds",
        example=1250.5,
    )

    word_count: int = Field(
        ..., description="Word count of the generated message", example=156
    )

    character_count: int = Field(
        ..., description="Character count of the generated message", example=892
    )

    tone_used: str = Field(
        ...,
        description="The tone that was applied",
        example="professional and friendly",
    )

    personalization_elements: List[str] = Field(
        default_factory=list,
        description="Key elements from candidate profile used in personalization",
        example=["5 years Python experience", "FastAPI expertise", "Located in Boston"],
    )

    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score of the generation quality (future enhancement)",
        example=0.92,
    )

    class Config:
        """Pydantic configuration for OutreachResponse."""

        json_schema_extra = {
            "example": {
                "draft_message": "Dear Alex, your extensive background in Python, particularly with FastAPI, and your work on RAG systems at Innovate Solutions is precisely what we're seeking for our Senior Python Developer role. At TechCorp, a fast-growing AI startup in Boston with a casual, innovation-focused culture, you'd lead projects building scalable microservices. We offer remote work flexibility and equity compensation. Would you be open to discussing this further?",
                "candidate_name": "Alex Johnson",
                "candidate_id": "candidate_001",
                "job_role_title": "Senior Python Developer",
                "generated_at": "2024-07-05T14:30:00Z",
                "generation_time_ms": 1250.5,
                "word_count": 156,
                "character_count": 892,
                "tone_used": "enthusiastic and professional",
                "personalization_elements": [
                    "Python expertise",
                    "FastAPI experience",
                    "RAG systems knowledge",
                    "Located in Boston",
                ],
                "confidence_score": 0.92,
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

    # For MVP, raw_resume_text from candidate object will be used by frontend for context.
    # Frontend will handle highlighting based on original_query_terms from SearchResponse.
    # match_reasons and highlighted_text can be enhanced in V2 if backend logic is added.
    match_context: Optional[str] = Field(  # Renaming/clarifying highlighted_text
        None,
        description="Full raw resume text for frontend display and highlighting.",
        example="Alex Johnson\nSenior Software Engineer...",
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
                "match_context": "Alex Johnson\nSenior Software Engineer... (full text)",
            }
        }


class SearchResponse(BaseModel):
    """
    Response model for candidate search queries.

    Contains search results, metadata, query information, and search performance insights.
    """

    query: str = Field(
        ...,
        description="Original search query submitted by the user",
        example="Python developer with FastAPI experience",
    )

    original_query_terms: Optional[List[str]] = Field(
        None,
        description="Key terms extracted from the original query and skill filters, for frontend highlighting assist.",
        example=["python", "fastapi", "senior developer"],
    )

    results: List[QueryResponseItem] = Field(
        default_factory=list,
        description="List of matching candidates ordered by relevance",
    )

    retrieved_count_before_post_filter: int = Field(
        ...,
        description="Number of candidates retrieved from vector store before any post-filtering (e.g., skills matching) was applied.",
        ge=0,
        example=15,
    )

    final_count_after_post_filter: int = Field(
        ...,
        description="Total number of candidates returned after all filtering.",
        ge=0,
        example=5,
    )

    processing_time_ms: float = Field(
        ...,
        description="Time taken to execute the search and process results in milliseconds",
        ge=0,
        example=245.7,
    )

    query_interpretation_notes: Optional[str] = Field(
        None,
        description="Notes on how the query was interpreted or processed.",
        example="Searching for candidates with skills: Python, FastAPI. Location: Remote.",
    )

    filters_applied: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters applied to the search (e.g., visa_status, location, min_experience)",
        example={
            "min_experience": 3,
            "skills_query": ["python", "fastapi"],
            "location": "Remote",
        },
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
                "original_query_terms": ["python", "fastapi", "senior developer"],
                "results": [
                    {
                        "candidate": {
                            "id": "candidate_001",
                            "name": "Alex Johnson",
                            "skills": ["Python", "FastAPI", "React"],
                        },
                        "relevance_score": 0.85,
                        "match_context": "Alex Johnson\nSenior Software Engineer... (full text)",
                    }
                ],
                "retrieved_count_before_post_filter": 15,
                "final_count_after_post_filter": 5,
                "processing_time_ms": 245.7,
                "query_interpretation_notes": "Searching for candidates with skills: Python, FastAPI. Location: Remote.",
                "filters_applied": {
                    "min_experience": 3,
                    "skills_query": ["python", "fastapi"],
                    "location": "Remote",
                },
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
