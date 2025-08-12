#!/usr/bin/env python3
"""
Debug script to check if skills are properly stored in ChromaDB metadata.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import Settings
from app.services.chroma_connector import ChromaConnector


async def check_skills_in_chromadb():
    """Check if skills are properly stored in ChromaDB."""
    print("🔍 Checking skills in ChromaDB metadata...")

    # Initialize ChromaDB connector
    settings = Settings()
    chroma_connector = ChromaConnector(settings)
    collection = chroma_connector._collection

    # Get a few candidates to check their metadata
    try:
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[[0.1] * 1536],  # Dummy embedding
            n_results=5,
            include=["metadatas", "documents"],
        )

        if results and results.get("metadatas") and results["metadatas"][0]:
            print(f"📊 Found {len(results['metadatas'][0])} candidates")

            for i, metadata in enumerate(results["metadatas"][0][:3]):
                name = metadata.get("name", "Unknown")
                skills = metadata.get("skills", [])
                skills_type = type(skills).__name__

                print(f"👤 Candidate {i+1}: {name}")
                print(f"   Skills ({skills_type}): {skills}")
                print(
                    f"   Skills count: {len(skills) if isinstance(skills, list) else 'N/A'}"
                )
                print()
        else:
            print("❌ No metadata found in ChromaDB!")

    except Exception as e:
        print(f"❌ Error checking ChromaDB: {e}")


if __name__ == "__main__":
    asyncio.run(check_skills_in_chromadb())
