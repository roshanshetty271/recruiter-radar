import sys
import logging
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings

# Set up verbose logging
logging.basicConfig(level=logging.INFO)


def debug_actual_extraction():
    print("🔍 Debugging Actual Fallback Extraction")
    print("=" * 60)

    llm_service = LLMService(settings_obj=settings)
    ai_service = AIExtractionService(llm_service)

    # Load Renata's resume
    resume_path = Path("backend/tests/test_data/resumes/renata_voss.txt")
    resume_text = resume_path.read_text(encoding="utf-8")

    print(f"📄 Testing with first 500 chars:")
    print(resume_text[:500])
    print("\n" + "=" * 60)

    # Call the actual fallback extraction
    result = ai_service._fallback_extraction(resume_text)

    print(f"\n📊 Final Result:")
    print(f"   Name: '{result.name}'")
    print(f"   Email: {result.email}")
    print(f"   Experience: {result.total_experience_years} years")
    print(f"   Skills: {len(result.technical_skills)}")
    print(f"   Confidence: {result.extraction_confidence:.2f}")


if __name__ == "__main__":
    debug_actual_extraction()
