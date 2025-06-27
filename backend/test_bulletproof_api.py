#!/usr/bin/env python3
"""
Enhanced bulletproof API testing for Phase 3 improvements.
Tests sophisticated recruiting features and enhanced assistant capabilities.
"""

import asyncio
import json
import time
from typing import Dict, Any

import httpx

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_SESSION_ID = "phase3_test_session_001"


# Test Colors
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_test_header(test_name: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}🧪 {test_name}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * (len(test_name) + 3)}{Colors.END}")


def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_info(message: str):
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")


def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


async def test_enhanced_assistant_capabilities():
    """Test sophisticated recruiting queries with the enhanced assistant."""
    print_test_header("Enhanced Assistant Recruiting Capabilities")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test sophisticated recruiting queries
        test_queries = [
            {
                "query": "Find senior Python developers with ML experience in the Bay Area",
                "expected_skills": ["python", "machine learning", "ai"],
                "expected_analysis": "recruiting_insights",
            },
            {
                "query": "I need junior developers with 2-3 years experience in React and Node.js",
                "expected_skills": ["react", "node", "javascript"],
                "expected_analysis": "experience_level",
            },
            {
                "query": "Show me full-stack engineers with AWS experience, remote work preferred",
                "expected_skills": ["aws", "full stack"],
                "expected_analysis": "remote_preference",
            },
            {
                "query": "Looking for H1B visa holders with Python and data science skills",
                "expected_skills": ["python", "data science"],
                "expected_analysis": "visa_status",
            },
        ]

        for i, test_case in enumerate(test_queries, 1):
            print_info(f"Test {i}: {test_case['query']}")

            try:
                # Send bulletproof chat request
                response = await client.post(
                    f"{BASE_URL}/chat/bulletproof",
                    json={"message": test_case["query"]},
                    headers={
                        "Content-Type": "application/json",
                        "X-Session-ID": TEST_SESSION_ID,
                    },
                )

                if response.status_code == 200:
                    data = response.json()

                    # Validate response structure
                    assert "ai_message" in data, "Missing ai_message in response"
                    assert "candidates" in data, "Missing candidates in response"
                    assert "source" in data, "Missing source in response"
                    assert "response_time" in data, "Missing response_time in response"

                    print_success(f"Query {i} completed successfully")
                    print_info(
                        f"Source: {data['source']}, Response time: {data['response_time']:.2f}s"
                    )
                    print_info(f"Found {len(data['candidates'])} candidates")

                    # Check for enhanced features if assistant was used
                    if data["source"] == "assistant":
                        print_info("Enhanced assistant features detected!")
                        if "recruiting_insights" in data.get("ai_message", "").lower():
                            print_success("✨ Recruiting insights provided")
                        if any(
                            skill.lower() in data.get("ai_message", "").lower()
                            for skill in test_case["expected_skills"]
                        ):
                            print_success("✨ Skill analysis detected")

                    # Brief pause between requests
                    await asyncio.sleep(1)

                else:
                    print_error(f"Query {i} failed with status {response.status_code}")
                    print_error(f"Response: {response.text}")

            except Exception as e:
                print_error(f"Query {i} failed with exception: {e}")


async def test_performance_metrics():
    """Test the enhanced performance metrics endpoint."""
    print_test_header("Performance Metrics Validation")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/chat/metrics")

            if response.status_code == 200:
                metrics = response.json()

                print_success("Performance metrics retrieved successfully!")

                # Validate metrics structure
                expected_keys = [
                    "total_requests",
                    "assistant_attempts",
                    "assistant_successes",
                    "fallback_activations",
                    "circuit_breaker_status",
                    "cache_stats",
                    "avg_response_time",
                ]

                for key in expected_keys:
                    if key in metrics:
                        print_success(f"✓ {key}: {metrics[key]}")
                    else:
                        print_warning(f"Missing metric: {key}")

                # Check cache stats specifically
                cache_stats = metrics.get("cache_stats", {})
                if cache_stats:
                    print_info("📊 Cache Performance:")
                    print_info(
                        f"   Hit Rate: {cache_stats.get('hit_rate', 0)*100:.1f}%"
                    )
                    print_info(f"   Total Hits: {cache_stats.get('hits', 0)}")
                    print_info(f"   Total Misses: {cache_stats.get('misses', 0)}")
                    print_info(
                        f"   Cache Size: {cache_stats.get('current_size', 0)} entries"
                    )

            else:
                print_error(
                    f"Metrics request failed with status {response.status_code}"
                )

        except Exception as e:
            print_error(f"Metrics test failed: {e}")


async def test_cache_effectiveness():
    """Test cache effectiveness with repeated queries."""
    print_test_header("Cache Effectiveness Testing")

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Test query that should be cached
        test_query = "Find Python developers with FastAPI experience"

        print_info(f"Testing cache with query: '{test_query}'")

        # First request (should miss cache)
        print_info("Making first request (cache miss expected)...")
        start_time = time.time()
        response1 = await client.post(
            f"{BASE_URL}/chat/bulletproof",
            json={"message": test_query},
            headers={
                "Content-Type": "application/json",
                "X-Session-ID": TEST_SESSION_ID,
            },
        )
        first_time = time.time() - start_time

        if response1.status_code == 200:
            data1 = response1.json()
            print_success(f"First request completed in {first_time:.2f}s")
            print_info(f"Source: {data1['source']}")

            # Brief pause
            await asyncio.sleep(1)

            # Second request (should hit cache if available)
            print_info("Making second request (cache hit expected)...")
            start_time = time.time()
            response2 = await client.post(
                f"{BASE_URL}/chat/bulletproof",
                json={"message": test_query},
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": TEST_SESSION_ID,
                },
            )
            second_time = time.time() - start_time

            if response2.status_code == 200:
                data2 = response2.json()
                print_success(f"Second request completed in {second_time:.2f}s")
                print_info(f"Source: {data2['source']}")

                # Analyze cache effectiveness
                if second_time < first_time * 0.8:  # At least 20% faster
                    print_success("🚀 Cache appears to be working effectively!")
                    speedup = ((first_time - second_time) / first_time) * 100
                    print_info(f"   Speedup: {speedup:.1f}% faster")
                else:
                    print_warning("Cache may not be providing significant speedup")

                # Check if responses are consistent
                if (
                    data1.get("candidates", []) == data2.get("candidates", [])
                    and len(data1.get("candidates", [])) > 0
                ):
                    print_success("✅ Response consistency maintained")
                else:
                    print_warning("Response consistency may be compromised")
            else:
                print_error(f"Second request failed: {response2.status_code}")
        else:
            print_error(f"First request failed: {response1.status_code}")


async def test_circuit_breaker_resilience():
    """Test circuit breaker behavior under controlled conditions."""
    print_test_header("Circuit Breaker Resilience Testing")

    async with httpx.AsyncClient(timeout=5.0) as client:
        print_info("Testing circuit breaker behavior...")

        # Check initial circuit breaker status
        try:
            metrics_response = await client.get(f"{BASE_URL}/chat/metrics")
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                cb_status = metrics.get("circuit_breaker_status", {})
                print_info(f"Initial circuit breaker status: {cb_status}")

                failures = cb_status.get("failures", 0)
                is_open = cb_status.get("is_open", False)

                if is_open:
                    print_warning("Circuit breaker is currently open!")
                else:
                    print_success("Circuit breaker is closed and ready")

                print_info(f"Current failure count: {failures}")

            else:
                print_warning("Could not retrieve circuit breaker status")

        except Exception as e:
            print_error(f"Circuit breaker test failed: {e}")


async def main():
    """Run all Phase 3 enhancement tests."""
    print(f"{Colors.PURPLE}{Colors.BOLD}")
    print("🚀 RecruiterRadar Phase 3 Enhancement Testing")
    print("=" * 50)
    print("Testing sophisticated recruiting features and performance improvements")
    print(f"{Colors.END}")

    # Run all tests
    await test_enhanced_assistant_capabilities()
    await test_performance_metrics()
    await test_cache_effectiveness()
    await test_circuit_breaker_resilience()

    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Phase 3 Testing Complete!{Colors.END}")
    print(
        f"{Colors.CYAN}Check the results above for any issues that need attention.{Colors.END}"
    )


if __name__ == "__main__":
    asyncio.run(main())
