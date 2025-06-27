"""
Session data endpoints for retrieving uploaded resumes and session status.

Provides access to processed resumes and session metrics.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status, Header

from app.models.api_models import ErrorResponse
from app.models.upload_models import ExtractedResumeData
from app.services.session_service import SessionService, get_session_service
from app.services.rag_service import RAGService
from app.dependencies import get_rag_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/session",
    tags=["Session"],
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)


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
    "/status",
    summary="Get session status and limits",
    description="""
Get detailed information about the current session including:
- Upload count and remaining uploads
- Message count and remaining messages  
- Session expiry information
- Current limits

Requires X-Session-ID header to identify the session.
    """,
    responses={
        200: {
            "description": "Session status information",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "device_123abc",
                        "upload_count": 3,
                        "message_count": 7,
                        "max_uploads": 10,
                        "max_messages": 10,
                        "remaining_uploads": 7,
                        "remaining_messages": 3,
                        "expires_at": "2024-01-21T10:30:00Z",
                        "created_at": "2024-01-20T10:30:00Z",
                        "last_activity": "2024-01-20T14:22:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Missing session ID",
            "model": ErrorResponse,
        },
        404: {
            "description": "Session not found",
            "model": ErrorResponse,
        },
    },
)
async def get_session_status(
    session_id: Optional[str] = Header(
        None, alias="X-Session-ID", description="Unique session identifier"
    ),
    session_service: SessionService = Depends(get_session_service),
):
    """Get current session status and usage information."""

    # Validate session ID
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="missing_session_id",
                message="Session ID required in X-Session-ID header",
            ).model_dump(exclude_none=True),
        )

    # Get session data
    session_data = await session_service.get_session_data(session_id)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="session_not_found",
                message=f"Session {session_id} not found",
            ).model_dump(exclude_none=True),
        )

    # Return formatted session status
    return {
        "session_id": session_data.session_id,
        "upload_count": session_data.upload_count,
        "message_count": session_data.message_count,
        "max_uploads": 10,  # From settings, could be made configurable
        "max_messages": 10,  # From settings, could be made configurable
        "remaining_uploads": max(0, 10 - session_data.upload_count),
        "remaining_messages": max(0, 10 - session_data.message_count),
        "expires_at": session_data.created_at.isoformat()
        + "Z",  # 48 hours from creation
        "created_at": session_data.created_at.isoformat() + "Z",
        "last_activity": session_data.last_activity.isoformat() + "Z",
    }


@router.post(
    "/reset",
    summary="Reset session data",
    description="""
Reset the current session by clearing upload and message counts.
This effectively creates a fresh session while keeping the same session ID.

⚠️ **Warning**: This will clear all conversation history and reset limits.
    """,
    responses={
        200: {
            "description": "Session reset successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Session reset successfully",
                        "session_id": "device_123abc",
                        "upload_count": 0,
                        "message_count": 0,
                    }
                }
            },
        },
        400: {
            "description": "Missing session ID",
            "model": ErrorResponse,
        },
    },
)
async def reset_session(
    session_id: Optional[str] = Header(
        None, alias="X-Session-ID", description="Unique session identifier"
    ),
    session_service: SessionService = Depends(get_session_service),
):
    """Reset session data and conversation history."""

    # Validate session ID
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="missing_session_id",
                message="Session ID required in X-Session-ID header",
            ).model_dump(exclude_none=True),
        )

    # Reset session data
    session_data = await session_service.reset_session(session_id)

    return {
        "message": "Session reset successfully",
        "session_id": session_data.session_id,
        "upload_count": session_data.upload_count,
        "message_count": session_data.message_count,
    }
