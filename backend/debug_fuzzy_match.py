#!/usr/bin/env python3
"""
Debug script to test the apply_fuzzy_skills_filter function directly.
"""

import sys
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.search_utils import apply_fuzzy_skills_filter


def test_fuzzy_skills_filter():
    """Test the fuzzy skills filter with sample data."""
    print("🧪 Testing apply_fuzzy_skills_filter function:")
    print("=" * 60)

    # Sample candidate data structure
    sample_candidates = [
        {
            "id": "c001",
            "metadata": {
                "name": "React Developer",
                "skills": "React, JavaScript, HTML, CSS, Node.js",
            },
        },
        {
            "id": "c002",
            "metadata": {
                "name": "Python Developer",
                "skills": "Python, Django, PostgreSQL, Docker",
            },
        },
        {
            "id": "c003",
            "metadata": {
                "name": "Full Stack Developer",
                "skills": "React, Python, Node.js, MongoDB",
            },
        },
        {
            "id": "c004",
            "metadata": {
                "name": "Systems Admin",
                "skills": "Linux, Docker, Kubernetes, AWS",
            },
        },
    ]

    # Test cases
    test_cases = [
        (["react"], "Should match React Developer and Full Stack Developer"),
        (["python"], "Should match Python Developer and Full Stack Developer"),
        (["linux"], "Should match Systems Admin"),
        (["nonexistent"], "Should match no candidates"),
    ]

    for required_skills, description in test_cases:
        print(f"\nTest: Required skills = {required_skills}")
        print(f"Expected: {description}")

        try:
            filtered = apply_fuzzy_skills_filter(
                candidates=sample_candidates,
                required_skills=required_skills,
                preferred_skills=[],
                fuzzy_threshold=0.8,
            )

            print(f"Results: {len(filtered)} candidates matched")
            for candidate in filtered:
                name = candidate["metadata"]["name"]
                skills = candidate["metadata"]["skills"]
                print(f"  - {name}: {skills}")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("-" * 40)


if __name__ == "__main__":
    test_fuzzy_skills_filter()
