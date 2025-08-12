#!/usr/bin/env python3
"""
Debug script to test the entire search pipeline.
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
from app.services.progressive_search_service import ProgressiveSearchService
from app.services.search_utils import extract_skills_from_query


async def test_search_pipeline():
    """Test the entire search pipeline."""
    print("🧪 Testing entire search pipeline for 'react' query...")

    # Initialize services
    settings = Settings()
    llm_service = LLMService(settings)
    chroma_connector = ChromaConnector(settings)
    rag_service = RAGService(settings, chroma_connector)
    progressive_search = ProgressiveSearchService(rag_service, llm_service)

    query = "react"

    # Step 1: Extract skills
    extracted_skills = extract_skills_from_query(query)
    print(f"1. Extracted skills: {extracted_skills}")

    # Step 2: Get embedding
    query_embedding = await llm_service.get_embedding(query)
    print(f"2. Embedding generated: {len(query_embedding)} dimensions")

    # Step 3: Test RAG service directly (bypass progressive search)
    print("\n3. Testing RAG service directly...")
    try:
        results_direct, count_before = await rag_service.similarity_search(
            query_embedding=query_embedding,
            query_text=query,
            k=50,
            filters={},
            required_skills=extracted_skills,
            preferred_skills=[],
        )
        print(f"   RAG service results: {len(results_direct)} candidates")
        print(f"   Count before post-filter: {count_before}")

        # Show first few candidates
        for i, result in enumerate(results_direct[:3]):
            metadata = result.get("metadata", {})
            name = metadata.get("name", "Unknown")
            skills = metadata.get("skills", "")
            print(f"   {i+1}. {name}: {skills[:50]}...")

    except Exception as e:
        print(f"   ❌ RAG service error: {e}")

    # Step 4: Test progressive search
    print("\n4. Testing progressive search...")
    try:
        results_progressive, search_metadata = (
            await progressive_search.search_with_progressive_fallback(
                query, query_embedding, k=50
            )
        )
        print(f"   Progressive search results: {len(results_progressive)} candidates")
        print(
            f"   Search metadata: {search_metadata.get('search_strategy', 'unknown')}"
        )

    except Exception as e:
        print(f"   ❌ Progressive search error: {e}")


if __name__ == "__main__":
    asyncio.run(test_search_pipeline())
