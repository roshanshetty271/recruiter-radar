#!/usr/bin/env python3
"""
Test name search functionality to ensure Alex Chen can be found
"""
import asyncio
from app.services.assistant_service import AssistantService


async def test_name_search():
    print("🧪 TESTING NAME SEARCH FUNCTIONALITY...")
    print("=" * 60)

    assistant_service = AssistantService()

    # Test 1: Direct name search
    print("1️⃣ Testing: 'Alex Chen'")
    result1 = await assistant_service.bulletproof_recruiter_chat(
        message="Alex Chen", session_id="test_name_search"
    )
    print(f"   📊 Found: {len(result1.candidates)} candidates")
    print(f"   🎯 Source: {result1.source}")
    if result1.candidates:
        print(f"   ✅ First result: {result1.candidates[0].get('name', 'Unknown')}")

    # Test 2: Skills of specific person
    print("\n2️⃣ Testing: 'skills of Alex Chen'")
    result2 = await assistant_service.bulletproof_recruiter_chat(
        message="skills of Alex Chen", session_id="test_name_search"
    )
    print(f"   📊 Found: {len(result2.candidates)} candidates")
    print(f"   🎯 Source: {result2.source}")
    if result2.candidates:
        print(f"   ✅ First result: {result2.candidates[0].get('name', 'Unknown')}")
        print(f"   🔧 Skills: {result2.candidates[0].get('skills', [])}")

    # Test 3: Python developers (should now show 25)
    print("\n3️⃣ Testing: 'Python developers' (should show 25)")
    result3 = await assistant_service.bulletproof_recruiter_chat(
        message="Python developers", session_id="test_name_search"
    )
    print(f"   📊 Found: {len(result3.candidates)} candidates")
    print(f"   🎯 Source: {result3.source}")

    print("\n" + "=" * 60)
    if len(result3.candidates) >= 20:
        print("✅ SUCCESS: Limit fix working!")
    else:
        print("❌ LIMIT STILL BROKEN")

    if (
        result2.candidates
        and "alex chen" in result2.candidates[0].get("name", "").lower()
    ):
        print("✅ SUCCESS: Name search working!")
    else:
        print("❌ NAME SEARCH STILL BROKEN")


if __name__ == "__main__":
    asyncio.run(test_name_search())
