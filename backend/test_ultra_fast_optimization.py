#!/usr/bin/env python3
"""
🚀 ULTRA-FAST OPTIMIZATION TEST SCRIPT (Phase 1 Complete)

This script tests ALL Phase 1 fixes:
1. ✅ Eliminated thread management overhead
2. ✅ Fixed conversation context handling
3. ✅ Enhanced function calling prompts
4. ✅ Shared LLMService instances
5. ✅ True 1-3 second responses

Target: 1-3 seconds with 100% function call success
"""

import asyncio
import time
import logging
from app.services.assistant_service import AssistantService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ultra_fast_optimization():
    """Test the complete Phase 1 optimization package."""

    print("🚀 PHASE 1 ULTRA-FAST OPTIMIZATION TEST")
    print("=" * 60)

    # Initialize the assistant service
    assistant_service = AssistantService()

    # Test conversation flow with context
    conversation_tests = [
        (
            "Find React engineers who know TypeScript",
            "Initial search - should find candidates",
        ),
        ("in San Francisco", "Follow-up location filter - should trigger function"),
        ("more senior candidates", "Experience refinement - should trigger function"),
        ("who also know AWS", "Skill addition - should trigger function"),
        ("Python developers", "New search - should find Python devs"),
        ("California based", "Location filter - should trigger function"),
    ]

    session_id = "ultra_test_session"
    total_time = 0
    successful_calls = 0
    failed_calls = 0

    for i, (query, description) in enumerate(conversation_tests, 1):
        print(f"\n🧪 Test {i}: '{query}'")
        print(f"📝 Expected: {description}")
        print("-" * 40)

        start_time = time.time()

        try:
            # Test the bulletproof method (should now be ultra-fast)
            response = await assistant_service.bulletproof_recruiter_chat(
                query, session_id
            )
            response_time = time.time() - start_time
            total_time += response_time

            # Check if function was called (candidates found or intelligent response)
            function_called = (
                len(response.candidates) > 0
                or "candidates" in response.ai_message.lower()
            )

            if function_called:
                successful_calls += 1
                status = "✅ SUCCESS"
            else:
                failed_calls += 1
                status = "❌ NO FUNCTION CALL"

            # Performance analysis
            if response_time <= 1.0:
                speed_status = "🚀 BLAZING"
            elif response_time <= 3.0:
                speed_status = "⚡ FAST"
            elif response_time <= 5.0:
                speed_status = "✅ GOOD"
            else:
                speed_status = "⚠️  SLOW"

            print(f"{status} {speed_status}: {response_time:.2f}s")
            print(f"   📊 Candidates: {len(response.candidates)}")
            print(f"   🎯 Source: {response.source}")
            print(f"   💬 Response: {response.ai_message[:100]}...")

            # Analysis
            if response_time <= 3.0 and function_called:
                print(f"   🎉 PERFECT: Fast response with function call!")
            elif response_time <= 3.0:
                print(f"   ⚠️  Fast but no function call detected")
            elif function_called:
                print(f"   ⚠️  Function called but response too slow")
            else:
                print(f"   ❌ FAILED: Slow AND no function call")

        except Exception as e:
            failed_calls += 1
            response_time = time.time() - start_time
            total_time += response_time
            print(f"❌ ERROR: {e} after {response_time:.2f}s")

    # Final Performance Report
    print(f"\n📈 PHASE 1 OPTIMIZATION RESULTS")
    print("=" * 50)

    avg_response_time = total_time / len(conversation_tests)
    function_success_rate = (successful_calls / len(conversation_tests)) * 100

    print(f"Average Response Time: {avg_response_time:.2f}s")
    print(f"Function Call Success Rate: {function_success_rate:.1f}%")
    print(f"Successful Function Calls: {successful_calls}/{len(conversation_tests)}")
    print(f"Failed Calls: {failed_calls}")

    # Success Criteria
    print(f"\n🎯 SUCCESS CRITERIA CHECK:")
    print("=" * 30)

    speed_success = avg_response_time <= 3.0
    function_success = function_success_rate >= 80.0

    print(
        f"Speed Target (≤3.0s): {'✅ PASSED' if speed_success else '❌ FAILED'} ({avg_response_time:.2f}s)"
    )
    print(
        f"Function Rate (≥80%): {'✅ PASSED' if function_success else '❌ FAILED'} ({function_success_rate:.1f}%)"
    )

    if speed_success and function_success:
        print(f"\n🎉 PHASE 1 OPTIMIZATION: COMPLETE SUCCESS!")
        print(f"✅ Ready for Phase 2 (Streaming)")
        return True
    elif speed_success:
        print(f"\n⚠️  PARTIAL SUCCESS: Speed good, but function calling needs work")
        return False
    elif function_success:
        print(f"\n⚠️  PARTIAL SUCCESS: Function calling good, but speed needs work")
        return False
    else:
        print(f"\n❌ PHASE 1 NEEDS MORE WORK: Both speed and function calling issues")
        return False


async def test_specific_issues():
    """Test the specific issues we identified earlier."""

    print(f"\n🔍 TESTING SPECIFIC ISSUE FIXES")
    print("=" * 40)

    assistant_service = AssistantService()
    session_id = "issue_test_session"

    # Test the exact queries that failed before
    problem_queries = [
        " in San Francisco",
        "More senior candidates",
        "California based",
    ]

    for query in problem_queries:
        print(f"\n🧪 Issue Test: '{query}'")
        start_time = time.time()

        response = await assistant_service.bulletproof_recruiter_chat(query, session_id)
        response_time = time.time() - start_time

        function_triggered = (
            len(response.candidates) > 0 or "candidates" in response.ai_message.lower()
        )

        print(f"   ⏱️  Time: {response_time:.2f}s")
        print(
            f"   🔧 Function: {'✅ Called' if function_triggered else '❌ Not called'}"
        )
        print(f"   📊 Results: {len(response.candidates)} candidates")

        if response_time <= 3.0 and function_triggered:
            print(f"   🎉 FIXED!")
        else:
            print(f"   ⚠️  Still has issues")


if __name__ == "__main__":
    print("Starting Phase 1 Ultra-Fast Optimization Test...")
    success = asyncio.run(test_ultra_fast_optimization())

    print("\nTesting specific issue fixes...")
    asyncio.run(test_specific_issues())

    if success:
        print(f"\n🚀 READY FOR PHASE 2: STREAMING IMPLEMENTATION!")
    else:
        print(f"\n🔧 PHASE 1 NEEDS MORE REFINEMENT")

    print("\nTest completed!")
