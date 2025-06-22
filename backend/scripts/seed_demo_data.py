#!/usr/bin/env python3
"""
Demo Data Seeding Script for RecruiterRadar MVP

Seeds the existing candidate_profiles.json data into ChromaDB with is_demo=true
for the special "demo_static" session. This allows the UI to show demo candidates
when users haven't uploaded any resumes yet.

Usage:
    python scripts/seed_demo_data.py
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.chroma_connector import ChromaConnector
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Demo session ID - special constant for demo data
DEMO_SESSION_ID = "demo_static"


async def seed_demo_data():
    """
    Seed demo candidates into ChromaDB with is_demo=true flag.
    """
    try:
        # Initialize services
        logger.info("Initializing services...")
        llm_service = LLMService(settings_obj=settings)
        chroma_connector = ChromaConnector(settings_obj=settings)
        rag_service = RAGService(settings_obj=settings, connector=chroma_connector)

        # Load demo data
        demo_data_path = backend_dir / "app" / "data" / "candidate_profiles.json"
        logger.info(f"Loading demo data from: {demo_data_path}")

        with open(demo_data_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)

        logger.info(f"Found {len(candidates)} demo candidates to seed")

        # Process each candidate
        success_count = 0
        error_count = 0

        for i, candidate in enumerate(candidates, 1):
            try:
                logger.info(
                    f"Processing candidate {i}/{len(candidates)}: {candidate['name']}"
                )

                # Extract candidate data
                candidate_id = f"demo_{candidate['id']}"
                name = candidate["name"]
                raw_text = candidate["raw_resume_text"]
                skills = candidate["skills"]
                experience_years = candidate["experience_years"]
                location = candidate["location"]
                visa_status = candidate["visa_status"]
                github_url = candidate.get("github_url")
                linkedin_url = candidate.get("linkedin_url")

                # Generate embedding for the resume text
                logger.debug(f"Generating embedding for {name}")
                embedding = await llm_service.get_embedding(raw_text)

                # Prepare metadata with is_demo=true flag
                # Convert skills list to comma-separated string for ChromaDB compatibility
                skills_str = (
                    ",".join(skills) if isinstance(skills, list) else str(skills)
                )

                metadata = {
                    "session_id": DEMO_SESSION_ID,
                    "filename": f"demo_{candidate['id']}.pdf",
                    "status": "processed_successfully",
                    "name": name,
                    "title": f"Demo Candidate - {name}",  # Mark as demo
                    "skills": skills_str,  # Convert to string
                    "location": location,
                    "experience_years": experience_years,
                    "visa_status": visa_status,
                    "github_url": github_url or "",  # Convert None to empty string
                    "linkedin_url": linkedin_url or "",  # Convert None to empty string
                    "upload_timestamp": "2024-01-01T00:00:00Z",  # Static timestamp for demo
                    "is_demo": True,  # KEY FLAG for demo data
                    "processing_time_ms": 0,
                }

                # Store in ChromaDB
                await rag_service.add_candidate_to_collection(
                    candidate_id=candidate_id,
                    embedding=embedding,
                    metadata=metadata,
                    document_text=raw_text,
                )

                success_count += 1
                logger.info(f"✅ Successfully seeded {name} ({candidate_id})")

            except Exception as e:
                error_count += 1
                logger.error(
                    f"❌ Failed to seed {candidate.get('name', 'Unknown')}: {e}"
                )
                continue

        # Summary
        logger.info(f"\n🎯 Demo Data Seeding Complete!")
        logger.info(f"✅ Successfully seeded: {success_count} candidates")
        logger.info(f"❌ Failed to seed: {error_count} candidates")
        logger.info(f"📊 Total processed: {len(candidates)} candidates")
        logger.info(f"🔑 Demo session ID: {DEMO_SESSION_ID}")

        # Verify the data was stored correctly
        logger.info("\n🔍 Verifying seeded data...")
        demo_candidates = await rag_service.search_resumes_by_filters(
            session_id=DEMO_SESSION_ID, filters={"is_demo": True}, limit=50
        )

        logger.info(
            f"✅ Verification: Found {len(demo_candidates)} demo candidates in database"
        )

        if demo_candidates:
            logger.info("📋 Sample demo candidates:")
            for candidate in demo_candidates[:5]:  # Show first 5
                logger.info(f"   - {candidate['name']} ({candidate['title']})")

        return success_count, error_count

    except Exception as e:
        logger.error(f"💥 Critical error during demo data seeding: {e}", exc_info=True)
        raise


async def main():
    """Main entry point for the seeding script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed demo data for RecruiterRadar MVP"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing demo data, don't seed new data",
    )

    args = parser.parse_args()

    try:
        if args.verify_only:
            logger.info("🔍 Verification mode - checking existing demo data...")
            chroma_connector = ChromaConnector(settings_obj=settings)
            rag_service = RAGService(settings_obj=settings, connector=chroma_connector)

            demo_candidates = await rag_service.search_resumes_by_filters(
                session_id=DEMO_SESSION_ID, filters={"is_demo": True}, limit=50
            )

            logger.info(f"✅ Found {len(demo_candidates)} demo candidates in database")
            return

        # Seed the demo data
        success_count, error_count = await seed_demo_data()

        if error_count == 0:
            logger.info("🎉 All demo data seeded successfully!")
            sys.exit(0)
        else:
            logger.warning(f"⚠️  Seeding completed with {error_count} errors")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Seeding interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
