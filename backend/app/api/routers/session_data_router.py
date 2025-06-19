"""
Session data endpoints for retrieving uploaded resumes and session status.

Provides access to processed resumes and session metrics.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.models.api_models import ErrorResponse
from app.models.upload_models import ExtractedResumeData
from app.services.session_service import SessionService
from app.services.rag_service import RAGService
from app.dependencies import get_session_service, get_rag_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Session"])


@router.get(
    "/{session_id}/resumes",
    response_model=List[ExtractedResumeData],
    summary="Get all uploaded resumes for session",
    description="""
Retrieve all successfully processed resumes for a session.

Used by the frontend to display uploaded candidates before
any search is performed.
    """,
)
async def get_session_resumes(
    session_id: str = Path(..., description="Session identifier"),
    rag_service: RAGService = Depends(get_rag_service),
) -> List[ExtractedResumeData]:
    """Get all resumes uploaded in this session."""
    try:
        # Query all candidates for this session
        results = await rag_service.search_resumes_by_filters(
            session_id=session_id,
            filters={},  # No filters - get all
            limit=50,  # Reasonable limit for UI
        )

        # Convert to ExtractedResumeData format
        resumes = []
        for candidate in results:
            resume = ExtractedResumeData(
                name=candidate["name"],
                title=candidate["title"],
                skills=candidate["skills"],
                location=candidate.get("location", ""),
                experience_years=candidate.get("experience_years", 0),
                email=candidate.get("email"),
                phone=candidate.get("phone"),
                summary=candidate.get("summary"),
                visa_status=candidate.get("visa_status"),
            )
            resumes.append(resume)

        logger.info(f"Retrieved {len(resumes)} resumes for session {session_id}")
        return resumes

    except Exception as e:
        logger.error(f"Error retrieving session resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="retrieval_error", message="Failed to retrieve uploaded resumes"
            ).model_dump(),
        )


@router.get(
    "/{session_id}/status",
    summary="Get session status and limits",
    description="Returns current usage and remaining limits for uploads and messages",
    response_model=dict,
)
async def get_session_status(
    session_id: str = Path(..., description="Session identifier"),
    session_service: SessionService = Depends(get_session_service),
) -> dict:
    """Get current session usage and limits."""
    try:
        upload_count = await session_service.get_upload_count(session_id)
        message_count = await session_service.get_message_count(session_id)

        return {
            "session_id": session_id,
            "uploads": {
                "used": upload_count,
                "limit": settings.max_uploads_per_session,
                "remaining": settings.max_uploads_per_session - upload_count,
            },
            "messages": {
                "used": message_count,
                "limit": settings.max_chat_messages_per_session,
                "remaining": settings.max_chat_messages_per_session - message_count,
            },
            "features": {
                "smart_chunking_enabled": settings.enable_smart_chunking,
                "query_suggestions_enabled": settings.enable_query_suggestions,
            },
        }

    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="status_error", message="Failed to retrieve session status"
            ).model_dump(),
        )
