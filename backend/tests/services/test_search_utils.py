"""
Tests for enhanced search utilities
"""

import pytest
from app.services.search_utils import (
    extract_negations_from_query,
    extract_skills_from_query_advanced,
    extract_location_from_query_advanced,
    normalize_location,
    enhance_search_query,
    validate_and_sanitize_query,
    get_query_quality_assessment,
    generate_search_suggestions_for_empty_results,
)


class TestNegationExtraction:
    """Test negation extraction functionality"""

    def test_basic_negations(self):
        """Test basic negation patterns"""
        result = extract_negations_from_query("Python developers but not Java")
        assert "java" in [skill.lower() for skill in result["excluded_skills"]]

    def test_dash_notation(self):
        """Test dash notation for exclusions"""
        result = extract_negations_from_query("React developers -Angular -Vue")
        excluded_lower = [skill.lower() for skill in result["excluded_skills"]]
        assert "angular" in excluded_lower
        assert "vue" in excluded_lower

    def test_complex_negations(self):
        """Test complex negation patterns"""
        result = extract_negations_from_query(
            "Frontend engineers without PHP, no Java but React is fine"
        )
        excluded_lower = [skill.lower() for skill in result["excluded_skills"]]
        assert "php" in excluded_lower
        assert "java" in excluded_lower

    def test_location_negations(self):
        """Test location negations"""
        result = extract_negations_from_query("Remote developers not in New York")
        assert "new york" in [loc.lower() for loc in result["excluded_locations"]]

    def test_no_negations(self):
        """Test queries without negations"""
        result = extract_negations_from_query("Python React developers in SF")
        assert not result["excluded_skills"]
        assert not result["excluded_locations"]
        assert not result["excluded_terms"]


class TestAdvancedSkillExtraction:
    """Test advanced skill extraction with context awareness"""

    def test_required_skills(self):
        """Test extraction of required skills"""
        result = extract_skills_from_query_advanced(
            "Need Python developers with Django"
        )
        assert "python" in result["required_skills"]
        assert "django" in result["required_skills"]

    def test_preferred_skills(self):
        """Test extraction of preferred skills"""
        result = extract_skills_from_query_advanced(
            "React developers, would prefer TypeScript experience"
        )
        assert "react" in result["required_skills"]
        assert "typescript" in result["preferred_skills"]

    def test_skill_categories(self):
        """Test skill categorization"""
        result = extract_skills_from_query_advanced(
            "Full stack developers: React frontend, Python backend, AWS DevOps"
        )
        categories = result["skill_categories"]
        assert "frontend" in categories
        assert "backend" in categories
        assert "devops" in categories

    def test_framework_variations(self):
        """Test framework name variations"""
        result = extract_skills_from_query_advanced(
            "Need React.js and Node.js developers"
        )
        required_lower = [skill.lower() for skill in result["required_skills"]]
        assert any("react" in skill for skill in required_lower)
        assert any("node" in skill for skill in required_lower)

    def test_ai_ml_skills(self):
        """Test AI/ML skill detection"""
        result = extract_skills_from_query_advanced(
            "Machine learning engineers with TensorFlow"
        )
        categories = result["skill_categories"]
        assert "ai_ml" in categories


class TestAdvancedLocationExtraction:
    """Test advanced location extraction"""

    def test_work_arrangements(self):
        """Test work arrangement detection"""
        result = extract_location_from_query_advanced("Remote Python developers")
        assert result["work_arrangement"] == "remote"

    def test_specific_locations(self):
        """Test specific location extraction"""
        result = extract_location_from_query_advanced(
            "React developers in San Francisco"
        )
        assert result["normalized_location"] == "San Francisco, CA"

    def test_international_locations(self):
        """Test international location mapping"""
        result = extract_location_from_query_advanced("Backend engineers in London")
        assert result["normalized_location"] == "London, UK"

    def test_location_flexibility(self):
        """Test location flexibility detection"""
        result = extract_location_from_query_advanced("Developers open to relocation")
        assert result["location_flexibility"] == "flexible"

    def test_hybrid_work(self):
        """Test hybrid work arrangement"""
        result = extract_location_from_query_advanced("Hybrid frontend developers")
        assert result["work_arrangement"] == "hybrid"


class TestLocationNormalization:
    """Test location normalization"""

    def test_common_abbreviations(self):
        """Test common city abbreviations"""
        assert normalize_location("SF") == "San Francisco, CA"
        assert normalize_location("NYC") == "New York, NY"
        assert normalize_location("LA") == "Los Angeles, CA"

    def test_work_arrangements(self):
        """Test work arrangement normalization"""
        assert normalize_location("remote") == "Remote"
        assert normalize_location("work from home") == "Remote"
        assert normalize_location("WFH") == "Remote"

    def test_international(self):
        """Test international location normalization"""
        assert normalize_location("UK") == "United Kingdom"
        assert normalize_location("Germany") == "Germany"

    def test_unknown_location(self):
        """Test unknown location handling"""
        result = normalize_location("Unknown City")
        assert result == "Unknown City"


class TestQueryValidation:
    """Test query validation and sanitization"""

    def test_clean_query(self):
        """Test normal query passes through"""
        result = validate_and_sanitize_query("Python developers in SF")
        assert result["sanitized"] == "Python developers in SF"
        assert not result["was_modified"]
        assert not result["issues"]

    def test_dangerous_content_removal(self):
        """Test removal of dangerous content"""
        result = validate_and_sanitize_query(
            "Python developers <script>alert('xss')</script>"
        )
        assert "<script>" not in result["sanitized"]
        assert result["was_modified"]
        assert result["issues"]

    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        result = validate_and_sanitize_query("Python    developers   in   SF")
        assert result["sanitized"] == "Python developers in SF"
        assert result["was_modified"]

    def test_empty_query(self):
        """Test empty query handling"""
        result = validate_and_sanitize_query("")
        assert result["sanitized"] == ""
        assert not result["was_modified"]


class TestQueryQuality:
    """Test query quality assessment"""

    def test_high_quality_query(self):
        """Test high quality query assessment"""
        result = get_query_quality_assessment(
            "Senior Python developers with Django and React experience in SF"
        )
        assert result["quality_score"] > 0.7
        assert result["strengths"]
        assert (
            "Senior" in result["strengths"][0]
            or "specific skills" in result["strengths"][0]
            or "experience level" in result["strengths"][0]
        )

    def test_low_quality_query(self):
        """Test low quality query assessment"""
        result = get_query_quality_assessment("developer")
        assert result["quality_score"] < 0.5
        assert result["issues"]
        assert result["suggestions"]

    def test_empty_query_quality(self):
        """Test empty query quality"""
        result = get_query_quality_assessment("")
        assert result["quality_score"] == 0.0
        assert "Query is empty" in result["issues"]

    def test_too_long_query(self):
        """Test overly long query assessment"""
        long_query = " ".join(["developer"] * 20)
        result = get_query_quality_assessment(long_query)
        assert result["quality_score"] < 0.8
        assert any("too long" in issue for issue in result["issues"])


class TestSuggestionsForEmptyResults:
    """Test suggestions for empty results"""

    def test_no_results_with_location(self):
        """Test suggestions when location filter yields no results"""
        suggestions = generate_search_suggestions_for_empty_results(
            "Python developers", {"location": "Remote Antarctica"}
        )
        assert any("location" in suggestion.lower() for suggestion in suggestions)

    def test_no_results_high_experience(self):
        """Test suggestions for high experience requirements"""
        suggestions = generate_search_suggestions_for_empty_results(
            "React developers", {"min_experience": 15}
        )
        assert any("experience" in suggestion.lower() for suggestion in suggestions)

    def test_no_results_specific_query(self):
        """Test suggestions for overly specific queries"""
        suggestions = generate_search_suggestions_for_empty_results(
            "Senior Principal Staff React Next.js TypeScript GraphQL PostgreSQL Docker Kubernetes developers",
            {},
        )
        assert any(
            "shorter" in suggestion.lower() or "general" in suggestion.lower()
            for suggestion in suggestions
        )


class TestEnhanceSearchQuery:
    """Test the main search query enhancement function"""

    def test_comprehensive_enhancement(self):
        """Test comprehensive query enhancement"""
        result = enhance_search_query("Senior Python developers in SF but not Java", {})

        # Check basic extraction
        assert result["extracted_location"]
        assert "python" in [skill.lower() for skill in result["extracted_skills"]]

        # Check advanced features
        assert result["negations"]["excluded_skills"]
        assert "java" in [
            skill.lower() for skill in result["negations"]["excluded_skills"]
        ]
        assert result["advanced_skills"]["required_skills"]
        assert result["intelligence_level"] == "advanced"

    def test_empty_query_fallback(self):
        """Test empty query fallback"""
        result = enhance_search_query("", {})
        assert result["used_fallback"]
        assert result["cleaned_query"] != ""
        assert result["suggestions"]

    def test_existing_filters_respected(self):
        """Test that existing filters are not overridden"""
        existing = {"location": "New York", "skills": "React,Vue"}
        result = enhance_search_query("Python developers in SF", existing)

        # Should not override existing filters
        assert result["enhanced_filters"]["location"] == "New York"
        assert "React" in result["enhanced_filters"]["skills"]

    def test_quality_assessment_included(self):
        """Test that query quality assessment is included"""
        result = enhance_search_query("Python developer", {})
        assert "query_quality" in result
        assert "quality_score" in result["query_quality"]

    def test_suggestions_generated(self):
        """Test that intelligent suggestions are generated"""
        result = enhance_search_query("frontend backend developer", {})
        assert result["suggestions"]
        # Should suggest full stack for frontend+backend combination
        assert any(
            "full stack" in suggestion.lower() for suggestion in result["suggestions"]
        )

    def test_work_arrangement_extraction(self):
        """Test work arrangement extraction"""
        result = enhance_search_query("Remote React developers", {})
        assert result["enhanced_filters"].get("work_arrangement") == "remote"

    def test_skill_priority_separation(self):
        """Test separation of required vs preferred skills"""
        result = enhance_search_query("Must have React, would prefer TypeScript", {})
        enhanced_filters = result["enhanced_filters"]

        if "required_skills" in enhanced_filters:
            assert any(
                "react" in skill.lower()
                for skill in enhanced_filters["required_skills"]
            )
        if "preferred_skills" in enhanced_filters:
            assert any(
                "typescript" in skill.lower()
                for skill in enhanced_filters["preferred_skills"]
            )


if __name__ == "__main__":
    pytest.main([__file__])
