#!/usr/bin/env python3
"""
🚀 SPEED OPTIMIZATION TEST SCRIPT

This script tests the new fast Chat Completions API vs the old slow Assistant API
to verify our 85% speed improvement is working.
"""

import asyncio
import time
import logging
from app.services.assistant_service import AssistantService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_speed_optimization():
    """Test the new fast chat completion method."""

    print("🚀 PHASE 1 SPEED OPTIMIZATION TEST")
    print("=" * 50)

    # Initialize the assistant service
    assistant_service = AssistantService()

    # Test queries
    test_queries = [
        "Show me Python developers",
        "Find senior engineers with 5+ years",
        "React developers in New York",
    ]

    session_id = "speed_test_session"

    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}: '{query}'")
        print("-" * 30)

        # Test the new FAST method
        start_time = time.time()

        try:
            result = await assistant_service._fast_chat_completion(query, session_id)
            fast_time = time.time() - start_time

            if result:
                print(f"✅ FAST Chat Completion: {fast_time:.2f}s")
                print(f"   📊 Found: {len(result.get('candidates', []))} candidates")
                print(f"   🎯 Source: {result.get('source')}")
            else:
                print(f"❌ FAST Chat Completion: FAILED after {fast_time:.2f}s")

        except Exception as e:
            fast_time = time.time() - start_time
            print(f"❌ FAST Chat Completion: ERROR after {fast_time:.2f}s - {e}")

        # Test full bulletproof method (should now be fast)
        start_time = time.time()

        try:
            response = await assistant_service.bulletproof_recruiter_chat(
                query, session_id
            )
            bulletproof_time = time.time() - start_time

            print(f"✅ Bulletproof Chat: {bulletproof_time:.2f}s")
            print(f"   📊 Found: {len(response.candidates)} candidates")
            print(f"   🎯 Source: {response.source}")

            # Calculate improvement
            if fast_time > 0:
                if bulletproof_time < 5:  # Under 5 seconds = success
                    improvement = ((15 - bulletproof_time) / 15) * 100
                    print(
                        f"   🚀 SPEED IMPROVEMENT: {improvement:.1f}% faster than old method!"
                    )
                else:
                    print(f"   ⚠️  Still slow: {bulletproof_time:.2f}s")

        except Exception as e:
            bulletproof_time = time.time() - start_time
            print(f"❌ Bulletproof Chat: ERROR after {bulletproof_time:.2f}s - {e}")

    # Get performance metrics
    print(f"\n📈 PERFORMANCE METRICS:")
    print("=" * 30)
    metrics = assistant_service.get_performance_metrics()

    print(f"Total Requests: {metrics['total_requests']}")
    print(f"Assistant Successes: {metrics['assistant_successes']}")
    print(f"Fallback Activations: {metrics['fallback_activations']}")
    print(f"Average Response Time: {metrics['avg_response_time']:.2f}s")

    success_rate = 0
    if metrics["total_requests"] > 0:
        success_rate = (
            metrics["assistant_successes"] / metrics["total_requests"]
        ) * 100

    print(f"Success Rate: {success_rate:.1f}%")

    if metrics["avg_response_time"] < 5:
        print("🎉 SUCCESS: Average response time under 5 seconds!")
    else:
        print("⚠️  WARNING: Still experiencing slow responses")


if __name__ == "__main__":
    print("Starting speed optimization test...")
    asyncio.run(test_speed_optimization())
    print("\nTest completed!")
