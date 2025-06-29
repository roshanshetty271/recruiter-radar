#!/usr/bin/env python3
"""
Logging Validation Test Script

This script makes a test API call to validate that our diagnostic logs are working properly.
It will help us verify that our assumptions about the candidate data flow are correct.

Run with: python test_logging_validation.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.services.assistant_service import AssistantService

# Configure detailed logging to see our diagnostic messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


async def test_chat_flow():
    """Test the chat flow to validate our logging is working."""
    print("🔍 TESTING CHAT FLOW FOR LOGGING VALIDATION")
    print("=" * 60)

    # Initialize the assistant service
    assistant_service = AssistantService()

    # Test queries that should trigger different behaviors
    test_queries = [
        "I want some python developers",  # Same as the screenshot
        "okay how about you show me candidates with java exp",  # Similar to the screenshot
    ]

    test_session_id = "test_session_123"

    for i, query in enumerate(test_queries, 1):
        print(f"\n🚀 TEST {i}: Testing query: '{query}'")
        print("-" * 50)

        try:
            # Call the bulletproof chat method
            response = await assistant_service.bulletproof_recruiter_chat(
                message=query, session_id=test_session_id
            )

            print(f"✅ Response received:")
            print(f"   - AI Message: {response.ai_message[:100]}...")
            print(f"   - Candidates Count: {len(response.candidates)}")
            print(f"   - Source: {response.source}")

            if response.candidates:
                print(
                    f"   - First 3 candidate names: {[c.get('name', 'NO_NAME') for c in response.candidates[:3]]}"
                )
            else:
                print("   - ⚠️ NO CANDIDATES RETURNED!")

        except Exception as e:
            print(f"❌ Error during test {i}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("🔍 LOGGING VALIDATION COMPLETE")
    print("Check the logs above for our 🚨 LOG entries A through G")


if __name__ == "__main__":
    asyncio.run(test_chat_flow())
