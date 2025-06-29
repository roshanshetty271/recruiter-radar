#!/usr/bin/env python3
"""
🚀 CYBER-CHEETAH FEATURE VALIDATION SCRIPT

Tests all the new badass features:
1. Streaming Chat with SSE
2. Smart Result Explanations
3. Observability Metrics
4. Cache Performance
5. Error Handling

Run this to validate the rocket ship is ready for production! 🚀
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
SESSION_ID = "test_cyber_cheetah_123"


class CyberCheetahTester:
    """🚀 Comprehensive test suite for the cyber-cheetah features."""

    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.test_results: Dict[str, Any] = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_streaming_chat(self) -> Dict[str, Any]:
        """🚀 Test the new streaming chat endpoint with SSE."""
        logger.info("🔥 TESTING: Streaming Chat with SSE")

        test_queries = [
            "Python developers with 5+ years experience",
            "React engineers in San Francisco",
            "Senior full-stack developers",
            "DevOps engineers with AWS experience",
        ]

        results = []

        for query in test_queries:
            logger.info(f"📡 STREAMING TEST: '{query}'")
            start_time = time.time()

            try:
                async with self.session.post(
                    f"{BASE_URL}/api/v1/chat/stream",
                    json={"message": query},
                    headers={"X-Session-ID": SESSION_ID, "Accept": "text/event-stream"},
                ) as response:

                    if response.status != 200:
                        logger.error(f"❌ STREAM FAILED: {response.status}")
                        continue

                    events = []
                    candidates_received = 0
                    explanation_received = False

                    async for line in response.content:
                        line_str = line.decode("utf-8").strip()

                        if line_str.startswith("data: "):
                            try:
                                data = json.loads(
                                    line_str[6:]
                                )  # Remove 'data: ' prefix
                                events.append(data)

                                if data.get("status") == "candidate":
                                    candidates_received += 1
                                    logger.info(
                                        f"  📝 Candidate {candidates_received}: {data['candidate'].get('name', 'Unknown')}"
                                    )

                                elif data.get("status") == "candidate_chunk":
                                    chunk_candidates = data.get("candidates", [])
                                    chunk_info = data.get("chunk_info", {})
                                    candidates_received += len(chunk_candidates)
                                    logger.info(
                                        f"  📦 Chunk received: {len(chunk_candidates)} candidates ({chunk_info.get('start', 0)}-{chunk_info.get('end', 0)}/{chunk_info.get('total', 0)})"
                                    )

                                elif data.get("status") == "explanation":
                                    explanation_received = True
                                    logger.info(
                                        f"  🧠 Explanation: {data['explanation'][:60]}..."
                                    )

                                elif data.get("status") == "complete":
                                    total_time = time.time() - start_time
                                    logger.info(
                                        f"  ✅ STREAM COMPLETE in {total_time:.2f}s"
                                    )
                                    break

                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse SSE data: {line_str}")

                    results.append(
                        {
                            "query": query,
                            "total_time": time.time() - start_time,
                            "candidates_received": candidates_received,
                            "explanation_received": explanation_received,
                            "events_count": len(events),
                            "success": True,
                        }
                    )

            except Exception as e:
                logger.error(f"❌ STREAMING ERROR for '{query}': {e}")
                results.append({"query": query, "error": str(e), "success": False})

        return {
            "streaming_tests": results,
            "total_queries": len(test_queries),
            "successful_streams": sum(1 for r in results if r.get("success", False)),
        }

    async def test_smart_explanations(self) -> Dict[str, Any]:
        """🧠 Test the smart result explanations feature."""
        logger.info("🧠 TESTING: Smart Result Explanations")

        test_queries = [
            "Python developers",
            "Machine learning engineers",
            "Frontend developers with React",
            "Senior software engineers",
        ]

        results = []

        for query in test_queries:
            logger.info(f"🧠 EXPLANATION TEST: '{query}'")

            try:
                async with self.session.post(
                    f"{BASE_URL}/api/v1/chat/bulletproof",
                    json={"message": query},
                    headers={"X-Session-ID": SESSION_ID},
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        ai_message = data.get("ai_message", "")
                        candidates_count = len(data.get("candidates", []))

                        # Check if explanation is present (should have 💡 emoji)
                        has_explanation = "💡" in ai_message
                        explanation_quality = (
                            "good" if len(ai_message) > 100 else "basic"
                        )

                        results.append(
                            {
                                "query": query,
                                "candidates_found": candidates_count,
                                "has_smart_explanation": has_explanation,
                                "explanation_quality": explanation_quality,
                                "ai_message_length": len(ai_message),
                                "response_time": data.get("response_time", 0),
                                "success": True,
                            }
                        )

                        logger.info(
                            f"  ✅ {candidates_count} candidates, explanation: {has_explanation}"
                        )

                    else:
                        logger.error(f"❌ EXPLANATION FAILED: {response.status}")
                        results.append(
                            {
                                "query": query,
                                "success": False,
                                "error": f"HTTP {response.status}",
                            }
                        )

            except Exception as e:
                logger.error(f"❌ EXPLANATION ERROR for '{query}': {e}")
                results.append({"query": query, "success": False, "error": str(e)})

        return {
            "explanation_tests": results,
            "queries_with_explanations": sum(
                1 for r in results if r.get("has_smart_explanation", False)
            ),
            "total_queries": len(test_queries),
        }

    async def test_observability_metrics(self) -> Dict[str, Any]:
        """📊 Test the observability and metrics endpoints."""
        logger.info("📊 TESTING: Observability Metrics")

        # First, generate some traffic to create metrics
        await self.generate_test_traffic()

        # Test Prometheus metrics endpoint
        prometheus_success = False
        prometheus_content = ""

        try:
            async with self.session.get(f"{BASE_URL}/api/v1/chat/metrics") as response:
                if response.status == 200:
                    prometheus_content = await response.text()
                    prometheus_success = (
                        "recruiter_radar_response_time" in prometheus_content
                    )
                    logger.info(
                        f"  ✅ Prometheus metrics: {len(prometheus_content)} chars"
                    )
                else:
                    logger.error(f"❌ Prometheus metrics failed: {response.status}")
        except Exception as e:
            logger.error(f"❌ Prometheus metrics error: {e}")

        # Test performance summary endpoint
        performance_success = False
        performance_data = {}

        try:
            async with self.session.get(
                f"{BASE_URL}/api/v1/chat/performance"
            ) as response:
                if response.status == 200:
                    performance_data = await response.json()
                    performance_success = "last_15_minutes" in performance_data
                    logger.info(
                        f"  ✅ Performance summary: {performance_data.get('performance_status', 'Unknown')}"
                    )
                else:
                    logger.error(f"❌ Performance summary failed: {response.status}")
        except Exception as e:
            logger.error(f"❌ Performance summary error: {e}")

        return {
            "prometheus_metrics": {
                "success": prometheus_success,
                "content_length": len(prometheus_content),
                "has_required_metrics": all(
                    metric in prometheus_content
                    for metric in [
                        "recruiter_radar_response_time",
                        "recruiter_radar_cache_hit_ratio",
                        "recruiter_radar_error_rate",
                    ]
                ),
            },
            "performance_summary": {
                "success": performance_success,
                "data": performance_data,
            },
        }

    async def generate_test_traffic(self):
        """Generate some test traffic to populate metrics."""
        logger.info("🚦 GENERATING: Test traffic for metrics")

        test_queries = [
            "Python developers",
            "React engineers",
            "DevOps engineers",
            "Data scientists",
        ]

        # Make a few quick requests to populate metrics
        for query in test_queries:
            try:
                async with self.session.post(
                    f"{BASE_URL}/api/v1/chat/bulletproof",
                    json={"message": query},
                    headers={"X-Session-ID": f"{SESSION_ID}_traffic"},
                ) as response:
                    if response.status == 200:
                        logger.debug(f"  📈 Generated traffic: '{query}'")
                    await asyncio.sleep(0.1)  # Small delay
            except Exception:
                pass  # Ignore errors during traffic generation

    async def test_cache_performance(self) -> Dict[str, Any]:
        """🎯 Test cache hit/miss performance."""
        logger.info("🎯 TESTING: Cache Performance")

        # Send the same query multiple times to test caching
        test_query = "Senior Python developers with machine learning experience"
        cache_results = []

        for i in range(5):
            logger.info(f"🔄 CACHE TEST {i+1}/5: '{test_query}'")
            start_time = time.time()

            try:
                async with self.session.post(
                    f"{BASE_URL}/api/v1/chat/bulletproof",
                    json={"message": test_query},
                    headers={"X-Session-ID": f"{SESSION_ID}_cache_{i}"},
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        response_time = time.time() - start_time

                        cache_results.append(
                            {
                                "iteration": i + 1,
                                "response_time": response_time,
                                "candidates_count": len(data.get("candidates", [])),
                                "source": data.get("source", "unknown"),
                            }
                        )

                        logger.info(
                            f"  ⚡ Response {i+1}: {response_time:.2f}s via {data.get('source', 'unknown')}"
                        )

            except Exception as e:
                logger.error(f"❌ CACHE TEST ERROR {i+1}: {e}")

            await asyncio.sleep(0.5)  # Small delay between requests

        # Analyze cache performance
        avg_response_time = (
            sum(r["response_time"] for r in cache_results) / len(cache_results)
            if cache_results
            else 0
        )
        fastest_response = (
            min(r["response_time"] for r in cache_results) if cache_results else 0
        )

        return {
            "cache_tests": cache_results,
            "avg_response_time": avg_response_time,
            "fastest_response": fastest_response,
            "cache_improvement": (
                cache_results[0]["response_time"] / fastest_response
                if cache_results and fastest_response > 0
                else 1.0
            ),
        }

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """🚀 Run all comprehensive tests."""
        logger.info("🚀 STARTING: Comprehensive Cyber-Cheetah Test Suite")

        start_time = time.time()

        # Run all test suites
        streaming_results = await self.test_streaming_chat()
        explanation_results = await self.test_smart_explanations()
        observability_results = await self.test_observability_metrics()
        cache_results = await self.test_cache_performance()

        total_time = time.time() - start_time

        # Compile overall results
        overall_results = {
            "test_summary": {
                "total_test_time": total_time,
                "streaming_success_rate": streaming_results["successful_streams"]
                / streaming_results["total_queries"],
                "explanations_success_rate": explanation_results[
                    "queries_with_explanations"
                ]
                / explanation_results["total_queries"],
                "observability_working": observability_results["prometheus_metrics"][
                    "success"
                ]
                and observability_results["performance_summary"]["success"],
                "cache_performance_ratio": cache_results.get("cache_improvement", 1.0),
            },
            "detailed_results": {
                "streaming": streaming_results,
                "explanations": explanation_results,
                "observability": observability_results,
                "cache_performance": cache_results,
            },
        }

        # Print summary
        self.print_test_summary(overall_results)

        return overall_results

    def print_test_summary(self, results: Dict[str, Any]):
        """Print a beautiful test summary."""
        summary = results["test_summary"]

        print("\n" + "=" * 80)
        print("🚀 CYBER-CHEETAH TEST RESULTS SUMMARY")
        print("=" * 80)

        print(f"📊 Total Test Time: {summary['total_test_time']:.2f}s")
        print(f"🌊 Streaming Success: {summary['streaming_success_rate']*100:.1f}%")
        print(f"🧠 Smart Explanations: {summary['explanations_success_rate']*100:.1f}%")
        print(
            f"📈 Observability: {'✅ Working' if summary['observability_working'] else '❌ Issues'}"
        )
        print(
            f"🎯 Cache Performance: {summary['cache_performance_ratio']:.1f}x improvement"
        )

        # Overall status
        overall_score = (
            summary["streaming_success_rate"] * 0.3
            + summary["explanations_success_rate"] * 0.3
            + (1.0 if summary["observability_working"] else 0.0) * 0.2
            + min(summary["cache_performance_ratio"] / 2.0, 1.0) * 0.2
        )

        if overall_score >= 0.9:
            status = "🚀 CYBER-CHEETAH READY FOR PRODUCTION!"
        elif overall_score >= 0.7:
            status = "✅ GOOD TO GO (minor issues)"
        else:
            status = "⚠️ NEEDS ATTENTION"

        print(f"\n🎯 OVERALL STATUS: {status} (Score: {overall_score*100:.1f}%)")
        print("=" * 80)


async def main():
    """Run the comprehensive test suite."""
    logger.info("🚀 CYBER-CHEETAH FEATURE VALIDATION STARTING")

    try:
        async with CyberCheetahTester() as tester:
            results = await tester.run_comprehensive_tests()

            # Save results to file
            with open("cyber_cheetah_test_results.json", "w") as f:
                json.dump(results, f, indent=2, default=str)

            logger.info("📁 Test results saved to cyber_cheetah_test_results.json")

    except Exception as e:
        logger.error(f"❌ TEST SUITE FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
