"""
Chat API endpoints for natural language candidate search.

This module provides the conversational interface for searching
uploaded resumes using natural language queries.
"""

import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.models.api_models import ChatRequest, ChatResponse, ErrorResponse
from app.services.session_service import SessionService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.dependencies import get_session_service, get_llm_service, get_rag_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Process natural language chat query",
    description="""
Send a natural language message to search uploaded resumes.

The AI will:
1. Parse your query into search filters
2. Search through uploaded resumes
3. Return matching candidates with a conversational response

**Examples:**
- "Show me Python developers"
- "Find senior engineers with 5+ years experience"
- "I need React developers in New York"
- "Anyone with AWS and DevOps skills?"

**Requirements:**
- Session ID required (pass in request body)
- Maximum 10 chat messages per session
- Resumes must be uploaded first

**Returns:**
Conversational AI response with matching candidates and metadata.
    """,
    responses={
        200: {
            "description": "Chat query processed successfully",
            "model": ChatResponse,
        },
        400: {
            "description": "Invalid request",
            "model": ErrorResponse,
        },
        429: {
            "description": "Chat message limit exceeded",
            "model": ErrorResponse,
        },
    },
)
async def process_chat(
    request: ChatRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    """
    Process natural language chat query using GPT-4o-mini conversational assistant.

    This endpoint:
    1. Validates session and message limits
    2. Retrieves conversation history from session
    3. Uses GPT-4o-mini with function calling to search/rank candidates
    4. Stores the conversation and returns AI response with candidates
    """
    start_time = time.time()

    # Validate message limit
    is_valid, error_msg = await session_service.validate_message_limit(x_session_id)
    if not is_valid:
        logger.info(f"Session {x_session_id} exceeded message limit")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error="message_limit_exceeded",
                message=error_msg or "Chat message limit exceeded",
            ).model_dump(),
        )

    try:
        logger.info(
            f"Processing chat message: '{request.message}' for session {x_session_id}"
        )

        # Get conversation history from session
        conversation_history = await session_service.get_conversation_history(
            x_session_id, max_messages=8  # Keep reasonable context window
        )

        # Add user message to conversation history
        await session_service.add_message_to_conversation(
            x_session_id, "user", request.message
        )

        # Call the new conversational LLM service
        chat_result = await llm_service.chat(
            user_message=request.message,
            session_id=x_session_id,
            conversation_history=conversation_history,
            rag_service=rag_service,
        )

        # Add AI response to conversation history
        await session_service.add_message_to_conversation(
            x_session_id,
            "assistant",
            chat_result["ai_message"],
            function_call=chat_result.get("function_calls"),
            candidates_returned=[c.get("id") for c in chat_result["candidates"]],
        )

        # Generate simple follow-up suggestions
        suggestions = await llm_service.generate_query_suggestions(
            current_query=request.message, num_results=chat_result["total_candidates"]
        )

        # Increment message count (after successful processing)
        await session_service.increment_message_count(x_session_id)
        remaining = (
            settings.max_chat_messages_per_session
            - await session_service.get_message_count(x_session_id)
        )

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Log success
        logger.info(
            f"Chat query processed in {processing_time}ms: "
            f"'{request.message[:50]}...' returned {chat_result['total_candidates']} candidates"
        )

        return ChatResponse(
            ai_message=chat_result["ai_message"],
            candidates=chat_result["candidates"],
            query_metadata={
                "function_calls": chat_result["function_calls"],
                "candidates_found": chat_result["total_candidates"],
                "search_type": "conversational_ai",
                "conversation_length": len(conversation_history)
                + 2,  # +2 for current exchange
            },
            remaining_messages=remaining,
            processing_time_ms=processing_time,
            suggestions=suggestions if suggestions else None,
        )

    except Exception as e:
        logger.error(f"Error processing chat query: {e}", exc_info=True)

        # Add error message to conversation for context
        await session_service.add_message_to_conversation(
            x_session_id,
            "assistant",
            "I encountered an issue processing your request. Please try rephrasing your question.",
        )

        # Still increment message count
        await session_service.increment_message_count(x_session_id)
        remaining = (
            settings.max_chat_messages_per_session
            - await session_service.get_message_count(x_session_id)
        )

        return ChatResponse(
            ai_message="I encountered an issue processing your request. Please try rephrasing your question or check that you have uploaded some resumes.",
            candidates=[],
            query_metadata={"error": str(e)},
            remaining_messages=remaining,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


@router.get(
    "/examples",
    summary="Get example chat queries",
    description="Returns example queries to help users get started",
    response_model=dict,
)
async def get_chat_examples() -> dict:
    """
    Return example chat queries for the UI.

    These help users understand what kinds of queries work well.
    """
    return {
        "examples": [
            {
                "category": "Skills-based",
                "queries": [
                    "Show me Python developers",
                    "Find React engineers",
                    "Anyone with AWS and Docker experience?",
                    "Full stack developers who know Node.js",
                ],
            },
            {
                "category": "Experience-based",
                "queries": [
                    "Senior engineers with 5+ years",
                    "Entry level developers",
                    "Mid-level Python developers",
                    "Experienced team leads",
                ],
            },
            {
                "category": "Location-based",
                "queries": [
                    "Developers in San Francisco",
                    "Remote React developers",
                    "Engineers in NYC or Boston",
                    "West coast Python developers",
                ],
            },
            {
                "category": "Combined",
                "queries": [
                    "Senior Python developers in California",
                    "Entry level React devs who know TypeScript",
                    "Full stack engineers with 3+ years and AWS",
                    "Remote senior developers with DevOps experience",
                ],
            },
        ]
    }
