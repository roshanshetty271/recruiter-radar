#!/usr/bin/env python3
"""
Debug script to test skills parsing logic.
"""

import re


def parse_skills(skills_raw):
    """Test the skills parsing logic."""
    if isinstance(skills_raw, str):
        # Handle both formats: comma-separated and list-like strings
        if skills_raw.startswith("['") or skills_raw.startswith('["'):
            # Malformed list-like string: ['Python', 'React', ...]
            # Extract items between quotes
            matches = re.findall(r"'([^']*)'|\"([^\"]*)\"", skills_raw)
            candidate_skills = [
                match[0] or match[1] for match in matches if match[0] or match[1]
            ]
            candidate_skills = [
                s.strip().lower() for s in candidate_skills if s.strip()
            ]
        else:
            # Normal comma-separated string
            candidate_skills = [
                s.strip().lower() for s in skills_raw.split(",") if s.strip()
            ]
    else:
        # Fallback for list (shouldn't happen with ChromaDB)
        candidate_skills = [s.lower() for s in skills_raw if s]

    return candidate_skills


def test_parsing():
    """Test both skill formats."""
    test_cases = [
        # Normal format
        "React, JavaScript, HTML, CSS, Node.js",
        # Malformed format
        "['Python', 'React', 'PostgreSQL', 'Docker', 'Kubernetes']",
        # Mixed quotes
        '["Python", "React", "PostgreSQL"]',
        # Empty
        "",
        # Single skill
        "React",
    ]

    print("🧪 Testing skills parsing logic:")
    print("=" * 60)

    for skills_raw in test_cases:
        print(f"Input: {skills_raw}")
        parsed = parse_skills(skills_raw)
        print(f"Output: {parsed}")
        print(f"Contains 'react': {'react' in parsed}")
        print(f"Contains 'python': {'python' in parsed}")
        print("-" * 40)


if __name__ == "__main__":
    test_parsing()
