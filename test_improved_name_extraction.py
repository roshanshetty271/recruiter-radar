import sys
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings


def test_improved_name_extraction():
    print("🧪 Testing Improved Name Extraction")
    print("=" * 60)

    llm_service = LLMService(settings_obj=settings)
    ai_service = AIExtractionService(llm_service)

    # Test cases with different realistic resume formats
    test_cases = [
        {
            "name": "Real Renata Voss Resume",
            "file": "backend/tests/test_data/resumes/renata_voss.txt",
        },
        {
            "name": "Standard Format",
            "text": "John Smith\nSoftware Engineer\njohn.smith@email.com\n(555) 123-4567\nPython, Java, React",
        },
        {
            "name": "Multi-word Name",
            "text": "Dricus du Plessis\nSenior Developer\ndricus.duplessis@company.com\nJavaScript, Node.js, AWS",
        },
        {
            "name": "Dr. with PhD",
            "text": "Dr. Sarah Chen, PhD\nPrincipal Architect\nsarah.chen@tech.com\nMachine Learning, Python, TensorFlow",
        },
        {
            "name": "Name with Middle Initial",
            "text": "Michael J. Johnson\nLead Engineer\nmichael.johnson@startup.com\nGo, Kubernetes, Docker",
        },
        {
            "name": "Hyphenated Name",
            "text": "Mary-Jane Rodriguez\nData Scientist\nmaryj.rodriguez@company.com\nPython, R, SQL",
        },
        {
            "name": "Job Title First (Should Skip)",
            "text": "SENIOR SOFTWARE ENGINEER\nAlex Thompson\nalex.thompson@email.com\nReact, TypeScript, GraphQL",
        },
        {
            "name": "All Caps Name",
            "text": "LISA ANDERSON\nProduct Manager\nlisa.anderson@company.com\nAgile, Scrum, Product Strategy",
        },
    ]

    for case in test_cases:
        print(f"\n🎯 Testing: {case['name']}")
        print("-" * 40)

        try:
            if "file" in case:
                # Load from file
                resume_path = Path(case["file"])
                if resume_path.exists():
                    resume_text = resume_path.read_text(encoding="utf-8")
                    print(f"📄 Loaded from file: {len(resume_text)} chars")
                else:
                    print(f"❌ File not found: {case['file']}")
                    continue
            else:
                # Use provided text
                resume_text = case["text"]
                print(f"📄 Test text: {resume_text.split()[0]} chars")

            # Test fallback extraction
            result = ai_service._fallback_extraction(resume_text)

            if result:
                extracted_name = result.name
                is_good_extraction = extracted_name != "Unknown Candidate" and not any(
                    keyword in extracted_name.lower()
                    for keyword in [
                        "director",
                        "engineer",
                        "manager",
                        "developer",
                        "senior",
                        "lead",
                    ]
                )

                status = "✅" if is_good_extraction else "⚠️"
                print(f"   {status} Extracted Name: '{extracted_name}'")
                print(f"   📧 Email: {result.email}")
                print(f"   💼 Experience: {result.total_experience_years} years")
                print(f"   🛠️ Skills: {len(result.technical_skills)}")
                print(f"   📊 Confidence: {result.extraction_confidence:.2f}")

                if not is_good_extraction:
                    print(f"   ⚠️ Potential issue: Name may be a job title")

            else:
                print("   ❌ Extraction failed")

        except Exception as e:
            print(f"   💥 Error: {e}")


if __name__ == "__main__":
    test_improved_name_extraction()
