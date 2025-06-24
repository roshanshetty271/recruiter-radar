"""
Upload-specific Pydantic models for the RecruiterRadar MVP.

This module contains data models used in the resume upload and processing pipeline,
including LLM extraction results, PDF processing results, and API responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProcessingStatus(str, Enum):
    """Status of resume processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    PDF_ERROR = "pdf_error"
    EXTRACTION_ERROR = "extraction_error"
    PARTIAL_SUCCESS = "partial_success"


class ChatMessage(BaseModel):
    """Individual chat message in conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When message was sent"
    )
    function_call: Optional[Dict[str, Any]] = Field(
        None, description="Function call data if this was a function call"
    )
    candidates_returned: Optional[List[str]] = Field(
        None, description="Candidate IDs returned in this response (for context)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Show me Python developers",
                "timestamp": "2024-01-20T10:30:00Z",
            }
        }


class ExtractedResumeData(BaseModel):
    """
    Structured data extracted from a resume by the LLM.

    This is the output of the LLM extraction process and maps
    to the fields we want to store for each candidate.
    """

    name: str = Field(
        ..., description="Full name of the candidate", example="Sarah Chen"
    )

    title: str = Field(
        ...,
        description="Most recent or prominent job title",
        example="Senior Full Stack Developer",
    )

    skills: List[str] = Field(
        default_factory=list,
        description="List of 5-7 key technical skills",
        max_items=10,
        example=["Python", "React", "AWS", "Docker", "PostgreSQL"],
    )

    location: Optional[str] = Field(
        None, description="City, State format", example="San Francisco, CA"
    )

    experience_years: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Total years of professional experience",
        example=6,
    )

    email: Optional[str] = Field(
        None, description="Contact email if found", example="sarah.chen@example.com"
    )

    phone: Optional[str] = Field(
        None, description="Contact phone if found", example="555-0123"
    )

    summary: Optional[str] = Field(
        None,
        description="1-2 sentence professional summary",
        max_length=500,
        example="Experienced full-stack developer specializing in scalable web applications.",
    )

    @validator("skills", pre=True)
    def clean_skills(cls, v):
        """Ensure skills is always a list and clean up entries."""
        if isinstance(v, str):
            # Handle comma-separated string from LLM
            return [s.strip() for s in v.split(",") if s.strip()]
        elif isinstance(v, list):
            return [str(s).strip() for s in v if s and str(s).strip()]
        return []

    @validator("location", "email", "phone", "summary")
    def clean_optional_strings(cls, v):
        """Clean optional string fields."""
        if v and isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v

    def to_candidate_profile_dict(
        self, resume_text: str, candidate_id: str
    ) -> Dict[str, Any]:
        """
        Convert to dictionary format suitable for CandidateProfile creation.

        Args:
            resume_text: The full extracted resume text
            candidate_id: Generated unique ID for the candidate

        Returns:
            Dictionary with CandidateProfile fields
        """
        return {
            "id": candidate_id,
            "name": self.name,
            "raw_resume_text": resume_text,
            "skills": self.skills,
            "experience_years": self.experience_years,
            "visa_status": None,  # Not extracted by LLM for privacy
            "location": self.location,
            "github_url": None,  # Could be extracted in future
            "linkedin_url": None,  # Could be extracted in future
        }

    def to_chromadb_metadata(self) -> Dict[str, Any]:
        """
        Convert to ChromaDB-compatible metadata format.

        ChromaDB has specific requirements for metadata types,
        so we ensure everything is properly serialized.
        """
        return {
            "name": self.name,
            "title": self.title,
            "skills": ",".join(self.skills),  # ChromaDB prefers strings
            "location": self.location or "",
            "experience_years": self.experience_years,
            "email": self.email or "",
            "phone": self.phone or "",
            "summary": self.summary or "",
            "extracted_at": datetime.utcnow().isoformat(),
        }


class PDFExtractionResult(BaseModel):
    """Result of PDF text extraction attempt."""

    success: bool = Field(..., description="Whether extraction was successful")

    text: str = Field(default="", description="Extracted text content")

    error: Optional[str] = Field(None, description="Error message if extraction failed")

    page_count: int = Field(default=0, description="Number of pages in PDF")

    char_count: int = Field(default=0, description="Total characters extracted")

    @validator("char_count", always=True)
    def set_char_count(cls, v, values):
        """Automatically set char_count based on text length."""
        if "text" in values and values["text"]:
            return len(values["text"])
        return v


class UploadStatusResponse(BaseModel):
    """API response for a resume upload attempt."""

    filename: str = Field(..., description="Original filename of the uploaded PDF")

    status: ProcessingStatus = Field(..., description="Current processing status")

    message: str = Field(..., description="Human-readable status message")

    extracted_name: Optional[str] = Field(
        None, description="Candidate name if successfully extracted"
    )

    candidate_id: Optional[str] = Field(
        None, description="Unique ID for the stored candidate"
    )

    processing_time_ms: int = Field(
        default=0, description="Time taken to process in milliseconds"
    )

    operation_type: Optional[str] = Field(
        None,
        description="Whether this was an 'add' or 'update' operation",
        example="update",
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "filename": "sarah_chen_resume.pdf",
                "status": "success",
                "message": "✅ Successfully processed resume for Sarah Chen",
                "extracted_name": "Sarah Chen",
                "candidate_id": "upload_device123_a1b2c3d4",
                "processing_time_ms": 3247,
            }
        }


class SessionData(BaseModel):
    """
    Session tracking data for upload limits.

    For MVP, this is stored in-memory in the SessionService.
    """

    session_id: str = Field(..., description="Unique session identifier")

    upload_count: int = Field(
        default=0, ge=0, description="Number of uploads in this session"
    )

    message_count: int = Field(
        default=0, ge=0, description="Number of chat messages in this session"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the session was created"
    )

    last_activity: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity timestamp"
    )

    conversation_history: List[ChatMessage] = Field(
        default_factory=list, description="Conversation history for chat context"
    )

    def increment_uploads(self) -> None:
        """Increment upload count and update activity."""
        self.upload_count += 1
        self.last_activity = datetime.utcnow()

    def increment_messages(self) -> None:
        """Increment message count and update activity."""
        self.message_count += 1
        self.last_activity = datetime.utcnow()

    def is_expired(self, expiry_hours: int = 48) -> bool:
        """Check if session has expired."""
        age = datetime.utcnow() - self.created_at
        return age.total_seconds() > (expiry_hours * 3600)

    def add_message(
        self,
        role: str,
        content: str,
        function_call: Optional[Dict[str, Any]] = None,
        candidates_returned: Optional[List[str]] = None,
    ) -> None:
        """Add a message to conversation history."""
        message = ChatMessage(
            role=role,
            content=content,
            function_call=function_call,
            candidates_returned=candidates_returned,
        )
        self.conversation_history.append(message)
        self.last_activity = datetime.utcnow()

    def get_conversation_for_llm(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation history formatted for OpenAI API.

        Returns the last N messages in OpenAI format, excluding function call metadata.
        """
        recent_messages = (
            self.conversation_history[-max_messages:]
            if max_messages > 0
            else self.conversation_history
        )

        return [{"role": msg.role, "content": msg.content} for msg in recent_messages]

    def trim_conversation(self, max_messages: int = 10) -> None:
        """Keep only the most recent messages to prevent token overflow."""
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "device_abc123",
                "upload_count": 3,
                "message_count": 5,
                "created_at": "2024-01-20T10:30:00Z",
                "last_activity": "2024-01-20T11:45:00Z",
            }
        }
