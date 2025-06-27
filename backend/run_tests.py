#!/usr/bin/env python3
"""
RecruiterRadar Test Runner

Provides convenient commands to run different types of tests.

Usage:
    python run_tests.py --comprehensive    # Run full comprehensive test suite
    python run_tests.py --quick           # Run quick smoke tests only
    python run_tests.py --assistant       # Run assistant-specific tests
    python run_tests.py --api             # Test API endpoints directly
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Coordinate different types of tests."""

    def __init__(self):
        self.results = {}

    async def run_comprehensive_tests(self):
        """Run the full comprehensive test suite."""
        logger.info("🚀 Running Comprehensive Test Suite...")

        try:
            from test_comprehensive_fixes import ComprehensiveTestSuite

            suite = ComprehensiveTestSuite()
            success = await suite.run_all_tests()

            self.results["comprehensive"] = {
                "passed": success,
                "timestamp": datetime.now().isoformat(),
            }

            return success

        except Exception as e:
            logger.error(f"❌ Comprehensive tests failed: {e}")
            return False

    async def run_quick_smoke_tests(self):
        """Run basic smoke tests to verify core functionality."""
        logger.info("💨 Running Quick Smoke Tests...")

        try:
            # Test 1: Service imports
            logger.info("Testing service imports...")
            from app.services.assistant_service import AssistantService
            from app.services.rag_service import RAGService
            from app.core.config import settings

            logger.info("✅ All services import successfully")

            # Test 2: Assistant service initialization
            logger.info("Testing assistant service initialization...")
            assistant_service = AssistantService()
            logger.info("✅ Assistant service initializes")

            # Test 3: Basic function call test
            logger.info("Testing basic function call...")
            result = await assistant_service._execute_function_call(
                "search_candidates", {"query": "test", "skills": ["Python"]}
            )
            smoke_passed = "candidates" in result
            logger.info(f"✅ Function call test: {'PASS' if smoke_passed else 'FAIL'}")

            self.results["smoke"] = {
                "passed": smoke_passed,
                "timestamp": datetime.now().isoformat(),
            }

            return smoke_passed

        except Exception as e:
            logger.error(f"❌ Smoke tests failed: {e}")
            return False

    async def run_assistant_tests(self):
        """Run assistant-specific tests."""
        logger.info("🤖 Running Assistant-Specific Tests...")

        try:
            from app.services.assistant_service import AssistantService

            assistant_service = AssistantService()

            tests_passed = 0
            total_tests = 0

            # Test 1: Dual tool system
            total_tests += 1
            try:
                search_result = await assistant_service._execute_function_call(
                    "search_candidates", {"query": "developers", "skills": ["Python"]}
                )
                if "candidates" in search_result:
                    tests_passed += 1
                    logger.info("✅ Search tool works")
                else:
                    logger.error("❌ Search tool failed")
            except Exception as e:
                logger.error(f"❌ Search tool error: {e}")

            # Test 2: Analysis tool
            total_tests += 1
            try:
                analysis_result = await assistant_service._execute_function_call(
                    "summarise_candidates",
                    {"attribute": "skills", "session_id": "test"},
                )
                # Should fail with "no previous results" but function should exist
                if "No previous search results" in analysis_result.get("error", ""):
                    tests_passed += 1
                    logger.info(
                        "✅ Analysis tool exists (correctly returns error for no cache)"
                    )
                else:
                    logger.error("❌ Analysis tool failed")
            except Exception as e:
                logger.error(f"❌ Analysis tool error: {e}")

            # Test 3: Bulletproof chat
            total_tests += 1
            try:
                response = await assistant_service.bulletproof_recruiter_chat(
                    "find developers", "test_session"
                )
                if hasattr(response, "ai_message") and hasattr(response, "candidates"):
                    tests_passed += 1
                    logger.info("✅ Bulletproof chat works")
                else:
                    logger.error("❌ Bulletproof chat failed")
            except Exception as e:
                logger.error(f"❌ Bulletproof chat error: {e}")

            success_rate = (tests_passed / total_tests) * 100
            passed = success_rate >= 66  # 2/3 tests must pass

            logger.info(
                f"Assistant tests: {tests_passed}/{total_tests} passed ({success_rate:.1f}%)"
            )

            self.results["assistant"] = {
                "passed": passed,
                "tests_passed": tests_passed,
                "total_tests": total_tests,
                "success_rate": success_rate,
                "timestamp": datetime.now().isoformat(),
            }

            return passed

        except Exception as e:
            logger.error(f"❌ Assistant tests failed: {e}")
            return False

    async def run_api_tests(self):
        """Test API endpoints directly."""
        logger.info("🌐 Running API Tests...")

        try:
            import httpx

            # Test if server is running
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8000/docs")
                    if response.status_code == 200:
                        logger.info("✅ Backend server is running")

                        # Test bulletproof chat endpoint (production-ready)
                        chat_response = await client.post(
                            "http://localhost:8000/api/v1/chat/bulletproof",
                            json={"message": "find developers"},
                            headers={"X-Session-ID": "test_api_session"},
                        )

                        if chat_response.status_code == 200:
                            data = chat_response.json()
                            api_working = all(
                                key in data for key in ["ai_message", "candidates"]
                            )
                            if api_working:
                                logger.info("✅ Chat API endpoint works")
                            else:
                                logger.error("❌ Chat API response malformed")

                            self.results["api"] = {
                                "passed": api_working,
                                "timestamp": datetime.now().isoformat(),
                            }
                            return api_working
                        else:
                            logger.error(
                                f"❌ Chat API returned {chat_response.status_code}"
                            )
                            return False
                    else:
                        logger.error("❌ Backend server not responding")
                        return False

            except httpx.ConnectError:
                logger.error(
                    "❌ Cannot connect to backend server. Is it running on localhost:8000?"
                )
                return False

        except ImportError:
            logger.error("❌ httpx not installed. Install with: pip install httpx")
            return False
        except Exception as e:
            logger.error(f"❌ API tests failed: {e}")
            return False


def main():
    """Main test runner with CLI interface."""
    parser = argparse.ArgumentParser(description="RecruiterRadar Test Runner")
    parser.add_argument(
        "--comprehensive", action="store_true", help="Run full comprehensive test suite"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run quick smoke tests only"
    )
    parser.add_argument(
        "--assistant", action="store_true", help="Run assistant-specific tests"
    )
    parser.add_argument(
        "--api", action="store_true", help="Test API endpoints directly"
    )
    parser.add_argument("--all", action="store_true", help="Run all test types")

    args = parser.parse_args()

    # Default to comprehensive if no specific test type
    if not any([args.comprehensive, args.quick, args.assistant, args.api, args.all]):
        args.comprehensive = True

    async def run_tests():
        runner = TestRunner()
        overall_success = True

        logger.info("🎯 RecruiterRadar Test Runner Started")
        start_time = time.time()

        if args.quick or args.all:
            success = await runner.run_quick_smoke_tests()
            overall_success = overall_success and success

        if args.assistant or args.all:
            success = await runner.run_assistant_tests()
            overall_success = overall_success and success

        if args.api or args.all:
            success = await runner.run_api_tests()
            overall_success = overall_success and success

        if args.comprehensive or args.all:
            success = await runner.run_comprehensive_tests()
            overall_success = overall_success and success

        # Results summary
        total_time = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"🏁 TEST RUNNER SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Overall Result: {'✅ PASS' if overall_success else '❌ FAIL'}")
        logger.info(f"Total Execution Time: {total_time:.2f}s")

        # Individual results
        for test_type, result in runner.results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            logger.info(f"{test_type.upper()}: {status}")

        # Save results
        results_file = (
            f"test_runner_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(results_file, "w") as f:
            json.dump(
                {
                    "overall_success": overall_success,
                    "total_time": total_time,
                    "individual_results": runner.results,
                },
                f,
                indent=2,
            )

        logger.info(f"\n📄 Results saved to: {results_file}")

        return overall_success

    # Run async tests
    success = asyncio.run(run_tests())

    if success:
        logger.info("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        logger.error("\n💥 SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
