"""
Session management API endpoints.

Handles session creation, tracking, and persistent user data
like saved candidates and comparison lists.
"""

import logging
from typing import List, Dict, Any, Optional
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


class SavedCandidateRequest(BaseModel):
    candidate_ids: List[str]
    action: str = "add"  # "add", "remove", "clear"


class SavedCandidateResponse(BaseModel):
    saved_candidate_ids: List[str]
    total_saved: int


class ComparisonListRequest(BaseModel):
    candidate_ids: List[str]
    action: str = "set"  # "set", "add", "remove", "clear"


class ComparisonListResponse(BaseModel):
    comparison_candidate_ids: List[str]
    total_in_comparison: int


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


@router.post(
    "/saved-candidates",
    response_model=SavedCandidateResponse,
    summary="💾 Manage Saved Candidates (Persistent)",
    description="""
**💾 PERSISTENT CANDIDATE BOOKMARKS - Never lose your favorites!**

This endpoint manages a recruiter's saved/bookmarked candidates that persist across sessions.

🔥 **Actions:**
- `add` - Add candidate IDs to saved list
- `remove` - Remove candidate IDs from saved list 
- `clear` - Clear all saved candidates

**Persistence:** Saved candidates survive page reloads, browser restarts, and device changes.

**Storage:** Uses simple server-side session storage keyed by session ID.

**Examples:**
```json
{
  "candidate_ids": ["candidate_123", "candidate_456"],
  "action": "add"
}
```
    """,
)
async def manage_saved_candidates(
    request: SavedCandidateRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
) -> SavedCandidateResponse:
    """
    💾 Manage persistent saved candidates list.

    Allows recruiters to bookmark candidates that persist across sessions.
    """
    try:
        logger.info(
            f"Managing saved candidates for session {x_session_id}: {request.action} {len(request.candidate_ids)} candidates"
        )

        # Get current saved candidates
        current_saved = await session_service.get_saved_candidates(x_session_id)

        if request.action == "add":
            # Add new candidates (avoid duplicates)
            updated_saved = list(set(current_saved + request.candidate_ids))

        elif request.action == "remove":
            # Remove specified candidates
            updated_saved = [
                cid for cid in current_saved if cid not in request.candidate_ids
            ]

        elif request.action == "clear":
            # Clear all saved candidates
            updated_saved = []

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. Must be 'add', 'remove', or 'clear'",
            )

        # Save updated list
        await session_service.set_saved_candidates(x_session_id, updated_saved)

        logger.info(
            f"✅ Saved candidates updated: {len(current_saved)} → {len(updated_saved)}"
        )

        return SavedCandidateResponse(
            saved_candidate_ids=updated_saved, total_saved=len(updated_saved)
        )

    except Exception as e:
        logger.error(f"❌ Failed to manage saved candidates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to manage saved candidates: {str(e)}",
        )


@router.get(
    "/saved-candidates",
    response_model=SavedCandidateResponse,
    summary="📋 Get Saved Candidates",
    description="Retrieve the current list of saved/bookmarked candidates for this session.",
)
async def get_saved_candidates(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
) -> SavedCandidateResponse:
    """📋 Get current saved candidates list."""
    try:
        saved_candidates = await session_service.get_saved_candidates(x_session_id)

        return SavedCandidateResponse(
            saved_candidate_ids=saved_candidates, total_saved=len(saved_candidates)
        )

    except Exception as e:
        logger.error(f"❌ Failed to get saved candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved candidates: {str(e)}",
        )


@router.post(
    "/comparison-list",
    response_model=ComparisonListResponse,
    summary="⚖️ Manage Comparison List (Persistent)",
    description="""
**⚖️ PERSISTENT CANDIDATE COMPARISON - Never lose your comparisons!**

This endpoint manages a recruiter's candidate comparison list that persists across sessions.

🔥 **Actions:**
- `set` - Replace entire comparison list
- `add` - Add candidate IDs to comparison list (max 3)
- `remove` - Remove candidate IDs from comparison list
- `clear` - Clear entire comparison list

**Limit:** Maximum 3 candidates in comparison list at once.

**Persistence:** Comparison list survives page reloads and browser restarts.

**Examples:**
```json
{
  "candidate_ids": ["candidate_123", "candidate_456", "candidate_789"],
  "action": "set"
}
```
    """,
)
async def manage_comparison_list(
    request: ComparisonListRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
) -> ComparisonListResponse:
    """
    ⚖️ Manage persistent candidate comparison list.

    Allows recruiters to build comparison lists that persist across sessions.
    """
    try:
        logger.info(
            f"Managing comparison list for session {x_session_id}: {request.action} {len(request.candidate_ids)} candidates"
        )

        # Get current comparison list
        current_comparison = await session_service.get_comparison_list(x_session_id)

        if request.action == "set":
            # Replace entire list (enforce 3 candidate limit)
            if len(request.candidate_ids) > 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot compare more than 3 candidates at once",
                )
            updated_comparison = request.candidate_ids

        elif request.action == "add":
            # Add new candidates (avoid duplicates, enforce limit)
            new_candidates = [
                cid for cid in request.candidate_ids if cid not in current_comparison
            ]
            updated_comparison = current_comparison + new_candidates

            if len(updated_comparison) > 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot compare more than 3 candidates. Currently have {len(current_comparison)}, trying to add {len(new_candidates)}",
                )

        elif request.action == "remove":
            # Remove specified candidates
            updated_comparison = [
                cid for cid in current_comparison if cid not in request.candidate_ids
            ]

        elif request.action == "clear":
            # Clear entire comparison list
            updated_comparison = []

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. Must be 'set', 'add', 'remove', or 'clear'",
            )

        # Save updated list
        await session_service.set_comparison_list(x_session_id, updated_comparison)

        logger.info(
            f"✅ Comparison list updated: {len(current_comparison)} → {len(updated_comparison)}"
        )

        return ComparisonListResponse(
            comparison_candidate_ids=updated_comparison,
            total_in_comparison=len(updated_comparison),
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"❌ Failed to manage comparison list: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to manage comparison list: {str(e)}",
        )


@router.get(
    "/comparison-list",
    response_model=ComparisonListResponse,
    summary="📊 Get Comparison List",
    description="Retrieve the current candidate comparison list for this session.",
)
async def get_comparison_list(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
) -> ComparisonListResponse:
    """📊 Get current comparison list."""
    try:
        comparison_list = await session_service.get_comparison_list(x_session_id)

        return ComparisonListResponse(
            comparison_candidate_ids=comparison_list,
            total_in_comparison=len(comparison_list),
        )

    except Exception as e:
        logger.error(f"❌ Failed to get comparison list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comparison list: {str(e)}",
        )
