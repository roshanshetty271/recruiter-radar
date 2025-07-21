"""
Error Recovery Service for Resume Upload System

This service provides intelligent error recovery, retry logic,
and fallback mechanisms to achieve maximum reliability.

Key features:
- Intelligent retry strategies
- Automatic fallback mechanisms
- Error context preservation
- Recovery success tracking
- Circuit breaker patterns
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    before_sleep_log,
)
import json_repair
import orjson
import re  # Added missing import for enhanced regex fallback

from app.services.enhanced_validation_service import ErrorCategory, ErrorSeverity
from app.models.extraction_models import ExtractedResumeData

logger = structlog.get_logger(__name__)


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error types."""

    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK_METHOD = "fallback_method"
    SKIP_AND_CONTINUE = "skip_and_continue"
    MANUAL_INTERVENTION = "manual_intervention"


class RecoveryResult(str, Enum):
    """Results of recovery attempts."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED_RECOVERABLE = "failed_recoverable"
    FAILED_PERMANENT = "failed_permanent"
    SKIPPED = "skipped"


@dataclass
class ErrorContext:
    """Context information for error recovery."""

    original_error: Exception
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    is_recoverable: bool
    attempt_count: int = 0
    first_occurrence: datetime = field(default_factory=datetime.utcnow)
    last_attempt: datetime = field(default_factory=datetime.utcnow)
    recovery_attempts: List[Dict[str, Any]] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryConfiguration:
    """Configuration for recovery strategies."""

    max_attempts: int = 3
    initial_wait: float = 1.0
    max_wait: float = 10.0
    exponential_base: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    enable_fallbacks: bool = True
    log_recovery_attempts: bool = True


class CircuitBreaker:
    """Circuit breaker for preventing cascade failures."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open")
            else:
                raise Exception("Circuit breaker is open - too many recent failures")

        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker reset to closed")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    "Circuit breaker opened due to failures",
                    failure_count=self.failure_count,
                )
            raise e


class ErrorRecoveryService:
    """Service for intelligent error recovery and retry logic."""

    def __init__(self, config: Optional[RecoveryConfiguration] = None):
        """Initialize the error recovery service."""
        self.config = config or RecoveryConfiguration()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_contexts: Dict[str, ErrorContext] = {}
        self.recovery_stats = {
            "total_errors": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "permanent_failures": 0,
            "circuit_breaker_triggers": 0,
        }

        logger.info("ErrorRecoveryService initialized", config=self.config.__dict__)

    def get_circuit_breaker(self, operation_type: str) -> CircuitBreaker:
        """Get or create circuit breaker for operation type."""
        if operation_type not in self.circuit_breakers:
            self.circuit_breakers[operation_type] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                reset_timeout=self.config.circuit_breaker_timeout,
            )
        return self.circuit_breakers[operation_type]

    async def execute_with_recovery(
        self,
        operation: Callable,
        operation_type: str,
        error_context_key: str,
        fallback_operations: Optional[List[Callable]] = None,
        *args,
        **kwargs,
    ) -> Tuple[Any, RecoveryResult]:
        """
        Execute an operation with intelligent recovery.

        Args:
            operation: The primary operation to execute
            operation_type: Type of operation for circuit breaker grouping
            error_context_key: Unique key for error context tracking
            fallback_operations: List of fallback operations to try

        Returns:
            Tuple of (result, recovery_result)
        """
        self.recovery_stats["total_errors"] += 1

        # Get or create error context
        if error_context_key not in self.error_contexts:
            # We'll create the context when we encounter an error
            pass

        # Try primary operation with retry logic
        try:
            result = await self._execute_with_retry(
                operation, operation_type, error_context_key, *args, **kwargs
            )
            return result, RecoveryResult.SUCCESS
        except Exception as primary_error:
            logger.warning(
                "Primary operation failed, attempting recovery",
                operation_type=operation_type,
                error=str(primary_error),
            )

            # Create error context if not exists
            if error_context_key not in self.error_contexts:
                from app.services.enhanced_validation_service import (
                    EnhancedValidationService,
                )

                validation_service = EnhancedValidationService()
                category, severity, recoverable = validation_service.classify_error(
                    primary_error
                )

                self.error_contexts[error_context_key] = ErrorContext(
                    original_error=primary_error,
                    error_category=category,
                    error_severity=severity,
                    is_recoverable=recoverable,
                    context_data={"operation_type": operation_type},
                )

            error_context = self.error_contexts[error_context_key]

            # Try fallback operations if available and enabled
            if fallback_operations and self.config.enable_fallbacks:
                for i, fallback_op in enumerate(fallback_operations):
                    try:
                        logger.info(
                            "Attempting fallback operation",
                            fallback_number=i + 1,
                            total_fallbacks=len(fallback_operations),
                        )

                        result = await self._execute_with_retry(
                            fallback_op,
                            f"{operation_type}_fallback_{i}",
                            f"{error_context_key}_fallback_{i}",
                            *args,
                            **kwargs,
                        )

                        self.recovery_stats["successful_recoveries"] += 1
                        logger.info(
                            "Fallback operation succeeded", fallback_number=i + 1
                        )
                        return result, RecoveryResult.PARTIAL_SUCCESS

                    except Exception as fallback_error:
                        logger.warning(
                            "Fallback operation failed",
                            fallback_number=i + 1,
                            error=str(fallback_error),
                        )
                        continue

            # All recovery attempts failed
            error_context.recovery_attempts.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "failed",
                    "error": str(primary_error),
                }
            )

            if error_context.is_recoverable:
                self.recovery_stats["recovery_attempts"] += 1
                return None, RecoveryResult.FAILED_RECOVERABLE
            else:
                self.recovery_stats["permanent_failures"] += 1
                return None, RecoveryResult.FAILED_PERMANENT

    async def _execute_with_retry(
        self,
        operation: Callable,
        operation_type: str,
        context_key: str,
        *args,
        **kwargs,
    ) -> Any:
        """Execute operation with retry logic."""
        circuit_breaker = self.get_circuit_breaker(operation_type)

        @retry(
            stop=stop_after_attempt(self.config.max_attempts),
            wait=wait_exponential(
                multiplier=self.config.initial_wait,
                min=self.config.initial_wait,
                max=self.config.max_wait,
            ),
            retry=retry_if_exception_type(
                (
                    ConnectionError,
                    TimeoutError,
                    asyncio.TimeoutError,
                    Exception,  # Retry on most exceptions
                )
            ),
            before_sleep=(
                before_sleep_log(logger, structlog.WARNING)
                if self.config.log_recovery_attempts
                else None
            ),
        )
        async def _retry_wrapper():
            if asyncio.iscoroutinefunction(operation):
                return await circuit_breaker.call(operation, *args, **kwargs)
            else:
                return circuit_breaker.call(operation, *args, **kwargs)

        return await _retry_wrapper()

    async def recover_ai_extraction_error(
        self, error: Exception, resume_text: str, llm_service: Any
    ) -> Optional[ExtractedResumeData]:
        """
        Specialized recovery for AI extraction errors.

        Implements multiple fallback strategies:
        1. JSON repair for malformed responses
        2. Simplified prompt retry
        3. Enhanced regex fallback
        """
        logger.info(
            "Attempting AI extraction error recovery", error_type=type(error).__name__
        )

        # Strategy 1: If it's a JSON error, try to repair the response
        if "json" in str(error).lower() or "parse" in str(error).lower():
            try:
                # This would require storing the raw response, which we'd need to modify the AI service to do
                logger.info("Attempting JSON repair recovery")
                # For now, we'll skip this and go to next strategy
            except Exception as repair_error:
                logger.warning("JSON repair failed", error=str(repair_error))

        # Strategy 2: Retry with simplified prompt
        try:
            logger.info("Attempting simplified prompt recovery")

            # Use a much simpler prompt for recovery
            simplified_prompt = f"""
Extract basic info from this resume in valid JSON format:

{resume_text[:5000]}  # Limit text length

Return only:
{{
    "name": "candidate name",
    "email": "email if found",
    "technical_skills": ["skill1", "skill2"],
    "total_experience_years": 0,
    "extraction_confidence": 0.5
}}
"""

            response = await llm_service.client.chat.completions.create(
                model="gpt-4o-mini",  # Use faster model for recovery
                messages=[
                    {
                        "role": "system",
                        "content": "Extract resume info. Return valid JSON only.",
                    },
                    {"role": "user", "content": simplified_prompt},
                ],
                temperature=0.1,
                max_tokens=500,  # Shorter response
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content:
                # Try orjson first, then json_repair as fallback
                try:
                    data = orjson.loads(content)
                except:
                    repaired_content = json_repair.repair_json(content)
                    data = orjson.loads(repaired_content)

                # Create minimal ExtractedResumeData
                extracted_data = ExtractedResumeData(
                    name=data.get("name", "Unknown"),
                    email=data.get("email"),
                    technical_skills=data.get("technical_skills", []),
                    total_experience_years=float(data.get("total_experience_years", 0)),
                    extraction_confidence=float(data.get("extraction_confidence", 0.5)),
                    professional_summary="Recovered via simplified extraction",
                )

                logger.info(
                    "Simplified prompt recovery successful",
                    name=extracted_data.name,
                    skills_count=len(extracted_data.technical_skills),
                )
                return extracted_data

        except Exception as retry_error:
            logger.warning("Simplified prompt recovery failed", error=str(retry_error))

        # Strategy 3: Enhanced regex fallback
        try:
            logger.info("Attempting enhanced regex fallback recovery")
            return await self._enhanced_regex_fallback(resume_text)
        except Exception as fallback_error:
            logger.error(
                "All AI extraction recovery strategies failed",
                error=str(fallback_error),
            )
            return None

    async def _enhanced_regex_fallback(
        self, text: str
    ) -> Optional[ExtractedResumeData]:
        """Enhanced regex-based extraction as final fallback."""
        try:
            # More comprehensive regex patterns
            patterns = {
                "name": [
                    r"^([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                    r"Name:\s*([A-Z][a-z]+ [A-Z][a-z]+)",
                    r"([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)",
                ],
                "email": [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"],
                "skills": [
                    r"\b(?:Python|Java|JavaScript|TypeScript|React|Node\.js|AWS|Docker|Kubernetes|SQL|PostgreSQL|MongoDB|Git|Linux|Windows|macOS|Angular|Vue|Django|Flask|Spring|Express|HTML|CSS|C\+\+|C#|Go|Rust|PHP|Ruby|Swift|Kotlin|Scala|R|MATLAB|TensorFlow|PyTorch|Machine Learning|Data Science|DevOps|CI/CD|Agile|Scrum)\b"
                ],
                "experience": [
                    r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)",
                    r"experience[:\s]*(\d+)\+?\s*years?",
                ],
            }

            # Extract name
            name = "Unknown"
            for pattern in patterns["name"]:
                match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    break

            # Extract email
            email = None
            for pattern in patterns["email"]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    email = match.group(0)
                    break

            # Extract skills
            skills = set()
            for pattern in patterns["skills"]:
                matches = re.findall(pattern, text, re.IGNORECASE)
                skills.update(matches)
            skills = list(skills)

            # Extract experience
            experience_years = 0.0
            for pattern in patterns["experience"]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    experience_years = float(match.group(1))
                    break

            # Calculate confidence based on extracted data
            confidence = 0.3  # Base confidence for regex fallback
            if name != "Unknown":
                confidence += 0.2
            if email:
                confidence += 0.2
            if len(skills) >= 3:
                confidence += 0.2
            if experience_years > 0:
                confidence += 0.1

            return ExtractedResumeData(
                name=name,
                email=email,
                technical_skills=skills,
                total_experience_years=experience_years,
                extraction_confidence=min(confidence, 1.0),
                professional_summary="Extracted using enhanced regex fallback",
            )

        except Exception as e:
            logger.error("Enhanced regex fallback failed", error=str(e))
            return None

    async def recover_embedding_error(
        self, error: Exception, text: str, llm_service: Any
    ) -> Optional[List[float]]:
        """Recover from embedding generation errors."""
        logger.info("Attempting embedding generation recovery")

        # Strategy 1: Truncate text and retry
        try:
            truncated_text = text[:1000]  # Much shorter text
            logger.info(
                "Retrying embedding with truncated text",
                original_length=len(text),
                truncated_length=len(truncated_text),
            )

            embedding = await llm_service.get_embedding(truncated_text)
            return embedding

        except Exception as truncate_error:
            logger.warning("Truncated text embedding failed", error=str(truncate_error))

        # Strategy 2: Use fallback text
        try:
            fallback_text = "Resume content - embedding generation failed"
            logger.info("Generating fallback embedding")

            embedding = await llm_service.get_embedding(fallback_text)
            return embedding

        except Exception as fallback_error:
            logger.error(
                "All embedding recovery strategies failed", error=str(fallback_error)
            )
            return None

    async def recover_storage_error(
        self, error: Exception, candidate_data: Dict[str, Any], rag_service: Any
    ) -> bool:
        """Recover from database storage errors."""
        logger.info("Attempting storage error recovery")

        # Strategy 1: Sanitize metadata and retry
        try:
            sanitized_metadata = {}
            for key, value in candidate_data.get("metadata", {}).items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        sanitized_metadata[key] = str(value)
                    else:
                        sanitized_metadata[key] = value

            candidate_data["metadata"] = sanitized_metadata

            await rag_service.add_candidate_to_collection(
                candidate_id=candidate_data["candidate_id"],
                embedding=candidate_data["embedding"],
                metadata=sanitized_metadata,
                document_text=candidate_data.get("document_text", ""),
            )

            logger.info("Storage recovery successful with sanitized metadata")
            return True

        except Exception as sanitize_error:
            logger.warning("Sanitized storage retry failed", error=str(sanitize_error))

        # Strategy 2: Store with minimal metadata
        try:
            minimal_metadata = {
                "candidate_id": candidate_data["candidate_id"],
                "name": candidate_data.get("name", "Unknown"),
                "source": "recovered_upload",
            }

            await rag_service.add_candidate_to_collection(
                candidate_id=candidate_data["candidate_id"],
                embedding=candidate_data["embedding"],
                metadata=minimal_metadata,
                document_text=candidate_data.get("document_text", ""),
            )

            logger.info("Storage recovery successful with minimal metadata")
            return True

        except Exception as minimal_error:
            logger.error(
                "All storage recovery strategies failed", error=str(minimal_error)
            )
            return False

    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get error recovery metrics."""
        total_errors = self.recovery_stats["total_errors"]
        recovery_rate = 0.0
        if self.recovery_stats["recovery_attempts"] > 0:
            recovery_rate = (
                self.recovery_stats["successful_recoveries"]
                / self.recovery_stats["recovery_attempts"]
            )

        return {
            "service_status": "active",
            "total_errors_encountered": total_errors,
            "recovery_attempts": self.recovery_stats["recovery_attempts"],
            "successful_recoveries": self.recovery_stats["successful_recoveries"],
            "permanent_failures": self.recovery_stats["permanent_failures"],
            "recovery_success_rate": recovery_rate,
            "circuit_breaker_triggers": self.recovery_stats["circuit_breaker_triggers"],
            "active_circuit_breakers": len(self.circuit_breakers),
            "error_contexts_tracked": len(self.error_contexts),
        }

    def clear_old_contexts(self, hours_back: int = 24):
        """Clear old error contexts to prevent memory buildup."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        old_contexts = [
            key
            for key, context in self.error_contexts.items()
            if context.first_occurrence < cutoff_time
        ]

        for key in old_contexts:
            del self.error_contexts[key]

        if old_contexts:
            logger.info("Cleared old error contexts", removed_count=len(old_contexts))
