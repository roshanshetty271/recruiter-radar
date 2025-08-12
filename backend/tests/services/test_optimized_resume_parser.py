"""
Comprehensive tests for Optimized Resume Parser

Tests text extraction, AI integration, and overall parsing workflow.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from io import BytesIO
from fastapi import UploadFile

from app.services.optimized_resume_parser import (
    OptimizedResumeParser,
    OptimizedResumeParsingError,
)
from app.services.llm_service import LLMService
from app.models.extraction_models import ExtractedResumeData
from app.models.candidate import CandidateProfile


class TestOptimizedResumeParser:
    """Test suite for Optimized Resume Parser with real-world scenarios."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing."""
        mock = Mock(spec=LLMService)
        mock.client = AsyncMock()
        return mock

    @pytest.fixture
    def resume_parser(self, mock_llm_service):
        """Create resume parser with mocked dependencies."""
        return OptimizedResumeParser(mock_llm_service)

    @pytest.fixture
    def sample_pdf_content(self):
        """Mock PDF content for testing."""
        # This would be actual PDF bytes in real scenario
        return b"Mock PDF content representing Renata Voss resume"

    @pytest.fixture
    def sample_docx_content(self):
        """Mock DOCX content for testing."""
        return b"Mock DOCX content"

    @pytest.fixture
    def sample_txt_content(self):
        """Sample text content."""
        return """John Doe
Software Engineer
john@email.com
(555) 123-4567

Experience:
- Software Engineer at TechCorp (2020-2023)
- Worked on React applications

Skills: JavaScript, React, Python""".encode(
            "utf-8"
        )

    @pytest.fixture
    def mock_upload_file(self, sample_txt_content):
        """Create mock UploadFile for testing."""
        file_obj = BytesIO(sample_txt_content)
        file_obj.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_resume.txt"
        mock_file.read = AsyncMock(return_value=sample_txt_content)
        mock_file.seek = AsyncMock()
        mock_file.size = len(sample_txt_content)

        return mock_file

    async def test_parse_uploaded_file_success(
        self, resume_parser, mock_upload_file, mock_llm_service
    ):
        """Test successful file parsing workflow."""
        # Mock successful AI extraction
        mock_extracted_data = ExtractedResumeData(
            name="John Doe",
            email="john@email.com",
            technical_skills=["JavaScript", "React", "Python"],
            total_experience_years=3.0,
            extraction_confidence=0.9,
        )

        with patch.object(
            resume_parser.ai_extractor,
            "extract_resume_data",
            return_value=mock_extracted_data,
        ):
            result = await resume_parser.parse_uploaded_file(mock_upload_file)

            assert isinstance(result, CandidateProfile)
            assert result.name == "John Doe"
            assert result.email == "john@email.com"
            assert len(result.skills) >= 3
            assert result.experience_years == 3

    async def test_parse_uploaded_file_with_name_override(
        self, resume_parser, mock_upload_file, mock_llm_service
    ):
        """Test file parsing with manual name override."""
        mock_extracted_data = ExtractedResumeData(
            name="Wrong Name",
            email="john@email.com",
            technical_skills=["JavaScript"],
            total_experience_years=2.0,
            extraction_confidence=0.7,
        )

        with patch.object(
            resume_parser.ai_extractor,
            "extract_resume_data",
            return_value=mock_extracted_data,
        ):
            result = await resume_parser.parse_uploaded_file(
                mock_upload_file, candidate_name="Correct Name"
            )

            assert result.name == "Correct Name"  # Should use override

    async def test_text_extraction_txt(self, resume_parser, sample_txt_content):
        """Test text extraction from TXT files."""
        result = await resume_parser._extract_text_optimized(sample_txt_content, ".txt")

        assert "John Doe" in result
        assert "Software Engineer" in result
        assert "JavaScript" in result

    async def test_timeout_handling(
        self, resume_parser, mock_upload_file, mock_llm_service
    ):
        """Test timeout handling during AI extraction."""
        # Mock timeout in AI extraction
        with patch.object(
            resume_parser.ai_extractor,
            "extract_resume_data",
            side_effect=asyncio.TimeoutError(),
        ):
            # Should not raise exception, should handle gracefully
            with patch.object(
                resume_parser.ai_extractor, "_fallback_extraction"
            ) as mock_fallback:
                mock_fallback.return_value = ExtractedResumeData(
                    name="Fallback Name",
                    email="test@email.com",
                    technical_skills=["Python"],
                    total_experience_years=1.0,
                    extraction_confidence=0.5,
                )

                result = await resume_parser.parse_uploaded_file(mock_upload_file)
                assert result.name == "Fallback Name"
                mock_fallback.assert_called_once()

    async def test_file_validation_size_limit(self, resume_parser):
        """Test file size validation."""
        # Create oversized mock file
        oversized_content = b"x" * (11 * 1024 * 1024)  # 11MB

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large_resume.pdf"
        mock_file.read = AsyncMock(return_value=oversized_content)
        mock_file.seek = AsyncMock()

        with pytest.raises(Exception):  # Should raise HTTPException in real scenario
            await resume_parser._validate_file(mock_file)

    async def test_file_validation_unsupported_type(self, resume_parser):
        """Test file type validation."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "resume.exe"  # Unsupported type
        mock_file.read = AsyncMock(return_value=b"small content")
        mock_file.seek = AsyncMock()

        with pytest.raises(Exception):  # Should raise HTTPException
            await resume_parser._validate_file(mock_file)

    def test_cache_functionality(self, resume_parser):
        """Test caching mechanism."""
        content = b"test content"
        filename = "test.txt"

        cache_key = resume_parser._generate_cache_key(content, filename)
        assert cache_key is not None
        assert isinstance(cache_key, str)

    def test_performance_metrics(self, resume_parser):
        """Test performance metrics collection."""
        metrics = resume_parser.get_performance_metrics()

        assert "status" in metrics
        # Should handle case where no operations have been performed yet

    async def test_parse_resume_optimized_success(
        self, resume_parser, sample_txt_content
    ):
        """Test optimized parsing method."""
        mock_extracted_data = ExtractedResumeData(
            name="Test User",
            email="test@email.com",
            technical_skills=["Python", "JavaScript"],
            total_experience_years=5.0,
            extraction_confidence=0.8,
        )

        with patch.object(
            resume_parser,
            "_extract_with_ai_optimized",
            return_value=mock_extracted_data,
        ):
            result = await resume_parser.parse_resume_optimized(
                sample_txt_content, ".txt"
            )

            assert result is not None
            assert result.name == "Test User"
            assert result.extraction_confidence == 0.8

    async def test_parse_resume_optimized_failure(
        self, resume_parser, sample_txt_content
    ):
        """Test optimized parsing when extraction fails."""
        with patch.object(
            resume_parser,
            "_extract_text_optimized",
            side_effect=Exception("Extraction failed"),
        ):
            result = await resume_parser.parse_resume_optimized(
                sample_txt_content, ".txt"
            )

            assert result is None

    @pytest.mark.parametrize(
        "file_extension,expected_method",
        [
            (".pdf", "_extract_text_from_pdf_optimized"),
            (".docx", "_extract_text_from_docx_optimized"),
            (".txt", None),  # Direct decode for txt
        ],
    )
    async def test_text_extraction_routing(
        self, resume_parser, file_extension, expected_method
    ):
        """Test that correct extraction method is called for each file type."""
        content = b"test content"

        if expected_method:
            with patch.object(
                resume_parser, expected_method, return_value="extracted text"
            ) as mock_method:
                result = await resume_parser._extract_text_optimized(
                    content, file_extension
                )
                mock_method.assert_called_once_with(content)
                assert result == "extracted text"
        else:
            # For .txt files, should decode directly
            result = await resume_parser._extract_text_optimized(
                content, file_extension
            )
            assert result == "test content"


class TestResumeParserBenchmark:
    """Benchmark tests for resume parser performance and accuracy."""

    def test_parsing_speed_benchmark(self):
        """Benchmark parsing speed for various file sizes."""
        # Will implement with actual timing measurements
        pass

    def test_accuracy_benchmark(self):
        """Benchmark extraction accuracy across resume types."""
        # Will implement with known good test cases
        pass


# Test data for various resume formats
TEST_RESUMES = {
    "simple": {
        "content": """John Doe
Software Engineer
john@email.com

Experience: 3 years
Skills: Python, JavaScript""",
        "expected": {
            "name": "John Doe",
            "email": "john@email.com",
            "min_skills": 2,
            "experience_years": 3,
        },
    },
    "renata_voss_case": {
        "content": """RENATA VOSS  
DIRECTOR OF SOFTWARE ENGINEERING
r.voss@email.com
(123) 456-7890
San Jose, CA

WORK EXPERIENCE
Director of Software Engineering
Adobe
2019 - current / San Jose, CA

Senior Engineering Manager  
PayPal
2014 - 2019 / San Jose, CA

Principal Software Engineer
Intel  
2010 - 2014 / Santa Clara, CA""",
        "expected": {
            "name": "RENATA VOSS",
            "email": "r.voss@email.com",
            "experience_years": 15,  # 2010 to 2025
            "min_skills": 5,
        },
    },
}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
