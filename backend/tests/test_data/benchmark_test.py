"""
Baseline Benchmark Test Script

This script establishes baseline metrics for resume extraction quality
before implementing fixes. Run this to measure current performance.
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Any
import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.ai_extraction_service import AIExtractionService
from app.services.llm_service import LLMService
from app.services.optimized_resume_parser import OptimizedResumeParser
from app.core.config import settings


class BenchmarkResults:
    """Class to store and analyze benchmark results."""

    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def add_result(self, test_name: str, result: Dict[str, Any]):
        """Add a test result."""
        result["test_name"] = test_name
        result["timestamp"] = time.time()
        self.results.append(result)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_tests = len(self.results)
        successful_extractions = sum(
            1 for r in self.results if r.get("extraction_success", False)
        )

        confidence_scores = [
            r.get("confidence", 0) for r in self.results if r.get("confidence")
        ]
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        )

        processing_times = [
            r.get("processing_time", 0)
            for r in self.results
            if r.get("processing_time")
        ]
        avg_processing_time = (
            sum(processing_times) / len(processing_times) if processing_times else 0
        )

        timeouts = sum(1 for r in self.results if r.get("timeout", False))
        fallbacks = sum(1 for r in self.results if r.get("used_fallback", False))

        return {
            "total_tests": total_tests,
            "successful_extractions": successful_extractions,
            "success_rate": (
                successful_extractions / total_tests if total_tests > 0 else 0
            ),
            "average_confidence": avg_confidence,
            "average_processing_time": avg_processing_time,
            "timeout_count": timeouts,
            "fallback_count": fallbacks,
            "total_benchmark_time": time.time() - self.start_time,
        }

    def save_results(self, filename: str):
        """Save results to JSON file."""
        data = {"summary": self.get_summary(), "detailed_results": self.results}

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)


# Test cases with expected results
TEST_CASES = {
    "renata_voss": {
        "file": "renata_voss.txt",
        "expected": {
            "name": "RENATA VOSS",
            "email": "r.voss@email.com",
            "experience_years": 15,  # 2010 to 2025
            "min_skills_count": 10,
            "location": "San Jose, CA",
        },
    },
    "simple_resume": {
        "file": "simple_resume.txt",
        "expected": {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "experience_years": 5,  # 2018 to 2023
            "min_skills_count": 6,
            "location": "New York, NY",
        },
    },
    "complex_resume": {
        "file": "complex_resume.txt",
        "expected": {
            "name": "Sarah Chen",
            "email": "sarah.chen@techgiant.com",
            "experience_years": 14,  # 2010 to 2024 (written as "Present")
            "min_skills_count": 15,
            "location": "Seattle, WA",
        },
    },
}


async def benchmark_ai_extraction(
    ai_service: AIExtractionService, test_cases: Dict[str, Dict]
) -> BenchmarkResults:
    """Benchmark AI extraction service with test cases."""
    print("🔬 Starting AI Extraction Benchmark...")
    results = BenchmarkResults()

    resumes_dir = Path(__file__).parent / "resumes"

    for test_name, test_case in test_cases.items():
        print(f"\n📄 Testing: {test_name}")

        # Load resume text
        resume_file = resumes_dir / test_case["file"]
        if not resume_file.exists():
            print(f"❌ Resume file not found: {resume_file}")
            continue

        resume_text = resume_file.read_text(encoding="utf-8")
        expected = test_case["expected"]

        # Time the extraction
        start_time = time.time()
        timeout_occurred = False
        used_fallback = False

        try:
            # Test with current timeout setting (15s)
            extracted_data = await ai_service.extract_resume_data(
                resume_text, timeout_seconds=15
            )

            if extracted_data.extraction_confidence == 0.5:
                used_fallback = True

        except asyncio.TimeoutError:
            print(f"⏰ Timeout occurred for {test_name}")
            timeout_occurred = True
            used_fallback = True
            # Get fallback result
            extracted_data = ai_service._fallback_extraction(resume_text)
        except Exception as e:
            print(f"❌ Error extracting {test_name}: {e}")
            extracted_data = None

        processing_time = time.time() - start_time

        # Analyze results
        if extracted_data:
            # Check accuracy against expected results
            name_correct = (
                extracted_data.name.lower() in expected["name"].lower()
                or expected["name"].lower() in extracted_data.name.lower()
            )
            email_correct = (
                extracted_data.email == expected["email"]
                if extracted_data.email
                else False
            )
            exp_close = (
                abs(
                    extracted_data.total_experience_years - expected["experience_years"]
                )
                <= 2
            )
            skills_sufficient = (
                len(extracted_data.technical_skills) >= expected["min_skills_count"]
            )

            accuracy_score = (
                sum([name_correct, email_correct, exp_close, skills_sufficient]) / 4
            )

            result = {
                "extraction_success": True,
                "confidence": extracted_data.extraction_confidence,
                "processing_time": processing_time,
                "timeout": timeout_occurred,
                "used_fallback": used_fallback,
                "accuracy_score": accuracy_score,
                "extracted_name": extracted_data.name,
                "extracted_email": extracted_data.email,
                "extracted_experience": extracted_data.total_experience_years,
                "extracted_skills_count": len(extracted_data.technical_skills),
                "expected_name": expected["name"],
                "expected_email": expected["email"],
                "expected_experience": expected["experience_years"],
                "expected_skills_count": expected["min_skills_count"],
                "name_correct": name_correct,
                "email_correct": email_correct,
                "experience_close": exp_close,
                "skills_sufficient": skills_sufficient,
            }

            print(f"  ✅ Extraction completed")
            print(f"  📊 Confidence: {extracted_data.extraction_confidence:.2f}")
            print(f"  🎯 Accuracy: {accuracy_score:.2f}")
            print(f"  ⏱️  Time: {processing_time:.2f}s")
            print(f"  🔄 Fallback used: {used_fallback}")

        else:
            result = {
                "extraction_success": False,
                "confidence": 0,
                "processing_time": processing_time,
                "timeout": timeout_occurred,
                "used_fallback": used_fallback,
                "accuracy_score": 0,
                "error": "Extraction failed completely",
            }
            print(f"  ❌ Extraction failed")

        results.add_result(test_name, result)

    return results


async def main():
    """Run the benchmark tests."""
    print("🚀 RecruiterRadar Resume Extraction Benchmark")
    print("=" * 50)

    try:
        # Initialize services with proper settings
        llm_service = LLMService(settings_obj=settings)
        ai_service = AIExtractionService(llm_service)

        # Run benchmarks
        results = await benchmark_ai_extraction(ai_service, TEST_CASES)

        # Print summary
        summary = results.get_summary()
        print("\n" + "=" * 50)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Average Confidence: {summary['average_confidence']:.2f}")
        print(f"Average Processing Time: {summary['average_processing_time']:.2f}s")
        print(f"Timeouts: {summary['timeout_count']}")
        print(f"Fallbacks Used: {summary['fallback_count']}")
        print(f"Total Benchmark Time: {summary['total_benchmark_time']:.2f}s")

        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = f"baseline_results_{timestamp}.json"
        results.save_results(results_file)
        print(f"\n💾 Results saved to: {results_file}")

        # Print recommendations
        print("\n🔍 ANALYSIS:")
        if summary["success_rate"] < 0.8:
            print("❌ Success rate below 80% - significant improvements needed")
        if summary["average_confidence"] < 0.7:
            print("⚠️  Low average confidence - extraction quality needs improvement")
        if summary["timeout_count"] > 0:
            print(
                "⏰ Timeouts occurred - consider increasing timeout or optimizing prompts"
            )
        if summary["fallback_count"] > summary["total_tests"] * 0.5:
            print(
                "🔄 High fallback usage - AI extraction needs reliability improvements"
            )

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
