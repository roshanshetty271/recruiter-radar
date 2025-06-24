"""
Session management service for tracking upload limits.

Provides in-memory session tracking for the MVP, managing upload
counts and session lifecycle without requiring external storage.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

from app.models.upload_models import SessionData
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """
    In-memory session management service.

    Tracks upload counts per session with basic cleanup of expired sessions.
    Thread-safe using asyncio.Lock for concurrent access.
    """

    def __init__(self):
        """Initialize the session service with empty session store."""
        self._sessions: Dict[str, SessionData] = {}
        self._lock = asyncio.Lock()
        logger.info("Initialized in-memory session service")

    async def get_or_create_session(self, session_id: str) -> SessionData:
        """
        Get existing session or create new one.

        Thread-safe session retrieval/creation with automatic cleanup
        of expired sessions when the store gets large.

        Args:
            session_id: Unique session identifier (e.g., device ID)

        Returns:
            SessionData instance
        """
        async with self._lock:
            # Periodic cleanup when session count gets high
            if len(self._sessions) > 100:
                await self._cleanup_expired_sessions()

            # Get or create session
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionData(session_id=session_id)
                logger.info(f"Created new session: {session_id}")

            # Update last activity
            session = self._sessions[session_id]
            session.last_activity = datetime.utcnow()

            return session

    async def validate_upload_limit(
        self, session_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if session can upload more files.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        session = await self.get_or_create_session(session_id)

        if session.upload_count >= settings.max_uploads_per_session:
            logger.info(
                f"Session {session_id} hit upload limit: {session.upload_count}"
            )
            return (
                False,
                f"You've reached the limit of {settings.max_uploads_per_session} uploads",
            )

        return True, None

    async def increment_upload_count(self, session_id: str) -> int:
        """
        Increment upload count for session.

        Args:
            session_id: Session identifier

        Returns:
            New upload count
        """
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.increment_uploads()
                logger.debug(
                    f"Session {session_id} upload count: {session.upload_count}"
                )
                return session.upload_count
            else:
                # Should not happen if validate_upload_limit is called first
                logger.warning(
                    f"Attempted to increment non-existent session: {session_id}"
                )
                return 0

    async def get_session_info(self, session_id: str) -> Optional[SessionData]:
        """
        Get session information if it exists.

        Args:
            session_id: Session identifier

        Returns:
            SessionData if exists, None otherwise
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def get_message_count(self, session_id: str) -> int:
        """Get current message count for session."""
        session = await self.get_or_create_session(session_id)
        return session.message_count

    async def validate_message_limit(
        self, session_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if session can send more messages.

        Returns:
            Tuple of (is_valid, error_message)
        """
        session = await self.get_or_create_session(session_id)

        if session.message_count >= settings.max_chat_messages_per_session:
            logger.info(
                f"Session {session_id} hit message limit: {session.message_count}"
            )
            return (
                False,
                f"Message limit of {settings.max_chat_messages_per_session} reached",
            )

        return True, None

    async def increment_message_count(self, session_id: str) -> int:
        """
        Increment message count for session.

        Returns:
            New message count
        """
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.increment_messages()
                logger.debug(
                    f"Session {session_id} message count: {session.message_count}"
                )
                return session.message_count
            else:
                logger.warning(
                    f"Attempted to increment message count for non-existent session: {session_id}"
                )
                return 0

    async def _cleanup_expired_sessions(self) -> None:
        """
        Remove expired sessions from memory.

        Called periodically when session count is high to prevent
        unbounded memory growth. Uses settings.session_expiry_hours.
        """
        current_time = datetime.utcnow()
        expired_cutoff = current_time - timedelta(hours=settings.session_expiry_hours)

        # Find expired sessions
        expired_ids = [
            sid
            for sid, session in self._sessions.items()
            if session.last_activity < expired_cutoff
        ]

        # Remove them
        for sid in expired_ids:
            del self._sessions[sid]

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions")

    async def get_active_session_count(self) -> int:
        """Get current number of active sessions (for monitoring)."""
        async with self._lock:
            return len(self._sessions)

    async def clear_all_sessions(self) -> None:
        """Clear all sessions (useful for testing)."""
        async with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            logger.info(f"Cleared all {count} sessions")

    # =============================================================================
    # Conversation History Management
    # =============================================================================

    async def add_message_to_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        function_call: Optional[Dict] = None,
        candidates_returned: Optional[List[str]] = None,
    ) -> None:
        """
        Add a message to the session's conversation history.

        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            content: Message content
            function_call: Optional function call metadata
            candidates_returned: Optional list of candidate IDs returned
        """
        async with self._lock:
            session = await self.get_or_create_session(session_id)
            session.add_message(role, content, function_call, candidates_returned)

            # Trim conversation if it gets too long (prevent token overflow)
            session.trim_conversation(max_messages=10)

            logger.debug(f"Added {role} message to session {session_id} conversation")

    async def get_conversation_history(
        self, session_id: str, max_messages: int = 10
    ) -> List[Dict]:
        """
        Get conversation history for a session in OpenAI API format.

        Args:
            session_id: Session identifier
            max_messages: Maximum number of recent messages to return

        Returns:
            List of messages in OpenAI format: [{"role": "user", "content": "..."}, ...]
        """
        session = await self.get_or_create_session(session_id)
        return session.get_conversation_for_llm(max_messages)

    async def clear_conversation_history(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].conversation_history.clear()
                logger.info(f"Cleared conversation history for session {session_id}")


# Global session service instance
# Will be initialized once in main.py lifespan
session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """
    Get the global session service instance.

    Returns:
        SessionService instance

    Raises:
        RuntimeError: If session service not initialized
    """
    if session_service is None:
        raise RuntimeError("Session service not initialized. Check app startup.")
    return session_service
