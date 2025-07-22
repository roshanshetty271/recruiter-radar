#!/usr/bin/env python3
"""
Debug script to find candidates with malformed skills data.
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


async def check_all_candidates():
    """Check all candidates for malformed skills data."""
    print("🔍 Checking all candidates for malformed skills data...")

    # Initialize ChromaDB connector
    settings = Settings()
    chroma_connector = ChromaConnector(settings)
    collection = chroma_connector._collection

    # Get all candidates
    try:
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[[0.1] * 1536],  # Dummy embedding
            n_results=60,  # Get more than 50
            include=["metadatas", "documents"],
        )

        if results and results.get("metadatas") and results["metadatas"][0]:
            print(f"📊 Found {len(results['metadatas'][0])} candidates in ChromaDB")

            malformed_candidates = []

            for i, (metadata, candidate_id) in enumerate(
                zip(results["metadatas"][0], results["ids"][0])
            ):
                candidate_id = metadata.get("candidate_id", f"unknown_{i}")
                name = metadata.get("name", "Unknown")
                skills = metadata.get("skills", "")
                skills_type = type(skills).__name__

                # Check for issues
                issues = []

                if not skills:
                    issues.append("Empty skills")
                elif isinstance(skills, str):
                    # Check if it looks malformed (e.g., contains brackets, quotes)
                    if skills.startswith("['") or skills.startswith('["'):
                        issues.append("List-like string (malformed)")
                    elif skills.count(",") == 0 and len(skills) > 50:
                        issues.append("Suspiciously long single skill")
                else:
                    issues.append(f"Unexpected type: {skills_type}")

                if issues:
                    malformed_candidates.append(
                        {
                            "id": candidate_id,
                            "name": name,
                            "skills": (
                                skills[:100] + "..."
                                if len(str(skills)) > 100
                                else skills
                            ),
                            "issues": issues,
                        }
                    )

                # Show first few candidates regardless
                if i < 5:
                    print(f"👤 {i+1}. {name} (ID: {candidate_id})")
                    print(
                        f"   Skills ({skills_type}): {str(skills)[:100]}{'...' if len(str(skills)) > 100 else ''}"
                    )
                    if issues:
                        print(f"   ⚠️ Issues: {', '.join(issues)}")
                    print()

            print(f"\n🚨 Found {len(malformed_candidates)} candidates with issues:")
            for candidate in malformed_candidates:
                print(
                    f"  - {candidate['name']} ({candidate['id']}): {', '.join(candidate['issues'])}"
                )
                print(f"    Skills: {candidate['skills']}")
                print()

        else:
            print("❌ No metadata found in ChromaDB!")

    except Exception as e:
        print(f"❌ Error checking ChromaDB: {e}")


if __name__ == "__main__":
    asyncio.run(check_all_candidates())
