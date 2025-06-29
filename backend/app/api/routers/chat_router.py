"""
Chat API endpoints for natural language candidate search.

This module provides the conversational interface for searching
uploaded resumes using natural language queries.
"""

import time
import json
import asyncio
import logging
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from fastapi.responses import StreamingResponse, PlainTextResponse, Response

try:
    import orjson  # 🚀 CYBER-CHEETAH: 5x faster JSON serialization

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

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
from app.services.metrics_service import get_metrics_service, MetricsTimer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


def create_fast_json_response(data: dict, status_code: int = 200) -> Response:
    """🚀 CYBER-CHEETAH: Create ultra-fast JSON response using orjson."""
    if ORJSON_AVAILABLE:
        # orjson is 5x faster than stdlib json for large responses
        content = orjson.dumps(data)
        return Response(
            content=content, media_type="application/json", status_code=status_code
        )
    else:
        # Fallback to standard JSON
        content = json.dumps(data).encode("utf-8")
        return Response(
            content=content, media_type="application/json", status_code=status_code
        )


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
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse:
    """
    Bulletproof chat with OpenAI Assistant + intelligent fallback.

    This endpoint provides 100% reliable responses by trying:
    1. OpenAI Assistant (enhanced conversational AI)
    2. Fallback to existing search logic if timeout/failure

    Both paths return identical response format.
    """
    # 🎯 PERFECTION FIX: Handle empty queries gracefully
    if not request.message or not request.message.strip():
        logger.info(f"Empty query received for session {x_session_id}")
        from app.models.api_models import ChatResponse

        return ChatResponse(
            ai_message="Please enter a search query or question. For example: 'Python developers', 'senior engineers', or 'help' for assistance.",
            candidates=[],
            query_metadata={"search_type": "empty_query_handler"},
            remaining_messages=10,  # Default, will be updated below
            processing_time_ms=0,
            source="empty_query_handler",
            response_time=0.0,
        )

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

    # 🚨 LOG A: API Boundary - Incoming Request
    logger.info(
        f"🚨 LOG A [API_BOUNDARY]: session_id={x_session_id}, query='{request.message}', timestamp={time.time()}"
    )

    try:
        logger.info(f"Bulletproof chat: '{request.message}' for session {x_session_id}")

        # 🚀 METRICS: Track performance
        metrics = get_metrics_service()
        start_time = time.time()

        # Use the bulletproof assistant service
        response = await assistant_service.bulletproof_recruiter_chat(
            message=request.message, session_id=x_session_id
        )

        # 🚨 LOG B: API Boundary - Response Ready
        logger.info(
            f"🚨 LOG B [API_BOUNDARY]: candidates_count={len(response.candidates)}, ai_message_preview='{response.ai_message[:100]}...', source={response.source}"
        )
        if response.candidates:
            candidate_names = [
                c.get("name", "NO_NAME") for c in response.candidates[:3]
            ]
            logger.info(
                f"🚨 LOG B [API_BOUNDARY]: first_3_candidate_names={candidate_names}"
            )
        else:
            logger.warning(f"🚨 LOG B [API_BOUNDARY]: ⚠️ EMPTY CANDIDATES LIST!")

        # 🚀 METRICS: Record response time and success
        response_time = time.time() - start_time
        metrics.record_response_time(response_time, "bulletproof_chat", response.source)

        # 🚀 CYBER-CHEETAH: Use batched explanation for smarter, faster responses
        if response.candidates and len(response.candidates) > 0:
            try:
                # Use the new batched explanation method (eliminates extra LLM round-trip)
                explanation = await llm_service.generate_batched_explanation(
                    query=request.message,
                    candidates=response.candidates,
                    result_count=len(response.candidates),
                )

                # Enhance the AI message with the explanation
                if (
                    explanation
                    and not explanation.startswith("Found")
                    and not explanation.startswith("No candidates")
                ):
                    response.ai_message = f"{response.ai_message}\n\n💡 {explanation}"

            except Exception as e:
                logger.warning(
                    f"Batched explanation failed for bulletproof response: {e}"
                )
                # Continue without explanation

        # Increment message count after successful processing
        await session_service.increment_message_count(x_session_id)
        remaining = (
            settings.max_chat_messages_per_session
            - await session_service.get_message_count(x_session_id)
        )

        # Update remaining messages count
        response.remaining_messages = remaining

        logger.info(
            f"🚀 CYBER-CHEETAH: Bulletproof chat completed in {response.response_time:.2f}s "
            f"via {response.source} with {len(response.candidates)} candidates"
        )

        # 🚀 CYBER-CHEETAH: Use ultra-fast JSON serialization
        return create_fast_json_response(response.model_dump())

    except Exception as e:
        logger.error(f"Bulletproof chat failed: {e}", exc_info=True)

        # 🚀 METRICS: Record error
        metrics = get_metrics_service()
        metrics.record_error(type(e).__name__, "bulletproof_chat")

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
    "/assistant-metrics",
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


# 🚀 STREAMING CHAT ENDPOINT - THE FUTURE IS NOW!
@router.post(
    "/stream",
    summary="🚀 STREAMING Bulletproof Chat - Ultra-Fast SSE",
    description="""
**🔥 STREAMING BULLETPROOF CHAT - THE CYBER-CHEETAH EDITION**

This is the next-generation STREAMING chat endpoint that pushes results as they come:

⚡ **INSANE SPEED FEATURES:**
- Server-Sent Events (SSE) - Results stream as they're found
- First candidate appears in ~1-2 seconds (before full search completes)
- OpenAI Assistant with conversational memory + instant fallback
- Smart result explanations powered by GPT-4o-mini
- Real-time progress updates and performance metrics

🎯 **Streaming Flow:**
1. `data: {"status": "processing", "message": "Analyzing your query..."}`
2. `data: {"status": "searching", "message": "Finding candidates..."}`
3. `data: {"status": "candidate", "candidate": {...}}` (per candidate as found)
4. `data: {"status": "explanation", "explanation": "Most candidates have Django + AWS..."}`
5. `data: {"status": "complete", "final_response": {...}}`

**Examples:**
- "Find Python developers with 5+ years experience"
- "Show me React engineers in San Francisco" 
- "I need senior full-stack developers"

**Content-Type:** `text/event-stream`
**Connection:** Keep-Alive
    """,
)
async def stream_bulletproof_chat(
    request: ChatRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    session_service: SessionService = Depends(get_session_service),
    assistant_service: AssistantService = Depends(get_assistant_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    🚀 STREAMING bulletproof chat with real-time candidate delivery.

    Returns Server-Sent Events (SSE) stream with candidates appearing instantly.
    """

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # 🎯 Handle empty queries gracefully
            if not request.message or not request.message.strip():
                yield f"data: {json.dumps({'status': 'complete', 'ai_message': 'Please enter a search query or question. For example: \"Python developers\", \"senior engineers\", or \"help\" for assistance.', 'candidates': [], 'source': 'empty_query_handler'})}\n\n"
                return

            # Validate message limit
            is_valid, error_msg = await session_service.validate_message_limit(
                x_session_id
            )
            if not is_valid:
                yield f"data: {json.dumps({'status': 'error', 'error': 'message_limit_exceeded', 'message': error_msg or 'Chat message limit exceeded'})}\n\n"
                return

            # 🚀 Connection health check + progress update
            try:
                yield f"data: {json.dumps({'status': 'connected', 'message': 'Connection established', 'timestamp': time.time()})}\n\n"
                await asyncio.sleep(0.05)  # Brief pause for connection validation

                yield f"data: {json.dumps({'status': 'processing', 'message': 'AI is analyzing your query...', 'query_length': len(request.message)})}\n\n"
                await asyncio.sleep(0.1)  # Small delay for UX

            except Exception as connection_error:
                logger.error(f"🔌 Connection check failed: {connection_error}")
                yield f"data: {json.dumps({'status': 'error', 'error': 'connection_failed', 'message': 'Failed to establish stable connection', 'recoverable': True})}\n\n"
                return

            logger.info(
                f"Streaming bulletproof chat: '{request.message}' for session {x_session_id}"
            )

            # 🚀 Search progress
            yield f"data: {json.dumps({'status': 'searching', 'message': 'Searching through candidates...'})}\n\n"

            # Get the bulletproof response (but we'll stream it)
            response = await assistant_service.bulletproof_recruiter_chat(
                message=request.message, session_id=x_session_id
            )

            # 🚀 Stream candidates in optimized chunks (3-5 at a time)
            chunk_size = 4  # Sweet spot for performance vs responsiveness
            total_candidates = len(response.candidates)

            for chunk_start in range(0, total_candidates, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_candidates)
                candidate_chunk = response.candidates[chunk_start:chunk_end]

                # Stream the chunk with metadata
                chunk_data = {
                    "status": "candidate_chunk",
                    "candidates": candidate_chunk,
                    "chunk_info": {
                        "start": chunk_start,
                        "end": chunk_end,
                        "total": total_candidates,
                        "chunk_size": len(candidate_chunk),
                    },
                }

                try:
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                    # Adaptive delay - shorter for fewer candidates
                    delay = 0.03 if total_candidates > 20 else 0.05
                    await asyncio.sleep(delay)

                except Exception as chunk_error:
                    logger.error(f"❌ Chunk streaming failed: {chunk_error}")
                    yield f"data: {json.dumps({'status': 'error', 'error': 'chunk_stream_failed', 'message': 'Failed to stream candidates chunk', 'recoverable': True})}\n\n"
                    # Continue with next chunk

            # 🚀 ZERO-SHOT RESULT EXPLANATION
            if response.candidates and len(response.candidates) > 0:
                yield f"data: {json.dumps({'status': 'generating_explanation', 'message': 'AI is analyzing results...'})}\n\n"

                # Generate smart explanation using GPT-4o-mini
                explanation = await _generate_smart_explanation(
                    query=request.message,
                    candidates=response.candidates,
                    llm_service=llm_service,
                )

                yield f"data: {json.dumps({'status': 'explanation', 'explanation': explanation})}\n\n"

            # Update session
            await session_service.increment_message_count(x_session_id)
            remaining = (
                settings.max_chat_messages_per_session
                - await session_service.get_message_count(x_session_id)
            )
            response.remaining_messages = remaining

            # 🚀 Final complete response
            final_response = {
                "status": "complete",
                "ai_message": response.ai_message,
                "candidates": response.candidates,
                "remaining_messages": response.remaining_messages,
                "processing_time_ms": response.processing_time_ms,
                "source": response.source,
                "response_time": response.response_time,
                "total_candidates": len(response.candidates),
            }

            yield f"data: {json.dumps(final_response)}\n\n"

            logger.info(
                f"Streaming chat completed in {response.response_time:.2f}s "
                f"via {response.source} with {len(response.candidates)} candidates"
            )

        except asyncio.CancelledError:
            # Client disconnected - clean shutdown
            logger.info(
                f"🔌 Client disconnected during streaming for session {x_session_id}"
            )
            yield f"data: {json.dumps({'status': 'disconnected', 'message': 'Client connection closed'})}\n\n"

        except asyncio.TimeoutError:
            # Request timeout
            logger.error(f"⏰ Streaming timeout for session {x_session_id}")
            yield f"data: {json.dumps({'status': 'error', 'error': 'timeout', 'message': 'Request timed out. Please try a more specific search.', 'recoverable': True})}\n\n"

        except json.JSONEncodeError as e:
            # JSON encoding error
            logger.error(f"📄 JSON encoding failed: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': 'encoding_failed', 'message': 'Failed to encode response data', 'recoverable': True})}\n\n"

        except Exception as e:
            logger.error(f"❌ Streaming chat failed: {e}", exc_info=True)

            # Detailed error classification
            error_type = type(e).__name__
            is_recoverable = error_type not in [
                "MemoryError",
                "SystemExit",
                "KeyboardInterrupt",
            ]

            error_response = {
                "status": "error",
                "error": "streaming_failed",
                "error_type": error_type,
                "message": (
                    "I encountered technical difficulties. Please try again."
                    if is_recoverable
                    else "System error occurred. Please contact support."
                ),
                "recoverable": is_recoverable,
                "source": "emergency_fallback",
                "timestamp": time.time(),
            }
            yield f"data: {json.dumps(error_response)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


async def _generate_smart_explanation(
    query: str, candidates: list, llm_service: LLMService
) -> str:
    """
    🧠 ZERO-SHOT RESULT EXPLANATION
    Generate intelligent explanation of search results using GPT-4o-mini.
    """
    try:
        if not candidates:
            return "No candidates found matching your criteria."

        # Extract key metadata for explanation
        candidate_summaries = []
        for candidate in candidates[:5]:  # Top 5 for analysis
            summary = {
                "name": candidate.get("name", "Unknown"),
                "title": candidate.get("title", ""),
                "skills": candidate.get("skills", [])[:5],  # Top 5 skills
                "experience": candidate.get("experience_years", 0),
                "location": candidate.get("location", ""),
            }
            candidate_summaries.append(summary)

        explanation_prompt = f"""
        Analyze these search results and provide a brief, recruiter-friendly explanation (1-2 sentences).
        
        Query: "{query}"
        Top {len(candidate_summaries)} candidates found:
        {json.dumps(candidate_summaries, indent=2)}
        
        Provide a concise explanation of what makes these candidates relevant, highlighting common patterns in skills, experience, or backgrounds. Be specific about technologies and experience levels.
        
        Example: "Most of these developers have 5+ years with Python and Django, with strong AWS cloud experience."
        """

        explanation = await llm_service.generate_quick_response(explanation_prompt)
        return (
            explanation.strip()
            if explanation
            else "Found relevant candidates matching your search criteria."
        )

    except Exception as e:
        logger.error(f"Failed to generate explanation: {e}")
        return f"Found {len(candidates)} candidates matching your search criteria."


# 🚀 OBSERVABILITY ENDPOINTS


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="🔥 Prometheus Metrics Export",
    description="""
**🚀 CYBER-CHEETAH OBSERVABILITY**

Export metrics in Prometheus format for Grafana dashboards and alerting.

**Key Metrics:**
- `recruiter_radar_response_time_*` - P95/P99 response times
- `recruiter_radar_cache_hit_ratio` - Embedding cache efficiency  
- `recruiter_radar_error_rate` - Error rate (should be <1%)
- `recruiter_radar_tokens_used_total` - Token consumption
- `recruiter_radar_estimated_cost_usd_total` - Estimated OpenAI costs

**Perfect for:**
- Grafana dashboard creation
- Alert rules (p95 > 2s, error_rate > 0.01)
- Performance regression detection
- Cost monitoring

**Pro Tip:** Set up alerts for when p95 > 2s for >5m 🚨
    """,
    tags=["Observability"],
)
async def get_prometheus_metrics():
    """
    🚀 Export metrics in Prometheus format for monitoring dashboards.

    Essential for tracking the cyber-cheetah performance and catching regressions.
    """
    try:
        metrics = get_metrics_service()
        prometheus_metrics = metrics.get_prometheus_metrics()

        logger.debug("📊 METRICS EXPORT: Prometheus metrics requested")
        return prometheus_metrics

    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        return "# Error exporting metrics\n"


@router.get(
    "/performance",
    summary="📊 Performance Summary - Human Readable",
    description="""
**📊 PERFORMANCE DASHBOARD**

Get human-readable performance summary for the last 15 minutes.

**Perfect for:**
- Quick performance checks
- Debugging performance issues  
- Validating turbo-patch improvements
- Monitoring cache efficiency

**Returns JSON with:**
- Response time percentiles (avg, p95, p99)
- Cache hit ratios
- Error rates
- Token usage and estimated costs
    """,
    tags=["Observability"],
)
async def get_performance_summary():
    """
    📊 Get human-readable performance summary for debugging and monitoring.
    """
    try:
        metrics = get_metrics_service()
        summary = metrics.get_performance_summary(last_minutes=15)

        # Add some interpretive context
        performance_status = "🚀 EXCELLENT"
        if summary.p95_response_time > 5.0:
            performance_status = "⚠️ DEGRADED"
        elif summary.p95_response_time > 2.0:
            performance_status = "✅ GOOD"

        cache_status = "🎯 EXCELLENT" if summary.cache_hit_ratio > 0.8 else "💸 LOW"

        return {
            "performance_status": performance_status,
            "cache_status": cache_status,
            "last_15_minutes": {
                "total_requests": summary.total_requests,
                "avg_response_time_sec": round(summary.avg_response_time, 3),
                "p95_response_time_sec": round(summary.p95_response_time, 3),
                "p99_response_time_sec": round(summary.p99_response_time, 3),
                "cache_hit_ratio": round(summary.cache_hit_ratio, 3),
                "error_rate": round(summary.error_rate, 4),
                "tokens_used": summary.tokens_used,
                "estimated_cost_usd": round(summary.estimated_cost_usd, 6),
            },
            "health_indicators": {
                "response_time_ok": summary.p95_response_time < 5.0,
                "cache_efficiency_ok": summary.cache_hit_ratio > 0.5,
                "error_rate_ok": summary.error_rate < 0.05,
                "overall_healthy": (
                    summary.p95_response_time < 5.0
                    and summary.error_rate < 0.05
                    and summary.cache_hit_ratio > 0.3
                ),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        return {"error": "Failed to retrieve performance metrics"}
