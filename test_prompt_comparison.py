import asyncio
import sys
import time
import json
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings
from backend.app.core.prompts import (
    RESUME_EXTRACTION_PROMPT_V5,
    RESUME_EXTRACTION_PROMPT_V6,
)


async def test_prompt_comparison():
    print("🧪 Prompt V5 vs V6 Comparison Test")
    print("=" * 70)

    llm_service = LLMService(settings_obj=settings)
    ai_service = AIExtractionService(llm_service)

    # Test with our known problematic resumes
    test_files = [
        "backend/tests/test_data/resumes/renata_voss.txt",
        "backend/tests/test_data/resumes/simple_resume.txt",
        "backend/tests/test_data/resumes/complex_resume.txt",
    ]

    results = {}

    for file_path in test_files:
        resume_path = Path(file_path)
        if not resume_path.exists():
            print(f"❌ File not found: {file_path}")
            continue

        resume_text = resume_path.read_text(encoding="utf-8")
        resume_name = resume_path.stem

        print(f"\n🎯 Testing: {resume_name}")
        print("=" * 50)
        print(f"📄 Resume length: {len(resume_text)} chars")

        results[resume_name] = {}

        # Test with both prompts
        for version, prompt_template in [
            ("V5", RESUME_EXTRACTION_PROMPT_V5),
            ("V6", RESUME_EXTRACTION_PROMPT_V6),
        ]:
            print(f"\n📝 Testing Prompt {version}:")

            try:
                start_time = time.time()

                # Temporarily replace the prompt in the service
                original_prompt_import = (
                    ai_service.__class__.__module__ + ".RESUME_EXTRACTION_PROMPT_V6"
                )

                # Prepare the prompt
                processed_text = ai_service._prepare_text_for_extraction(resume_text)
                prompt = prompt_template.format(resume_text=processed_text)

                # Call the LLM directly with the specific prompt
                extraction_task = ai_service._call_llm_for_extraction(prompt)
                result = await asyncio.wait_for(extraction_task, timeout=30)

                end_time = time.time()
                duration = end_time - start_time

                if result:
                    # Calculate metrics
                    metrics = {
                        "success": True,
                        "duration": duration,
                        "name": result.name,
                        "email": result.email,
                        "experience_years": result.total_experience_years,
                        "technical_skills_count": len(result.technical_skills),
                        "soft_skills_count": len(result.soft_skills),
                        "work_experience_count": len(result.work_experience),
                        "education_count": len(result.education),
                        "confidence": result.extraction_confidence,
                        "has_phone": bool(result.phone),
                        "has_location": bool(result.location),
                    }

                    print(f"   ✅ SUCCESS in {duration:.2f}s")
                    print(f"      Name: '{result.name}'")
                    print(f"      Email: {result.email}")
                    print(f"      Experience: {result.total_experience_years} years")
                    print(f"      Technical Skills: {len(result.technical_skills)}")
                    print(f"      Work Experience: {len(result.work_experience)}")
                    print(f"      Confidence: {result.extraction_confidence:.2f}")

                else:
                    metrics = {
                        "success": False,
                        "duration": duration,
                        "error": "No result returned",
                    }
                    print(f"   ❌ FAILED in {duration:.2f}s - No result")

                results[resume_name][version] = metrics

            except asyncio.TimeoutError:
                print(f"   ⏰ TIMEOUT after 30s")
                results[resume_name][version] = {
                    "success": False,
                    "duration": 30.0,
                    "error": "Timeout",
                }
            except Exception as e:
                print(f"   💥 ERROR: {e}")
                results[resume_name][version] = {
                    "success": False,
                    "duration": time.time() - start_time,
                    "error": str(e),
                }

            # Wait between tests to avoid rate limiting
            await asyncio.sleep(2)

    # Generate comparison report
    print("\n\n📊 COMPARISON REPORT")
    print("=" * 70)

    for resume_name, resume_results in results.items():
        print(f"\n📄 {resume_name.upper()}:")
        print("-" * 40)

        v5_result = resume_results.get("V5", {})
        v6_result = resume_results.get("V6", {})

        # Success comparison
        v5_success = v5_result.get("success", False)
        v6_success = v6_result.get("success", False)

        print(
            f"Success:      V5: {'✅' if v5_success else '❌'}  V6: {'✅' if v6_success else '❌'}"
        )

        if v5_success and v6_success:
            # Performance comparison
            v5_time = v5_result.get("duration", 0)
            v6_time = v6_result.get("duration", 0)
            time_diff = ((v6_time - v5_time) / v5_time * 100) if v5_time > 0 else 0

            print(
                f"Duration:     V5: {v5_time:.2f}s  V6: {v6_time:.2f}s ({time_diff:+.1f}%)"
            )

            # Quality comparison
            quality_metrics = [
                ("Name Match", "name"),
                ("Experience", "experience_years"),
                ("Tech Skills", "technical_skills_count"),
                ("Work Exp", "work_experience_count"),
                ("Confidence", "confidence"),
            ]

            for metric_name, metric_key in quality_metrics:
                v5_val = v5_result.get(metric_key, "N/A")
                v6_val = v6_result.get(metric_key, "N/A")

                if isinstance(v5_val, (int, float)) and isinstance(
                    v6_val, (int, float)
                ):
                    if v6_val > v5_val:
                        indicator = "📈"
                    elif v6_val < v5_val:
                        indicator = "📉"
                    else:
                        indicator = "➡️"
                else:
                    indicator = "🔍"

                print(f"{metric_name:12}: V5: {v5_val}  V6: {v6_val} {indicator}")
        else:
            if not v5_success:
                print(f"V5 Error: {v5_result.get('error', 'Unknown')}")
            if not v6_success:
                print(f"V6 Error: {v6_result.get('error', 'Unknown')}")

    # Overall summary
    print(f"\n🏆 OVERALL SUMMARY:")
    print("-" * 30)

    v5_successes = sum(
        1 for r in results.values() if r.get("V5", {}).get("success", False)
    )
    v6_successes = sum(
        1 for r in results.values() if r.get("V6", {}).get("success", False)
    )
    total_tests = len(results)

    print(
        f"Success Rate: V5: {v5_successes}/{total_tests} ({v5_successes/total_tests*100:.1f}%)"
    )
    print(
        f"              V6: {v6_successes}/{total_tests} ({v6_successes/total_tests*100:.1f}%)"
    )

    if v5_successes > 0 and v6_successes > 0:
        v5_avg_time = (
            sum(
                r["V5"]["duration"]
                for r in results.values()
                if r.get("V5", {}).get("success")
            )
            / v5_successes
        )
        v6_avg_time = (
            sum(
                r["V6"]["duration"]
                for r in results.values()
                if r.get("V6", {}).get("success")
            )
            / v6_successes
        )
        time_improvement = (
            ((v5_avg_time - v6_avg_time) / v5_avg_time * 100) if v5_avg_time > 0 else 0
        )

        print(
            f"Avg Duration: V5: {v5_avg_time:.2f}s  V6: {v6_avg_time:.2f}s ({time_improvement:+.1f}%)"
        )

    # Save detailed results
    with open("prompt_comparison_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Detailed results saved to: prompt_comparison_results.json")


if __name__ == "__main__":
    asyncio.run(test_prompt_comparison())
