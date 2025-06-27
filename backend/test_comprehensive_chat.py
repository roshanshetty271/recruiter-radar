#!/usr/bin/env python3
"""
🚀 COMPREHENSIVE RecruiterRadar Chat API Test Suite

Tests all edge cases and user prompt scenarios to ensure:
1. Intent detection works correctly (conversation vs search)
2. Conversational queries get helpful responses without triggering search
3. Search queries properly trigger semantic search
4. Edge cases are handled gracefully
5. Performance is acceptable across all scenarios

Run this after implementing the intent detection fix.
"""

import requests
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class TestCase:
    """Test case for a specific query type"""

    query: str
    expected_intent: str  # "conversation" or "search"
    description: str
    expected_candidates: str  # "none", "some", "any"
    should_be_fast: bool = True  # Should complete in < 5 seconds


class ComprehensiveChatTester:
    """Comprehensive test suite for chat API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def test_all_scenarios(self):
        """Run all test scenarios"""
        print("🚀 COMPREHENSIVE RECRUITERRADAR CHAT API TEST SUITE")
        print("=" * 70)
        print(
            "Testing intent detection, conversational handling, and search functionality\n"
        )

        # Define comprehensive test cases
        test_categories = {
            "🤖 CONVERSATIONAL QUERIES (Should NOT trigger search)": [
                TestCase("explain", "conversation", "Basic help request", "none"),
                TestCase(
                    "what can you do", "conversation", "Capability inquiry", "none"
                ),
                TestCase("help", "conversation", "Help request", "none"),
                TestCase("hello", "conversation", "Greeting", "none"),
                TestCase("hi there", "conversation", "Casual greeting", "none"),
                TestCase("thanks", "conversation", "Gratitude", "none"),
                TestCase("thank you", "conversation", "Polite thanks", "none"),
                TestCase(
                    "how does this work", "conversation", "System question", "none"
                ),
                TestCase(
                    "what features do you have",
                    "conversation",
                    "Feature inquiry",
                    "none",
                ),
                TestCase("can you help me", "conversation", "General help", "none"),
                TestCase("tell me more", "conversation", "Vague request", "none"),
                TestCase(
                    "I need assistance", "conversation", "Assistance request", "none"
                ),
                TestCase("what is this", "conversation", "System inquiry", "none"),
                TestCase("how do I use this", "conversation", "Usage question", "none"),
                TestCase("goodbye", "conversation", "Farewell", "none"),
                TestCase("that's great", "conversation", "Positive feedback", "none"),
                TestCase("amazing", "conversation", "Single word praise", "none"),
                TestCase("cool", "conversation", "Casual positive", "none"),
                TestCase("hmm", "conversation", "Thinking sound", "none"),
                TestCase("okay", "conversation", "Acknowledgment", "none"),
            ],
            "🔍 CLEAR SEARCH QUERIES (Should trigger search)": [
                TestCase("Python developers", "search", "Basic skill search", "some"),
                TestCase("React engineers", "search", "Frontend skill search", "any"),
                TestCase(
                    "JavaScript developers", "search", "Popular skill search", "any"
                ),
                TestCase(
                    "machine learning engineers", "search", "ML skill search", "any"
                ),
                TestCase("data scientists", "search", "Data science search", "any"),
                TestCase(
                    "software engineers", "search", "General engineering search", "some"
                ),
                TestCase("full stack developers", "search", "Full stack search", "any"),
                TestCase("backend developers", "search", "Backend search", "any"),
                TestCase("frontend engineers", "search", "Frontend search", "any"),
                TestCase("DevOps engineers", "search", "DevOps search", "any"),
            ],
            "👨‍💼 EXPERIENCE-BASED SEARCHES": [
                TestCase(
                    "senior developers", "search", "Experience level search", "some"
                ),
                TestCase("junior engineers", "search", "Junior level search", "any"),
                TestCase(
                    "5+ years experience", "search", "Years experience search", "any"
                ),
                TestCase(
                    "experienced developers", "search", "Experience search", "some"
                ),
                TestCase("lead engineers", "search", "Leadership role search", "any"),
                TestCase("principal engineers", "search", "Senior role search", "any"),
                TestCase("staff engineers", "search", "Staff level search", "any"),
                TestCase(
                    "entry level developers", "search", "Entry level search", "any"
                ),
            ],
            "📍 LOCATION-BASED SEARCHES": [
                TestCase(
                    "developers in San Francisco",
                    "search",
                    "City location search",
                    "any",
                ),
                TestCase(
                    "engineers in NYC", "search", "City abbreviation search", "any"
                ),
                TestCase("remote developers", "search", "Remote work search", "any"),
                TestCase("California engineers", "search", "State search", "any"),
                TestCase("Seattle developers", "search", "City search", "any"),
                TestCase(
                    "New York engineers", "search", "Full city name search", "any"
                ),
            ],
            "🔎 SPECIFIC CANDIDATE SEARCHES": [
                TestCase("Alex Chen", "search", "Name search", "any"),
                TestCase(
                    "skills of Sarah Johnson",
                    "search",
                    "Specific candidate skills",
                    "any",
                ),
                TestCase(
                    "show me John Smith", "search", "Show specific candidate", "any"
                ),
                TestCase(
                    "find Maria Rodriguez", "search", "Find specific person", "any"
                ),
                TestCase(
                    "tell me about David Wilson", "search", "Candidate details", "any"
                ),
            ],
            "🎯 COMPLEX SEARCH QUERIES": [
                TestCase(
                    "Python developers with 5+ years",
                    "search",
                    "Skill + experience",
                    "any",
                ),
                TestCase(
                    "senior React engineers in SF",
                    "search",
                    "Multi-criteria search",
                    "any",
                ),
                TestCase(
                    "full stack developers with AWS", "search", "Multiple skills", "any"
                ),
                TestCase(
                    "machine learning engineers with Python",
                    "search",
                    "Domain + skill",
                    "any",
                ),
                TestCase(
                    "find senior backend developers",
                    "search",
                    "Find + level + domain",
                    "any",
                ),
                TestCase(
                    "show me JavaScript developers in remote",
                    "search",
                    "Complex command",
                    "any",
                ),
            ],
            "⚡ EDGE CASES & AMBIGUOUS QUERIES": [
                TestCase("developers", "search", "Single word - should search", "some"),
                TestCase("engineers", "search", "Single word - should search", "some"),
                TestCase("python", "search", "Technology name only", "any"),
                TestCase("react", "search", "Framework name only", "any"),
                TestCase("senior", "search", "Level only", "any"),
                TestCase("remote", "search", "Location only", "any"),
                TestCase("find", "conversation", "Command without object", "none"),
                TestCase("show me", "conversation", "Incomplete command", "none"),
                TestCase("I want", "conversation", "Incomplete desire", "none"),
                TestCase("can you find", "conversation", "Incomplete request", "none"),
                TestCase("looking for", "conversation", "Incomplete search", "none"),
                TestCase("", "conversation", "Empty query", "none"),
                TestCase("   ", "conversation", "Whitespace only", "none"),
                TestCase("?", "conversation", "Question mark only", "none"),
                TestCase("???", "conversation", "Multiple question marks", "none"),
                TestCase("adsfjkladsf", "conversation", "Random text", "none"),
                TestCase("123456", "conversation", "Numbers only", "none"),
                TestCase("!!!", "conversation", "Punctuation only", "none"),
            ],
            "🌟 FOLLOW-UP & CONTEXTUAL QUERIES": [
                TestCase(
                    "tell me more about them", "conversation", "Vague follow-up", "none"
                ),
                TestCase(
                    "what about their skills",
                    "conversation",
                    "Skills follow-up",
                    "none",
                ),
                TestCase(
                    "how experienced are they",
                    "conversation",
                    "Experience follow-up",
                    "none",
                ),
                TestCase(
                    "where are they located",
                    "conversation",
                    "Location follow-up",
                    "none",
                ),
                TestCase(
                    "show me more", "conversation", "More results request", "none"
                ),
                TestCase("any others", "conversation", "Additional results", "none"),
                TestCase("what else", "conversation", "Vague continuation", "none"),
            ],
            "🎭 CONVERSATIONAL VARIATIONS": [
                TestCase(
                    "Could you explain this to me?",
                    "conversation",
                    "Polite explanation request",
                    "none",
                ),
                TestCase(
                    "I'm not sure what to do",
                    "conversation",
                    "Uncertainty expression",
                    "none",
                ),
                TestCase(
                    "This is confusing", "conversation", "Confusion statement", "none"
                ),
                TestCase(
                    "I don't understand",
                    "conversation",
                    "Lack of understanding",
                    "none",
                ),
                TestCase(
                    "What should I search for?",
                    "conversation",
                    "Search guidance request",
                    "none",
                ),
                TestCase(
                    "How do I find candidates?",
                    "conversation",
                    "Process question",
                    "none",
                ),
                TestCase(
                    "What kind of searches can I do?",
                    "conversation",
                    "Capability question",
                    "none",
                ),
                TestCase(
                    "Give me some examples", "conversation", "Example request", "none"
                ),
            ],
        }

        # Run all test categories
        for category_name, test_cases in test_categories.items():
            print(f"\n{category_name}")
            print("-" * 50)

            for test_case in test_cases:
                self.run_single_test(test_case)

        # Print comprehensive summary
        self.print_final_summary()

    def run_single_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run a single test case"""
        self.total_tests += 1

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/chat/bulletproof",
                json={"message": test_case.query},
                headers={
                    "X-Session-ID": f"test_session_{self.total_tests}",
                    "Content-Type": "application/json",
                },
                timeout=60,  # Longer timeout for comprehensive testing
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                candidates_count = len(data.get("candidates", []))
                ai_message = data.get("ai_message", "")
                source = data.get("source", "unknown")

                # Analyze results
                success, analysis = self.analyze_test_result(
                    test_case, data, response_time
                )

                if success:
                    self.passed_tests += 1
                    status_icon = "✅"
                else:
                    self.failed_tests += 1
                    status_icon = "❌"

                # Print result
                print(
                    f"{status_icon} {test_case.query[:30]:<30} | {response_time:.2f}s | {candidates_count:2} candidates | {source:<12} | {analysis}"
                )

                result = {
                    "query": test_case.query,
                    "expected_intent": test_case.expected_intent,
                    "candidates_count": candidates_count,
                    "response_time": response_time,
                    "source": source,
                    "success": success,
                    "analysis": analysis,
                    "ai_message": (
                        ai_message[:100] + "..."
                        if len(ai_message) > 100
                        else ai_message
                    ),
                }

            else:
                self.failed_tests += 1
                analysis = f"HTTP {response.status_code}"
                print(f"❌ {test_case.query[:30]:<30} | ERROR   | {analysis}")

                result = {
                    "query": test_case.query,
                    "expected_intent": test_case.expected_intent,
                    "success": False,
                    "analysis": analysis,
                    "error": response.text,
                }

        except Exception as e:
            self.failed_tests += 1
            analysis = f"Exception: {str(e)[:50]}"
            print(f"❌ {test_case.query[:30]:<30} | ERROR   | {analysis}")

            result = {
                "query": test_case.query,
                "expected_intent": test_case.expected_intent,
                "success": False,
                "analysis": analysis,
                "error": str(e),
            }

        self.results.append(result)
        return result

    def analyze_test_result(
        self, test_case: TestCase, response_data: Dict, response_time: float
    ) -> tuple[bool, str]:
        """Analyze if the test result matches expectations"""
        candidates_count = len(response_data.get("candidates", []))
        source = response_data.get("source", "unknown")
        ai_message = response_data.get("ai_message", "")

        issues = []

        # Check candidate expectations
        if test_case.expected_candidates == "none" and candidates_count > 0:
            issues.append(f"Expected no candidates, got {candidates_count}")
        elif test_case.expected_candidates == "some" and candidates_count == 0:
            issues.append("Expected some candidates, got none")

        # Check response time for fast queries
        if test_case.should_be_fast and response_time > 15:
            issues.append(f"Too slow: {response_time:.2f}s")

        # Check for conversational intent (should not trigger search)
        if test_case.expected_intent == "conversation":
            if candidates_count > 0:
                issues.append("Conversational query triggered search")
            if source in ["real_rag", "semantic_search"] and candidates_count > 0:
                issues.append("Wrong source for conversation")

        # Check for search intent (should trigger search for specific queries)
        if test_case.expected_intent == "search":
            if "find" in test_case.query.lower() or "show" in test_case.query.lower():
                if candidates_count == 0 and "no candidates" not in ai_message.lower():
                    issues.append("Search query found nothing unexpectedly")

        # Check AI message quality
        if not ai_message or len(ai_message.strip()) < 10:
            issues.append("AI message too short or empty")

        success = len(issues) == 0
        analysis = "PASS" if success else "; ".join(issues)

        return success, analysis

    def print_final_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 70)
        print("🎯 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)

        print(f"📊 Overall Results:")
        print(f"   Total Tests: {self.total_tests}")
        print(f"   ✅ Passed: {self.passed_tests}")
        print(f"   ❌ Failed: {self.failed_tests}")
        print(f"   🎯 Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")

        # Analyze by intent type
        conversation_tests = [
            r for r in self.results if r.get("expected_intent") == "conversation"
        ]
        search_tests = [r for r in self.results if r.get("expected_intent") == "search"]

        conv_passed = len([r for r in conversation_tests if r.get("success")])
        search_passed = len([r for r in search_tests if r.get("success")])

        print(f"\n🤖 Conversational Intent Tests:")
        print(
            f"   Passed: {conv_passed}/{len(conversation_tests)} ({(conv_passed/len(conversation_tests))*100:.1f}%)"
        )

        print(f"\n🔍 Search Intent Tests:")
        print(
            f"   Passed: {search_passed}/{len(search_tests)} ({(search_passed/len(search_tests))*100:.1f}%)"
        )

        # Performance analysis
        response_times = [
            r.get("response_time", 0) for r in self.results if r.get("response_time")
        ]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            print(f"\n⚡ Performance Analysis:")
            print(f"   Average Response Time: {avg_time:.2f}s")
            print(f"   Fastest Response: {min_time:.2f}s")
            print(f"   Slowest Response: {max_time:.2f}s")

        # Failed tests analysis
        failed_results = [r for r in self.results if not r.get("success")]
        if failed_results:
            print(f"\n❌ Failed Tests Analysis:")
            for result in failed_results[:10]:  # Show first 10 failures
                print(
                    f"   '{result['query'][:40]}' - {result.get('analysis', 'Unknown error')}"
                )

            if len(failed_results) > 10:
                print(f"   ... and {len(failed_results) - 10} more failures")

        # Success criteria
        print(f"\n🏆 SUCCESS CRITERIA:")
        success_rate = (self.passed_tests / self.total_tests) * 100

        if success_rate >= 90:
            print(
                "   🎉 EXCELLENT: >90% success rate - Intent detection working perfectly!"
            )
        elif success_rate >= 80:
            print("   👍 GOOD: >80% success rate - Most cases working well")
        elif success_rate >= 70:
            print("   ⚠️  FAIR: >70% success rate - Needs some improvements")
        else:
            print("   🚨 POOR: <70% success rate - Significant issues need fixing")

        print("\n" + "=" * 70)
        print("🚀 Test Complete! Check results above for detailed analysis.")
        print("=" * 70)


def main():
    """Run the comprehensive test suite"""
    tester = ComprehensiveChatTester()
    tester.test_all_scenarios()


if __name__ == "__main__":
    main()
