#!/usr/bin/env python3
"""
Setup script for the LLM extraction test harness.
Creates directory structure and provides sample resume templates.
"""

import os
from pathlib import Path


def create_test_structure():
    """Create the test directory structure."""
    base_dir = Path(__file__).parent
    test_dir = base_dir / "test_resumes"

    categories = ["standard", "challenging", "edge_cases", "real_world"]

    for category in categories:
        category_dir = test_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Create a README for each category
        readme_content = get_readme_content(category)
        with open(category_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

    # Create main README
    with open(test_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(get_main_readme())

    # Create sample .env file
    env_example = base_dir / ".env.example"
    with open(env_example, "w", encoding="utf-8") as f:
        f.write("OPENAI_API_KEY=your-api-key-here\n")

    print(f"[SUCCESS] Test directory structure created at: {test_dir}")
    print("\n[INFO] Directory structure:")
    print("test_resumes/")
    for category in categories:
        print(f"  +-- {category}/")
        print(f"  |   +-- README.md")
    print("  +-- README.md")
    print("\n[ACTION] Don't forget to:")
    print("1. Copy .env.example to .env and add your OpenAI API key")
    print("2. Add 3-5 PDF resumes to each category folder")
    print("3. Run: pip install -r requirements-test.txt")


def get_readme_content(category: str) -> str:
    """Get README content for a category."""
    descriptions = {
        "standard": """# Standard Resume Test Cases

This folder should contain clean, well-formatted resumes that represent the ideal case.

## Characteristics:
- Single column layout
- Clear section headers
- Standard fonts
- Consistent formatting
- Machine-readable text (not scanned)

## Suggested test files:
- `software_engineer_clean.pdf` - Traditional SWE resume
- `data_scientist_simple.pdf` - Academic-style CV
- `product_manager_standard.pdf` - Business resume format
- `designer_minimal.pdf` - Clean creative resume

## Expected success rate: 95-100%
""",
        "challenging": """# Challenging Resume Test Cases

This folder should contain resumes with complex layouts that might challenge the parser.

## Characteristics:
- Multi-column layouts
- Heavy graphical elements
- Non-standard fonts
- Tables and charts
- Mixed text orientations

## Suggested test files:
- `two_column_designer.pdf` - Creative dual-column layout
- `infographic_resume.pdf` - Heavy visual elements
- `academic_cv_long.pdf` - 5+ page detailed CV
- `consultant_matrix.pdf` - Complex table structures

## Expected success rate: 70-85%
""",
        "edge_cases": """# Edge Case Test Files

This folder should contain unusual formats that test the limits of extraction.

## Characteristics:
- Scanned/image-based PDFs
- Non-English resumes
- Corrupted or poorly formatted PDFs
- Unusual file encodings
- Minimal text content

## Suggested test files:
- `scanned_image_resume.pdf` - Photo/scan of physical resume
- `non_english_resume.pdf` - Resume in another language
- `corrupted_partial.pdf` - Damaged PDF file
- `text_as_image.pdf` - Text rendered as images

## Expected success rate: 40-70%
""",
        "real_world": """# Real World Test Cases

This folder should contain actual resumes from various sources.

## Characteristics:
- LinkedIn PDF exports
- Indeed resume downloads  
- Job board formatted resumes
- ATS-generated PDFs
- Various real-world formats

## Suggested test files:
- `linkedin_export.pdf` - Direct LinkedIn profile export
- `indeed_formatted.pdf` - Indeed's resume format
- `monster_template.pdf` - Monster.com template
- `ats_parsed.pdf` - Pre-processed by an ATS

## Expected success rate: 75-90%
""",
    }
    return descriptions.get(
        category, "# Test Category\n\nAdd PDF resumes here for testing."
    )


def get_main_readme() -> str:
    """Get main README content."""
    return """# Resume Test Collection

This directory contains test resumes organized by complexity for validating the LLM extraction pipeline.

## Categories:

### [STANDARD] standard/
Clean, well-formatted resumes that should parse easily. Target: 95%+ success rate.

### [CHALLENGING] challenging/
Complex layouts with multiple columns, graphics, tables. Target: 70-85% success rate.

### [EDGE CASES] edge_cases/
Unusual formats, scanned images, non-English text. Target: 40-70% success rate.

### [REAL WORLD] real_world/
Actual resumes from job sites and platforms. Target: 75-90% success rate.

## Adding Test Files:

1. Ensure you have permission to use the resumes (use synthetic/anonymous data)
2. Name files descriptively (e.g., `role_format_issue.pdf`)
3. Aim for 3-5 files per category minimum
4. Include diverse roles, experience levels, and formats

## Privacy Note:
[WARNING] Never commit real resumes with personal information to version control!
Use synthetic data or thoroughly anonymized resumes only.
"""


def create_requirements_file():
    """Create requirements file for the test harness."""
    requirements = """# Test harness requirements
pypdf==3.17.0
openai==1.3.0
python-dotenv==1.0.0
rich==13.7.0

# Optional but recommended
pytest==7.4.3
pytest-asyncio==0.21.1
"""

    req_path = Path(__file__).parent / "requirements-test.txt"
    with open(req_path, "w", encoding="utf-8") as f:
        f.write(requirements)

    print(f"\n[INFO] Requirements file created: {req_path}")


if __name__ == "__main__":
    create_test_structure()
    create_requirements_file()
