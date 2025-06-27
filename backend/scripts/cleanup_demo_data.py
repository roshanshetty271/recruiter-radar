#!/usr/bin/env python3
"""
Cleanup Demo Data Script

This script removes all demo/synthetic candidates from ChromaDB,
keeping only the real resume data that was just ingested.

Usage:
    cd backend
    python scripts/cleanup_demo_data.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.chroma_connector import ChromaConnector

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def cleanup_demo_data():
    """Remove all demo/synthetic candidates, keeping only real resume data."""
    logger.info("🧹 Starting ChromaDB Cleanup - Removing Demo Data")

    try:
        # Initialize ChromaConnector
        chroma_connector = ChromaConnector(settings)

        # Get the collection
        collection = chroma_connector.get_collection()

        # Get all documents with their metadata
        logger.info("📊 Analyzing current ChromaDB contents...")

        # Query all documents to see what we have
        all_results = collection.get(include=["metadatas", "documents"])

        total_candidates = len(all_results["ids"])
        logger.info(f"📈 Found {total_candidates} total candidates in ChromaDB")

        if total_candidates == 0:
            logger.info("✅ ChromaDB is already empty!")
            return

        # Known real resume names from our ingestion
        real_resume_names = {
            "RENATA VOSS",
            "SALVADOR SANZ",
            "KIAN WOODS",
            "KIAN MARSHALL",
            "ARIA FISCHER",
            "LEANDER HARTMAN",
            "Gaia Park",
            "Giulia Gonzalez",
            "Ilya Karaslavov",
            "Tasiana Ukura",
            "Cynthia Dwayne",
            "Caius Kessler",
            "Charles McTurland",
            "ZARA GREENE",
            "LUCIAN ASHFORD",
        }

        # Categorize candidates
        real_resume_ids = []
        demo_candidate_ids = []
        unknown_ids = []

        for i, candidate_id in enumerate(all_results["ids"]):
            metadata = all_results["metadatas"][i] if all_results["metadatas"] else {}
            candidate_name = metadata.get("name", "Unknown")
            filename = metadata.get("filename", "")
            title = metadata.get("title", "")

            # Check if this is a real resume based on the known names
            if candidate_name in real_resume_names:
                real_resume_ids.append(candidate_id)
            # Check if this is demo/test data to remove
            elif (
                candidate_id.startswith("demo_")
                or candidate_id.startswith("hash_test-device")
                or "test_resume" in filename
                or candidate_name
                in [
                    "John Smith",
                    "Sarah Johnson",
                    "Mike Chen",
                    "Emily Davis",
                    "David Wilson",
                ]
                or "Demo Candidate" in title
            ):
                demo_candidate_ids.append(candidate_id)
            else:
                unknown_ids.append(candidate_id)

        # Report what we found
        logger.info("📋 CHROMADB ANALYSIS:")
        logger.info(f"  ✅ Real resumes: {len(real_resume_ids)}")
        logger.info(f"  🗑️  Demo candidates: {len(demo_candidate_ids)}")
        logger.info(f"  ❓ Unknown: {len(unknown_ids)}")

        # Show some examples of what will be kept vs removed
        if real_resume_ids:
            logger.info(f"  📄 Sample real resumes to KEEP:")
            for i, rid in enumerate(real_resume_ids[:3]):
                metadata = all_results["metadatas"][all_results["ids"].index(rid)]
                name = metadata.get("name", "Unknown")
                filename = metadata.get("filename", "N/A")
                logger.info(f"    ✅ {rid} → {name} ({filename})")
            if len(real_resume_ids) > 3:
                logger.info(f"    ... and {len(real_resume_ids) - 3} more")

        if demo_candidate_ids:
            logger.info(f"  🗑️  Sample demo candidates to REMOVE:")
            for i, did in enumerate(demo_candidate_ids[:5]):
                metadata = all_results["metadatas"][all_results["ids"].index(did)]
                name = metadata.get("name", "Unknown")
                logger.info(f"    ❌ {did} → {name}")
            if len(demo_candidate_ids) > 5:
                logger.info(f"    ... and {len(demo_candidate_ids) - 5} more")

        # Confirm deletion
        if not demo_candidate_ids:
            logger.info(
                "🎉 No demo candidates found to remove! Database only has real resumes."
            )
            return

        logger.info(f"\n⚠️  ABOUT TO DELETE {len(demo_candidate_ids)} demo candidates!")
        logger.info(
            "This will keep your real resume data and remove synthetic/demo data."
        )

        # Delete demo candidates
        logger.info("🗑️  Deleting demo candidates...")

        # ChromaDB delete expects a list of IDs
        collection.delete(ids=demo_candidate_ids)

        logger.info(
            f"✅ Successfully deleted {len(demo_candidate_ids)} demo candidates!"
        )

        # Verify final state
        final_results = collection.get()
        final_count = len(final_results["ids"])

        logger.info("=" * 60)
        logger.info("🎉 CHROMADB CLEANUP COMPLETE!")
        logger.info(f"📊 Before: {total_candidates} candidates")
        logger.info(f"📊 After: {final_count} candidates")
        logger.info(f"🗑️  Removed: {len(demo_candidate_ids)} demo candidates")
        logger.info(f"✅ Kept: {len(real_resume_ids)} real resumes")
        logger.info("=" * 60)

        if final_count == len(real_resume_ids):
            logger.info("🎯 Perfect! Your database now contains only real resume data.")
            logger.info(
                "🔍 Try searching for candidates - you'll see much more realistic results!"
            )
        else:
            logger.warning(
                "⚠️  Final count doesn't match expected. Some unknown candidates remain."
            )

    except Exception as e:
        logger.error(f"💥 Error during cleanup: {e}", exc_info=True)


if __name__ == "__main__":
    # Load and validate configuration
    try:
        from app.core.config import settings

        logger.info("✅ Configuration loaded successfully")
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file and ensure API_OPENAI_API_KEY is set")
        sys.exit(1)

    asyncio.run(cleanup_demo_data())
