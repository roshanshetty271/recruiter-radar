"""
Pydantic models for candidate data structures.

This module defines the core CandidateProfile model used throughout the RecruiterRadar MVP
for representing candidate information, skills, and resume data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator


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

    summary_text: str = Field(
        ...,
        description="Professional summary or bio text used for embeddings",
        example="Senior Software Engineer with 5 years of experience...",
    )

    raw_resume_text: str = Field(
        ...,
        description="Complete raw resume content for detailed analysis",
        example="Alex Johnson\nSenior Software Engineer\n\nExperience:\n...",
    )

    skills: List[str] = Field(
        default_factory=list,
        description="List of technical and professional skills",
        example=["Python", "FastAPI", "React", "Machine Learning"],
    )

    experience_years: Optional[int] = Field(
        None, description="Years of professional experience", ge=0, le=50, example=5
    )

    education: Optional[str] = Field(
        None,
        description="Educational background",
        example="B.S. Computer Science, Stanford University",
    )

    location: Optional[str] = Field(
        None,
        description="Current location or preferred work location",
        example="San Francisco, CA",
    )

    visa_status: Optional[str] = Field(
        None, description="Work authorization status", example="US Citizen"
    )

    contact_info: Optional[str] = Field(
        None,
        description="Contact information (email, phone, etc.)",
        example="alex.johnson@email.com",
    )

    @validator("skills")
    def validate_skills_not_empty_strings(cls, v):
        """Ensure skills list doesn't contain empty strings."""
        return [skill.strip() for skill in v if skill.strip()]

    @validator("summary_text", "raw_resume_text")
    def validate_text_fields_not_empty(cls, v):
        """Ensure critical text fields are not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Text field cannot be empty")
        return v.strip()

    class Config:
        """Pydantic configuration for the CandidateProfile model."""

        json_schema_extra = {
            "example": {
                "id": "candidate_001",
                "name": "Alex Johnson",
                "summary_text": "Senior Software Engineer with 5 years of experience in full-stack development, specializing in Python, React, and cloud technologies. Led multiple high-impact projects and mentored junior developers.",
                "raw_resume_text": "Alex Johnson\nSenior Software Engineer\n\nContact: alex.johnson@email.com | (555) 123-4567\n\nExperience:\n• Senior Software Engineer at TechCorp (2019-Present)\n• Software Engineer at StartupXYZ (2017-2019)\n\nSkills: Python, React, AWS, Docker, PostgreSQL",
                "skills": ["Python", "FastAPI", "React", "AWS", "Docker", "PostgreSQL"],
                "experience_years": 5,
                "education": "B.S. Computer Science, Stanford University",
                "location": "San Francisco, CA",
                "visa_status": "US Citizen",
                "contact_info": "alex.johnson@email.com",
            }
        }
