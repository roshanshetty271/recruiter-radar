#!/usr/bin/env python3
"""
Test Metadata Field Fix

Quick test to verify that candidates now show proper names, titles, and experience
instead of "Unknown" and "0 years exp".
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(__file__))

from app.services.semantic_search import SemanticSearchEngine


async def test_metadata_extraction():
    """Test that candidate metadata is properly extracted"""
    print("🔍 TESTING METADATA EXTRACTION FIX")
    print("=" * 60)

    search_engine = SemanticSearchEngine()

    # Test a simple search
    query = "show me all available candidates"
    print(f"🧪 Testing query: '{query}'")

    try:
        result = await search_engine.search_candidates(
            query=query, session_id="test-session", max_results=5
        )

        candidates = result.get("candidates", [])
        print(f"\n✅ Found {len(candidates)} candidates")

        if not candidates:
            print("❌ NO CANDIDATES FOUND - Check data ingestion!")
            return False

        # Check first few candidates
        success = True
        for i, candidate in enumerate(candidates[:3]):
            name = candidate.get("name", "Unknown")
            title = candidate.get("title", "Unknown")
            experience = candidate.get("experience", "Unknown")
            skills = candidate.get("skills", [])

            print(f"\n👤 Candidate {i+1}:")
            print(f"   Name: {name}")
            print(f"   Title: {title}")
            print(f"   Experience: {experience}")
            print(f"   Skills: {skills[:3] if skills else 'None'}")

            # Check if we still have "Unknown" issues
            if name == "Unknown":
                print(f"   ❌ STILL SHOWING 'Unknown' NAME!")
                success = False
            elif title == "Software Engineer" and experience == "0 years":
                print(f"   ⚠️ GENERIC DATA (might be placeholder)")
            else:
                print(f"   ✅ LOOKS GOOD!")

        print(f"\n🤖 AI Response: {result.get('ai_response', 'No response')[:100]}...")

        return success

    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


async def main():
    """Run metadata fix test"""
    print("🔧 METADATA FIELD FIX TESTER")
    print("Checking if candidates show real names instead of 'Unknown'")
    print()

    success = await test_metadata_extraction()

    print("\n" + "=" * 60)
    if success:
        print("🎉 METADATA FIX WORKS! Real candidate data is showing!")
        print("Check your frontend - candidates should have proper names now!")
    else:
        print("❌ METADATA FIX NEEDS MORE WORK")
        print("Check the debug logs above for clues")


if __name__ == "__main__":
    asyncio.run(main())
