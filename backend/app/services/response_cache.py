"""
Response Cache Service for RecruiterRadar

Provides intelligent caching for chat responses to improve performance and reduce costs.
Uses in-memory caching with TTL (Time To Live) for MVP, with Redis-like behavior.

Key Features:
- Query normalization for better cache hit rates
- TTL-based expiration for fresh results
- Cache size limits to prevent memory issues
- Performance metrics tracking
- Context-aware caching (session-independent for common queries)
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached response with metadata."""

    ai_message: str
    candidates: List[Dict[str, Any]]
    cached_at: float
    ttl_seconds: int
    query_hash: str
    source: str = "cache"
    hit_count: int = 1

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > (self.cached_at + self.ttl_seconds)

    def to_response_dict(self, processing_time_ms: int = 0) -> Dict[str, Any]:
        """Convert to response format matching ChatResponse."""
        return {
            "ai_message": self.ai_message,
            "candidates": self.candidates,
            "source": "cache",
            "response_time": 0.001,  # Cache hits are very fast
            "processing_time_ms": processing_time_ms,
            "cached_at": datetime.fromtimestamp(self.cached_at).isoformat(),
            "cache_hit_count": self.hit_count,
        }


class ResponseCache:
    """
    In-memory response cache with TTL and intelligent query normalization.

    Designed to cache common recruiting queries to improve performance
    and reduce OpenAI API costs while maintaining response freshness.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize the response cache.

        Args:
            max_size: Maximum number of cached responses
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CachedResponse] = {}

        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_evictions": 0,
            "cache_expirations": 0,
            "total_cached_responses": 0,
        }

        logger.info(
            f"ResponseCache initialized: max_size={max_size}, default_ttl={default_ttl}s"
        )

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for better cache hit rates.

        Makes queries case-insensitive and removes common variations.
        """
        if not query:
            return ""

        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove common variations that don't change semantic meaning
        replacements = {
            "developers": "developer",
            "engineers": "engineer",
            "programmers": "programmer",
            "find me": "find",
            "show me": "show",
            "i need": "need",
            "looking for": "find",
            "search for": "find",
            "  ": " ",  # Multiple spaces to single space
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def _generate_cache_key(
        self, query: str, session_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key from normalized query.

        For recruiting queries, we generally want session-independent caching
        since "Python developers" should return similar results regardless of user.
        """
        normalized_query = self._normalize_query(query)

        # For MVP, use query-only caching (session-independent)
        # In future, could include session context for personalized results
        cache_data = {
            "query": normalized_query,
            "version": "v1",  # Allow cache versioning for future changes
        }

        # Create hash from normalized data
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()

        return cache_hash

    def get(
        self, query: str, session_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query.

        Args:
            query: User's search query
            session_context: Optional session context (for future personalization)

        Returns:
            Cached response dict or None if not found/expired
        """
        self.metrics["total_requests"] += 1

        cache_key = self._generate_cache_key(query, session_context)

        if cache_key not in self.cache:
            self.metrics["cache_misses"] += 1
            logger.debug(f"Cache miss for query: '{query}' (key: {cache_key[:8]}...)")
            return None

        cached_response = self.cache[cache_key]

        # Check if expired
        if cached_response.is_expired():
            logger.debug(
                f"Cache expired for query: '{query}' (key: {cache_key[:8]}...)"
            )
            del self.cache[cache_key]
            self.metrics["cache_expirations"] += 1
            self.metrics["cache_misses"] += 1
            return None

        # Cache hit - increment hit count and return
        cached_response.hit_count += 1
        self.metrics["cache_hits"] += 1

        logger.debug(
            f"Cache hit for query: '{query}' (key: {cache_key[:8]}..., hits: {cached_response.hit_count})"
        )

        return cached_response.to_response_dict(processing_time_ms=1)

    def set(
        self,
        query: str,
        ai_message: str,
        candidates: List[Dict[str, Any]],
        ttl: Optional[int] = None,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Cache a response.

        Args:
            query: User's search query
            ai_message: AI response message
            candidates: List of candidate results
            ttl: Custom TTL in seconds (uses default if None)
            session_context: Optional session context

        Returns:
            Cache key for the stored response
        """
        if ttl is None:
            ttl = self.default_ttl

        cache_key = self._generate_cache_key(query, session_context)

        # Check if we need to evict old entries
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        # Create cached response
        cached_response = CachedResponse(
            ai_message=ai_message,
            candidates=candidates,
            cached_at=time.time(),
            ttl_seconds=ttl,
            query_hash=cache_key,
        )

        self.cache[cache_key] = cached_response
        self.metrics["total_cached_responses"] += 1

        logger.debug(
            f"Cached response for query: '{query}' (key: {cache_key[:8]}..., ttl: {ttl}s)"
        )

        return cache_key

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry to make room."""
        if not self.cache:
            return

        # Find oldest entry by cached_at timestamp
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].cached_at)
        del self.cache[oldest_key]
        self.metrics["cache_evictions"] += 1

        logger.debug(f"Evicted oldest cache entry: {oldest_key[:8]}...")

    def clear(self) -> int:
        """Clear all cached responses."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {count} cached responses")
        return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        expired_keys = [
            key for key, response in self.cache.items() if response.is_expired()
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self.metrics["cache_expirations"] += len(expired_keys)
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.metrics["total_requests"]
        hit_rate = (
            (self.metrics["cache_hits"] / total_requests * 100)
            if total_requests > 0
            else 0
        )

        return {
            **self.metrics,
            "hit_rate_percentage": round(hit_rate, 2),
            "current_cache_size": len(self.cache),
            "max_cache_size": self.max_size,
            "cache_utilization_percentage": round(
                len(self.cache) / self.max_size * 100, 2
            ),
            "default_ttl_seconds": self.default_ttl,
        }

    def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular cached queries by hit count."""
        sorted_responses = sorted(
            self.cache.values(), key=lambda x: x.hit_count, reverse=True
        )

        return [
            {
                "query_hash": response.query_hash[:8] + "...",
                "hit_count": response.hit_count,
                "cached_at": datetime.fromtimestamp(response.cached_at).isoformat(),
                "candidates_count": len(response.candidates),
                "expires_at": datetime.fromtimestamp(
                    response.cached_at + response.ttl_seconds
                ).isoformat(),
            }
            for response in sorted_responses[:limit]
        ]


# Global cache instance (singleton pattern)
response_cache = ResponseCache(max_size=1000, default_ttl=3600)  # 1 hour TTL


def get_response_cache() -> ResponseCache:
    """Get the global response cache instance."""
    return response_cache


# Cache maintenance functions
async def periodic_cache_cleanup():
    """Periodic cleanup of expired cache entries."""
    try:
        expired_count = response_cache.cleanup_expired()
        if expired_count > 0:
            logger.info(f"Periodic cleanup: removed {expired_count} expired entries")
    except Exception as e:
        logger.error(f"Error during periodic cache cleanup: {e}")


def should_cache_response(candidates: List[Dict[str, Any]], source: str) -> bool:
    """
    Determine if a response should be cached.

    Cache responses that:
    - Have candidates (successful searches)
    - Come from assistant or fallback (not errors)
    - Are not too large (reasonable candidate count)
    """
    if source in ["emergency_fallback", "fallback_error"]:
        return False

    if not candidates:
        return False  # Don't cache empty results

    if len(candidates) > 50:
        return False  # Don't cache very large result sets

    return True
