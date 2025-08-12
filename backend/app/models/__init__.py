"""
RecruiterRadar MVP Pydantic Models Package.

This package contains all Pydantic models used throughout the RecruiterRadar application
for data validation, serialization, and API contract definition.

Models are organized into categories:
- candidate.py: Core candidate data structures
- api_models.py: API request/response models and query parameters
- query_models.py: Query intelligence and search intent models
- extraction_models.py: Resume parsing and data extraction models
"""

# Core candidate models
from .candidate import CandidateProfile

# API request/response models
from .api_models import (
    OutreachRequest,
    OutreachResponse,
    QueryResponseItem,
    SearchResponse,
    ErrorResponse,
    SearchQueryParams,
)

# Query intelligence models
from .query_models import (
    ExperienceLevel,
    RoleType,
    SkillCategory,
    LocationMatch,
    SkillMatch,
    QueryIntent,
    QueryEnhancementResult,
    SearchContext,
)

# Export all models for easy importing
__all__ = [
    # Candidate models
    "CandidateProfile",
    # API models
    "OutreachRequest",
    "OutreachResponse",
    "QueryResponseItem",
    "SearchResponse",
    "ErrorResponse",
    "SearchQueryParams",
    # Query intelligence models
    "ExperienceLevel",
    "RoleType",
    "SkillCategory",
    "LocationMatch",
    "SkillMatch",
    "QueryIntent",
    "QueryEnhancementResult",
    "SearchContext",
]
