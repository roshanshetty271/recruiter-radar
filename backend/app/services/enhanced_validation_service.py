"""
Enhanced Validation Service for Resume Upload System

This service provides comprehensive validation, error classification,
and recovery mechanisms to achieve 99.9% success rate.

Key features:
- Multi-layer file validation
- Intelligent error classification
- Automatic error recovery
- Detailed error reporting
- Performance monitoring
"""

import hashlib
import mimetypes
import structlog

# Handle python-magic import gracefully (it can be problematic on Windows)
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import re

logger = structlog.get_logger(__name__)


class ValidationError(Exception):
    """Base validation error."""

    pass


class RecoverableError(ValidationError):
    """Error that can be automatically recovered from."""

    pass


class IrrecoverableError(ValidationError):
    """Error that cannot be recovered from automatically."""

    pass


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    FILE_VALIDATION = "file_validation"
    TEXT_EXTRACTION = "text_extraction"
    AI_PROCESSING = "ai_processing"
    EMBEDDING_GENERATION = "embedding_generation"
    DATABASE_STORAGE = "database_storage"
    NETWORK_CONNECTIVITY = "network_connectivity"
    RATE_LIMITING = "rate_limiting"
    CONFIGURATION = "configuration"


@dataclass
class ValidationResult:
    """Result of validation check."""

    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.INFO
    category: ErrorCategory = ErrorCategory.FILE_VALIDATION
    recoverable: bool = True
    suggested_action: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FileValidationResult:
    """Comprehensive file validation result."""

    filename: str
    file_size: int
    detected_type: str
    mime_type: str
    is_valid: bool
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    file_hash: str
    estimated_processing_time: float

    @property
    def has_critical_errors(self) -> bool:
        return any(error.severity == ErrorSeverity.CRITICAL for error in self.errors)

    @property
    def has_recoverable_errors(self) -> bool:
        return any(error.recoverable for error in self.errors)


class EnhancedValidationService:
    """Enhanced validation service with comprehensive error handling."""

    SUPPORTED_MIME_TYPES = {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
        "text/html": ".html",  # Sometimes resumes are in HTML format
        "application/rtf": ".rtf",  # Rich Text Format
    }

    SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".html", ".rtf"}

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_FILE_SIZE = 100  # 100 bytes minimum

    # Magic number patterns for file type detection
    FILE_SIGNATURES = {
        b"%PDF": ".pdf",
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": ".doc",
        b"PK\x03\x04": ".docx",  # Also zip files, need more specific check
        b"{\\rtf": ".rtf",
    }

    def __init__(self):
        """Initialize the validation service."""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "errors_by_category": {},
            "recovery_attempts": 0,
            "successful_recoveries": 0,
        }

        logger.info("EnhancedValidationService initialized")

    def validate_file_comprehensive(
        self, file_content: bytes, filename: str, additional_checks: bool = True
    ) -> FileValidationResult:
        """
        Perform comprehensive file validation with multiple layers of checks.

        Args:
            file_content: File content as bytes
            filename: Original filename
            additional_checks: Whether to perform additional expensive checks

        Returns:
            FileValidationResult with detailed validation information
        """
        self.validation_stats["total_validations"] += 1

        errors = []
        warnings = []
        file_size = len(file_content)
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]

        logger.info(
            "Starting comprehensive file validation",
            filename=filename,
            file_size=file_size,
            file_hash=file_hash,
        )

        # Layer 1: Basic validation
        basic_validation = self._validate_basic_properties(file_content, filename)
        if not basic_validation.is_valid:
            errors.append(basic_validation)

        # Layer 2: File type validation
        type_validation = self._validate_file_type(file_content, filename)
        if not type_validation.is_valid:
            errors.append(type_validation)

        detected_type = type_validation.metadata.get("detected_extension", "unknown")
        mime_type = type_validation.metadata.get("mime_type", "unknown")

        # Layer 3: Content validation
        content_validation = self._validate_file_content(file_content, detected_type)
        if not content_validation.is_valid:
            if content_validation.severity == ErrorSeverity.CRITICAL:
                errors.append(content_validation)
            else:
                warnings.append(content_validation)

        # Layer 4: Security validation
        security_validation = self._validate_file_security(file_content, filename)
        if not security_validation.is_valid:
            errors.append(security_validation)

        # Additional checks if requested
        if additional_checks:
            # Layer 5: Performance estimation
            perf_validation = self._estimate_processing_performance(
                file_content, detected_type
            )
            if not perf_validation.is_valid:
                warnings.append(perf_validation)

        # Determine overall validity
        is_valid = len([e for e in errors if e.severity == ErrorSeverity.CRITICAL]) == 0

        if is_valid:
            self.validation_stats["successful_validations"] += 1

        # Estimate processing time
        estimated_time = self._estimate_processing_time(file_size, detected_type)

        result = FileValidationResult(
            filename=filename,
            file_size=file_size,
            detected_type=detected_type,
            mime_type=mime_type,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            file_hash=file_hash,
            estimated_processing_time=estimated_time,
        )

        logger.info(
            "File validation completed",
            filename=filename,
            is_valid=is_valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
            estimated_processing_time=estimated_time,
        )

        return result

    def _validate_basic_properties(
        self, file_content: bytes, filename: str
    ) -> ValidationResult:
        """Validate basic file properties."""
        file_size = len(file_content)

        # Check file size
        if file_size > self.MAX_FILE_SIZE:
            return ValidationResult(
                is_valid=False,
                error_code="file_too_large",
                error_message=f"File size {file_size / 1024 / 1024:.1f}MB exceeds maximum {self.MAX_FILE_SIZE / 1024 / 1024:.1f}MB",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=False,
                suggested_action="Compress file or use a smaller version",
                metadata={"file_size": file_size, "max_size": self.MAX_FILE_SIZE},
            )

        if file_size < self.MIN_FILE_SIZE:
            return ValidationResult(
                is_valid=False,
                error_code="file_too_small",
                error_message=f"File size {file_size} bytes is too small to contain meaningful content",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=False,
                suggested_action="Ensure file contains actual resume content",
                metadata={"file_size": file_size, "min_size": self.MIN_FILE_SIZE},
            )

        # Check filename
        if not filename or filename.strip() == "":
            return ValidationResult(
                is_valid=False,
                error_code="missing_filename",
                error_message="Filename is required",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=True,
                suggested_action="Provide a filename with proper extension",
                metadata={"filename": filename},
            )

        # Check for suspicious filename patterns
        suspicious_patterns = [
            r"[\x00-\x1f\x7f-\x9f]",  # Control characters
            r'[<>:"|?*]',  # Windows forbidden characters
            r"\.{2,}",  # Multiple dots
            r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)",  # Windows reserved names
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    error_code="suspicious_filename",
                    error_message="Filename contains suspicious characters",
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=True,
                    suggested_action="Use alphanumeric characters and standard extensions",
                    metadata={"filename": filename, "pattern": pattern},
                )

        return ValidationResult(
            is_valid=True, metadata={"filename": filename, "file_size": file_size}
        )

    def _validate_file_type(
        self, file_content: bytes, filename: str
    ) -> ValidationResult:
        """Validate file type using multiple detection methods."""
        # Method 1: Extension-based detection
        file_extension = Path(filename).suffix.lower()

        # Method 2: MIME type detection
        try:
            if MAGIC_AVAILABLE and magic:
                mime_type = magic.from_buffer(file_content, mime=True)
            else:
                mime_type = mimetypes.guess_type(filename)[0] or "unknown"
        except Exception:
            mime_type = mimetypes.guess_type(filename)[0] or "unknown"

        # Method 3: Magic number detection
        detected_by_magic = self._detect_by_magic_numbers(file_content)

        logger.info(
            "File type detection",
            filename=filename,
            extension=file_extension,
            mime_type=mime_type,
            magic_detection=detected_by_magic,
        )

        # Validate extension
        if file_extension not in self.SUPPORTED_EXTENSIONS:
            return ValidationResult(
                is_valid=False,
                error_code="unsupported_extension",
                error_message=f"File extension '{file_extension}' not supported. Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=False,
                suggested_action=f"Convert file to one of: {', '.join(self.SUPPORTED_EXTENSIONS)}",
                metadata={
                    "extension": file_extension,
                    "supported_extensions": list(self.SUPPORTED_EXTENSIONS),
                    "mime_type": mime_type,
                    "detected_extension": detected_by_magic,
                },
            )

        # Validate MIME type
        if mime_type not in self.SUPPORTED_MIME_TYPES and mime_type != "unknown":
            return ValidationResult(
                is_valid=False,
                error_code="unsupported_mime_type",
                error_message=f"MIME type '{mime_type}' not supported",
                severity=ErrorSeverity.WARNING,  # Warning because extension might be correct
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=True,
                suggested_action="File might still be processable if extension is correct",
                metadata={
                    "mime_type": mime_type,
                    "supported_mime_types": list(self.SUPPORTED_MIME_TYPES.keys()),
                    "detected_extension": detected_by_magic,
                },
            )

        # Check for type mismatch
        expected_extension = self.SUPPORTED_MIME_TYPES.get(mime_type)
        if (
            expected_extension
            and expected_extension != file_extension
            and mime_type != "unknown"
        ):
            return ValidationResult(
                is_valid=True,  # Not critical, but suspicious
                error_code="type_mismatch",
                error_message=f"File extension '{file_extension}' doesn't match detected type '{expected_extension}'",
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=True,
                suggested_action="Verify file is correct format",
                metadata={
                    "extension": file_extension,
                    "detected_extension": expected_extension,
                    "mime_type": mime_type,
                },
            )

        return ValidationResult(
            is_valid=True,
            metadata={
                "extension": file_extension,
                "mime_type": mime_type,
                "detected_extension": detected_by_magic or file_extension,
            },
        )

    def _detect_by_magic_numbers(self, file_content: bytes) -> Optional[str]:
        """Detect file type by magic numbers."""
        if len(file_content) < 4:
            return None

        for signature, extension in self.FILE_SIGNATURES.items():
            if file_content.startswith(signature):
                # Special handling for ZIP-based formats (like .docx)
                if signature == b"PK\x03\x04":
                    # Check for Office Open XML signatures
                    if (
                        b"word/" in file_content[:1024]
                        or b"[Content_Types].xml" in file_content[:1024]
                    ):
                        return ".docx"
                    return ".zip"  # Generic ZIP file
                return extension

        return None

    def _validate_file_content(
        self, file_content: bytes, file_type: str
    ) -> ValidationResult:
        """Validate file content for basic integrity."""
        if file_type == ".pdf":
            return self._validate_pdf_content(file_content)
        elif file_type == ".docx":
            return self._validate_docx_content(file_content)
        elif file_type in [".txt", ".html"]:
            return self._validate_text_content(file_content)

        return ValidationResult(is_valid=True)

    def _validate_pdf_content(self, file_content: bytes) -> ValidationResult:
        """Validate PDF file content."""
        try:
            # Check for PDF header
            if not file_content.startswith(b"%PDF"):
                return ValidationResult(
                    is_valid=False,
                    error_code="invalid_pdf_header",
                    error_message="File does not have valid PDF header",
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=False,
                    suggested_action="Ensure file is a valid PDF",
                )

            # Check for PDF footer
            if b"%%EOF" not in file_content[-1024:]:
                return ValidationResult(
                    is_valid=False,
                    error_code="truncated_pdf",
                    error_message="PDF file appears to be truncated or corrupted",
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=True,
                    suggested_action="Try re-saving or re-exporting the PDF",
                )

            # Check if it's an image-only PDF (no text content)
            text_indicators = [
                b"/Type/Font",
                b"/Subtype/Type1",
                b"/Type/Catalog",
                b"stream",
            ]
            has_text_content = any(
                indicator in file_content for indicator in text_indicators
            )

            if not has_text_content:
                return ValidationResult(
                    is_valid=True,
                    error_code="image_only_pdf",
                    error_message="PDF may contain only images (will require OCR)",
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.TEXT_EXTRACTION,
                    recoverable=True,
                    suggested_action="OCR extraction will be attempted",
                    metadata={"requires_ocr": True},
                )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_code="pdf_validation_error",
                error_message=f"Error validating PDF: {str(e)}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=True,
                suggested_action="File may still be processable",
            )

        return ValidationResult(is_valid=True)

    def _validate_docx_content(self, file_content: bytes) -> ValidationResult:
        """Validate DOCX file content."""
        try:
            # DOCX is a ZIP file, check ZIP structure
            if not file_content.startswith(b"PK"):
                return ValidationResult(
                    is_valid=False,
                    error_code="invalid_docx_structure",
                    error_message="DOCX file does not have valid ZIP structure",
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=False,
                )

            # Check for Office Open XML indicators
            office_indicators = [b"word/", b"[Content_Types].xml", b"document.xml"]
            has_office_content = any(
                indicator in file_content for indicator in office_indicators
            )

            if not has_office_content:
                return ValidationResult(
                    is_valid=False,
                    error_code="not_office_document",
                    error_message="File is ZIP but not a valid Office document",
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=False,
                    suggested_action="Ensure file is saved in correct DOCX format",
                )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_code="docx_validation_error",
                error_message=f"Error validating DOCX: {str(e)}",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=True,
            )

        return ValidationResult(is_valid=True)

    def _validate_text_content(self, file_content: bytes) -> ValidationResult:
        """Validate text file content."""
        try:
            # Try to decode as UTF-8
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                # Try other common encodings
                text = file_content.decode("latin-1")
            except UnicodeDecodeError:
                return ValidationResult(
                    is_valid=False,
                    error_code="invalid_text_encoding",
                    error_message="Text file has invalid or unsupported encoding",
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=True,
                    suggested_action="Save file in UTF-8 encoding",
                )

        # Check if file has meaningful content
        if len(text.strip()) < 50:
            return ValidationResult(
                is_valid=False,
                error_code="insufficient_text_content",
                error_message="Text file has insufficient content for resume processing",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=False,
                suggested_action="Ensure file contains complete resume text",
            )

        return ValidationResult(is_valid=True)

    def _validate_file_security(
        self, file_content: bytes, filename: str
    ) -> ValidationResult:
        """Validate file for security concerns."""
        # Check file size ratio (compression bombs)
        if len(file_content) > 0:
            # For ZIP-based files, check compression ratio
            if filename.lower().endswith((".docx", ".zip")):
                # This is a simplified check - in production, you'd want more sophisticated detection
                if len(file_content) < 1000 and b"PK" in file_content:
                    # Suspiciously small ZIP file
                    return ValidationResult(
                        is_valid=False,
                        error_code="suspicious_compression",
                        error_message="File has suspicious compression characteristics",
                        severity=ErrorSeverity.WARNING,
                        category=ErrorCategory.FILE_VALIDATION,
                        recoverable=True,
                        suggested_action="File will be processed with extra caution",
                    )

        # Check for embedded executables or scripts
        dangerous_signatures = [
            b"MZ\x90\x00",  # PE executable
            b"\x7fELF",  # ELF executable
            b"<script",  # JavaScript in HTML/XML
            b"<?php",  # PHP code
            b"<%",  # ASP code
        ]

        for signature in dangerous_signatures:
            if signature in file_content:
                return ValidationResult(
                    is_valid=False,
                    error_code="embedded_executable",
                    error_message="File contains embedded executable or script content",
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.FILE_VALIDATION,
                    recoverable=False,
                    suggested_action="Remove embedded content and re-save as clean document",
                )

        return ValidationResult(is_valid=True)

    def _estimate_processing_performance(
        self, file_content: bytes, file_type: str
    ) -> ValidationResult:
        """Estimate processing performance and warn about potential issues."""
        file_size = len(file_content)

        # Warn about large files that may be slow to process
        if file_size > 5 * 1024 * 1024:  # 5MB
            return ValidationResult(
                is_valid=True,
                error_code="large_file_warning",
                error_message=f"Large file ({file_size / 1024 / 1024:.1f}MB) may take longer to process",
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.FILE_VALIDATION,
                recoverable=True,
                suggested_action="Consider compressing or optimizing the file",
                metadata={"estimated_extra_time": "30-60 seconds"},
            )

        # Specific warnings for PDF files
        if file_type == ".pdf" and file_size > 2 * 1024 * 1024:
            if b"/XObject" in file_content and b"/Image" in file_content:
                return ValidationResult(
                    is_valid=True,
                    error_code="image_heavy_pdf",
                    error_message="PDF contains many images and may require OCR processing",
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.TEXT_EXTRACTION,
                    recoverable=True,
                    suggested_action="Processing may take extra time for image text extraction",
                    metadata={"estimated_extra_time": "60-120 seconds"},
                )

        return ValidationResult(is_valid=True)

    def _estimate_processing_time(self, file_size: int, file_type: str) -> float:
        """Estimate processing time based on file characteristics."""
        base_time = 2.0  # Base processing time in seconds

        # Size-based estimation
        size_factor = file_size / (1024 * 1024)  # MB
        size_time = size_factor * 0.5  # 0.5 seconds per MB

        # Type-based estimation
        type_multipliers = {
            ".txt": 0.5,
            ".docx": 1.0,
            ".pdf": 1.5,  # PDFs can be more complex
            ".html": 0.8,
            ".rtf": 0.9,
        }

        type_multiplier = type_multipliers.get(file_type, 1.0)

        estimated_time = (base_time + size_time) * type_multiplier

        # Cap at reasonable maximum
        return min(estimated_time, 120.0)  # Max 2 minutes per file

    def classify_error(
        self, error: Exception
    ) -> Tuple[ErrorCategory, ErrorSeverity, bool]:
        """
        Classify an error by category, severity, and recoverability.

        Returns:
            Tuple of (category, severity, recoverable)
        """
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Network-related errors
        if any(
            keyword in error_message
            for keyword in ["connection", "timeout", "network", "dns"]
        ):
            return ErrorCategory.NETWORK_CONNECTIVITY, ErrorSeverity.WARNING, True

        # Rate limiting errors
        if any(
            keyword in error_message
            for keyword in ["rate limit", "quota", "too many requests"]
        ):
            return ErrorCategory.RATE_LIMITING, ErrorSeverity.WARNING, True

        # AI/LLM specific errors
        if any(
            keyword in error_message
            for keyword in ["openai", "model", "token", "prompt"]
        ):
            return ErrorCategory.AI_PROCESSING, ErrorSeverity.ERROR, True

        # Database errors
        if any(
            keyword in error_message
            for keyword in ["chromadb", "database", "storage", "collection"]
        ):
            return ErrorCategory.DATABASE_STORAGE, ErrorSeverity.ERROR, True

        # File processing errors
        if any(
            keyword in error_message
            for keyword in ["pdf", "docx", "extraction", "parsing"]
        ):
            return ErrorCategory.TEXT_EXTRACTION, ErrorSeverity.ERROR, True

        # Configuration errors
        if any(
            keyword in error_message
            for keyword in ["config", "setting", "environment", "api_key"]
        ):
            return ErrorCategory.CONFIGURATION, ErrorSeverity.CRITICAL, False

        # Default classification
        return ErrorCategory.FILE_VALIDATION, ErrorSeverity.ERROR, True

    def get_validation_metrics(self) -> Dict[str, Any]:
        """Get validation service metrics."""
        success_rate = 0.0
        if self.validation_stats["total_validations"] > 0:
            success_rate = (
                self.validation_stats["successful_validations"]
                / self.validation_stats["total_validations"]
            )

        recovery_rate = 0.0
        if self.validation_stats["recovery_attempts"] > 0:
            recovery_rate = (
                self.validation_stats["successful_recoveries"]
                / self.validation_stats["recovery_attempts"]
            )

        return {
            "service_status": "active",
            "total_validations": self.validation_stats["total_validations"],
            "success_rate": success_rate,
            "recovery_rate": recovery_rate,
            "errors_by_category": dict(self.validation_stats["errors_by_category"]),
            "supported_formats": list(self.SUPPORTED_EXTENSIONS),
            "max_file_size_mb": self.MAX_FILE_SIZE / 1024 / 1024,
        }
