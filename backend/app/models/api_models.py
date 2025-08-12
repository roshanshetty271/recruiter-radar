"""
API Models for RecruiterRadar

These Pydantic models define the API contract between frontend and backend.
Designed with future extensibility in mind while supporting MVP functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from pydantic import BaseModel, Field, validator, model_validator
from .candidate import CandidateProfile
from .extraction_models import ExtractedResumeData
from pydantic import EmailStr  # Local import to avoid top-level circular issues


# ============= Search Validation Models =============


class SearchQueryValidation(BaseModel):
    """Validation model for search query parameters with comprehensive error handling"""

    query: str = Field(
        "", min_length=0, max_length=200, description="Natural language search query"
    )
    page: int = Field(1, ge=1, le=1000, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")
    limit: Optional[int] = Field(
        None, ge=1, le=100, description="Legacy limit parameter"
    )
    visa_status: Optional[str] = Field(
        None, max_length=50, description="Visa status filter"
    )
    location: Optional[str] = Field(None, max_length=100, description="Location filter")
    min_experience: Optional[int] = Field(
        None, ge=0, le=50, description="Minimum years of experience"
    )
    skills: Optional[str] = Field(
        None, max_length=500, description="Comma-separated skills list"
    )

    @validator("query")
    def validate_query_content(cls, v):
        """Validate query content for potentially problematic characters"""
        if not v:
            return v

        # Check for suspicious patterns that might cause issues
        dangerous_patterns = [
            r"<script",
            r"javascript:",
            r"data:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
        ]

        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, v_lower):
                raise ValueError(
                    f"Query contains potentially unsafe content: {pattern}"
                )

        # Check for excessive special characters
        special_char_count = len(re.findall(r"[<>{}[\]\\|]", v))
        if special_char_count > 5:
            raise ValueError(
                "Query contains too many special characters that may affect search quality"
            )

        return v.strip()

    @validator("visa_status")
    def validate_visa_status(cls, v):
        """Validate visa status against known values"""
        if not v:
            return v

        valid_visa_statuses = {
            "us citizen",
            "us_citizen",
            "citizen",
            "h1b",
            "h-1b",
            "h1-b",
            "green card",
            "green_card",
            "greencard",
            "permanent resident",
            "f1 opt",
            "f-1 opt",
            "opt",
            "f1",
            "f-1",
            "l1",
            "l-1",
            "l1a",
            "l1b",
            "e3",
            "e-3",
            "tn",
            "tn visa",
            "o1",
            "o-1",
            "student",
            "work authorization",
            "pending",
            "requires sponsorship",
        }

        v_normalized = v.lower().strip()
        if v_normalized not in valid_visa_statuses:
            # Don't raise error, just log warning for now (MVP approach)
            pass

        return v.strip()

    @validator("location")
    def validate_location(cls, v):
        """Validate location string"""
        if not v:
            return v

        # Basic sanity checks
        if len(v) < 2:
            raise ValueError("Location must be at least 2 characters")

        # Check for obvious nonsense
        if re.match(r'^[0-9!@#$%^&*()_+={}[\]|\\:";\'<>?,./]*$', v):
            raise ValueError(
                "Location appears to contain only numbers or special characters"
            )

        return v.strip()

    @validator("skills")
    def validate_skills_format(cls, v):
        """Validate skills format and content"""
        if not v:
            return v

        v = v.strip()
        if not v:
            return v

        # Split by common delimiters
        skills_list = re.split(r"[,;|]+", v)
        skills_list = [skill.strip() for skill in skills_list if skill.strip()]

        if len(skills_list) > 20:
            raise ValueError("Too many skills specified (maximum 20)")

        # Validate individual skills
        for skill in skills_list:
            if len(skill) < 1:
                continue
            if len(skill) > 50:
                raise ValueError(f"Skill '{skill}' is too long (maximum 50 characters)")
            if re.match(r'^[0-9!@#$%^&*()_+={}[\]|\\:";\'<>?,./]*$', skill):
                raise ValueError(
                    f"Skill '{skill}' appears to contain only numbers or special characters"
                )

        # Return cleaned up skills
        return ",".join(skills_list)

    @model_validator(mode="after")
    def validate_pagination_logic(self):
        """Validate pagination parameters work together correctly"""
        page = self.page
        page_size = self.page_size
        limit = self.limit

        # If both limit and page_size are provided, ensure they don't conflict
        if limit is not None and page != 1:
            raise ValueError("Cannot use 'limit' parameter with pagination (page > 1)")

        # Validate reasonable pagination bounds
        total_requested = page * page_size
        if total_requested > 10000:
            raise ValueError("Requested page would exceed maximum results (10,000)")

        return self

    class Config:
        json_json_schema_extra = {
            "example": {
                "query": "Python developers with AI experience",
                "page": 1,
                "page_size": 20,
                "visa_status": "US Citizen",
                "location": "San Francisco",
                "min_experience": 3,
                "skills": "Python,FastAPI,Docker",
            }
        }


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
        json_schema_extra = {
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
        json_schema_extra = {
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


# NEW: Pagination Models
class PaginationInfo(BaseModel):
    """Pagination metadata for search results"""

    current_page: int = Field(..., ge=1, description="Current page number (1-based)")
    page_size: int = Field(..., ge=1, le=100, description="Number of results per page")
    total_candidates: int = Field(
        ..., ge=0, description="Total number of matching candidates"
    )
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    start_index: int = Field(
        ..., ge=0, description="0-based index of first result on this page"
    )
    end_index: int = Field(
        ..., ge=0, description="0-based index of last result on this page"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "current_page": 2,
                "page_size": 20,
                "total_candidates": 95,
                "total_pages": 5,
                "has_next": True,
                "has_previous": True,
                "start_index": 20,
                "end_index": 39,
            }
        }


class SearchMetadata(BaseModel):
    """Enhanced metadata about the search operation"""

    query: str = Field(..., description="Original search query")
    processing_time_ms: float = Field(
        ..., description="Total processing time in milliseconds"
    )
    filters_applied: Dict[str, Any] = Field(
        ..., description="Filters that were applied to the search"
    )
    ai_confidence: float = Field(
        ..., ge=0, le=1, description="AI confidence in query interpretation"
    )
    semantic_themes: List[str] = Field(
        [], description="Identified semantic themes in the query"
    )
    suggested_refinements: List[str] = Field(
        [], description="Suggested query improvements"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Python developers with AI experience",
                "processing_time_ms": 245.7,
                "filters_applied": {"skills": "Python,FastAPI", "min_experience": 3},
                "ai_confidence": 0.89,
                "semantic_themes": ["AI/ML", "Backend Development"],
                "suggested_refinements": ["Consider adding location preference"],
            }
        }


class QueryResponseItem(BaseModel):
    """Individual candidate in search results"""

    id: str = Field(..., description="Unique candidate identifier")
    name: str = Field(..., description="Candidate's full name")
    email: Optional[EmailStr] = Field(None, description="Candidate's email address")
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
    """Enhanced response model for candidate search with pagination"""

    results: List[QueryResponseItem] = Field(
        ..., description="List of matching candidates on current page"
    )
    pagination: PaginationInfo = Field(..., description="Pagination metadata")
    search_metadata: SearchMetadata = Field(
        ..., description="Enhanced search operation metadata"
    )

    # Backward compatibility fields
    total_results: int = Field(
        ...,
        ge=0,
        description="Total number of results found (deprecated: use pagination.total_candidates)",
    )
    search_time_ms: float = Field(
        ...,
        description="Time taken for search in milliseconds (deprecated: use search_metadata.processing_time_ms)",
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
    search_metadata_legacy: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional search insights (legacy field, use search_metadata instead)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": "candidate_001",
                        "name": "Sarah Chen",
                        "email": "sarah.chen@example.com",
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
        json_schema_extra = {
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
    Enhanced model for search query parameters with pagination support.

    Used to validate and structure search parameters from query strings.
    """

    q: str = Field(
        ...,
        description="Search query string",
        min_length=1,
        max_length=500,
        example="Python developer with FastAPI experience",
    )

    # Pagination parameters
    page: Optional[int] = Field(
        1, description="Page number (1-based)", ge=1, le=1000, example=1
    )
    page_size: Optional[int] = Field(
        20, description="Number of results per page", ge=1, le=100, example=20
    )

    # Legacy parameter (for backward compatibility)
    limit: Optional[int] = Field(
        None,
        description="Legacy: Maximum number of results to return (deprecated: use page_size)",
        ge=1,
        le=100,
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

        json_json_schema_extra = {
            "example": {
                "q": "Python developer with 5+ years FastAPI experience",
                "limit": 10,
                "min_score": 0.3,
                "skills_filter": ["Python", "FastAPI", "Docker"],
            }
        }


# ============= Upload Models =============


class UploadResponse(BaseModel):
    """Enhanced response model for AI-powered resume upload"""

    success: bool = Field(..., description="Whether upload was successful")
    candidate_id: str = Field(..., description="Generated candidate ID")
    candidate_name: str = Field(..., description="Extracted candidate name")

    # AI-Enhanced extraction data
    extracted_data: ExtractedResumeData = Field(
        ..., description="Complete AI-extracted resume data"
    )

    # File metadata
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    processing_time_ms: float = Field(
        ..., description="Time taken to process file in milliseconds"
    )
    message: str = Field(..., description="Status message")

    # Backward compatibility fields (derived from extracted_data)
    extracted_skills: List[str] = Field(
        ..., description="Technical skills extracted from resume"
    )
    experience_years: int = Field(..., description="Total years of experience")
    location: Optional[str] = Field(None, description="Extracted location")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "candidate_id": "uploaded_a1b2c3d4",
                "candidate_name": "Alex Johnson",
                "extracted_data": {
                    "name": "Alex Johnson",
                    "email": "alex.johnson@email.com",
                    "phone": "+1-555-123-4567",
                    "location": "San Francisco, CA",
                    "current_title": "Senior Software Engineer",
                    "total_experience_years": 5.5,
                    "technical_skills": [
                        "Python",
                        "FastAPI",
                        "Docker",
                        "PostgreSQL",
                        "React",
                        "AWS",
                    ],
                    "soft_skills": ["Leadership", "Communication", "Problem Solving"],
                    "work_experience": [
                        {
                            "company": "TechCorp Inc",
                            "title": "Senior Software Engineer",
                            "duration": "2021 - Present",
                            "description": "Lead development of microservices architecture",
                            "technologies": ["Python", "FastAPI", "Docker"],
                        }
                    ],
                    "education": [
                        {
                            "degree": "Bachelor of Science",
                            "field": "Computer Science",
                            "school": "UC Berkeley",
                            "graduation_year": "2019",
                        }
                    ],
                    "github_url": "https://github.com/alexjohnson",
                    "linkedin_url": "https://linkedin.com/in/alexjohnson",
                    "professional_summary": "Experienced software engineer with expertise in Python and cloud technologies",
                    "extraction_confidence": 0.92,
                },
                "file_name": "alex_resume.pdf",
                "file_size": 245678,
                "processing_time_ms": 1234.56,
                "message": "Resume processed successfully. Alex Johnson is now searchable with 6 technical skills extracted (92% AI confidence).",
                "extracted_skills": [
                    "Python",
                    "FastAPI",
                    "Docker",
                    "PostgreSQL",
                    "React",
                    "AWS",
                ],
                "experience_years": 5,
                "location": "San Francisco, CA",
            }
        }


class UploadErrorResponse(BaseModel):
    """Error response for failed uploads"""

    success: bool = Field(False, description="Upload failed")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    file_name: Optional[str] = Field(None, description="Original filename if available")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "file_too_large",
                "message": "File size exceeds 10MB limit",
                "file_name": "large_resume.pdf",
                "details": {"max_size_mb": 10, "actual_size_mb": 15.2},
            }
        }


# ============= Batch Upload Models =============


class CandidatePreview(BaseModel):
    """Minimal info for a newly added candidate."""

    candidate_id: str = Field(..., description="Unique ID of the candidate")
    name: str = Field(..., description="Candidate name")
    email: Optional[EmailStr] = Field(None, description="Candidate email")
    top_skills: List[str] = Field([], description="Up to 5 key skills")


class CandidateUpdateInfo(BaseModel):
    """Info about an existing candidate that was updated (deduplicated)."""

    candidate_id: str
    name: str
    email: Optional[EmailStr] = None
    updated_fields: Optional[List[str]] = Field(
        None, description="Fields that were updated during deduplication"
    )


class FileError(BaseModel):
    """Represents a failure while processing a resume file."""

    file_name: str
    error: str
    message: Optional[str] = None


class BatchUploadStats(BaseModel):
    """Aggregated statistics for a batch upload."""

    total_files: int
    successful: int
    new_candidates: int
    duplicates_updated: int
    failed: int
    processing_time_seconds: float
    top_skills: Optional[List[str]] = None
    average_experience_years: Optional[float] = None


class BatchUploadResponse(BaseModel):
    """Response model for /upload-batch endpoint."""

    summary: str
    stats: BatchUploadStats
    added: List[CandidatePreview]
    updated: List[CandidateUpdateInfo]
    failed: List[FileError]


# ============= Enhanced Candidate Profile Models =============


class WorkExperienceItem(BaseModel):
    """Structured work experience item extracted from resume."""

    company: str = Field(..., description="Company/organization name")
    position: str = Field(..., description="Job title/position")
    duration: str = Field(
        ..., description="Duration of employment (e.g., 'March 2021 - Present')"
    )
    description: str = Field(..., description="Job description and achievements")
    technologies: List[str] = Field(
        default_factory=list, description="Technologies used in this role"
    )


class EducationItem(BaseModel):
    """Structured education item extracted from resume."""

    institution: str = Field(..., description="Educational institution name")
    degree: str = Field(..., description="Degree/certification obtained")
    field: Optional[str] = Field(None, description="Field of study")
    year: Optional[str] = Field(None, description="Graduation year or period")
    gpa: Optional[str] = Field(None, description="GPA if mentioned")


class EnhancedCandidateProfile(BaseModel):
    """Enhanced candidate profile with AI-extracted structured data."""

    # Basic information (from existing CandidateProfile)
    id: str
    name: str
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    experience_years: int
    skills: List[str]
    visa_status: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    raw_resume_text: Optional[str] = None

    # Enhanced structured data
    professional_summary: Optional[str] = Field(
        None, description="AI-extracted professional summary or objective"
    )
    current_title: Optional[str] = Field(
        None, description="Current or most recent job title"
    )
    work_experience: List[WorkExperienceItem] = Field(
        default_factory=list, description="Structured work experience history"
    )
    education: List[EducationItem] = Field(
        default_factory=list, description="Structured education history"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Professional certifications"
    )
    languages: List[str] = Field(
        default_factory=list, description="Programming and spoken languages"
    )
    key_achievements: List[str] = Field(
        default_factory=list, description="AI-identified key achievements"
    )

    # Extraction metadata
    extraction_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for AI extraction (0.0-1.0)",
    )
    has_structured_data: bool = Field(
        default=False, description="Whether structured data was successfully extracted"
    )
    extraction_timestamp: Optional[datetime] = Field(
        None, description="When the structured data was extracted"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "c001",
                "name": "Alex Chen",
                "email": "alex.chen@email.com",
                "location": "San Francisco, CA",
                "experience_years": 5,
                "skills": ["Python", "React", "PostgreSQL", "Docker"],
                "visa_status": "H1B",
                "professional_summary": "Experienced full-stack engineer with 5+ years building scalable web applications...",
                "current_title": "Senior Software Engineer",
                "work_experience": [
                    {
                        "company": "TechCorp Inc.",
                        "position": "Senior Software Engineer",
                        "duration": "March 2021 - Present",
                        "description": "Led migration of legacy monolith to microservices architecture...",
                        "technologies": ["Python", "React", "Kubernetes"],
                    }
                ],
                "education": [
                    {
                        "institution": "University of California, Berkeley",
                        "degree": "Bachelor of Science in Computer Science",
                        "field": "Computer Science",
                        "year": "2015-2019",
                    }
                ],
                "has_structured_data": True,
                "extraction_confidence": 0.92,
            }
        }


# ============= Candidate Insights Model =============


class CandidateInsightsResponse(BaseModel):
    """AI-generated insights for a single candidate profile."""

    candidate_id: str
    fit_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Overall fit score for last search context (0-100)",
    )
    strengths: List[str] = Field(
        ..., description="Top strengths or highlights identified"
    )
    interview_questions: List[str] = Field(
        ..., description="Suggested interview questions"
    )

    class Config:
        json_json_schema_extra = {
            "example": {
                "candidate_id": "candidate_abc123",
                "fit_score": 87.5,
                "strengths": [
                    "Expert in Python and FastAPI",
                    "Led migration to microservices at previous role",
                    "AWS Certified Solutions Architect",
                ],
                "interview_questions": [
                    "Describe a challenging API scalability problem you solved.",
                    "How do you design a CI/CD workflow for microservices?",
                    "Explain trade-offs between SQL and NoSQL you have encountered.",
                ],
            }
        }


# ============= AI Comparison Analysis Models =============


class HiddenInsight(BaseModel):
    """A discovered insight about a candidate that's not obvious from their resume."""

    candidate_id: str = Field(
        ..., description="ID of the candidate this insight relates to"
    )
    insight_type: str = Field(
        ..., description="Type of insight", example="rare_skill_combo"
    )
    title: str = Field(
        ...,
        description="Brief insight title",
        example="🔥 Rare combo: Only 3% of developers have React + Robotics",
    )
    description: str = Field(..., description="Detailed insight explanation")
    impact_level: str = Field(..., description="Impact level", example="high")

    class Config:
        json_json_schema_extra = {
            "example": {
                "candidate_id": "victor_chen_001",
                "insight_type": "rare_skill_combo",
                "title": "🔥 Rare combo: Only 3% of developers have React + Robotics",
                "description": "Victor's React + robotics combination exists in only 3% of the market, making him extremely valuable for autonomous systems roles.",
                "impact_level": "high",
            }
        }


class ComparisonMatrix(BaseModel):
    """Visual comparison matrix showing how candidates rank across different criteria."""

    technical_match: Dict[str, float] = Field(
        ..., description="Technical skill match percentages by candidate_id"
    )
    culture_fit: Dict[str, float] = Field(
        ..., description="Culture fit scores by candidate_id"
    )
    retention_risk: Dict[str, float] = Field(
        ..., description="Retention risk scores by candidate_id"
    )
    growth_potential: Dict[str, float] = Field(
        ..., description="Growth potential scores by candidate_id"
    )

    class Config:
        json_json_schema_extra = {
            "example": {
                "technical_match": {
                    "alex_chen": 61,
                    "victor_chen": 85,
                    "alex_popov": 26,
                },
                "culture_fit": {"alex_chen": 70, "victor_chen": 82, "alex_popov": 65},
                "retention_risk": {
                    "alex_chen": 30,
                    "victor_chen": 15,
                    "alex_popov": 45,
                },
                "growth_potential": {
                    "alex_chen": 75,
                    "victor_chen": 90,
                    "alex_popov": 60,
                },
            }
        }


class ComparisonWinner(BaseModel):
    """The AI's recommended candidate with reasoning."""

    candidate_id: str = Field(..., description="ID of the recommended candidate")
    candidate_name: str = Field(..., description="Name of the recommended candidate")
    confidence: float = Field(
        ..., ge=0, le=100, description="AI confidence in this recommendation (0-100)"
    )
    reasoning: str = Field(
        ..., description="AI's reasoning for why this candidate is the best choice"
    )
    key_advantages: List[str] = Field(
        ..., description="Top 3 key advantages of this candidate"
    )
    potential_risks: List[str] = Field(
        ..., description="Potential risks or concerns to consider"
    )

    class Config:
        json_json_schema_extra = {
            "example": {
                "candidate_id": "victor_chen_001",
                "candidate_name": "Victor Chen",
                "confidence": 89,
                "reasoning": "Victor's rare React + robotics combination is exactly what you need for autonomous systems work. His hidden GitHub activity shows real Tesla autopilot contributions that aren't on his resume.",
                "key_advantages": [
                    "Rare skill combination (React + Robotics) - only 3% market penetration",
                    "Hidden Tesla autopilot experience discovered in GitHub",
                    "Perfect technical fit for autonomous systems role",
                ],
                "potential_risks": [
                    "H1B sponsorship required",
                    "May have higher salary expectations due to rare skills",
                ],
            }
        }


class ComparisonRequest(BaseModel):
    """Request model for analyzing multiple candidates for comparison."""

    candidate_ids: List[str] = Field(
        ...,
        min_items=2,
        max_items=5,
        description="List of candidate IDs to compare (2-5 candidates)",
    )
    job_role_title: Optional[str] = Field(
        None,
        max_length=200,
        description="Job role title for context-aware analysis",
        example="Senior React Developer",
    )
    job_role_description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Job role description for better matching",
        example="Looking for someone to lead our autonomous vehicle UI development",
    )
    company_context: Optional[str] = Field(
        None,
        max_length=500,
        description="Company context for culture fit analysis",
        example="Fast-paced startup environment with autonomous vehicle focus",
    )

    @validator("candidate_ids")
    def validate_unique_candidates(cls, v):
        """Ensure all candidate IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Candidate IDs must be unique")
        return v

    class Config:
        json_json_schema_extra = {
            "example": {
                "candidate_ids": ["alex_chen_001", "victor_chen_001", "alex_popov_001"],
                "job_role_title": "Senior React Developer",
                "job_role_description": "Lead our autonomous vehicle UI development team",
                "company_context": "Fast-paced startup focused on autonomous vehicle technology",
            }
        }


class ComparisonAnalysisResponse(BaseModel):
    """Complete AI analysis response for candidate comparison."""

    # Core recommendation
    winner: ComparisonWinner = Field(
        ..., description="AI's recommended candidate with reasoning"
    )

    # Individual candidate insights (reusing existing structure!)
    candidates: List[CandidateInsightsResponse] = Field(
        ..., description="Individual insights for each candidate being compared"
    )

    # Advanced comparison features
    hidden_insights: List[HiddenInsight] = Field(
        ..., description="Discovered insights that aren't obvious from resumes"
    )
    comparison_matrix: ComparisonMatrix = Field(
        ..., description="Visual comparison scores across key criteria"
    )

    # Meta information
    analysis_timestamp: datetime = Field(
        ..., description="When this analysis was generated"
    )
    processing_time_ms: float = Field(
        ..., description="Time taken to analyze in milliseconds"
    )
    job_context: Optional[str] = Field(
        None, description="Job role context used for analysis"
    )
    ai_confidence: float = Field(
        ..., ge=0, le=1, description="Overall AI confidence in the analysis"
    )

    class Config:
        json_json_schema_extra = {
            "example": {
                "winner": {
                    "candidate_id": "victor_chen_001",
                    "candidate_name": "Victor Chen",
                    "confidence": 89,
                    "reasoning": "Victor's rare React + robotics combination is exactly what you need...",
                    "key_advantages": [
                        "Rare skill combination",
                        "Hidden Tesla experience",
                    ],
                    "potential_risks": ["H1B sponsorship required"],
                },
                "candidates": [
                    {
                        "candidate_id": "victor_chen_001",
                        "fit_score": 89,
                        "strengths": ["React + Robotics expertise", "Tesla background"],
                        "interview_questions": [
                            "Describe your autonomous systems experience"
                        ],
                    }
                ],
                "hidden_insights": [
                    {
                        "candidate_id": "victor_chen_001",
                        "insight_type": "github_discovery",
                        "title": "🚀 Hidden Tesla autopilot contributions",
                        "description": "GitHub shows contributions to Tesla autopilot that aren't on resume",
                        "impact_level": "high",
                    }
                ],
                "comparison_matrix": {
                    "technical_match": {"victor_chen_001": 89, "alex_chen_001": 72},
                    "culture_fit": {"victor_chen_001": 85, "alex_chen_001": 78},
                    "retention_risk": {"victor_chen_001": 15, "alex_chen_001": 25},
                    "growth_potential": {"victor_chen_001": 92, "alex_chen_001": 80},
                },
                "analysis_timestamp": "2024-01-15T10:30:00Z",
                "processing_time_ms": 8500.5,
                "job_context": "Senior React Developer for autonomous vehicles",
                "ai_confidence": 0.89,
            }
        }
