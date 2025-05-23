"""
RecruiterRadar MVP Pydantic Models Package.

This package contains all Pydantic models used throughout the RecruiterRadar application
for data validation, serialization, and API contract definition.

Models are organized into two main categories:
- candidate.py: Core candidate data structures
- api_models.py: API request/response models and query parameters
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
]
