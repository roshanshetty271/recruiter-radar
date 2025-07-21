import asyncio
import sys
import time
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings


async def test_retry_logic():
    print("🔬 Testing Retry Logic and Adaptive Timeouts")
    print("=" * 60)

    llm_service = LLMService(settings_obj=settings)
    ai_service = AIExtractionService(llm_service)

    # Load the Renata resume that previously failed
    resume_path = Path("backend/tests/test_data/resumes/renata_voss.txt")
    resume_text = resume_path.read_text(encoding="utf-8")

    print(f"📄 Testing with Renata resume ({len(resume_text)} chars)")
    print()

    test_cases = [
        ("Adaptive Timeout (Auto-calculated)", None),
        ("Fixed Short Timeout (5s - should trigger retry)", 5.0),
        ("Fixed Medium Timeout (25s)", 25.0),
    ]

    for test_name, timeout in test_cases:
        print(f"🎯 Test: {test_name}")
        print("-" * 40)

        start_time = time.time()
        try:
            result = await ai_service.extract_resume_data(
                resume_text, timeout_seconds=timeout
            )
            end_time = time.time()

            if result:
                print(f"✅ SUCCESS in {end_time - start_time:.2f}s")
                print(f"   Name: {result.name}")
                print(f"   Experience: {result.total_experience_years} years")
                print(
                    f"   Skills: {len(result.technical_skills + result.soft_skills)} total"
                )
                print(f"   Confidence: {result.extraction_confidence:.2f}")
                print(f"   Jobs: {len(result.work_experience)}")
                print(f"   Email: {result.email}")
                print(f"   Location: {result.location}")
            else:
                print(f"❌ FAILED in {end_time - start_time:.2f}s - No result returned")

        except Exception as e:
            end_time = time.time()
            print(f"💥 ERROR in {end_time - start_time:.2f}s: {e}")

        print()

        # Wait between tests to avoid rate limiting
        await asyncio.sleep(2)

    # Test Analytics
    print("📊 Analytics Summary:")
    print("-" * 30)
    print(f"   Total extractions recorded: {len(ai_service.analytics.extractions)}")
    if ai_service.analytics.extractions:
        success_count = sum(1 for e in ai_service.analytics.extractions if e["success"])
        print(f"   Successful extractions: {success_count}")
        print(
            f"   Failed extractions: {len(ai_service.analytics.extractions) - success_count}"
        )
        avg_time = sum(
            e["extraction_time"] for e in ai_service.analytics.extractions
        ) / len(ai_service.analytics.extractions)
        print(f"   Average extraction time: {avg_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_retry_logic())
