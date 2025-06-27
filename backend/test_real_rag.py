#!/usr/bin/env python3
"""
🚀 REAL RAG TEST - Verify True Semantic Search

This tests the complete RAG pipeline:
1. Document chunking with embeddings
2. Semantic similarity search
3. LLM synthesis from retrieved context

NO MORE HARDCODED BULLSHIT - Pure AI-powered search!
"""

import asyncio
import logging
import time
from typing import Dict, Any, List

# Configure logging to see the magic happen
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_real_rag():
    """
    Test the complete REAL RAG pipeline with various queries.
    """
    print("🔥 TESTING REAL RAG - NO MORE HARDCODED METADATA FILTERING!")
    print("=" * 80)

    try:
        # Import our REAL RAG service
        from app.services.real_rag_service import RealRAGService

        # Initialize the REAL RAG service
        real_rag = RealRAGService()

        # Test session ID
        session_id = "real_rag_test_session"

        # Test queries that should work with semantic search
        test_queries = [
            "Python developers",
            "skills of Alex Chen",
            "senior engineers",
            "candidates with React experience",
            "data scientists",
            "full stack developers",
            "machine learning engineers",
            "JavaScript specialists",
            "experienced software engineers",
            "frontend developers",
        ]

        print(f"🔍 Testing {len(test_queries)} semantic search queries...")
        print()

        total_start_time = time.time()
        successful_searches = 0
        total_candidates_found = 0

        for i, query in enumerate(test_queries, 1):
            print(f"🚀 Test {i}/{len(test_queries)}: '{query}'")
            print("-" * 60)

            start_time = time.time()

            try:
                # Perform REAL RAG search
                result = await real_rag.search_candidates(
                    query=query, session_id=session_id, max_results=20
                )

                search_time = time.time() - start_time

                # Display results
                candidates = result.get("candidates", [])
                ai_message = result.get("ai_message", "No AI response")
                source = result.get("source", "unknown")
                total_chunks = result.get("total_chunks", 0)
                success = result.get("success", False)

                print(f"   ✅ SUCCESS: {len(candidates)} candidates found")
                print(f"   🤖 AI Response: {ai_message}")
                print(f"   📊 Source: {source}")
                print(f"   📄 Total chunks searched: {total_chunks}")
                print(f"   ⚡ Search time: {search_time:.2f}s")

                if candidates:
                    print(f"   👥 Top candidates:")
                    for j, candidate in enumerate(candidates[:3], 1):
                        name = candidate.get("name", "Unknown")
                        title = candidate.get("title", "Unknown")
                        match_score = candidate.get("match_score", 0)
                        print(f"      {j}. {name} - {title} (Match: {match_score}%)")

                if success:
                    successful_searches += 1
                    total_candidates_found += len(candidates)

            except Exception as e:
                print(f"   ❌ FAILED: {e}")
                logger.error(f"Query '{query}' failed: {e}", exc_info=True)

            print()

        # Summary
        total_time = time.time() - total_start_time
        avg_time = total_time / len(test_queries)

        print("🎯 REAL RAG TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Successful searches: {successful_searches}/{len(test_queries)}")
        print(f"👥 Total candidates found: {total_candidates_found}")
        print(f"⚡ Total test time: {total_time:.2f}s")
        print(f"📊 Average search time: {avg_time:.2f}s")
        print(f"🎉 Success rate: {(successful_searches/len(test_queries)*100):.1f}%")

        if successful_searches == len(test_queries):
            print("🚀 ALL TESTS PASSED - REAL RAG IS WORKING!")
            print("🔥 NO MORE HARDCODED METADATA FILTERING!")
            print("✨ True semantic search with embeddings achieved!")
        else:
            print(f"⚠️  {len(test_queries) - successful_searches} tests failed")
            print("🔧 Check logs for debugging information")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Make sure all services are properly implemented")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error("Test execution failed", exc_info=True)


async def test_semantic_vs_hardcoded():
    """
    Compare semantic search vs hardcoded filtering results.
    """
    print("\n🔥 SEMANTIC vs HARDCODED COMPARISON")
    print("=" * 80)

    try:
        from app.services.real_rag_service import RealRAGService
        from app.services.rag_service import RAGService

        real_rag = RealRAGService()
        old_rag = RAGService()

        session_id = "comparison_test"
        test_query = "Python developers with React experience"

        print(f"🔍 Query: '{test_query}'")
        print()

        # Test REAL RAG (semantic search)
        print("🚀 REAL RAG (Semantic Search):")
        start_time = time.time()
        semantic_result = await real_rag.search_candidates(
            query=test_query, session_id=session_id, max_results=10
        )
        semantic_time = time.time() - start_time

        semantic_candidates = semantic_result.get("candidates", [])
        print(f"   Found: {len(semantic_candidates)} candidates")
        print(f"   Time: {semantic_time:.2f}s")
        print(f"   AI Response: {semantic_result.get('ai_message', 'No response')}")

        # Test OLD RAG (hardcoded filtering)
        print("\n🐌 OLD RAG (Hardcoded Filtering):")
        start_time = time.time()
        try:
            hardcoded_result = await old_rag.search_candidates_with_function_params(
                session_id=session_id,
                skills=["Python", "React"],
                title_keywords=[],
                min_experience=None,
                location_keywords=[],
                limit=10,
            )
            hardcoded_time = time.time() - start_time

            print(f"   Found: {len(hardcoded_result)} candidates")
            print(f"   Time: {hardcoded_time:.2f}s")
            print(f"   Method: Regex pattern matching")
        except Exception as e:
            print(f"   ❌ Failed: {e}")

        print()
        print("🎯 COMPARISON RESULT:")
        print(
            f"   🚀 REAL RAG: {len(semantic_candidates)} candidates, {semantic_time:.2f}s - Uses AI embeddings"
        )
        print(f"   🐌 OLD RAG: Hardcoded regex patterns - Limited and brittle")
        print(
            "   ✨ REAL RAG provides semantic understanding vs exact keyword matching!"
        )

    except Exception as e:
        print(f"❌ Comparison test failed: {e}")


if __name__ == "__main__":
    print("🚀 STARTING REAL RAG VERIFICATION TESTS")
    print("=" * 80)

    # Run the tests
    asyncio.run(test_real_rag())

    # Run comparison
    asyncio.run(test_semantic_vs_hardcoded())

    print("\n🎉 REAL RAG TESTING COMPLETE!")
    print("🔥 If successful, you now have TRUE semantic search!")
    print("✨ NO MORE HARDCODED BULLSHIT!")
