#!/usr/bin/env python3
"""
Migration script to re-ingest candidate profiles with skills as lists in metadata.

This fixes the issue where skills were stored as comma-separated strings
instead of lists, causing skill filtering to fail.

Usage: python backend/scripts/reingest_add_skills.py
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import Settings
from app.services.llm_service import LLMService
from app.services.chroma_connector import ChromaConnector
from app.services.rag_service import RAGService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_candidates():
    """Re-ingest all candidates with correct skills metadata."""
    logger.info("🔧 Starting migration: adding skills as lists to ChromaDB metadata")

    # Initialize services
    settings = Settings()
    llm_service = LLMService(settings)
    chroma_connector = ChromaConnector(settings)
    rag_service = RAGService(settings, chroma_connector)

    # Load candidate data
    candidates_file = backend_dir / "app" / "data" / "candidate_profiles.json"
    if not candidates_file.exists():
        logger.error(f"❌ Candidate profiles not found: {candidates_file}")
        return

    with open(candidates_file, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    logger.info(f"📂 Loaded {len(candidates)} candidates from {candidates_file}")

    # Process each candidate
    successful = 0
    failed = 0

    for i, candidate in enumerate(candidates, 1):
        try:
            candidate_id = candidate.get("id")
            name = candidate.get("name", "Unknown")

            logger.info(
                f"🔄 ({i}/{len(candidates)}) Processing {name} (ID: {candidate_id})"
            )

            # Generate embedding for the candidate
            resume_text = candidate.get("raw_resume_text", "")
            if not resume_text:
                logger.warning(f"⚠️ No resume text for {name}, using fallback")
                resume_text = (
                    f"Name: {name}. Skills: {', '.join(candidate.get('skills', []))}"
                )

            embedding = await llm_service.get_embedding(resume_text)

            # Prepare metadata with skills as list (not string)
            metadata = {
                "candidate_id": str(candidate_id),
                "name": str(name),
                "email": str(candidate.get("email", "")).lower().strip() or None,
                "skills": candidate.get("skills", []),  # Store as list!
                "experience_years": int(candidate.get("experience_years", 0)),
                "visa_status": str(candidate.get("visa_status", "Not Specified")),
                "location": str(candidate.get("location", "Not Specified")),
                "github_url": str(candidate.get("github_url", "")),
                "linkedin_url": str(candidate.get("linkedin_url", "")),
            }

            # Add/update in ChromaDB (this will replace existing document with same ID)
            await rag_service.add_candidate_to_collection(
                candidate_id=candidate_id,
                embedding=embedding,
                metadata=metadata,
                document_text=resume_text,
            )

            successful += 1
            logger.info(f"✅ Successfully migrated {name}")

        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to migrate {name}: {e}")

    logger.info(
        f"🎉 Migration complete! ✅ {successful} successful, ❌ {failed} failed"
    )


if __name__ == "__main__":
    asyncio.run(migrate_candidates())
