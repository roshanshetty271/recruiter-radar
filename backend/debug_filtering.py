#!/usr/bin/env python3
"""
Debug script to test RAG service similarity search directly.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import Settings
from app.services.llm_service import LLMService
from app.services.chroma_connector import ChromaConnector
from app.services.rag_service import RAGService


async def test_direct_filtering():
    """Test RAG service filtering directly."""
    print("🧪 Testing RAG service filtering directly...")

    # Initialize services
    settings = Settings()
    llm_service = LLMService(settings)
    chroma_connector = ChromaConnector(settings)
    rag_service = RAGService(settings, chroma_connector)

    # Test queries
    test_queries = ["react", "python", "java"]

    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")

        # Get embedding for the query
        query_embedding = await llm_service.get_embedding(query)

        # Call similarity search directly with skill filtering
        try:
            results, count_before_filter = await rag_service.similarity_search(
                query_embedding=query_embedding,
                query_text=query,
                k=50,  # Get all candidates
                filters={},  # No pre-filters
                required_skills=[query],  # Use the query as required skill
                preferred_skills=[],
            )

            print(f"   Results after filtering: {len(results)}")
            print(f"   Count before filter: {count_before_filter}")

            # Show first few matches
            for i, result in enumerate(results[:3]):
                metadata = result.get("metadata", {})
                name = metadata.get("name", "Unknown")
                skills = metadata.get("skills", "")
                print(f"   {i+1}. {name}: {skills[:100]}...")

        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_direct_filtering())
