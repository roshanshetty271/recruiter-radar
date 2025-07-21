import asyncio
import sys
import time
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings


async def test_real_extraction():
    print("🔬 Testing Real-World Extraction Conditions")
    print("=" * 50)

    llm_service = LLMService(settings_obj=settings)
    ai_service = AIExtractionService(llm_service)

    # Load the same Renata resume that failed in production
    resume_path = Path("backend/tests/test_data/resumes/renata_voss.txt")
    resume_text = resume_path.read_text(encoding="utf-8")

    print(f"📄 Testing with resume text ({len(resume_text)} chars):")
    print(resume_text[:200] + "...")
    print()

    # Test with different timeout values to understand the issue
    timeouts = [5, 10, 15, 30, 45]

    for timeout in timeouts:
        print(f"⏱️  Testing with {timeout}s timeout...")
        start_time = time.time()

        try:
            result = await ai_service.extract_resume_data(
                resume_text, timeout_seconds=timeout
            )
            elapsed = time.time() - start_time

            if result:
                fallback_used = result.extraction_confidence == 0.5
                print(f"  ✅ Success in {elapsed:.1f}s")
                print(f"  📊 Name: {result.name}")
                print(f"  📧 Email: {result.email}")
                print(f"  💼 Experience: {result.total_experience_years}")
                print(
                    f"  🔧 Skills: {len(result.technical_skills)} - {result.technical_skills[:3]}..."
                )
                print(f"  🎯 Confidence: {result.extraction_confidence}")
                print(f"  🔄 Fallback used: {fallback_used}")
            else:
                print(f"  ❌ Failed - No result")

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"  ⏰ Timeout after {elapsed:.1f}s")

            # Test fallback in timeout scenario
            try:
                fallback_result = ai_service._fallback_extraction(resume_text)
                print(f"  🔄 Fallback result:")
                print(f"    📊 Name: {fallback_result.name}")
                print(f"    💼 Experience: {fallback_result.total_experience_years}")
                print(f"    🔧 Skills: {len(fallback_result.technical_skills)}")
                print(f"    🎯 Confidence: {fallback_result.extraction_confidence}")
            except Exception as fb_e:
                print(f"  ❌ Fallback also failed: {fb_e}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ Exception after {elapsed:.1f}s: {e}")

        print()


if __name__ == "__main__":
    asyncio.run(test_real_extraction())
