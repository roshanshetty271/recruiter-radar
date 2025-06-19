#!/usr/bin/env python3
"""
Create synthetic resume data for testing the extraction pipeline.
This helps test without using real personal data.
"""

from pathlib import Path
from typing import List, Dict
import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Synthetic data pools
FIRST_NAMES = [
    "Alex",
    "Sarah",
    "Michael",
    "Emily",
    "David",
    "Jessica",
    "Ryan",
    "Amanda",
    "James",
    "Lisa",
]
LAST_NAMES = [
    "Chen",
    "Patel",
    "Johnson",
    "Williams",
    "Brown",
    "Davis",
    "Miller",
    "Wilson",
    "Moore",
    "Taylor",
]

TITLES = [
    "Senior Software Engineer",
    "Full Stack Developer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Product Manager",
    "DevOps Engineer",
    "Frontend Developer",
    "Backend Engineer",
    "Solutions Architect",
    "Engineering Manager",
]

COMPANIES = [
    "TechCorp",
    "DataSystems Inc",
    "CloudNet Solutions",
    "AI Innovations",
    "Digital Dynamics",
]

SKILLS_POOL = {
    "languages": [
        "Python",
        "JavaScript",
        "Java",
        "Go",
        "TypeScript",
        "Rust",
        "C++",
        "Ruby",
        "Scala",
    ],
    "frameworks": [
        "React",
        "Django",
        "FastAPI",
        "Node.js",
        "Spring Boot",
        "Vue.js",
        "Angular",
        "Flask",
    ],
    "databases": ["PostgreSQL", "MongoDB", "Redis", "MySQL", "Cassandra", "DynamoDB"],
    "tools": [
        "Docker",
        "Kubernetes",
        "AWS",
        "Git",
        "Jenkins",
        "Terraform",
        "GraphQL",
        "REST APIs",
    ],
    "ml": [
        "TensorFlow",
        "PyTorch",
        "Scikit-learn",
        "Pandas",
        "NumPy",
        "Keras",
        "NLP",
        "Computer Vision",
    ],
}

CITIES = [
    "San Francisco, CA",
    "New York, NY",
    "Seattle, WA",
    "Austin, TX",
    "Boston, MA",
    "Denver, CO",
    "Chicago, IL",
    "Los Angeles, CA",
]


def generate_synthetic_resume_text(
    complexity: str = "standard", include_all_fields: bool = True
) -> Dict[str, any]:
    """Generate synthetic resume data."""

    # Basic info
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    name = f"{first_name} {last_name}"
    email = f"{first_name.lower()}.{last_name.lower()}@email.com"
    phone = f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"
    location = random.choice(CITIES)

    # Professional info
    title = random.choice(TITLES)
    years_exp = random.randint(2, 15)

    # Skills (select random subset)
    skills = []
    for category, skill_list in SKILLS_POOL.items():
        num_skills = random.randint(1, 3)
        skills.extend(random.sample(skill_list, min(num_skills, len(skill_list))))

    # Build resume text based on complexity
    if complexity == "standard":
        text = f"""
{name}
{title}
{email} | {phone} | {location}

PROFESSIONAL SUMMARY
Experienced {title} with {years_exp} years of experience in software development and system design. 
Proven track record of delivering scalable solutions and leading technical initiatives.

TECHNICAL SKILLS
{', '.join(skills[:8])}

PROFESSIONAL EXPERIENCE

{title} | {random.choice(COMPANIES)} | 2022 - Present
• Led development of microservices architecture serving 1M+ users
• Improved system performance by 40% through optimization
• Mentored team of 5 junior developers

Software Engineer | {random.choice(COMPANIES)} | 2019 - 2022  
• Developed RESTful APIs and web applications
• Implemented CI/CD pipelines reducing deployment time by 60%
• Collaborated with cross-functional teams

EDUCATION
Bachelor of Science in Computer Science | University of Technology | 2019
"""

    elif complexity == "challenging":
        # Add more complex formatting, multiple columns simulation
        text = f"""
{name.upper()}                                    CONTACT
{title}                               Email: {email}
                                             Phone: {phone}
                                             Location: {location}

================================================================================

CORE COMPETENCIES          |          TECHNICAL STACK
{skills[0]:20} |          Backend: {', '.join(skills[1:4])}
{skills[4]:20} |          Frontend: {', '.join(skills[5:7])}
{skills[7]:20} |          Database: {', '.join(skills[8:10])}

EXPERIENCE HIGHLIGHTS
+-----------------------------------------------------+
| {years_exp}+ Years Experience | 10+ Projects Delivered |
| 5-Star Performance Reviews | 3x Promoted            |
+-----------------------------------------------------+

{random.choice(COMPANIES)} — {title} (Current)
* Architected cloud-native solutions
* Led Agile transformation initiative
* Achieved 99.9% uptime SLA
"""

    elif complexity == "edge_cases":
        # Minimal or unusual formatting
        if random.choice([True, False]):
            # Minimal
            text = f"{name}\n{email}\n{years_exp} years experience\n"
            skills = skills[:3]  # Fewer skills extracted
        else:
            # Unusual
            text = f"""
:::RESUME START:::
NAME={name}
ROLE={title}
CONTACT={email},{phone}
LOCATION={location}
SKILLS={';'.join(skills[:5])}
EXPERIENCE_YEARS={years_exp}
:::RESUME END:::
"""
    else:
        # Default to standard format if complexity not recognized
        text = f"""
{name}
{title}
{email} | {phone} | {location}

PROFESSIONAL SUMMARY
Experienced {title} with {years_exp} years of experience.

SKILLS
{', '.join(skills[:8])}
"""

    # Conditionally remove fields for testing
    if not include_all_fields:
        remove_fields = random.sample(
            ["phone", "location", "email"], random.randint(1, 2)
        )
        if "phone" in remove_fields and phone:
            text = text.replace(phone, "")
            phone = None
        if "location" in remove_fields and location:
            text = text.replace(location, "")
            location = None
        if "email" in remove_fields and email:
            text = text.replace(email, "")
            email = None

    return {
        "text": text.strip(),
        "expected_extraction": {
            "name": name,
            "title": title,
            "skills": skills[:7],  # Expected to extract top 7
            "location": location,
            "experience_years": years_exp,
            "email": email,
            "phone": phone,
            "summary": f"Experienced {title} with {years_exp} years of experience",
        },
    }


def create_pdf_from_text(text: str, output_path: Path):
    """Create a PDF file from resume text."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Split text into lines and create paragraphs
    lines = text.strip().split("\n")

    for i, line in enumerate(lines):
        if i == 0:  # Name - larger font
            style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                alignment=TA_CENTER,
                fontSize=18,
            )
            para = Paragraph(line, style)
        elif i == 1:  # Title
            style = ParagraphStyle(
                "CustomSubtitle",
                parent=styles["Heading2"],
                alignment=TA_CENTER,
                fontSize=14,
            )
            para = Paragraph(line, style)
        else:
            para = Paragraph(line, styles["Normal"])

        story.append(para)
        if line.strip() == "":  # Add extra space for empty lines
            story.append(Spacer(1, 0.2 * inch))
        else:
            story.append(Spacer(1, 0.1 * inch))

    doc.build(story)


def generate_test_suite():
    """Generate a full suite of test PDFs."""
    script_dir = Path(__file__).parent
    test_dir = script_dir / "test_resumes"

    test_cases = [
        # Standard cases
        ("standard", "software_engineer_clean.pdf", True),
        ("standard", "data_scientist_simple.pdf", True),
        ("standard", "product_manager_standard.pdf", True),
        # Challenging cases
        ("challenging", "two_column_designer.pdf", True),
        ("challenging", "complex_formatted.pdf", True),
        # Edge cases
        ("edge_cases", "minimal_info.pdf", False),  # Missing some fields
        ("edge_cases", "unusual_format.pdf", True),
    ]

    results = []

    for complexity, filename, include_all in test_cases:
        category_dir = test_dir / complexity
        category_dir.mkdir(parents=True, exist_ok=True)

        # Generate synthetic data
        resume_data = generate_synthetic_resume_text(complexity, include_all)

        # Create PDF
        pdf_path = category_dir / filename
        create_pdf_from_text(resume_data["text"], pdf_path)

        # Save expected results for validation
        results.append(
            {
                "file": str(pdf_path.relative_to(test_dir)),
                "expected": resume_data["expected_extraction"],
            }
        )

        print(f"[SUCCESS] Created: {pdf_path}")

    # Save expected results
    import json

    with open(test_dir / "expected_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[INFO] Expected results saved to: {test_dir / 'expected_results.json'}")
    print("\n[SUCCESS] Test suite generation complete!")


if __name__ == "__main__":
    try:
        generate_test_suite()
    except ImportError:
        print("[ERROR] reportlab not installed.")
        print("Run: pip install reportlab")
        print(
            "\nAlternatively, you can manually add PDF files to the test directories."
        )
