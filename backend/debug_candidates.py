#!/usr/bin/env python3
"""
Debug script to analyze candidate database and search issues
"""
import asyncio
import sys
from app.services.rag_service import RAGService


async def debug_candidates():
    print("🔍 DEBUGGING CANDIDATE DATABASE...")
    print("=" * 60)

    rag_service = RAGService()

    # 1. Check total candidates
    print("1️⃣ CHECKING TOTAL CANDIDATES...")
    all_results = await rag_service.search_candidates_with_function_params(
        session_id="debug_session",
        skills=None,
        title_keywords=None,
        min_experience=None,
        location_keywords=None,
        limit=100,  # High limit
    )

    print(f"📊 TOTAL CANDIDATES: {len(all_results)}")

    # 2. Check Python candidates with high limit
    print("\n2️⃣ CHECKING PYTHON CANDIDATES (limit=100)...")
    python_results = await rag_service.search_candidates_with_function_params(
        session_id="debug_session",
        skills=["Python"],
        title_keywords=None,
        min_experience=None,
        location_keywords=None,
        limit=100,
    )

    print(f"🐍 PYTHON CANDIDATES (limit=100): {len(python_results)}")

    # 3. Check Python candidates with default limit
    print("\n3️⃣ CHECKING PYTHON CANDIDATES (default limit)...")
    python_results_default = await rag_service.search_candidates_with_function_params(
        session_id="debug_session",
        skills=["Python"],
        title_keywords=None,
        min_experience=None,
        location_keywords=None,
        # No limit specified - should use default 50
    )

    print(f"🐍 PYTHON CANDIDATES (default): {len(python_results_default)}")

    # 4. Look for Alex Chen
    print("\n4️⃣ SEARCHING FOR ALEX CHEN...")
    alex_found = False
    for i, candidate in enumerate(all_results):
        name = candidate.get("name", "").lower()
        if "alex" in name and "chen" in name:
            alex_found = True
            print(f"🎯 FOUND: {candidate.get('name')}")
            print(f"   Skills: {candidate.get('skills', [])}")
            print(f"   Location: {candidate.get('location', 'N/A')}")
            print(f"   Title: {candidate.get('title', 'N/A')}")
            break

    if not alex_found:
        print("❌ ALEX CHEN NOT FOUND!")
        # Show first 10 candidate names
        print("\n📋 FIRST 10 CANDIDATES:")
        for i, candidate in enumerate(all_results[:10]):
            print(f"   {i+1}. {candidate.get('name', 'Unknown')}")

    # 5. Check if there are Python skill variations
    print("\n5️⃣ CHECKING PYTHON SKILL VARIATIONS...")
    python_variations = set()
    for candidate in all_results:
        skills = candidate.get("skills", [])
        for skill in skills:
            if "python" in skill.lower():
                python_variations.add(skill)

    print(f"🔤 PYTHON SKILL VARIATIONS: {sorted(python_variations)}")

    print("\n" + "=" * 60)
    print("✅ DEBUG COMPLETE")


if __name__ == "__main__":
    asyncio.run(debug_candidates())
