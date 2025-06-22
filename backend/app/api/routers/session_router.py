"""
Session management API endpoints.

Provides session creation, validation, and status endpoints for managing
user sessions with upload and message limits.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field

from app.models.api_models import ErrorResponse
from app.models.upload_models import SessionData
from app.services.session_service import SessionService
from app.dependencies import get_session_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Session"])


class SessionResponse(BaseModel):
    """Response model for session endpoints."""

    session_id: str = Field(..., description="Unique session identifier")
    uploads_remaining: int = Field(..., description="Number of uploads remaining")
    messages_remaining: int = Field(
        ..., description="Number of chat messages remaining"
    )
    upload_count: int = Field(..., description="Current upload count")
    message_count: int = Field(..., description="Current message count")
    max_uploads: int = Field(..., description="Maximum uploads allowed")
    max_messages: int = Field(..., description="Maximum messages allowed")


@router.get(
    "",
    response_model=SessionResponse,
    summary="Get or create session",
    description="""
Get existing session information or create a new session.

**Behavior:**
- If `X-Session-ID` header is provided and valid → returns existing session
- If header is missing or invalid → creates new session
- Always returns session limits and current usage

**Headers:**
- `X-Session-ID` (optional): Existing session identifier

**Returns:**
Session information with current usage and remaining limits.
    """,
    responses={
        200: {
            "description": "Session retrieved or created successfully",
            "model": SessionResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_or_create_session(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """
    Get existing session or create a new one.

    This endpoint implements the "single source of truth" pattern for sessions:
    - Frontend calls this on startup to get authoritative session ID
    - All subsequent requests use this session ID
    - No more silent session creation in other endpoints
    """
    try:
        # If session ID provided, try to get existing session
        if x_session_id:
            existing_session = await session_service.get_session_info(x_session_id)
            if existing_session:
                logger.info(f"Retrieved existing session: {x_session_id}")
                return _build_session_response(existing_session)
            else:
                logger.info(f"Session {x_session_id} not found, creating new session")

        # Create new session (either no ID provided or ID was invalid)
        import uuid

        new_session_id = f"session_{uuid.uuid4().hex[:12]}"
        session = await session_service.get_or_create_session(new_session_id)

        logger.info(f"Created new session: {new_session_id}")
        return _build_session_response(session)

    except Exception as e:
        logger.error(f"Error in session endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="session_error", message="Failed to get or create session"
            ).model_dump(),
        )


def _build_session_response(session: SessionData) -> SessionResponse:
    """Build SessionResponse from SessionData."""
    uploads_remaining = max(0, settings.max_uploads_per_session - session.upload_count)
    messages_remaining = max(
        0, settings.max_chat_messages_per_session - session.message_count
    )

    return SessionResponse(
        session_id=session.session_id,
        uploads_remaining=uploads_remaining,
        messages_remaining=messages_remaining,
        upload_count=session.upload_count,
        message_count=session.message_count,
        max_uploads=settings.max_uploads_per_session,
        max_messages=settings.max_chat_messages_per_session,
    )
