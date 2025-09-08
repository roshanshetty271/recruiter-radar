"""
Pydantic models for candidate data structures.

This module defines the core CandidateProfile model used throughout the RecruiterRadar MVP
for representing candidate information, skills, and resume data.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator, EmailStr


class CandidateProfile(BaseModel):
    """
    Core model representing a candidate's profile information.

    This model serves as the primary data structure for candidate information
    throughout the RAG pipeline, from data ingestion to search results.
    """

    id: str = Field(
        ..., description="Unique identifier for the candidate", example="candidate_001"
    )

    name: str = Field(
        ..., description="Full name of the candidate", example="Alex Johnson"
    )

    # Optional email – used for deduplication when uploading resumes
    email: Optional[EmailStr] = Field(
        None,
        description="Candidate's primary email address (used for deduplication)",
        example="alex.johnson@example.com",
    )

    raw_resume_text: str = Field(
        ...,
        description="The full, raw text content of the candidate's resume, used for generating embeddings.",
    )

    skills: List[str] = Field(
        default_factory=list,
        description="List of key skills extracted or provided for the candidate.",
    )

    experience_years: int = Field(
        ...,
        ge=0,
        le=60,  # Max 60 years, more realistic than 50
        description="Total years of relevant professional experience.",
    )

    visa_status: Optional[str] = Field(
        None,
        description="Current US visa or work authorization status (e.g., H1B, Green Card, US Citizen, F-1 OPT).",
    )

    location: Optional[str] = Field(
        None,
        description="Current city and state of residence or preferred location (e.g., San Francisco, CA).",
    )

    github_url: Optional[HttpUrl] = Field(
        None, description="Optional URL to the candidate's GitHub profile."
    )

    linkedin_url: Optional[HttpUrl] = Field(
        None, description="Optional URL to the candidate's LinkedIn profile."
    )

    # NEW: Store metadata from ChromaDB (including fast_path_extraction data)
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata from ChromaDB, including extracted resume data",
    )

    @validator("skills")
    def validate_skills_not_empty_strings(cls, v):
        """Ensure skills list doesn't contain empty strings."""
        return [skill.strip() for skill in v if skill.strip()]

    @validator("raw_resume_text")
    def validate_text_fields_not_empty(cls, v):
        """Ensure critical text fields are not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Text field cannot be empty")
        return v.strip()

    class Config:
        """Pydantic configuration for the CandidateProfile model."""

        json_schema_extra = {
            "example": {
                "id": "c001",
                "name": "Alex Chen",
                "email": "alex.chen@example.com",
                "raw_resume_text": "ALEX CHEN\nSoftware Engineer...\n\nEXPERIENCE...",
                "skills": ["Python", "React", "PostgreSQL", "Docker"],
                "experience_years": 5,
                "visa_status": "H1B",
                "location": "San Francisco, CA",
                "github_url": "https://github.com/alexchen",
                "linkedin_url": "https://linkedin.com/in/alex-chen-dev",
                "metadata": {
                    "fast_path_extraction": {
                        "work_experience": [],
                        "education": [],
                        "confidence": 0.9,
                    }
                },
            }
        }
        # If we want to allow arbitrary user data (not recommended for strict models)
        # extra = "allow"
        # Forbid extra fields to ensure data conformity
        extra = "forbid"
