"""
Data models for resume chunking functionality.

These models support the ETL pipeline for processing larger resumes
by breaking them into semantic chunks with individual embeddings.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChunkType(str, Enum):
    """Types of resume chunks for semantic understanding."""

    HEADER = "header"  # Name, contact, summary
    EXPERIENCE = "experience"  # Work history
    EDUCATION = "education"  # Academic background
    SKILLS = "skills"  # Technical skills
    MIXED = "mixed"  # General content
    FULL = "full"  # Entire resume (for small docs)


class ChunkMetadata(BaseModel):
    """Metadata for a single resume chunk."""

    chunk_id: str = Field(
        ...,
        description="Unique identifier for this chunk",
        example="upload_device123_abc_chunk_0",
    )

    parent_id: str = Field(
        ...,
        description="Parent candidate ID this chunk belongs to",
        example="upload_device123_abc",
    )

    chunk_type: ChunkType = Field(..., description="Semantic type of this chunk")

    chunk_index: int = Field(
        ..., ge=0, description="Position of this chunk in the resume"
    )

    total_chunks: int = Field(
        ..., ge=1, description="Total number of chunks for this resume"
    )

    char_count: int = Field(..., ge=0, description="Number of characters in this chunk")

    is_primary: bool = Field(
        default=False, description="Whether this is the primary chunk for display"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this chunk was created"
    )


class ChunkedResumeResult(BaseModel):
    """Result of chunking a resume."""

    chunks: List[Dict[str, Any]] = Field(
        ..., description="List of chunks with content and metadata"
    )

    chunk_count: int = Field(..., ge=1, description="Number of chunks created")

    total_chars: int = Field(
        ..., ge=0, description="Total characters in original resume"
    )

    chunking_strategy: str = Field(..., description="Strategy used for chunking")

    primary_chunk_index: int = Field(
        default=0, ge=0, description="Index of the primary chunk"
    )
