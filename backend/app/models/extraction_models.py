from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WorkExperience(BaseModel):
    """Model for work experience extracted from resume."""

    company: str
    title: str
    duration: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)


class Education(BaseModel):
    """Model for education information extracted from resume."""

    degree: str
    field: str
    school: str
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None


class Project(BaseModel):
    """Model for project information extracted from resume."""

    name: str
    description: str
    technologies: List[str]
    url: Optional[str] = None


class ExtractedResumeData(BaseModel):
    """Comprehensive resume data extracted by AI."""

    # Personal Info
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    # Professional Info
    current_title: Optional[str] = None
    desired_roles: List[str] = Field(default_factory=list)
    total_experience_years: float = 0

    # Skills (AI extracts ALL, no hardcoded list!)
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)

    # Experience & Education
    work_experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    # Additional Info
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    clearance_level: Optional[str] = None

    # Online Presence
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    other_urls: List[str] = Field(default_factory=list)

    # AI-Generated Summary
    professional_summary: Optional[str] = None
    key_achievements: List[str] = Field(default_factory=list)

    # Metadata
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)

    @validator("work_experience")
    def validate_work_experience(cls, v):
        """Ensure we handle any number of jobs."""
        if len(v) > 20:  # Sanity check for extremely long careers
            logger.warning(f"Resume has {len(v)} work experiences - unusually high")
        return v

    @validator("technical_skills")
    def validate_technical_skills(cls, v):
        """Remove duplicates and clean skills."""
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in v:
            skill_clean = skill.strip()
            if skill_clean and skill_clean.lower() not in seen:
                seen.add(skill_clean.lower())
                unique_skills.append(skill_clean)
        return unique_skills

    @validator("soft_skills")
    def validate_soft_skills(cls, v):
        """Remove duplicates and clean soft skills."""
        seen = set()
        unique_skills = []
        for skill in v:
            skill_clean = skill.strip()
            if skill_clean and skill_clean.lower() not in seen:
                seen.add(skill_clean.lower())
                unique_skills.append(skill_clean)
        return unique_skills

    @validator("education")
    def validate_education(cls, v):
        """Handle multiple education entries."""
        if len(v) > 10:  # Sanity check
            logger.warning(f"Resume has {len(v)} education entries - unusually high")
        return v

    @validator("projects")
    def validate_projects(cls, v):
        """Handle multiple projects."""
        if len(v) > 50:  # Sanity check
            logger.warning(f"Resume has {len(v)} projects - unusually high")
        return v

    @validator("certifications")
    def validate_certifications(cls, v):
        """Remove duplicate certifications."""
        seen = set()
        unique_certs = []
        for cert in v:
            cert_clean = cert.strip()
            if cert_clean and cert_clean.lower() not in seen:
                seen.add(cert_clean.lower())
                unique_certs.append(cert_clean)
        return unique_certs
