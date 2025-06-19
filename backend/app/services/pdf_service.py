"""
Enhanced PDF service that handles problematic PDFs better.

This replaces your current pdf_service.py with better extraction logic.
"""

import logging
import re
import io
from typing import Tuple, Optional
import pypdf
from app.models.upload_models import PDFExtractionResult

logger = logging.getLogger(__name__)


class PDFService:
    """Service for handling PDF operations with robust text extraction."""

    # Common ligature replacements
    LIGATURE_MAP = {
        "ﬂ": "fl",
        "ﬁ": "fi",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬆ": "st",
        "ﬅ": "st",
    }

    @staticmethod
    def clean_extracted_text(text: str) -> str:
        """
        Clean extracted text from common PDF issues.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Fix ligatures
        for ligature, replacement in PDFService.LIGATURE_MAP.items():
            text = text.replace(ligature, replacement)

        # Fix weird fl pattern from your logs
        text = re.sub(r"fl(?=[A-Z])", "", text)  # Remove fl before capitals
        text = re.sub(r"flfflifl", "", text)  # Remove the repeated pattern

        # Fix excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Fix common PDF extraction issues
        text = text.replace("\x00", "")  # Null characters
        text = text.replace("\xa0", " ")  # Non-breaking spaces

        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

        return text.strip()

    @staticmethod
    async def extract_text_from_pdf(file_content: bytes) -> PDFExtractionResult:
        """
        Extract text from PDF with multiple fallback strategies.

        Args:
            file_content: PDF file bytes

        Returns:
            PDFExtractionResult with extracted text or error
        """
        try:
            pdf_stream = io.BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_stream)

            if reader.is_encrypted:
                try:
                    reader.decrypt("")  # Try empty password
                except:
                    return PDFExtractionResult(
                        success=False, error="PDF is password protected"
                    )

            page_count = len(reader.pages)
            all_text_parts = []

            # Try multiple extraction methods
            for page_num, page in enumerate(reader.pages):
                try:
                    # Method 1: Standard extraction
                    text = page.extract_text()

                    # Check if extraction looks corrupted
                    if text and "flfflifl" in text[:100]:
                        logger.warning(
                            f"Page {page_num} has corrupted extraction, trying visitor method"
                        )

                        # Method 2: Visitor text extraction (more robust)
                        visitor_text = []

                        def visitor_body(text, cm, tm, font_dict, font_size):
                            if text and text.strip():
                                visitor_text.append(text)

                        page.extract_text(visitor_text=visitor_body)
                        text = " ".join(visitor_text)

                    if text:
                        # Clean the text
                        cleaned_text = PDFService.clean_extracted_text(text)
                        if cleaned_text:
                            all_text_parts.append(cleaned_text)

                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {str(e)}")
                    continue

            if not all_text_parts:
                return PDFExtractionResult(
                    success=False,
                    error="Could not extract any text from PDF",
                    page_count=page_count,
                )

            # Join all text
            full_text = "\n\n".join(all_text_parts)

            # Final cleaning
            full_text = PDFService.clean_extracted_text(full_text)

            # Validate extraction quality
            word_count = len(full_text.split())
            if word_count < 20:
                logger.warning(f"Extracted text seems too short: {word_count} words")

            logger.info(
                f"Successfully extracted {len(full_text)} chars "
                f"({word_count} words) from {page_count} pages"
            )

            return PDFExtractionResult(
                success=True,
                text=full_text,
                page_count=page_count,
                char_count=len(full_text),
            )

        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}", exc_info=True)
            return PDFExtractionResult(
                success=False, error=f"Failed to read PDF: {str(e)}"
            )

    @staticmethod
    def truncate_text_for_llm(
        text: str, max_chars: int = 12000, preserve_structure: bool = True
    ) -> str:
        """
        Intelligently truncate text for LLM processing.

        Args:
            text: Full text to truncate
            max_chars: Maximum characters (default safer than 15000)
            preserve_structure: Try to keep complete sentences

        Returns:
            Truncated text
        """
        if len(text) <= max_chars:
            return text

        if preserve_structure:
            # Try to truncate at sentence boundary
            truncated = text[:max_chars]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")

            # Use the latest boundary
            boundary = max(last_period, last_newline)
            if boundary > max_chars * 0.8:  # Don't lose too much
                return truncated[: boundary + 1]

        return text[:max_chars]

    @staticmethod
    def truncate_text_for_embedding(
        text: str, max_chars: int = 6000  # Safe for 8192 token limit
    ) -> str:
        """
        Truncate text specifically for embedding generation.

        Prioritizes the beginning of the resume (name, summary, recent experience).
        """
        if len(text) <= max_chars:
            return text

        # For embeddings, we want the most representative part
        # Usually that's the beginning of a resume
        return PDFService.truncate_text_for_llm(text, max_chars)

    @staticmethod
    def validate_pdf_size(file_size: int, max_size_mb: int = 10) -> Optional[str]:
        """Validate PDF file size."""
        max_bytes = max_size_mb * 1024 * 1024
        if file_size > max_bytes:
            return f"File too large. Maximum size is {max_size_mb}MB"
        return None

    @staticmethod
    def validate_content_type(content_type: str) -> bool:
        """Validate file is PDF."""
        valid_types = ["application/pdf", "application/x-pdf"]
        return content_type.lower() in valid_types
