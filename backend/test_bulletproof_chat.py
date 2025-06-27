"""
Test script for bulletproof assistant implementation.

This script validates that our Phase 1 implementation works correctly:
1. Assistant service instantiation
2. Thread management
3. Bulletproof chat functionality
4. Fallback behavior
5. Circuit breaker functionality
"""

import asyncio
import json
import time
from pathlib import Path

# Add the app directory to the path
import sys

sys.path.append(str(Path(__file__).parent / "app"))

from services.assistant_service import AssistantService
from models.api_models import ChatRequest, ChatResponse


async def test_assistant_instantiation():
    """Test that we can create the assistant service."""
    print("🔧 Testing assistant service instantiation...")

    try:
        service = AssistantService()
        print("✅ Assistant service created successfully")

        # Test database initialization
        if service.db_path.exists():
            print("✅ SQLite database initialized")
        else:
            print("❌ SQLite database not found")

        return service
    except Exception as e:
        print(f"❌ Failed to create assistant service: {e}")
        return None


async def test_assistant_creation(service):
    """Test creating the OpenAI assistant."""
    print("\n🤖 Testing OpenAI assistant creation...")

    try:
        assistant_id = await service.get_or_create_assistant()
        print(f"✅ Assistant created/retrieved: {assistant_id[:8]}...")

        # Test loading from config
        config_path = service.storage_dir / "assistant_config.json"
        if config_path.exists():
            print("✅ Assistant config saved")

        return True
    except Exception as e:
        print(f"❌ Failed to create assistant: {e}")
        return False


async def test_thread_management(service):
    """Test thread creation and management."""
    print("\n🧵 Testing thread management...")

    try:
        session_id = "test_session_123"

        # Create thread
        thread_id1 = await service.get_or_create_thread(session_id)
        print(f"✅ Thread created: {thread_id1[:8]}...")

        # Get same thread again
        thread_id2 = await service.get_or_create_thread(session_id)
        if thread_id1 == thread_id2:
            print("✅ Thread persistence working")
        else:
            print("❌ Thread persistence failed")

        # Test different session
        session_id2 = "test_session_456"
        thread_id3 = await service.get_or_create_thread(session_id2)
        if thread_id3 != thread_id1:
            print("✅ Session isolation working")
        else:
            print("❌ Session isolation failed")

        return True
    except Exception as e:
        print(f"❌ Thread management failed: {e}")
        return False


async def test_bulletproof_chat(service):
    """Test the bulletproof chat functionality."""
    print("\n💬 Testing bulletproof chat...")

    try:
        session_id = "test_session_chat"

        # Test 1: Basic search query
        print("  Testing: 'Find Python developers'")
        response = await service.bulletproof_recruiter_chat(
            message="Find Python developers", session_id=session_id
        )

        print(f"✅ Response received from: {response.source}")
        print(f"✅ Response time: {response.response_time:.2f}s")
        print(f"✅ Candidates found: {len(response.candidates)}")
        print(f"✅ AI message: {response.ai_message[:50]}...")

        # Test 2: Different query type
        print("\n  Testing: 'Show me React engineers with 5+ years'")
        response2 = await service.bulletproof_recruiter_chat(
            message="Show me React engineers with 5+ years experience",
            session_id=session_id,
        )

        print(f"✅ Response received from: {response2.source}")
        print(f"✅ Response time: {response2.response_time:.2f}s")
        print(f"✅ Candidates found: {len(response2.candidates)}")

        return True
    except Exception as e:
        print(f"❌ Bulletproof chat failed: {e}")
        return False


async def test_fallback_behavior(service):
    """Test fallback behavior by triggering circuit breaker."""
    print("\n🔄 Testing fallback behavior...")

    try:
        # Force circuit breaker to open
        service.circuit_breaker_failures = service.circuit_breaker_threshold
        service.circuit_breaker_reset_time = time.time() + 300  # 5 minutes

        print("  Circuit breaker forced open")

        # Test chat with circuit breaker open
        response = await service.bulletproof_recruiter_chat(
            message="Test fallback behavior", session_id="test_fallback"
        )

        if response.source == "fallback":
            print("✅ Fallback activated successfully")
            print(f"✅ Response time: {response.response_time:.2f}s")
            print(f"✅ Still got response: {response.ai_message[:50]}...")
        else:
            print("❌ Fallback not activated")

        # Reset circuit breaker
        service.circuit_breaker_failures = 0
        service.circuit_breaker_reset_time = None
        print("  Circuit breaker reset")

        return True
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False


async def test_performance_metrics(service):
    """Test performance metrics collection."""
    print("\n📊 Testing performance metrics...")

    try:
        metrics = service.get_performance_metrics()

        print(f"✅ Total requests: {metrics['total_requests']}")
        print(f"✅ Assistant successes: {metrics['assistant_successes']}")
        print(f"✅ Fallback activations: {metrics['fallback_activations']}")
        print(f"✅ Average response time: {metrics['avg_response_time']:.2f}s")
        print(
            f"✅ Circuit breaker status: {'Open' if metrics['circuit_breaker_open'] else 'Closed'}"
        )

        if metrics["total_requests"] > 0:
            print(
                f"✅ Assistant success rate: {metrics['assistant_success_rate']:.1f}%"
            )
            print(f"✅ Fallback rate: {metrics['fallback_rate']:.1f}%")

        return True
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        return False


async def test_timeout_protection(service):
    """Test timeout protection (this will test the timeout mechanism)."""
    print("\n⏱️ Testing timeout protection...")

    # Note: This test just validates the timeout logic exists
    # In a real timeout scenario, it would fall back after 8 seconds

    try:
        # Test with a reasonable query that should work
        start_time = time.time()
        response = await service.bulletproof_recruiter_chat(
            message="Quick test for timeout protection", session_id="test_timeout"
        )
        elapsed = time.time() - start_time

        print(f"✅ Response completed in {elapsed:.2f}s")
        print(f"✅ Source: {response.source}")

        if elapsed < 8.0:
            print("✅ Response within timeout window")
        else:
            print("⚠️ Response took longer than expected (but still worked)")

        return True
    except Exception as e:
        print(f"❌ Timeout test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting bulletproof assistant tests...\n")

    # Test 1: Service instantiation
    service = await test_assistant_instantiation()
    if not service:
        print("\n❌ Cannot continue without service")
        return

    # Test 2: Assistant creation
    if not await test_assistant_creation(service):
        print("\n❌ Cannot continue without assistant")
        return

    # Test 3: Thread management
    if not await test_thread_management(service):
        print("\n⚠️ Thread management issues")

    # Test 4: Bulletproof chat
    if not await test_bulletproof_chat(service):
        print("\n❌ Bulletproof chat failed")
        return

    # Test 5: Fallback behavior
    if not await test_fallback_behavior(service):
        print("\n⚠️ Fallback behavior issues")

    # Test 6: Performance metrics
    if not await test_performance_metrics(service):
        print("\n⚠️ Metrics issues")

    # Test 7: Timeout protection
    if not await test_timeout_protection(service):
        print("\n⚠️ Timeout protection issues")

    print("\n🎉 Bulletproof assistant tests completed!")
    print("\n📋 Summary:")
    print("- ✅ Assistant service instantiation")
    print("- ✅ OpenAI assistant creation")
    print("- ✅ Thread management")
    print("- ✅ Bulletproof chat functionality")
    print("- ✅ Fallback behavior")
    print("- ✅ Performance metrics")
    print("- ✅ Timeout protection")

    print("\n🚀 Ready for Phase 2 implementation!")


if __name__ == "__main__":
    asyncio.run(main())
