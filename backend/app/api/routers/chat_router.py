"""
Chat API endpoints for natural language candidate search.

This module provides the conversational interface for searching
uploaded resumes using natural language queries.
"""

import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request

from app.models.api_models import ChatRequest, ChatResponse, ErrorResponse
from app.services.session_service import SessionService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.assistant_service import AssistantService
from app.dependencies import (
    get_session_service,
    get_llm_service,
    get_rag_service,
    get_assistant_service,
)
from app.core.config import settings
from app.services.response_cache import get_response_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/bulletproof",
    response_model=ChatResponse,
    summary="Bulletproof chat with OpenAI Assistant + fallback",
    description="""
**NEW: BULLETPROOF CHAT ENDPOINT**

This is the next-generation chat endpoint with guaranteed responses:

🚀 **Key Features:**
- OpenAI Assistant with conversational memory
- 8-second timeout with seamless fallback to existing search logic
- Thread-based conversation persistence 
- Circuit breaker protection
- Performance monitoring
- 100% response reliability - NEVER times out

🎯 **How it works:**
1. Try OpenAI Assistant with recruiting expertise (primary path)
2. If timeout/failure → Instant fallback to proven search logic
3. Both paths return identical candidate data format
4. Frontend never knows which path was used

**Examples:**
- "Find Python developers with 5+ years experience"
- "Show me React engineers in San Francisco" 
- "I need senior full-stack developers"
- "Any DevOps engineers with AWS experience?"

**Returns:**
Same ChatResponse format as existing endpoint but with enhanced reliability.
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
async def bulletproof_chat(
    request: ChatRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> ChatResponse:
    """
    Bulletproof chat with OpenAI Assistant + intelligent fallback.

    This endpoint provides 100% reliable responses by trying:
    1. OpenAI Assistant (enhanced conversational AI)
    2. Fallback to existing search logic if timeout/failure

    Both paths return identical response format.
    """
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
        logger.info(f"Bulletproof chat: '{request.message}' for session {x_session_id}")

        # Use the bulletproof assistant service
        response = await assistant_service.bulletproof_recruiter_chat(
            message=request.message, session_id=x_session_id
        )

        # Increment message count after successful processing
        await session_service.increment_message_count(x_session_id)
        remaining = (
            settings.max_chat_messages_per_session
            - await session_service.get_message_count(x_session_id)
        )

        # Update remaining messages count
        response.remaining_messages = remaining

        logger.info(
            f"Bulletproof chat completed in {response.response_time:.2f}s "
            f"via {response.source} with {len(response.candidates)} candidates"
        )

        return response

    except Exception as e:
        logger.error(f"Bulletproof chat failed: {e}", exc_info=True)

        # Still increment message count
        await session_service.increment_message_count(x_session_id)
        remaining = (
            settings.max_chat_messages_per_session
            - await session_service.get_message_count(x_session_id)
        )

        # Emergency fallback
        return ChatResponse(
            ai_message="I'm experiencing technical difficulties. Please try your search again.",
            candidates=[],
            remaining_messages=remaining,
            source="emergency_fallback",
            response_time=0.0,
        )


@router.post(
    "",
    response_model=ChatResponse,
    summary="Process natural language chat query (Legacy)",
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
    "/metrics",
    summary="Get assistant performance metrics",
    description="Returns performance metrics for monitoring assistant health",
    response_model=dict,
)
async def get_assistant_metrics(
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> dict:
    """
    Get performance metrics for the assistant service.

    Returns information about:
    - Assistant success rate
    - Fallback activation rate
    - Average response times
    - Circuit breaker status
    """
    return assistant_service.get_performance_metrics()


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


@router.get(
    "/cache/stats",
    summary="Get response cache statistics",
    description="Returns detailed statistics about the response cache performance",
    response_model=dict,
)
async def get_cache_stats() -> dict:
    """
    Get comprehensive cache statistics.

    Returns information about:
    - Cache hit/miss rates
    - Current cache size and utilization
    - Popular cached queries
    - Performance metrics
    """
    cache = get_response_cache()
    stats = cache.get_cache_stats()
    popular_queries = cache.get_popular_queries(limit=5)

    return {
        **stats,
        "popular_queries": popular_queries,
    }


@router.post(
    "/cache/clear",
    summary="Clear response cache",
    description="Clear all cached responses (admin operation)",
    response_model=dict,
)
async def clear_cache() -> dict:
    """
    Clear all cached responses.

    This is an administrative operation that removes all cached responses.
    Use with caution as it will impact performance until cache rebuilds.
    """
    cache = get_response_cache()
    cleared_count = cache.clear()

    logger.info(f"Cache cleared by admin: {cleared_count} entries removed")

    return {
        "message": "Cache cleared successfully",
        "entries_cleared": cleared_count,
        "timestamp": time.time(),
    }


@router.post(
    "/cache/cleanup",
    summary="Clean up expired cache entries",
    description="Remove expired cache entries to free memory",
    response_model=dict,
)
async def cleanup_cache() -> dict:
    """
    Remove expired cache entries.

    This operation removes only expired entries, preserving valid cached responses.
    Useful for maintenance and memory management.
    """
    cache = get_response_cache()
    expired_count = cache.cleanup_expired()

    logger.info(f"Cache cleanup: {expired_count} expired entries removed")

    return {
        "message": "Cache cleanup completed",
        "expired_entries_removed": expired_count,
        "timestamp": time.time(),
    }
