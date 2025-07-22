"""
Query Intelligence Models

Pydantic models for query parsing, enhancement, and search intent representation.
These models support the intelligent semantic search system.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ExperienceLevel(str, Enum):
    """Experience level categories for candidates"""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class RoleType(str, Enum):
    """Common role categories for skill expansion"""

    FRONTEND_DEVELOPER = "frontend_developer"
    BACKEND_DEVELOPER = "backend_developer"
    FULLSTACK_DEVELOPER = "fullstack_developer"
    MOBILE_DEVELOPER = "mobile_developer"
    DEVOPS_ENGINEER = "devops_engineer"
    CLOUD_ENGINEER = "cloud_engineer"
    DATA_SCIENTIST = "data_scientist"
    DATA_ENGINEER = "data_engineer"
    ML_ENGINEER = "ml_engineer"
    QA_ENGINEER = "qa_engineer"
    PRODUCT_MANAGER = "product_manager"
    DESIGNER = "designer"
    SECURITY_ENGINEER = "security_engineer"
    GENERIC = "generic"


class SkillCategory(str, Enum):
    """Categories for organizing skills"""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD_PLATFORM = "cloud_platform"
    TOOL = "tool"
    METHODOLOGY = "methodology"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


class LocationMatch(BaseModel):
    """Represents a normalized location with metadata"""

    original_query: str = Field(..., description="Original location string from user")
    normalized_location: Optional[str] = Field(
        None, description="Cleaned, standardized location"
    )
    city: Optional[str] = Field(None, description="Extracted city name")
    state: Optional[str] = Field(None, description="Extracted state/province")
    country: Optional[str] = Field(None, description="Extracted country")
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in location parsing"
    )
    is_valid: bool = Field(
        default=False, description="Whether location is valid and usable"
    )
    suggested_radius_km: Optional[int] = Field(
        None, description="Suggested search radius in kilometers"
    )


class SkillMatch(BaseModel):
    """Represents a skill with metadata and confidence"""

    skill: str = Field(..., description="The skill name")
    category: Optional[SkillCategory] = Field(None, description="Skill category")
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in skill extraction"
    )
    is_exact_match: bool = Field(
        default=True, description="Whether this was explicitly mentioned or inferred"
    )
    synonyms: List[str] = Field(
        default_factory=list, description="Alternative names for this skill"
    )


class QueryIntent(BaseModel):
    """
    Structured representation of user search intent after LLM parsing.
    This is the core model for intelligent query understanding.
    """

    original_query: str = Field(..., description="The raw user query")

    # Role and experience
    role_type: Optional[RoleType] = Field(None, description="Detected role category")
    role_keywords: List[str] = Field(
        default_factory=list, description="Role-related keywords found"
    )
    experience_level: Optional[ExperienceLevel] = Field(
        None, description="Required experience level"
    )
    experience_years_min: Optional[int] = Field(
        None, ge=0, description="Minimum years of experience"
    )
    experience_years_max: Optional[int] = Field(
        None, ge=0, description="Maximum years of experience"
    )

    # Skills analysis
    required_skills: List[SkillMatch] = Field(
        default_factory=list, description="Must-have skills"
    )
    preferred_skills: List[SkillMatch] = Field(
        default_factory=list, description="Nice-to-have skills"
    )
    excluded_skills: List[str] = Field(
        default_factory=list, description="Skills to avoid"
    )

    # Location
    location_match: Optional[LocationMatch] = Field(
        None, description="Parsed location information"
    )

    # Search metadata
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall parsing confidence"
    )
    is_empty_query: bool = Field(
        default=False, description="Whether query was empty or generic"
    )
    parsing_errors: List[str] = Field(
        default_factory=list, description="Any issues during parsing"
    )

    # Additional filters
    additional_filters: Dict[str, Any] = Field(
        default_factory=dict, description="Other extracted filters"
    )

    @validator("experience_years_max")
    def validate_experience_range(cls, v, values):
        """Ensure max experience is greater than min experience"""
        if v is not None and "experience_years_min" in values:
            min_years = values["experience_years_min"]
            if min_years is not None and v < min_years:
                raise ValueError(
                    "Maximum experience years must be >= minimum experience years"
                )
        return v

    def has_skills_filter(self) -> bool:
        """Check if query contains skill-related filters"""
        return len(self.required_skills) > 0 or len(self.preferred_skills) > 0

    def has_location_filter(self) -> bool:
        """Check if query contains valid location filter"""
        return self.location_match is not None and self.location_match.is_valid

    def has_experience_filter(self) -> bool:
        """Check if query contains experience-related filters"""
        return (
            self.experience_level is not None
            or self.experience_years_min is not None
            or self.experience_years_max is not None
        )


class QueryEnhancementResult(BaseModel):
    """
    Result of query enhancement process, including the parsed intent
    and additional metadata about the enhancement process.
    """

    query_intent: QueryIntent = Field(..., description="Parsed query intent")
    processing_time_ms: float = Field(..., description="Time taken to process query")
    llm_tokens_used: Optional[int] = Field(None, description="LLM tokens consumed")
    fallback_used: bool = Field(
        default=False, description="Whether fallback parsing was used"
    )
    enhancement_version: str = Field(
        default="1.0", description="Version of enhancement algorithm"
    )

    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence query enhancement"""
        return self.query_intent.confidence_score >= 0.8 and not self.fallback_used


class SearchContext(BaseModel):
    """
    Additional context for search operations, including user preferences
    and search session information.
    """

    user_id: Optional[str] = Field(
        None, description="User identifier for personalization"
    )
    session_id: Optional[str] = Field(None, description="Search session identifier")
    previous_queries: List[str] = Field(
        default_factory=list, description="Previous queries in session"
    )
    search_preferences: Dict[str, Any] = Field(
        default_factory=dict, description="User search preferences"
    )
    max_results: int = Field(
        default=20, ge=1, le=100, description="Maximum results to return"
    )
    include_explanations: bool = Field(
        default=True, description="Whether to include match explanations"
    )
