#!/usr/bin/env python3
"""
Debug script to test skills extraction from queries.
"""

import sys
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.search_utils import extract_skills_from_query


def test_skill_extraction():
    """Test skills extraction for various queries."""
    test_queries = [
        "react",
        "python",
        "show me react developers",
        "python developers",
        "web developers",
        "cloud skills",
        "show me candidates with java skills",
        "find python and react developers",
    ]

    print("🧪 Testing skills extraction:")
    print("=" * 50)

    for query in test_queries:
        extracted_skills = extract_skills_from_query(query)
        print(f"Query: '{query}'")
        print(f"Extracted skills: {extracted_skills}")
        print(f"Skills count: {len(extracted_skills)}")
        print("-" * 30)


if __name__ == "__main__":
    test_skill_extraction()
