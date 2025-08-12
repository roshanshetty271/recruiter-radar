"""
FULL PIPELINE SEARCH TEST SUITE - End-to-End Testing
Tests complete search pipeline: Router → Fast Path → RAG Service → ChromaDB → Results
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os


class FullPipelineSearchTest:
    """End-to-end search pipeline testing with real API calls"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.stats = {
            "total_tests": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "success_rate": 0.0,
            "fast_path_used": 0,
            "intelligent_path_used": 0,
            "fast_path_percentage": 0.0,
            "intelligent_path_percentage": 0.0,
            "avg_response_time": 0.0,
            "avg_search_time": 0.0,
            "avg_candidates_returned": 0.0,
            "zero_results": 0,
            "zero_results_percentage": 0.0,
            "performance_target_met": 0,  # Under 3 seconds
            "performance_target_percentage": 0.0,
        }

    def get_comprehensive_test_queries(self) -> List[Dict[str, Any]]:
        """Generate comprehensive test queries for full pipeline testing"""

        test_queries = []

        # ===== FAST PATH VALIDATION QUERIES (40 tests) =====
        fast_path_tests = [
            # Single skills - should use fast path
            {
                "query": "Java developers",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "single_skill",
            },
            {
                "query": "Python engineers",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "single_skill",
            },
            {
                "query": "JavaScript developer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "single_skill",
            },
            {
                "query": "React developer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "single_skill",
            },
            {
                "query": "Node.js engineer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "single_skill",
            },
            {
                "query": "Angular developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "single_skill",
            },
            {
                "query": "Vue developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "single_skill",
            },
            {
                "query": "Django developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "single_skill",
            },
            {
                "query": "Flask developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "single_skill",
            },
            {
                "query": "Spring Boot developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "single_skill",
            },
            # Skills with experience - should use fast path + extract experience
            {
                "query": "Java developer with 5+ years",
                "expected_path": "fast",
                "min_candidates": 2,
                "expected_min_experience": 5,
                "category": "skill_experience",
            },
            {
                "query": "Python engineer over 3 years",
                "expected_path": "fast",
                "min_candidates": 2,
                "expected_min_experience": 3,
                "category": "skill_experience",
            },
            {
                "query": "Senior JavaScript developer",
                "expected_path": "fast",
                "min_candidates": 2,
                "expected_min_experience": 5,
                "category": "skill_experience",
            },
            {
                "query": "Junior React developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_min_experience": 1,
                "category": "skill_experience",
            },
            {
                "query": "React developer with 4 years",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_min_experience": 4,
                "category": "skill_experience",
            },
            # Skills with location - should use fast path + extract location
            {
                "query": "Java developer in California",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_location": "California",
                "category": "skill_location",
            },
            {
                "query": "Python engineer in CA",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_location": "CA",
                "category": "skill_location",
            },
            {
                "query": "JavaScript developer in New York",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_location": "New York",
                "category": "skill_location",
            },
            {
                "query": "React developer in San Francisco",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_location": "San Francisco",
                "category": "skill_location",
            },
            {
                "query": "Remote Java developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_location": "Remote",
                "category": "skill_location",
            },
            # Complex but should still use fast path
            {
                "query": "Senior Java developer in California",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_min_experience": 5,
                "expected_location": "California",
                "category": "complex_fast",
            },
            {
                "query": "Python engineer with 5+ years remote",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_min_experience": 5,
                "expected_location": "Remote",
                "category": "complex_fast",
            },
            {
                "query": "React developer over 3 years in San Francisco",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_min_experience": 3,
                "expected_location": "San Francisco",
                "category": "complex_fast",
            },
            # Case variations - should use fast path
            {
                "query": "JAVA DEVELOPER",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "case_variation",
            },
            {
                "query": "python engineer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "case_variation",
            },
            {
                "query": "Javascript Developer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "case_variation",
            },
            # Alternative names - should use fast path
            {
                "query": "JS developer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "alternative_name",
            },
            {
                "query": "ReactJS engineer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "alternative_name",
            },
            {
                "query": "NodeJS developer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "alternative_name",
            },
            {
                "query": "Golang developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "alternative_name",
            },
            # Database skills
            {
                "query": "PostgreSQL developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "database",
            },
            {
                "query": "MongoDB engineer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "database",
            },
            {
                "query": "MySQL developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "database",
            },
            {
                "query": "Redis developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "database",
            },
            # Cloud/DevOps skills
            {
                "query": "AWS developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "cloud",
            },
            {
                "query": "Docker engineer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "cloud",
            },
            {
                "query": "Kubernetes developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "cloud",
            },
            {
                "query": "DevOps engineer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "role",
            },
            # Role-based searches
            {
                "query": "Frontend developer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "role",
            },
            {
                "query": "Backend engineer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "role",
            },
            {
                "query": "Full stack developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "role",
            },
        ]
        test_queries.extend(fast_path_tests)

        # ===== INTELLIGENT PATH QUERIES (20 tests) =====
        intelligent_path_tests = [
            # Complex natural language - should use intelligent path
            {
                "query": "I need a talented software engineer who knows machine learning",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "natural_language",
            },
            {
                "query": "Looking for someone who can build scalable web applications",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "natural_language",
            },
            {
                "query": "Find me a developer experienced in building APIs and microservices",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "natural_language",
            },
            {
                "query": "Need a programmer who understands data structures and algorithms",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "natural_language",
            },
            {
                "query": "Looking for talent in artificial intelligence and deep learning",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "natural_language",
            },
            # Multiple skill combinations - should use intelligent path
            {
                "query": "React and Node.js developer with GraphQL experience",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "multi_skill",
            },
            {
                "query": "Python developer with machine learning and data science skills",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "multi_skill",
            },
            {
                "query": "Full stack engineer proficient in React, Node.js, and PostgreSQL",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "multi_skill",
            },
            {
                "query": "Java developer with Spring Boot, Kafka, and AWS experience",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "multi_skill",
            },
            {
                "query": "DevOps engineer skilled in Docker, Kubernetes, and Terraform",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "multi_skill",
            },
            # Complex requirements - should use intelligent path
            {
                "query": "Senior architect with microservices and cloud native experience",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "complex_requirements",
            },
            {
                "query": "Tech lead who can mentor junior developers and design systems",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "complex_requirements",
            },
            {
                "query": "Principal engineer with expertise in distributed systems",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "complex_requirements",
            },
            {
                "query": "CTO level candidate with startup and scaling experience",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "complex_requirements",
            },  # May have 0 results
            # Domain-specific queries - should use intelligent path
            {
                "query": "Fintech developer with payment processing experience",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "domain_specific",
            },
            {
                "query": "Healthcare software engineer familiar with HIPAA compliance",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "domain_specific",
            },
            {
                "query": "Gaming developer with Unity and C# experience",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "domain_specific",
            },
            {
                "query": "Blockchain developer with Solidity and smart contracts",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "domain_specific",
            },
            # Vague/ambiguous queries - should use intelligent path
            {
                "query": "Good programmer",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "vague",
            },
            {
                "query": "Talented developer",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "vague",
            },
        ]
        test_queries.extend(intelligent_path_tests)

        # ===== EDGE CASES & ERROR HANDLING (15 tests) =====
        edge_case_tests = [
            # Empty/minimal queries
            {"query": "", "expected_error": True, "category": "edge_case"},
            {"query": "   ", "expected_error": True, "category": "edge_case"},
            {
                "query": "a",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "edge_case",
            },
            # Special characters
            {
                "query": "C++ developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "special_chars",
            },
            {
                "query": "C# engineer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "special_chars",
            },
            {
                "query": ".NET developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "special_chars",
            },
            {
                "query": "Node.js developer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "special_chars",
            },
            {
                "query": "React.js engineer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "special_chars",
            },
            # Numbers and years
            {
                "query": "Java developer 5 years",
                "expected_path": "fast",
                "min_candidates": 1,
                "expected_min_experience": 5,
                "category": "numbers",
            },
            {
                "query": "Python 3.9 developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "numbers",
            },
            {
                "query": "Angular 15 developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "numbers",
            },
            # Very long queries
            {
                "query": "I am looking for a very experienced senior software engineer who has worked with Java Spring Boot microservices architecture and has extensive experience in building scalable distributed systems",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "long_query",
            },
            # Non-English characters (if any)
            {
                "query": "développeur Python",
                "expected_path": "intelligent",
                "min_candidates": 0,
                "category": "non_english",
            },
            # Typos
            {
                "query": "Javva developer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "typo",
            },  # Should still match Java
            {
                "query": "Pyhton engineer",
                "expected_path": "fast",
                "min_candidates": 1,
                "category": "typo",
            },  # Should still match Python
        ]
        test_queries.extend(edge_case_tests)

        # ===== PERFORMANCE STRESS TESTS (10 tests) =====
        stress_tests = [
            # High-volume skill searches
            {
                "query": "JavaScript developer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "stress",
                "expected_max_time": 2000,
            },
            {
                "query": "Python engineer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "stress",
                "expected_max_time": 2000,
            },
            {
                "query": "Java developer",
                "expected_path": "fast",
                "min_candidates": 3,
                "category": "stress",
                "expected_max_time": 2000,
            },
            {
                "query": "React developer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "stress",
                "expected_max_time": 2000,
            },
            {
                "query": "Node.js engineer",
                "expected_path": "fast",
                "min_candidates": 2,
                "category": "stress",
                "expected_max_time": 2000,
            },
            # Complex queries with time limits
            {
                "query": "Senior full stack developer with React Node.js and AWS",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "stress",
                "expected_max_time": 5000,
            },
            {
                "query": "Machine learning engineer with Python TensorFlow and PyTorch",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "stress",
                "expected_max_time": 5000,
            },
            {
                "query": "DevOps engineer with Kubernetes Docker and Terraform experience",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "stress",
                "expected_max_time": 5000,
            },
            {
                "query": "Data scientist with Python machine learning and data visualization",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "stress",
                "expected_max_time": 5000,
            },
            {
                "query": "Cloud architect with AWS microservices and serverless experience",
                "expected_path": "intelligent",
                "min_candidates": 1,
                "category": "stress",
                "expected_max_time": 5000,
            },
        ]
        test_queries.extend(stress_tests)

        return test_queries

    async def run_single_search_test(
        self, session: aiohttp.ClientSession, test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single search test against the real API"""

        query = test_case["query"]
        start_time = time.time()

        try:
            # Handle empty query edge case
            if test_case.get("expected_error", False):
                try:
                    async with session.get(
                        f"{self.base_url}/api/v1/candidates/query",
                        params={"q": query, "page": 1, "page_size": 20},
                    ) as response:
                        response_time = (time.time() - start_time) * 1000

                        if response.status >= 400:
                            return {
                                "query": query,
                                "category": test_case["category"],
                                "success": True,  # Expected error
                                "expected_error": True,
                                "actual_error": True,
                                "status_code": response.status,
                                "response_time_ms": round(response_time, 2),
                            }
                        else:
                            return {
                                "query": query,
                                "category": test_case["category"],
                                "success": False,  # Should have errored but didn't
                                "expected_error": True,
                                "actual_error": False,
                                "status_code": response.status,
                                "response_time_ms": round(response_time, 2),
                            }
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "query": query,
                        "category": test_case["category"],
                        "success": True,  # Expected error
                        "expected_error": True,
                        "actual_error": True,
                        "error_message": str(e),
                        "response_time_ms": round(response_time, 2),
                    }

            # Normal search test
            async with session.get(
                f"{self.base_url}/api/v1/candidates/query",
                params={"q": query, "page": 1, "page_size": 20},
            ) as response:
                response_time = (time.time() - start_time) * 1000

                if response.status != 200:
                    return {
                        "query": query,
                        "category": test_case["category"],
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "response_time_ms": round(response_time, 2),
                    }

                data = await response.json()

                # Extract key information from response
                total_results = data.get("total_results", 0)
                search_time_ms = data.get("search_time_ms", 0)
                results = data.get("results", [])
                search_metadata = data.get("search_metadata", {})

                # Determine if fast path was used
                query_interpretation = data.get("query_interpretation", "")
                path_used = (
                    "fast"
                    if "fast path" in query_interpretation.lower()
                    else "intelligent"
                )

                # Validate expectations
                result = {
                    "query": query,
                    "category": test_case["category"],
                    "success": True,
                    "response_time_ms": round(response_time, 2),
                    "search_time_ms": search_time_ms,
                    "total_results": total_results,
                    "candidates_returned": len(results),
                    "path_used": path_used,
                    "query_interpretation": query_interpretation,
                    "search_metadata": search_metadata,
                }

                # Check expectations
                expectations_met = []
                expectations_failed = []

                # Path expectation
                expected_path = test_case.get("expected_path")
                if expected_path:
                    if path_used == expected_path:
                        expectations_met.append(f"path_{expected_path}")
                    else:
                        expectations_failed.append(
                            f"expected_{expected_path}_got_{path_used}"
                        )

                # Minimum candidates expectation
                min_candidates = test_case.get("min_candidates", 0)
                if total_results >= min_candidates:
                    expectations_met.append(f"min_candidates_{min_candidates}")
                else:
                    expectations_failed.append(
                        f"expected_min_{min_candidates}_got_{total_results}"
                    )

                # Performance expectation
                max_time = test_case.get("expected_max_time")
                if max_time:
                    if response_time <= max_time:
                        expectations_met.append(f"performance_under_{max_time}ms")
                    else:
                        expectations_failed.append(f"performance_over_{max_time}ms")

                # Experience extraction (for fast path tests)
                expected_min_experience = test_case.get("expected_min_experience")
                if expected_min_experience and results:
                    # Check if any results have the expected experience level
                    found_experience = any(
                        candidate.get("experience_years", 0) >= expected_min_experience
                        for candidate in results
                    )
                    if found_experience:
                        expectations_met.append(
                            f"experience_{expected_min_experience}y"
                        )
                    else:
                        expectations_failed.append(
                            f"no_experience_{expected_min_experience}y"
                        )

                # Location filtering (for location tests)
                expected_location = test_case.get("expected_location")
                if expected_location and results:
                    # Check if results are filtered by location
                    found_location = any(
                        expected_location.lower()
                        in candidate.get("location", "").lower()
                        for candidate in results
                    )
                    if found_location:
                        expectations_met.append(f"location_{expected_location}")
                    else:
                        expectations_failed.append(f"no_location_{expected_location}")

                result.update(
                    {
                        "expectations_met": expectations_met,
                        "expectations_failed": expectations_failed,
                        "all_expectations_met": len(expectations_failed) == 0,
                    }
                )

                # Add sample results for analysis
                if results:
                    result["sample_candidates"] = [
                        {
                            "name": candidate.get("name", "Unknown"),
                            "relevance_score": candidate.get("relevance_score", 0),
                            "experience_years": candidate.get("experience_years", 0),
                            "location": candidate.get("location", "Unknown"),
                            "skills": candidate.get("skills", [])[:5],  # First 5 skills
                        }
                        for candidate in results[:3]  # Top 3 candidates
                    ]

                return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "query": query,
                "category": test_case["category"],
                "success": False,
                "error": str(e),
                "response_time_ms": round(response_time, 2),
            }

    async def run_all_tests(self):
        """Run all pipeline tests"""

        print("🚀 Starting FULL PIPELINE Search Test Suite...")
        print("=" * 80)

        # Check if API is running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/ping") as response:
                    if response.status != 200:
                        print(f"❌ API not running at {self.base_url}")
                        print(
                            "   Please start the backend server first: uvicorn app.main:app --reload"
                        )
                        return
        except Exception as e:
            print(f"❌ Cannot connect to API at {self.base_url}")
            print(f"   Error: {e}")
            print(
                "   Please start the backend server first: uvicorn app.main:app --reload"
            )
            return

        test_queries = self.get_comprehensive_test_queries()
        total_tests = len(test_queries)

        print(f"📊 Total test cases: {total_tests}")
        print(f"🎯 Testing: Fast Path, Intelligent Path, Edge Cases, Performance")
        print(f"🌐 API Base URL: {self.base_url}")
        print()

        # Run tests in smaller batches for real API calls
        batch_size = 5  # Smaller batches for API calls
        successful_tests = 0
        total_response_time = 0
        total_search_time = 0
        total_candidates = 0
        fast_path_count = 0
        intelligent_path_count = 0
        zero_results_count = 0
        performance_target_met = 0

        async with aiohttp.ClientSession() as session:
            for i in range(0, total_tests, batch_size):
                batch = test_queries[i : i + batch_size]
                batch_results = []

                print(
                    f"🔄 Running batch {i//batch_size + 1}/{(total_tests + batch_size - 1)//batch_size} ({len(batch)} tests)..."
                )

                # Run batch tests concurrently
                tasks = [
                    self.run_single_search_test(session, test_case)
                    for test_case in batch
                ]
                batch_results = await asyncio.gather(*tasks)

                # Collect statistics
                for result in batch_results:
                    self.test_results.append(result)
                    if result["success"]:
                        successful_tests += 1
                        if not result.get("expected_error", False):
                            total_response_time += result["response_time_ms"]
                            search_time = result.get("search_time_ms", 0)
                            total_search_time += search_time
                            candidates = result.get("total_results", 0)
                            total_candidates += candidates

                            # Track path usage
                            if result.get("path_used") == "fast":
                                fast_path_count += 1
                            elif result.get("path_used") == "intelligent":
                                intelligent_path_count += 1

                            # Track zero results
                            if candidates == 0:
                                zero_results_count += 1

                            # Track performance (under 3 seconds)
                            if result["response_time_ms"] < 3000:
                                performance_target_met += 1

                # Show progress
                batch_success_rate = (
                    sum(1 for r in batch_results if r["success"])
                    / len(batch_results)
                    * 100
                )
                print(f"✅ Batch completed: {batch_success_rate:.1f}% success rate")

                # Small delay between batches to avoid overwhelming the API
                await asyncio.sleep(0.5)

        # Calculate final statistics
        non_error_tests = total_tests - sum(
            1 for r in self.test_results if r.get("expected_error", False)
        )

        self.stats.update(
            {
                "total_tests": total_tests,
                "successful_searches": successful_tests,
                "failed_searches": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests) * 100,
                "fast_path_used": fast_path_count,
                "intelligent_path_used": intelligent_path_count,
                "fast_path_percentage": (
                    (fast_path_count / non_error_tests) * 100
                    if non_error_tests > 0
                    else 0
                ),
                "intelligent_path_percentage": (
                    (intelligent_path_count / non_error_tests) * 100
                    if non_error_tests > 0
                    else 0
                ),
                "avg_response_time": (
                    total_response_time / non_error_tests if non_error_tests > 0 else 0
                ),
                "avg_search_time": (
                    total_search_time / non_error_tests if non_error_tests > 0 else 0
                ),
                "avg_candidates_returned": (
                    total_candidates / non_error_tests if non_error_tests > 0 else 0
                ),
                "zero_results": zero_results_count,
                "zero_results_percentage": (
                    (zero_results_count / non_error_tests) * 100
                    if non_error_tests > 0
                    else 0
                ),
                "performance_target_met": performance_target_met,
                "performance_target_percentage": (
                    (performance_target_met / non_error_tests) * 100
                    if non_error_tests > 0
                    else 0
                ),
            }
        )

        print()
        print("🎉 All pipeline tests completed!")
        print("=" * 80)

    def save_results_to_file(self, filename: str = None):
        """Save comprehensive pipeline test results to JSON file"""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pipeline_test_results_{timestamp}.json"

        # Prepare comprehensive results
        output_data = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "full_pipeline_end_to_end",
                "api_base_url": self.base_url,
                "total_test_cases": len(self.test_results),
                "test_categories": list(set(r["category"] for r in self.test_results)),
            },
            "pipeline_statistics": {
                "total_tests": self.stats["total_tests"],
                "successful_searches": self.stats["successful_searches"],
                "failed_searches": self.stats["failed_searches"],
                "success_rate_percent": round(self.stats["success_rate"], 2),
                "fast_path_used": self.stats["fast_path_used"],
                "intelligent_path_used": self.stats["intelligent_path_used"],
                "fast_path_percentage": round(self.stats["fast_path_percentage"], 2),
                "intelligent_path_percentage": round(
                    self.stats["intelligent_path_percentage"], 2
                ),
                "average_response_time_ms": round(self.stats["avg_response_time"], 2),
                "average_search_time_ms": round(self.stats["avg_search_time"], 2),
                "average_candidates_returned": round(
                    self.stats["avg_candidates_returned"], 2
                ),
                "zero_results_count": self.stats["zero_results"],
                "zero_results_percentage": round(
                    self.stats["zero_results_percentage"], 2
                ),
                "performance_target_met": self.stats["performance_target_met"],
                "performance_target_percentage": round(
                    self.stats["performance_target_percentage"], 2
                ),
            },
            "category_breakdown": self._generate_category_breakdown(),
            "path_analysis": self._generate_path_analysis(),
            "performance_analysis": self._generate_performance_analysis(),
            "detailed_results": self.test_results,
            "failed_tests": [r for r in self.test_results if not r["success"]],
            "fast_path_tests": [
                r for r in self.test_results if r.get("path_used") == "fast"
            ],
            "intelligent_path_tests": [
                r for r in self.test_results if r.get("path_used") == "intelligent"
            ],
            "zero_result_tests": [
                r for r in self.test_results if r.get("total_results", 0) == 0
            ],
            "high_performance_tests": [
                r for r in self.test_results if r.get("response_time_ms", 0) < 1000
            ],
            "expectation_failures": [
                r for r in self.test_results if not r.get("all_expectations_met", True)
            ],
        }

        # Save to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"📄 Results saved to: {filename}")
        return filename

    def _generate_category_breakdown(self) -> Dict[str, Any]:
        """Generate breakdown by test category"""
        categories = {}

        for result in self.test_results:
            category = result["category"]
            if category not in categories:
                categories[category] = {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "fast_path_used": 0,
                    "intelligent_path_used": 0,
                    "avg_response_time": 0,
                    "avg_candidates": 0,
                    "success_rate": 0,
                }

            categories[category]["total_tests"] += 1
            if result["success"] and not result.get("expected_error", False):
                categories[category]["successful_tests"] += 1

                if result.get("path_used") == "fast":
                    categories[category]["fast_path_used"] += 1
                elif result.get("path_used") == "intelligent":
                    categories[category]["intelligent_path_used"] += 1

        # Calculate percentages and averages
        for category, stats in categories.items():
            category_results = [
                r
                for r in self.test_results
                if r["category"] == category
                and r["success"]
                and not r.get("expected_error", False)
            ]
            if category_results:
                stats["success_rate"] = (
                    stats["successful_tests"] / stats["total_tests"]
                ) * 100
                stats["avg_response_time"] = sum(
                    r["response_time_ms"] for r in category_results
                ) / len(category_results)
                stats["avg_candidates"] = sum(
                    r.get("total_results", 0) for r in category_results
                ) / len(category_results)

        return categories

    def _generate_path_analysis(self) -> Dict[str, Any]:
        """Generate analysis of fast vs intelligent path usage"""
        fast_path_results = [
            r for r in self.test_results if r.get("path_used") == "fast"
        ]
        intelligent_path_results = [
            r for r in self.test_results if r.get("path_used") == "intelligent"
        ]

        return {
            "fast_path": {
                "total_uses": len(fast_path_results),
                "avg_response_time": (
                    sum(r["response_time_ms"] for r in fast_path_results)
                    / len(fast_path_results)
                    if fast_path_results
                    else 0
                ),
                "avg_candidates": (
                    sum(r.get("total_results", 0) for r in fast_path_results)
                    / len(fast_path_results)
                    if fast_path_results
                    else 0
                ),
                "under_1s": sum(
                    1 for r in fast_path_results if r["response_time_ms"] < 1000
                ),
                "under_2s": sum(
                    1 for r in fast_path_results if r["response_time_ms"] < 2000
                ),
            },
            "intelligent_path": {
                "total_uses": len(intelligent_path_results),
                "avg_response_time": (
                    sum(r["response_time_ms"] for r in intelligent_path_results)
                    / len(intelligent_path_results)
                    if intelligent_path_results
                    else 0
                ),
                "avg_candidates": (
                    sum(r.get("total_results", 0) for r in intelligent_path_results)
                    / len(intelligent_path_results)
                    if intelligent_path_results
                    else 0
                ),
                "under_3s": sum(
                    1 for r in intelligent_path_results if r["response_time_ms"] < 3000
                ),
                "under_5s": sum(
                    1 for r in intelligent_path_results if r["response_time_ms"] < 5000
                ),
            },
        }

    def _generate_performance_analysis(self) -> Dict[str, Any]:
        """Generate performance analysis"""
        response_times = [
            r["response_time_ms"]
            for r in self.test_results
            if r["success"] and not r.get("expected_error", False)
        ]

        if not response_times:
            return {"error": "No successful tests for performance analysis"}

        return {
            "response_time_distribution": {
                "min_ms": min(response_times),
                "max_ms": max(response_times),
                "avg_ms": sum(response_times) / len(response_times),
                "median_ms": sorted(response_times)[len(response_times) // 2],
                "under_1s": sum(1 for t in response_times if t < 1000),
                "1s_to_3s": sum(1 for t in response_times if 1000 <= t < 3000),
                "3s_to_5s": sum(1 for t in response_times if 3000 <= t < 5000),
                "over_5s": sum(1 for t in response_times if t >= 5000),
            },
            "performance_targets": {
                "fast_path_target_1s": sum(
                    1
                    for r in self.test_results
                    if r.get("path_used") == "fast" and r["response_time_ms"] < 1000
                ),
                "intelligent_path_target_3s": sum(
                    1
                    for r in self.test_results
                    if r.get("path_used") == "intelligent"
                    and r["response_time_ms"] < 3000
                ),
                "overall_target_3s": sum(1 for t in response_times if t < 3000),
            },
        }

    def print_summary(self):
        """Print comprehensive summary of pipeline test results"""

        print("\n🎯 FULL PIPELINE TEST RESULTS SUMMARY")
        print("=" * 80)

        # Overall statistics
        print(f"📊 Total Tests: {self.stats['total_tests']}")
        print(
            f"✅ Successful: {self.stats['successful_searches']} ({self.stats['success_rate']:.1f}%)"
        )
        print(f"❌ Failed: {self.stats['failed_searches']}")
        print(f"⏱️  Average Response Time: {self.stats['avg_response_time']:.1f}ms")
        print(f"🔍 Average Candidates: {self.stats['avg_candidates_returned']:.1f}")

        # Path usage
        print(f"\n🚀 PATH USAGE ANALYSIS:")
        print(
            f"  ⚡ Fast Path Used: {self.stats['fast_path_used']} ({self.stats['fast_path_percentage']:.1f}%)"
        )
        print(
            f"  🧠 Intelligent Path Used: {self.stats['intelligent_path_used']} ({self.stats['intelligent_path_percentage']:.1f}%)"
        )

        # Performance analysis
        print(f"\n⚡ PERFORMANCE ANALYSIS:")
        print(
            f"  Under 3 seconds: {self.stats['performance_target_met']} ({self.stats['performance_target_percentage']:.1f}%)"
        )
        print(
            f"  Zero results: {self.stats['zero_results']} ({self.stats['zero_results_percentage']:.1f}%)"
        )

        # Category breakdown
        print(f"\n📋 CATEGORY PERFORMANCE:")
        category_stats = self._generate_category_breakdown()
        for category, stats in category_stats.items():
            print(
                f"  {category.upper():20} | {stats['success_rate']:5.1f}% | {stats['avg_response_time']:6.1f}ms | {stats['avg_candidates']:4.1f} candidates"
            )

        # Path analysis
        path_analysis = self._generate_path_analysis()
        print(f"\n🔄 PATH PERFORMANCE COMPARISON:")
        print(
            f"  Fast Path    | {path_analysis['fast_path']['avg_response_time']:6.1f}ms avg | {path_analysis['fast_path']['avg_candidates']:4.1f} candidates avg"
        )
        print(
            f"  Intelligent  | {path_analysis['intelligent_path']['avg_response_time']:6.1f}ms avg | {path_analysis['intelligent_path']['avg_candidates']:4.1f} candidates avg"
        )

        # Show some examples
        print(f"\n🌟 FASTEST SEARCHES:")
        fast_tests = sorted(
            [
                r
                for r in self.test_results
                if r["success"] and not r.get("expected_error", False)
            ],
            key=lambda x: x["response_time_ms"],
        )[:5]
        for i, test in enumerate(fast_tests, 1):
            path_icon = "⚡" if test.get("path_used") == "fast" else "🧠"
            print(
                f"  {i}. {path_icon} '{test['query']}' → {test.get('total_results', 0)} results ({test['response_time_ms']:.0f}ms)"
            )

        print(f"\n🐌 SLOWEST SEARCHES:")
        slow_tests = sorted(
            [
                r
                for r in self.test_results
                if r["success"] and not r.get("expected_error", False)
            ],
            key=lambda x: x["response_time_ms"],
            reverse=True,
        )[:5]
        for i, test in enumerate(slow_tests, 1):
            path_icon = "⚡" if test.get("path_used") == "fast" else "🧠"
            print(
                f"  {i}. {path_icon} '{test['query']}' → {test.get('total_results', 0)} results ({test['response_time_ms']:.0f}ms)"
            )

        if self.stats["failed_searches"] > 0:
            print(f"\n❌ FAILED SEARCHES:")
            failed_tests = [
                r
                for r in self.test_results
                if not r["success"] and not r.get("expected_error", False)
            ][:5]
            for i, test in enumerate(failed_tests, 1):
                error = test.get("error", "Unknown error")
                print(f"  {i}. '{test['query']}' → {error}")

        # Expectation analysis
        expectation_failures = [
            r
            for r in self.test_results
            if not r.get("all_expectations_met", True) and r["success"]
        ]
        if expectation_failures:
            print(f"\n⚠️  EXPECTATION FAILURES ({len(expectation_failures)} tests):")
            for i, test in enumerate(expectation_failures[:5], 1):
                failures = ", ".join(test.get("expectations_failed", []))
                print(f"  {i}. '{test['query']}' → {failures}")

        print("\n" + "=" * 80)


async def main():
    """Main function to run the full pipeline test suite"""

    # Initialize test suite
    test_suite = FullPipelineSearchTest()

    # Run all tests
    await test_suite.run_all_tests()

    # Print summary
    test_suite.print_summary()

    # Save detailed results to file
    results_file = test_suite.save_results_to_file()

    print(f"\n🎉 Full Pipeline Test Suite Complete!")
    print(f"📊 Summary: {test_suite.stats['success_rate']:.1f}% success rate")
    print(
        f"⚡ Fast Path: {test_suite.stats['fast_path_percentage']:.1f}% | 🧠 Intelligent: {test_suite.stats['intelligent_path_percentage']:.1f}%"
    )
    print(f"⏱️  Performance: {test_suite.stats['avg_response_time']:.1f}ms average")
    print(f"📄 Detailed results: {results_file}")


if __name__ == "__main__":
    # Run the full pipeline test suite
    asyncio.run(main())
