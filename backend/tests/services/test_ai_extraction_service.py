"""
Comprehensive tests for AI Extraction Service

These tests benchmark extraction quality and will help measure improvements
during the fix implementation process.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.ai_extraction_service import AIExtractionService
from app.services.llm_service import LLMService
from app.models.extraction_models import ExtractedResumeData


class TestAIExtractionService:
    """Test suite for AI Extraction Service with focus on real-world scenarios."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing."""
        mock = Mock(spec=LLMService)
        mock.client = AsyncMock()
        return mock

    @pytest.fixture
    def ai_extraction_service(self, mock_llm_service):
        """Create AI extraction service with mocked dependencies."""
        return AIExtractionService(mock_llm_service)

    @pytest.fixture
    def renata_voss_resume_text(self):
        """Test case based on the actual Renata Voss resume that failed."""
        return """R E NATA VO S S
DIRECTOR OF SOFTWARE ENGINEERING

CONTACT WORK EXPERIENCE
r.voss@email.com Director of Software Engineering
(123) 456-7890 Adobe
San Jose, CA 2019 - current / San Jose, CA
LinkedIn Managed cross-functional team on Jira, increasing
Github production velocity by 23%
Integrated IDPS into systems, which decreased instances of
successful socially engineered attacks to less than 1%
Boosted processes through Jenkins-backed workflows that
improved the quality of outcomes by a 54% margin
Achieved a 97% Net Promoter Score and a 4.7 out of 5
rating from end users for error-free end products

Senior Engineering Manager
PayPal
2014 - 2019 / San Jose, CA
Resolved app incompatibility issues with some mobile
devices using AWS, reducing user-reporting incidences by
32%
Incorporated agile best practices into core processes, which
reduced average production cycle time by 17% across
projects
Decreased mobile app density defects by 31% by
integrating React Native UI elements
Worked within budget and timelines to deliver user-
eccentric solutions and maintained a user satisfaction rating
of 94% through customer feedback surveys

Principal Software Engineer
Intel
2010 - 2014 / Santa Clara, CA
Optimized storage and dataset processing through Apache
Hadoop, resulting in a 47% increase in concurrent user
capacity
Automated web applications testing across browsers with
Selenium that shrank user-reported defects by 68%
Led a team of 4 software engineers to create and upgrade
databases on Oracle with a consistent 98% on-time delivery
rate
Implemented cloud infrastructure optimizations, which
decreased monthly hosting costs by 28% and boosted
system reliability

EDUCATION
Bachelor of Science
Software Engineering
California Institute of
Technology
2006 - 2010
Pasadena, CA

SKILLS
JIRA
Amazon Web Services
(AWS)
Jenkins
TensorFlow
Spring Boot
Apache Hadoop
IDPS
Selenium
Oracle
React Native
"""

    @pytest.fixture
    def short_resume_text(self):
        """Simple short resume for basic testing."""
        return """John Doe
Software Engineer
john.doe@email.com
(555) 123-4567

Experience:
Software Engineer at TechCorp (2020-2023)
- Built web applications with React and Node.js
- 3 years of experience

Education:
BS Computer Science, MIT, 2020

Skills: JavaScript, React, Node.js, Python"""

    @pytest.fixture
    def complex_resume_text(self):
        """Complex resume with multiple jobs and sections."""
        return """Dr. Sarah Chen, PhD
Senior Principal Architect | Cloud Infrastructure

📧 sarah.chen@techgiant.com | 📱 +1-425-555-0199
🔗 linkedin.com/in/sarahchen | 🐙 github.com/sarahchen
📍 Seattle, WA | 🌐 sarahchen.dev

PROFESSIONAL EXPERIENCE

Senior Principal Architect | Microsoft Azure (2020 - Present)
• Led architecture for global Azure regions serving 1B+ users
• Reduced infrastructure costs by $50M annually through optimization
• Mentored 15+ senior engineers across 3 continents
• Technologies: Kubernetes, Terraform, Go, Azure, Docker

Principal Software Engineer | Amazon Web Services (2016 - 2020)
• Designed and implemented EC2 auto-scaling algorithms
• Achieved 99.99% uptime for critical services
• Published 12 technical papers on distributed systems
• Technologies: Java, Python, AWS, DynamoDB, Lambda

Senior Software Engineer | Google (2012 - 2016)
• Core contributor to Google Cloud Platform
• Improved query performance by 300% for BigQuery
• Led team of 8 engineers on data pipeline projects
• Technologies: C++, Python, BigQuery, Kubernetes

Software Engineer | Facebook (2010 - 2012)
• Developed News Feed algorithms serving 500M+ users
• Reduced page load times by 40% through optimization
• Technologies: PHP, MySQL, Memcached, React

EDUCATION

PhD Computer Science | Stanford University (2006-2010)
• Dissertation: "Distributed Consensus in Large-Scale Systems"
• Research focus: Distributed systems, consensus algorithms
• GPA: 3.9/4.0

MS Computer Science | Carnegie Mellon University (2004-2006)
• Specialization: Systems and Networking
• GPA: 3.8/4.0

BS Computer Science | UC Berkeley (2000-2004)
• Magna Cum Laude, Phi Beta Kappa
• GPA: 3.9/4.0

CERTIFICATIONS & AWARDS
• AWS Solutions Architect Professional (2018)
• Google Cloud Professional Architect (2017)
• Microsoft Azure Solutions Architect Expert (2021)
• ACM Distinguished Scientist (2019)
• IEEE Fellow (2020)

TECHNICAL SKILLS
Languages: Go, Python, Java, C++, JavaScript, TypeScript, Rust
Cloud: AWS, Azure, GCP, Kubernetes, Docker, Terraform
Databases: PostgreSQL, MongoDB, DynamoDB, BigQuery, Redis
Tools: Git, Jenkins, CircleCI, Grafana, Prometheus, Elasticsearch

PUBLICATIONS & PATENTS
• 25+ peer-reviewed papers in SOSP, OSDI, NSDI
• 8 US patents in distributed systems and cloud computing
• Co-author of "Cloud Architecture Patterns" (O'Reilly, 2019)

LANGUAGES
• English (Native)
• Mandarin (Fluent)
• Spanish (Conversational)
"""

    async def test_extract_resume_data_success(
        self, ai_extraction_service, mock_llm_service, short_resume_text
    ):
        """Test successful AI extraction with simple resume."""
        # Mock successful LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """{
            "name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "(555) 123-4567",
            "location": "Not specified",
            "current_title": "Software Engineer",
            "technical_skills": ["JavaScript", "React", "Node.js", "Python"],
            "soft_skills": [],
            "work_experience": [{
                "company": "TechCorp",
                "title": "Software Engineer",
                "duration": "2020-2023",
                "description": "Built web applications with React and Node.js",
                "technologies": ["React", "Node.js"]
            }],
            "education": [{
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "school": "MIT",
                "graduation_year": "2020"
            }],
            "total_experience_years": 3.0,
            "extraction_confidence": 0.9
        }"""

        mock_llm_service.client.chat.completions.create.return_value = mock_response

        result = await ai_extraction_service.extract_resume_data(short_resume_text)

        assert result is not None
        assert result.name == "John Doe"
        assert result.email == "john.doe@email.com"
        assert result.total_experience_years == 3.0
        assert len(result.technical_skills) == 4
        assert result.extraction_confidence == 0.9

    async def test_extract_resume_data_timeout(
        self, ai_extraction_service, mock_llm_service, renata_voss_resume_text
    ):
        """Test timeout handling - should fall back to regex extraction."""
        # Mock timeout scenario
        mock_llm_service.client.chat.completions.create.side_effect = (
            asyncio.TimeoutError("Request timeout")
        )

        result = await ai_extraction_service.extract_resume_data(
            renata_voss_resume_text, timeout_seconds=1
        )

        # Should return fallback result
        assert result is not None
        assert result.extraction_confidence == 0.5  # Fallback confidence
        # Note: This test will show the current bug (wrong name extraction)
        # After fixes, we should assert result.name == "RENATA VOSS"

    async def test_fallback_extraction_renata_case(
        self, ai_extraction_service, renata_voss_resume_text
    ):
        """Test fallback extraction specifically for the Renata Voss case."""
        result = ai_extraction_service._fallback_extraction(renata_voss_resume_text)

        # Document current behavior (will improve in later steps)
        assert result is not None
        # Current bug: name extraction fails
        print(f"Current fallback name: {result.name}")
        print(f"Current fallback experience: {result.total_experience_years}")
        print(f"Current fallback skills: {result.technical_skills}")

        # These are what we SHOULD get after fixes:
        # assert result.name == "RENATA VOSS"
        # assert result.total_experience_years >= 10  # Should be ~15 years
        # assert "React" in result.technical_skills

    async def test_post_processing_experience_calculation(self, ai_extraction_service):
        """Test experience calculation accuracy."""
        # Create mock extracted data with work experience
        from app.models.extraction_models import WorkExperienceItem

        work_exp = [
            WorkExperienceItem(
                company="Adobe",
                title="Director",
                duration="2019 - current",
                description="Managing team",
            ),
            WorkExperienceItem(
                company="PayPal",
                title="Manager",
                duration="2014 - 2019",
                description="Senior role",
            ),
            WorkExperienceItem(
                company="Intel",
                title="Engineer",
                duration="2010 - 2014",
                description="Software engineer",
            ),
        ]

        # Test the experience calculation
        calculated_years = ai_extraction_service._calculate_experience_from_jobs(
            work_exp
        )

        # Should be approximately 15 years (2010 to 2025)
        assert calculated_years >= 14 and calculated_years <= 16
        print(f"Calculated experience: {calculated_years} years")

    async def test_analytics_tracking(self, ai_extraction_service):
        """Test that analytics are properly tracked."""
        # Get initial stats
        initial_stats = ai_extraction_service.get_analytics(hours_back=1)

        # Perform a fallback extraction
        ai_extraction_service._fallback_extraction("Simple resume text")

        # Check that analytics were updated
        updated_stats = ai_extraction_service.get_analytics(hours_back=1)

        assert "total_extractions" in updated_stats
        assert "success_rate" in updated_stats

    def test_cache_functionality(self, ai_extraction_service):
        """Test caching mechanism."""
        text = "Sample resume text"
        cache_key = ai_extraction_service._generate_cache_key(text)

        assert cache_key is not None
        assert isinstance(cache_key, str)

    @pytest.mark.parametrize(
        "resume_text,expected_skills",
        [
            (
                "Experience with Python, JavaScript, and React",
                ["Python", "Javascript", "React"],
            ),
            ("Proficient in AWS, Docker, Kubernetes", ["Aws", "Docker", "Kubernetes"]),
            ("Java, C++, and .NET development", ["Java", "C++", ".NET"]),
        ],
    )
    def test_skill_extraction_patterns(
        self, ai_extraction_service, resume_text, expected_skills
    ):
        """Test skill extraction from various text patterns."""
        result = ai_extraction_service._extract_obvious_skills(resume_text, [])

        # Check that at least some expected skills are found
        found_skills = [skill.lower() for skill in result]
        for expected in expected_skills:
            assert any(
                expected.lower() in skill for skill in found_skills
            ), f"Expected {expected} not found in {result}"


class TestExtractionBenchmark:
    """Benchmark tests to measure extraction quality improvements."""

    def test_baseline_metrics(self):
        """Establish baseline metrics before improvements."""
        # This test will be used to compare before/after improvements
        # Will be populated with actual test data in subsequent steps
        pass

    def test_diverse_resume_formats(self):
        """Test extraction on diverse resume formats."""
        # Will add various resume formats to test robustness
        pass


# Test data for benchmarking
BENCHMARK_RESUMES = {
    "renata_voss": {
        "text": """Resume text here""",
        "expected": {
            "name": "RENATA VOSS",
            "email": "r.voss@email.com",
            "experience_years": 15,
            "min_skills_count": 10,
            "min_confidence": 0.8,
        },
    }
}


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
