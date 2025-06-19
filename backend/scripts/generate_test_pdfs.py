from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import random
from pathlib import Path
import os


def generate_test_resume(filename, name, title, skills, years, location):
    """Generate a simple test PDF resume."""
    c = canvas.Canvas(str(filename), pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, height - 1 * inch, name)

    # Title
    c.setFont("Helvetica", 14)
    c.drawString(1 * inch, height - 1.5 * inch, title)

    # Contact
    c.setFont("Helvetica", 12)
    c.drawString(
        1 * inch, height - 1.8 * inch, f"{location} • {years} years experience"
    )

    # Skills
    c.drawString(1 * inch, height - 2.3 * inch, "Skills:")
    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, height - 2.6 * inch, ", ".join(skills))

    # Experience
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, height - 3.2 * inch, "Experience")

    c.setFont("Helvetica", 11)
    y_pos = height - 3.6 * inch

    # Add some experience
    for i in range(2):
        c.drawString(
            1 * inch,
            y_pos,
            f"• Led development of {random.choice(['web', 'mobile', 'API'])} applications",
        )
        y_pos -= 0.3 * inch
        c.drawString(
            1 * inch, y_pos, f"• Managed team of {random.randint(3, 8)} developers"
        )
        y_pos -= 0.3 * inch
        c.drawString(
            1 * inch, y_pos, f"• Improved performance by {random.randint(20, 80)}%"
        )
        y_pos -= 0.5 * inch

    c.save()
    print(f"Generated: {filename}")


def main():
    # Ensure the output directory exists
    output_dir = Path(__file__).parent / "test_resumes"
    output_dir.mkdir(exist_ok=True)

    print(f"Generating resumes in: {output_dir.resolve()}")

    # Generate test resumes
    test_candidates = [
        (
            "John Smith",
            "Senior Python Developer",
            ["Python", "Django", "AWS", "PostgreSQL"],
            7,
            "San Francisco, CA",
        ),
        (
            "Sarah Johnson",
            "Full Stack Engineer",
            ["React", "Node.js", "TypeScript", "MongoDB"],
            5,
            "New York, NY",
        ),
        (
            "Mike Chen",
            "DevOps Engineer",
            ["Kubernetes", "Docker", "AWS", "Terraform"],
            6,
            "Seattle, WA",
        ),
        (
            "Emily Davis",
            "Frontend Developer",
            ["React", "Vue.js", "JavaScript", "CSS"],
            3,
            "Austin, TX",
        ),
        (
            "David Wilson",
            "Backend Engineer",
            ["Java", "Spring Boot", "MySQL", "Redis"],
            4,
            "Boston, MA",
        ),
    ]

    for i, (name, title, skills, years, location) in enumerate(test_candidates):
        filename = output_dir / f"test_resume_{i+1}_{name.replace(' ', '_')}.pdf"
        generate_test_resume(filename, name, title, skills, years, location)


if __name__ == "__main__":
    main()
