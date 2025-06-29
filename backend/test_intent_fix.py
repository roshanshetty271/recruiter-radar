#!/usr/bin/env python3
"""
Test Intent Detection Fix

Quick test to verify that "hi" gets conversational response
and "Python developers" gets search results.
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(__file__))

from app.services.real_rag_service import RealRAGService


async def test_intent_detection():
    """Test the smart intent detection"""
    print("🧠 TESTING SMART INTENT DETECTION")
    print("=" * 50)

    rag_service = RealRAGService()

    # Test cases
    test_cases = [
        # Should be CONVERSATIONAL
        ("hi", "conversation"),
        ("hello", "conversation"),
        ("help", "conversation"),
        ("what can you do", "conversation"),
        ("thanks", "conversation"),
        # Should be SEARCH
        ("Python developers", "search"),
        ("senior engineers", "search"),
        ("find React developers", "search"),
        ("JavaScript", "search"),
        ("5 years experience", "search"),
    ]

    all_passed = True

    for query, expected_intent in test_cases:
        try:
            result = await rag_service._detect_intent_smart(query)
            actual_intent = result["intent"]
            reason = result["reason"]

            status = "✅" if actual_intent == expected_intent else "❌"
            print(f"{status} '{query}' → {actual_intent} ({reason})")

            if actual_intent != expected_intent:
                all_passed = False
                print(f"   Expected: {expected_intent}, Got: {actual_intent}")

        except Exception as e:
            print(f"❌ '{query}' → ERROR: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL INTENT TESTS PASSED!")
    else:
        print("❌ SOME INTENT TESTS FAILED")

    return all_passed


async def test_full_responses():
    """Test the full response pipeline"""
    print("\n🚀 TESTING FULL RESPONSE PIPELINE")
    print("=" * 50)

    rag_service = RealRAGService()

    # Test greeting
    print("\n🧪 Testing greeting: 'hi'")
    result = await rag_service.search_candidates(query="hi", session_id="test-session")

    print(f"   Intent: {result.get('source', 'unknown')}")
    print(f"   Response: {result.get('ai_message', 'No message')[:100]}...")
    print(f"   Candidates: {len(result.get('candidates', []))}")

    # Test search
    print("\n🧪 Testing search: 'Python developers'")
    result = await rag_service.search_candidates(
        query="Python developers", session_id="test-session"
    )

    print(f"   Intent: {result.get('source', 'unknown')}")
    print(f"   Response: {result.get('ai_message', 'No message')[:100]}...")
    print(f"   Candidates: {len(result.get('candidates', []))}")


async def main():
    """Run all tests"""
    print("🔧 INTENT DETECTION FIX TESTER")
    print("Verifying 'hi' doesn't trigger candidate search!")
    print()

    # Test intent detection
    intent_ok = await test_intent_detection()

    # Test full pipeline
    await test_full_responses()

    print("\n" + "=" * 60)
    if intent_ok:
        print("🎉 INTENT FIX WORKS! 'hi' should now get a proper greeting!")
    else:
        print("❌ INTENT FIX NEEDS MORE WORK")
    print("Try saying 'hi' in your frontend now!")


if __name__ == "__main__":
    asyncio.run(main())
