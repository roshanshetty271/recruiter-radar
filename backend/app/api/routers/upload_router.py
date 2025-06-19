"""
API router for resume upload functionality.

Handles PDF upload, processing, and provides detailed status feedback
for each upload attempt.
"""

import time
import logging
import hashlib
from typing import Optional
import re

from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Depends, status

from app.core.config import settings
from app.models.upload_models import (
    UploadStatusResponse,
    ProcessingStatus,
    ExtractedResumeData,
)
from app.models.candidate import CandidateProfile
from app.models.api_models import ErrorResponse
from app.services.pdf_service import PDFService
from app.services.session_service import get_session_service, SessionService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.dependencies import get_llm_service, get_rag_service
from app.services.chunking_service import ChunkingService
from app.models.chunk_models import ChunkType, ChunkMetadata

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Upload limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


def generate_candidate_id(
    extracted_email: Optional[str], file_content: bytes, session_id: str
) -> str:
    """
    Generate deterministic candidate ID based on email or file hash.

    This ensures the same candidate (by email or exact file) gets the same ID,
    enabling updates instead of duplicates.

    Args:
        extracted_email: Email address extracted from resume (primary key)
        file_content: Raw PDF bytes for hash generation (fallback key)
        session_id: Session identifier (for namespacing)

    Returns:
        Deterministic candidate ID
    """
    if extracted_email:
        # Use email as primary identifier (normalized)
        normalized_email = extracted_email.lower().strip()
        email_hash = hashlib.sha256(normalized_email.encode()).hexdigest()[:12]
        return f"email_{session_id}_{email_hash}"
    else:
        # Fallback to file content hash
        file_hash = hashlib.sha256(file_content).hexdigest()[:12]
        return f"hash_{session_id}_{file_hash}"


def extract_email_from_text(text: str) -> Optional[str]:
    """
    Extract the first email address found in resume text.

    Args:
        text: Resume text content

    Returns:
        First email address found, or None
    """
    # Basic email regex - matches most professional email formats
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    matches = re.findall(email_pattern, text)

    if matches:
        # Return the first email found
        return matches[0].strip()

    return None


@router.post(
    "/resume",
    response_model=UploadStatusResponse,
    summary="Upload and process a resume",
    description="""
Upload a PDF resume for AI-powered processing and storage.

The system will:
1. Extract text from the PDF
2. Use AI to extract structured information (name, skills, experience, etc.)
3. Generate embeddings for semantic search
4. Store the resume for future search and outreach

**Requirements:**
- File must be PDF format
- Maximum size: 10MB
- Session ID required in X-Session-ID header
- Maximum 10 uploads per session

**Returns:**
Detailed status including extracted candidate name and processing time.
    """,
    responses={
        200: {
            "description": "Resume processed successfully",
            "model": UploadStatusResponse,
            "content": {
                "application/json": {
                    "example": {
                        "filename": "john_doe_resume.pdf",
                        "status": "success",
                        "message": "✅ Successfully processed resume for John Doe",
                        "extracted_name": "John Doe",
                        "candidate_id": "upload_device123_a1b2c3d4",
                        "processing_time_ms": 3892,
                    }
                }
            },
        },
        400: {
            "description": "Invalid file or missing session ID",
            "model": ErrorResponse,
        },
        413: {"description": "File size exceeds limit", "model": ErrorResponse},
        429: {
            "description": "Upload limit exceeded for session",
            "model": ErrorResponse,
        },
    },
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF resume file to upload"),
    session_id: Optional[str] = Header(
        None, alias="X-Session-ID", description="Unique session identifier"
    ),
    session_service: SessionService = Depends(get_session_service),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
) -> UploadStatusResponse:
    """
    Process uploaded resume with comprehensive error handling.

    Now supports smart chunking for large resumes when enabled.
    """
    start_time = time.time()

    # Validate session ID
    if not session_id:
        logger.warning("Upload attempted without session ID")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="missing_session_id",
                message="Session ID required in X-Session-ID header",
            ).model_dump(exclude_none=True),
        )

    # Check upload limit
    is_valid, error_msg = await session_service.validate_upload_limit(session_id)
    if not is_valid:
        logger.info(f"Session {session_id} exceeded upload limit")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error="upload_limit_exceeded",
                message=error_msg or "Upload limit exceeded",
            ).model_dump(exclude_none=True),
        )

    # Validate file type
    if not file.content_type or not PDFService.validate_content_type(file.content_type):
        logger.warning(f"Invalid file type uploaded: {file.content_type}")
        return UploadStatusResponse(
            filename=file.filename,
            status=ProcessingStatus.PDF_ERROR,
            message="❌ File must be PDF format",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Read and validate file size
    try:
        file_content = await file.read()
        file_size = len(file_content)

        # Validate size
        size_error = PDFService.validate_pdf_size(file_size)
        if size_error:
            logger.warning(f"File too large: {file_size} bytes")
            return UploadStatusResponse(
                filename=file.filename,
                status=ProcessingStatus.PDF_ERROR,
                message=f"❌ {size_error}",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    except Exception as e:
        logger.error(f"Error reading uploaded file: {str(e)}")
        return UploadStatusResponse(
            filename=file.filename,
            status=ProcessingStatus.PDF_ERROR,
            message="❌ Failed to read uploaded file",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Extract text from PDF
    logger.info(
        f"Processing PDF: {file.filename} ({file_size / 1024:.1f}KB) for session {session_id}"
    )
    pdf_result = await PDFService.extract_text_from_pdf(file_content)

    if not pdf_result.success:
        logger.warning(f"PDF extraction failed: {pdf_result.error}")
        return UploadStatusResponse(
            filename=file.filename,
            status=ProcessingStatus.PDF_ERROR,
            message=f"❌ {pdf_result.error}",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Log extraction details
    logger.info(
        f"PDF extraction successful: {pdf_result.char_count} chars from {pdf_result.page_count} pages"
    )

    # Extract email for candidate ID generation (before expensive LLM extraction)
    extracted_email = extract_email_from_text(pdf_result.text)
    logger.info(f"Email detected in resume: {'Yes' if extracted_email else 'No'}")

    # Generate deterministic candidate ID
    candidate_id = generate_candidate_id(extracted_email, file_content, session_id)

    # Check if this candidate already exists (delete-before-add for updates)
    try:
        was_updated = await rag_service.delete_candidate_if_exists(
            candidate_id, session_id
        )
        operation_type = "update" if was_updated else "add"
        logger.info(f"Candidate {candidate_id}: {operation_type} operation")
    except Exception as e:
        logger.warning(f"Could not check/delete existing candidate {candidate_id}: {e}")
        operation_type = "add"  # Proceed with add if delete check fails

    # Check if smart chunking is enabled
    if (
        settings.enable_smart_chunking
        and pdf_result.char_count > settings.embedding_text_limit
    ):
        logger.info(
            f"Using smart chunking for large resume ({pdf_result.char_count} chars)"
        )

        # Initialize chunking service
        chunking_service = ChunkingService()

        # Chunk the resume
        chunk_result = await chunking_service.chunk_resume(
            text=pdf_result.text, candidate_id=candidate_id, filename=file.filename
        )

        # Extract structured data from the primary chunk
        primary_chunk = chunk_result.chunks[chunk_result.primary_chunk_index]
        extraction_text = primary_chunk["content"]

        logger.info(
            f"Extracting structured data from primary chunk ({len(extraction_text)} chars)"
        )
        extracted_data = await llm_service.extract_structured_resume_data(
            extraction_text
        )

        # Handle extraction failure
        if not extracted_data:
            logger.warning(f"LLM extraction failed for {file.filename}")
            extracted_data = ExtractedResumeData(
                name="Unknown Candidate",
                title="Resume Processing Failed",
                skills=[],
                experience_years=0,
            )
            status = ProcessingStatus.EXTRACTION_ERROR
            message = "⚠️ Could not extract information from resume. File stored for manual review."
        else:
            status = ProcessingStatus.SUCCESS
            message = f"✅ Successfully {'updated' if operation_type == 'update' else 'processed'} resume for {extracted_data.name}"

        # Process each chunk
        chunks_stored = 0
        embedding_errors = []

        for i, chunk in enumerate(chunk_result.chunks):
            try:
                # Generate embedding for this chunk
                logger.info(
                    f"Generating embedding for chunk {i+1}/{chunk_result.chunk_count} "
                    f"({chunk['metadata']['char_count']} chars)"
                )
                embedding = await llm_service.get_embedding(chunk["content"])

                # Prepare metadata for this chunk
                chunk_metadata = extracted_data.to_chromadb_metadata()
                chunk_metadata.update(
                    {
                        "source": "upload",
                        "session_id": session_id,
                        "candidate_id": candidate_id,
                        "filename": file.filename,
                        "upload_status": status.value,
                        "page_count": pdf_result.page_count,
                        "chunk_id": chunk["chunk_id"],
                        "parent_id": candidate_id,
                        "chunk_type": chunk["metadata"]["chunk_type"],
                        "chunk_index": chunk["metadata"]["chunk_index"],
                        "total_chunks": chunk["metadata"]["total_chunks"],
                        "is_primary": chunk["metadata"]["is_primary"],
                    }
                )

                # Store chunk in ChromaDB
                await rag_service.add_candidate_to_collection(
                    candidate_id=chunk["chunk_id"],
                    embedding=embedding,
                    metadata=chunk_metadata,
                    document_text=chunk["content"],
                )
                chunks_stored += 1

            except Exception as e:
                logger.error(f"Failed to process chunk {i}: {str(e)}")
                embedding_errors.append(f"Chunk {i}: {str(e)[:50]}")

        # Check if we stored at least one chunk
        if chunks_stored == 0:
            logger.error("Failed to store any chunks")
            return UploadStatusResponse(
                filename=file.filename,
                status=ProcessingStatus.EXTRACTION_ERROR,
                message="❌ Failed to process resume for search",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Update message with chunk info
        if chunks_stored < chunk_result.chunk_count:
            status = ProcessingStatus.PARTIAL_SUCCESS
            message = f"⚠️ Partially processed {extracted_data.name} ({chunks_stored}/{chunk_result.chunk_count} chunks)"
        else:
            message = f"✅ Successfully processed {extracted_data.name} ({chunk_result.chunk_count} chunks indexed)"

    else:
        # Original single-embedding logic for small resumes
        logger.info("Using standard single-embedding processing")

        # Truncate text for LLM if needed
        resume_text = PDFService.truncate_text_for_llm(pdf_result.text)

        # Extract structured data
        logger.info(f"Extracting structured data from {len(resume_text)} chars")
        extracted_data = await llm_service.extract_structured_resume_data(resume_text)

        # Handle extraction failure
        if not extracted_data:
            logger.warning(f"LLM extraction failed for {file.filename}")
            extracted_data = ExtractedResumeData(
                name="Unknown Candidate",
                title="Resume Processing Failed",
                skills=[],
                experience_years=0,
            )
            status = ProcessingStatus.EXTRACTION_ERROR
            message = "⚠️ Could not extract information from resume. File stored for manual review."
        else:
            status = ProcessingStatus.SUCCESS
            message = f"✅ Successfully {'updated' if operation_type == 'update' else 'processed'} resume for {extracted_data.name}"

        # Generate embedding
        try:
            embedding_text = PDFService.truncate_text_for_embedding(pdf_result.text)
            logger.info(
                f"Generating embedding for {len(embedding_text)} chars (original: {len(pdf_result.text)})"
            )
            embedding = await llm_service.get_embedding(embedding_text)
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return UploadStatusResponse(
                filename=file.filename,
                status=ProcessingStatus.EXTRACTION_ERROR,
                message="❌ Failed to generate search embedding",
                extracted_name=extracted_data.name if extracted_data else None,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Prepare metadata
        metadata = extracted_data.to_chromadb_metadata()
        metadata.update(
            {
                "source": "upload",
                "session_id": session_id,
                "candidate_id": candidate_id,
                "filename": file.filename,
                "upload_status": status.value,
                "page_count": pdf_result.page_count,
            }
        )

        # Store in ChromaDB
        try:
            await rag_service.add_candidate_to_collection(
                candidate_id=candidate_id,
                embedding=embedding,
                metadata=metadata,
                document_text=pdf_result.text,
            )
        except Exception as e:
            logger.error(f"Failed to store resume in ChromaDB: {str(e)}")
            return UploadStatusResponse(
                filename=file.filename,
                status=ProcessingStatus.EXTRACTION_ERROR,
                message="❌ Failed to store resume data",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    # Increment upload count on successful storage
    await session_service.increment_upload_count(session_id)

    # Calculate processing time
    processing_time = int((time.time() - start_time) * 1000)

    logger.info(
        f"Upload complete: {file.filename} processed in {processing_time}ms "
        f"with status '{status.value}' for session {session_id}"
    )

    # Return response
    return UploadStatusResponse(
        filename=file.filename,
        status=status,
        message=message,
        extracted_name=(
            extracted_data.name if extracted_data.name != "Unknown Candidate" else None
        ),
        candidate_id=candidate_id,
        processing_time_ms=processing_time,
        operation_type=operation_type,
    )


@router.get(
    "/status",
    summary="Check upload service status",
    description="Get information about upload service configuration and limits",
    responses={
        200: {
            "description": "Upload service status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "operational",
                        "max_file_size_mb": 10,
                        "max_uploads_per_session": 10,
                        "supported_formats": ["pdf"],
                        "session_header": "X-Session-ID",
                    }
                }
            },
        }
    },
)
async def upload_service_status():
    """Get upload service configuration and status."""
    return {
        "status": "operational",
        "max_file_size_mb": settings.max_pdf_size_mb,
        "max_uploads_per_session": settings.max_uploads_per_session,
        "supported_formats": ["pdf"],
        "session_header": "X-Session-ID",
        "session_expiry_hours": settings.session_expiry_hours,
    }
