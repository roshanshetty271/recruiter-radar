#!/usr/bin/env python3
"""
Quick Debug Script - Check if the fixes work

Run this to see if your ChromaDB has data and test the search.
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(__file__))

from app.services.chroma_connector import ChromaConnector
from app.services.semantic_search import SemanticSearchEngine
from app.core.config import settings


async def debug_chromadb():
    """Check ChromaDB collection status"""
    print("🔍 DEBUGGING CHROMADB COLLECTION...")

    try:
        # Initialize connector
        chroma = ChromaConnector(settings)
        collection = chroma.get_collection()

        # Check collection stats
        count = collection.count()
        print(f"📊 Main collection document count: {count}")

        if count == 0:
            print("❌ MAIN COLLECTION IS EMPTY!")
            print("   You need to run data ingestion first:")
            print("   cd backend && python ingest_data.py")
            return False

        # Get sample data
        sample = collection.peek(limit=5)
        print(f"📄 Sample documents: {len(sample.get('documents', []))}")

        if sample.get("metadatas") and len(sample["metadatas"]) > 0:
            first_metadata = sample["metadatas"][0]
            print(f"🏷️ Sample metadata keys: {list(first_metadata.keys())}")
            print(
                f"👤 Sample candidate: {first_metadata.get('candidate_name', 'Unknown')}"
            )

        return True

    except Exception as e:
        print(f"❌ ChromaDB check failed: {e}")
        return False


async def test_search():
    """Test the semantic search with the fixes"""
    print("\n🔍 TESTING SEMANTIC SEARCH...")

    try:
        search_engine = SemanticSearchEngine()

        # Test queries
        test_queries = [
            "Python developers",
            "senior engineers",
            "React",
            "data scientist",
        ]

        for query in test_queries:
            print(f"\n🧪 Testing query: '{query}'")

            result = await search_engine.search_candidates(
                query=query, session_id="debug-session", max_results=5
            )

            candidates = result.get("candidates", [])
            print(f"   ✅ Found {len(candidates)} candidates")

            if candidates:
                for i, candidate in enumerate(candidates[:2]):
                    print(
                        f"   👤 {i+1}. {candidate.get('name', 'Unknown')} - {candidate.get('title', 'No title')}"
                    )
            else:
                print(f"   📄 AI Response: {result.get('ai_response', 'No response')}")

        return True

    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


async def main():
    """Run all debug checks"""
    print("🚀 QUICK FIX DEBUG SCRIPT")
    print("=" * 50)

    # Check ChromaDB
    chroma_ok = await debug_chromadb()

    if chroma_ok:
        # Test search
        search_ok = await test_search()

        if search_ok:
            print("\n✅ ALL CHECKS PASSED!")
            print("   Your fixes should work now. Try the frontend!")
        else:
            print("\n❌ SEARCH TESTS FAILED")
            print("   Check the logs above for errors")
    else:
        print("\n❌ CHROMADB ISSUES DETECTED")
        print("   Fix the data ingestion first")


if __name__ == "__main__":
    asyncio.run(main())
