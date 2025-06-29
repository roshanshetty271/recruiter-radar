"""
🚀 OBSERVABILITY METRICS SERVICE
Basic performance and usage metrics for RecruiterRadar production monitoring.

Tracks key metrics for the cyber-cheetah performance optimization:
- Response times (p95, p99)
- Cache hit ratios
- Token usage and costs
- Error rates
- Vector DB performance
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import asyncio
import threading

logger = logging.getLogger(__name__)


@dataclass
class MetricEntry:
    """Individual metric measurement."""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics summary."""

    total_requests: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    cache_hit_ratio: float = 0.0
    error_rate: float = 0.0
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0


class MetricsService:
    """
    🚀 CYBER-CHEETAH METRICS

    Lightweight, in-memory metrics service for tracking production performance.
    Perfect for monitoring the turbo-patch improvements and catching regressions.
    """

    def __init__(self, max_history_minutes: int = 60):
        """
        Initialize metrics service with in-memory storage.

        Args:
            max_history_minutes: How long to keep metrics in memory
        """
        self.max_history = timedelta(minutes=max_history_minutes)
        self._lock = threading.Lock()

        # Time-series data (thread-safe collections)
        self.response_times: deque = deque(maxlen=10000)
        self.cache_hits: deque = deque(maxlen=1000)
        self.cache_misses: deque = deque(maxlen=1000)
        self.errors: deque = deque(maxlen=1000)
        self.token_usage: deque = deque(maxlen=1000)

        # Real-time counters
        self.total_requests = 0
        self.total_errors = 0
        self.total_tokens = 0

        # Start cleanup task
        asyncio.create_task(self._cleanup_old_metrics())

        logger.info(
            f"🔥 METRICS SERVICE: Initialized with {max_history_minutes}m history"
        )

    def record_response_time(
        self, duration_seconds: float, endpoint: str = "chat", source: str = "unknown"
    ):
        """Record API response time."""
        with self._lock:
            entry = MetricEntry(
                timestamp=datetime.now(),
                value=duration_seconds,
                labels={"endpoint": endpoint, "source": source},
            )
            self.response_times.append(entry)
            self.total_requests += 1

        logger.debug(f"📊 RESPONSE TIME: {duration_seconds:.3f}s ({endpoint}/{source})")

    def record_cache_hit(self, cache_type: str = "embedding"):
        """Record cache hit."""
        with self._lock:
            entry = MetricEntry(
                timestamp=datetime.now(),
                value=1.0,
                labels={"type": cache_type, "result": "hit"},
            )
            self.cache_hits.append(entry)

        logger.debug(f"🎯 CACHE HIT: {cache_type}")

    def record_cache_miss(self, cache_type: str = "embedding"):
        """Record cache miss."""
        with self._lock:
            entry = MetricEntry(
                timestamp=datetime.now(),
                value=1.0,
                labels={"type": cache_type, "result": "miss"},
            )
            self.cache_misses.append(entry)

        logger.debug(f"💸 CACHE MISS: {cache_type}")

    def record_error(self, error_type: str, endpoint: str = "chat"):
        """Record error occurrence."""
        with self._lock:
            entry = MetricEntry(
                timestamp=datetime.now(),
                value=1.0,
                labels={"type": error_type, "endpoint": endpoint},
            )
            self.errors.append(entry)
            self.total_errors += 1

        logger.warning(f"❌ ERROR: {error_type} on {endpoint}")

    def record_token_usage(
        self, tokens: int, model: str = "gpt-4o-mini", operation: str = "chat"
    ):
        """Record token usage for cost tracking."""
        with self._lock:
            entry = MetricEntry(
                timestamp=datetime.now(),
                value=float(tokens),
                labels={"model": model, "operation": operation},
            )
            self.token_usage.append(entry)
            self.total_tokens += tokens

        # Estimate cost (rough approximations)
        cost_per_token = {
            "gpt-4o-mini": 0.00000015,  # $0.15 per 1M tokens
            "text-embedding-3-small": 0.00000002,  # $0.02 per 1M tokens
        }

        estimated_cost = tokens * cost_per_token.get(model, 0.0001)
        logger.debug(
            f"💰 TOKENS: {tokens} ({model}/{operation}) ~${estimated_cost:.6f}"
        )

    def get_performance_summary(self, last_minutes: int = 15) -> PerformanceMetrics:
        """
        Get performance metrics summary for the last N minutes.

        Args:
            last_minutes: Time window for metrics calculation

        Returns:
            PerformanceMetrics summary
        """
        cutoff = datetime.now() - timedelta(minutes=last_minutes)

        with self._lock:
            # Filter recent entries
            recent_responses = [e for e in self.response_times if e.timestamp > cutoff]
            recent_hits = [e for e in self.cache_hits if e.timestamp > cutoff]
            recent_misses = [e for e in self.cache_misses if e.timestamp > cutoff]
            recent_errors = [e for e in self.errors if e.timestamp > cutoff]
            recent_tokens = [e for e in self.token_usage if e.timestamp > cutoff]

        # Calculate response time percentiles
        if recent_responses:
            response_values = [e.value for e in recent_responses]
            avg_time = statistics.mean(response_values)
            p95_time = (
                statistics.quantiles(response_values, n=20)[18]
                if len(response_values) > 20
                else max(response_values)
            )
            p99_time = (
                statistics.quantiles(response_values, n=100)[98]
                if len(response_values) > 100
                else max(response_values)
            )
        else:
            avg_time = p95_time = p99_time = 0.0

        # Calculate cache hit ratio
        total_cache_ops = len(recent_hits) + len(recent_misses)
        cache_hit_ratio = (
            len(recent_hits) / total_cache_ops if total_cache_ops > 0 else 0.0
        )

        # Calculate error rate
        total_ops = len(recent_responses)
        error_rate = len(recent_errors) / total_ops if total_ops > 0 else 0.0

        # Calculate token usage and cost
        total_recent_tokens = sum(e.value for e in recent_tokens)
        estimated_cost = total_recent_tokens * 0.00000015  # Rough estimate

        return PerformanceMetrics(
            total_requests=len(recent_responses),
            avg_response_time=avg_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            cache_hit_ratio=cache_hit_ratio,
            error_rate=error_rate,
            tokens_used=int(total_recent_tokens),
            estimated_cost_usd=estimated_cost,
        )

    def get_prometheus_metrics(self) -> str:
        """
        🚀 PROMETHEUS EXPORT
        Generate Prometheus-format metrics for Grafana dashboards.
        """
        summary = self.get_performance_summary(last_minutes=15)

        metrics = f"""# HELP recruiter_radar_response_time_seconds Response time in seconds
# TYPE recruiter_radar_response_time_seconds histogram
recruiter_radar_response_time_avg {summary.avg_response_time:.3f}
recruiter_radar_response_time_p95 {summary.p95_response_time:.3f}
recruiter_radar_response_time_p99 {summary.p99_response_time:.3f}

# HELP recruiter_radar_cache_hit_ratio Cache hit ratio (0-1)
# TYPE recruiter_radar_cache_hit_ratio gauge
recruiter_radar_cache_hit_ratio {summary.cache_hit_ratio:.3f}

# HELP recruiter_radar_error_rate Error rate (0-1)
# TYPE recruiter_radar_error_rate gauge
recruiter_radar_error_rate {summary.error_rate:.3f}

# HELP recruiter_radar_tokens_used_total Total tokens used
# TYPE recruiter_radar_tokens_used_total counter
recruiter_radar_tokens_used_total {summary.tokens_used}

# HELP recruiter_radar_estimated_cost_usd_total Estimated cost in USD
# TYPE recruiter_radar_estimated_cost_usd_total counter
recruiter_radar_estimated_cost_usd_total {summary.estimated_cost_usd:.6f}

# HELP recruiter_radar_requests_total Total requests processed
# TYPE recruiter_radar_requests_total counter
recruiter_radar_requests_total {self.total_requests}
"""
        return metrics

    async def _cleanup_old_metrics(self):
        """Background task to clean up old metrics."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                cutoff = datetime.now() - self.max_history

                with self._lock:
                    # Clean up old entries
                    self.response_times = deque(
                        [e for e in self.response_times if e.timestamp > cutoff],
                        maxlen=10000,
                    )
                    self.cache_hits = deque(
                        [e for e in self.cache_hits if e.timestamp > cutoff],
                        maxlen=1000,
                    )
                    self.cache_misses = deque(
                        [e for e in self.cache_misses if e.timestamp > cutoff],
                        maxlen=1000,
                    )
                    self.errors = deque(
                        [e for e in self.errors if e.timestamp > cutoff], maxlen=1000
                    )
                    self.token_usage = deque(
                        [e for e in self.token_usage if e.timestamp > cutoff],
                        maxlen=1000,
                    )

                logger.debug("🧹 METRICS CLEANUP: Removed old entries")

            except Exception as e:
                logger.error(f"Metrics cleanup failed: {e}")


# Global metrics instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get or create global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


# Convenience decorators and context managers
class MetricsTimer:
    """Context manager for timing operations."""

    def __init__(self, operation: str, endpoint: str = "unknown"):
        self.operation = operation
        self.endpoint = endpoint
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        metrics = get_metrics_service()

        if exc_type is None:
            metrics.record_response_time(duration, self.endpoint, self.operation)
        else:
            metrics.record_error(str(exc_type.__name__), self.endpoint)
            metrics.record_response_time(
                duration, self.endpoint, f"{self.operation}_error"
            )


def track_performance(endpoint: str = "unknown", operation: str = "unknown"):
    """Decorator for tracking function performance."""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with MetricsTimer(operation, endpoint):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            with MetricsTimer(operation, endpoint):
                return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
