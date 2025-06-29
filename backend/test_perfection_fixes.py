#!/usr/bin/env python3
"""
🎯 PERFECTION FIXES TEST

Focused test for the 3 specific fixes to get from 95.5% to 99%+:
1. "How do I find candidates?" - should go to conversational
2. "show me John Smith" - should provide helpful suggestion
3. Empty query "" - should provide friendly response

These were the last 3 issues preventing 100% success.
"""

import asyncio
import time
import requests
import json
import uuid
from typing import Dict, Any

# Test endpoints
BASE_URL = "http://localhost:8000"
CHAT_URL = f"{BASE_URL}/api/v1/chat/bulletproof"

# The 3 specific test cases that needed fixes
PERFECTION_TEST_CASES = [
    {
        "query": "How do I find candidates?",
        "expected_behavior": "Should be conversational (no candidates found)",
        "expected_source": "real_rag",  # Should go through conversational path
        "expected_candidates": 0,
        "description": "Meta question about system - should be conversational",
    },
    {
        "query": "show me John Smith",
        "expected_behavior": "Should provide helpful suggestion for non-existent candidate",
        "expected_source": "real_rag",
        "expected_candidates": 0,
        "description": "Search for non-existent person - should provide helpful suggestions",
    },
    {
        "query": "find Maria Rodriguez",
        "expected_behavior": "Should provide helpful suggestion for non-existent candidate",
        "expected_source": "real_rag",
        "expected_candidates": 0,
        "description": "Search for non-existent person - should provide helpful suggestions",
    },
    {
        "query": "",
        "expected_behavior": "Should provide friendly empty query response",
        "expected_source": "empty_query_handler",
        "expected_candidates": 0,
        "description": "Empty query - should provide friendly guidance",
    },
]


async def test_perfection_fix(
    test_case: Dict[str, Any], test_number: int
) -> Dict[str, Any]:
    """Test a specific perfection fix."""

    session_id = f"perfection-test-{test_number}-{uuid.uuid4().hex[:8]}"
    query = test_case["query"]

    payload = {"message": query}

    headers = {"X-Session-ID": session_id, "Content-Type": "application/json"}

    start_time = time.time()

    try:
        response = requests.post(CHAT_URL, json=payload, headers=headers, timeout=15)

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            data = response.json()
            candidates_found = len(data.get("candidates", []))
            source = data.get("source", "unknown")
            ai_message = data.get("ai_message", "")

            # Check if the fix worked
            success = (
                candidates_found == test_case["expected_candidates"]
                and source == test_case["expected_source"]
            )

            return {
                "query": query,
                "duration": duration,
                "status": "SUCCESS" if success else "PARTIAL_SUCCESS",
                "candidates_found": candidates_found,
                "source": source,
                "ai_message": (
                    ai_message[:100] + "..." if len(ai_message) > 100 else ai_message
                ),
                "expected_candidates": test_case["expected_candidates"],
                "expected_source": test_case["expected_source"],
                "fix_working": success,
                "session_id": session_id,
            }
        else:
            return {
                "query": query,
                "duration": duration,
                "status": "ERROR",
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "session_id": session_id,
                "fix_working": False,
            }

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        return {
            "query": query,
            "duration": duration,
            "status": "TIMEOUT/ERROR",
            "error": str(e),
            "session_id": session_id,
            "fix_working": False,
        }


async def run_perfection_fixes_test():
    """Run the focused perfection fixes test."""

    print("🎯 PERFECTION FIXES TEST")
    print("=" * 70)
    print("Testing the 3 specific fixes for 99%+ success rate:")
    print("1. 'How do I find candidates?' conversational routing")
    print("2. 'show me John Smith' helpful suggestions")
    print("3. Empty query friendly response")
    print()

    total_tests = len(PERFECTION_TEST_CASES)
    fixes_working = 0
    total_time = 0

    # Test each perfection fix
    for i, test_case in enumerate(PERFECTION_TEST_CASES, 1):
        query = test_case["query"]
        query_display = f"'{query}'" if query else "'<empty>'"
        print(f"🧪 Test {i}/{total_tests}: {query_display}")
        print(f"   📝 {test_case['description']}")

        result = await test_perfection_fix(test_case, i)
        duration = result["duration"]
        total_time += duration

        if result["fix_working"]:
            fixes_working += 1
            status_icon = "✅"
            status_text = "FIX WORKING"
        elif result["status"] == "PARTIAL_SUCCESS":
            status_icon = "⚠️"
            status_text = "PARTIAL SUCCESS"
        else:
            status_icon = "❌"
            status_text = "FIX FAILED"

        print(
            f"   {status_icon} {duration:.2f}s | {result.get('candidates_found', 0)} candidates | {result.get('source', 'unknown')} | {status_text}"
        )

        if result.get("ai_message"):
            print(f"      💬 Response: {result['ai_message']}")

        if not result["fix_working"] and result["status"] != "ERROR":
            print(
                f"      🎯 Expected: {result.get('expected_candidates', 0)} candidates from {result.get('expected_source', 'unknown')}"
            )

        if result["status"] == "ERROR":
            print(f"      ❌ Error: {result.get('error', 'Unknown error')}")

        print()

        # Small delay between tests
        await asyncio.sleep(0.5)

    print("🎯 PERFECTION FIXES TEST RESULTS")
    print("=" * 70)
    print(f"📊 Fix Results:")
    print(f"   Total Fixes Tested: {total_tests}")
    print(f"   ✅ Fixes Working: {fixes_working}")
    print(f"   ❌ Fixes Failing: {total_tests - fixes_working}")
    print(f"   🎯 Fix Success Rate: {(fixes_working/total_tests)*100:.1f}%")
    print(f"   ⚡ Average Time: {total_time/total_tests:.2f}s")

    # Success assessment
    fix_rate = (fixes_working / total_tests) * 100
    if fix_rate == 100:
        print(f"\n🎉 PERFECT! ALL PERFECTION FIXES WORKING!")
        print(f"   🚀 Ready for 99%+ comprehensive success rate!")
        print(f"   🏆 The TURBO-PATCH + PERFECTION FIXES = UNSTOPPABLE!")
    elif fix_rate >= 75:
        print(f"\n✅ EXCELLENT! Most perfection fixes working!")
        print(f"   Success rate: {fix_rate:.1f}%")
    else:
        print(f"\n🔧 PERFECTION FIXES need attention")
        print(f"   Current fix rate: {fix_rate:.1f}%")

    return fixes_working, total_tests - fixes_working


if __name__ == "__main__":
    asyncio.run(run_perfection_fixes_test())
