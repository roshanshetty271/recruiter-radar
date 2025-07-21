import asyncio
import sys
import time
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings


async def test_fallback_extraction():
    print("🔬 Testing Enhanced Fallback Extraction")
    print("=" * 60)

    llm_service = LLMService(settings_obj=settings)
    ai_service = AIExtractionService(llm_service)

    # Load test resumes
    test_files = [
        "backend/tests/test_data/resumes/renata_voss.txt",
        "backend/tests/test_data/resumes/simple_resume.txt",
        "backend/tests/test_data/resumes/complex_resume.txt",
    ]

    for file_path in test_files:
        resume_path = Path(file_path)
        if not resume_path.exists():
            print(f"❌ Test file not found: {file_path}")
            continue

        resume_text = resume_path.read_text(encoding="utf-8")
        resume_name = resume_path.stem

        print(f"\n🎯 Testing Fallback for: {resume_name}")
        print("-" * 50)
        print(f"📄 Resume length: {len(resume_text)} chars")

        # Force fallback extraction by calling it directly
        try:
            result = ai_service._fallback_extraction(resume_text)

            if result:
                print(f"✅ FALLBACK SUCCESS:")
                print(f"   📛 Name: '{result.name}'")
                print(f"   📧 Email: {result.email}")
                print(f"   📱 Phone: {result.phone}")
                print(f"   🏠 Location: {result.location}")
                print(f"   💼 Experience: {result.total_experience_years} years")
                print(f"   🛠️ Skills: {len(result.technical_skills)} total")
                print(
                    f"      Skills: {', '.join(result.technical_skills[:5])}{'...' if len(result.technical_skills) > 5 else ''}"
                )
                print(f"   🔗 GitHub: {result.github_url}")
                print(f"   🔗 LinkedIn: {result.linkedin_url}")
                print(f"   📊 Confidence: {result.extraction_confidence:.2f}")
                print(f"   📝 Summary: {result.professional_summary}")
            else:
                print("❌ FALLBACK FAILED - No result returned")

        except Exception as e:
            print(f"💥 FALLBACK ERROR: {e}")

        print()

    # Test with problematic text that would cause name extraction issues
    print("🧪 Testing Edge Cases:")
    print("-" * 30)

    edge_cases = [
        {
            "name": "Job Title as First Line",
            "text": "DIRECTOR OF SOFTWARE ENGINEERING\nJohn Smith\njohn@email.com\nPython, Java, AWS\n5 years experience",
        },
        {
            "name": "Multiple Job Titles",
            "text": "SENIOR SOFTWARE ENGINEER\nLEAD DEVELOPER\nMary Johnson\nmary.johnson@company.com\nReact, Node.js, Docker\nExperience: 8 years",
        },
        {
            "name": "Complex Work History",
            "text": "Alice Chen\nalice.chen@tech.com\nSenior Engineer at Adobe 2019-2024\nSoftware Engineer at PayPal 2014-2019\nJunior Developer at StartupXYZ 2012-2014\nPython, JavaScript, AWS, Docker",
        },
    ]

    for case in edge_cases:
        print(f"\n🔬 Edge Case: {case['name']}")
        try:
            result = ai_service._fallback_extraction(case["text"])
            print(
                f"   Name: '{result.name}' ({'✅' if result.name != 'Unknown Candidate' else '❌'})"
            )
            print(f"   Experience: {result.total_experience_years} years")
            print(f"   Skills: {len(result.technical_skills)}")
            print(f"   Confidence: {result.extraction_confidence:.2f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_fallback_extraction())
