#!/usr/bin/env python3
"""
Analyze ChromaDB Contents Script

This script analyzes the current ChromaDB contents and shows detailed
information about what candidates are stored to help identify what data
we have and what needs to be cleaned up.

Usage:
    cd backend
    python scripts/analyze_chromadb_contents.py
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


async def analyze_chromadb_contents():
    """Analyze and display detailed ChromaDB contents."""
    logger.info("📊 Analyzing ChromaDB Contents")

    try:
        # Initialize ChromaConnector
        chroma_connector = ChromaConnector(settings)

        # Get the collection
        collection = chroma_connector.get_collection()

        # Get all documents with their metadata
        logger.info("📋 Fetching all candidates from ChromaDB...")

        # Query all documents to see what we have
        all_results = collection.get(include=["metadatas", "documents"])

        total_candidates = len(all_results["ids"])
        logger.info(f"📈 Found {total_candidates} total candidates in ChromaDB")

        if total_candidates == 0:
            logger.info("✅ ChromaDB is empty!")
            return

        # Group candidates by type
        real_resumes = []
        test_data = []
        other_data = []

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

        for i, candidate_id in enumerate(all_results["ids"]):
            metadata = all_results["metadatas"][i] if all_results["metadatas"] else {}

            candidate_info = {
                "id": candidate_id,
                "name": metadata.get("name", "Unknown"),
                "title": metadata.get("title", "Unknown"),
                "filename": metadata.get("filename", "N/A"),
                "source": metadata.get("source", "Unknown"),
                "skills": metadata.get("skills", ""),
                "location": metadata.get("location", "Unknown"),
            }

            # Categorize based on known real resume names
            if candidate_info["name"] in real_resume_names:
                real_resumes.append(candidate_info)
            elif "test_resume" in candidate_info["filename"] or candidate_info[
                "name"
            ] in ["John Smith", "Sarah Johnson", "Mike Chen"]:
                test_data.append(candidate_info)
            else:
                other_data.append(candidate_info)

        # Display analysis
        logger.info("=" * 80)
        logger.info("📊 CHROMADB DETAILED ANALYSIS")
        logger.info("=" * 80)

        logger.info(f"✅ REAL RESUMES (from your PDF files): {len(real_resumes)}")
        for candidate in real_resumes[:10]:  # Show first 10
            logger.info(f"  📄 {candidate['name']} - {candidate['title']}")
            logger.info(f"     File: {candidate['filename']}")
            logger.info(f"     ID: {candidate['id']}")
            logger.info("")
        if len(real_resumes) > 10:
            logger.info(f"     ... and {len(real_resumes) - 10} more real resumes")

        logger.info(f"🧪 TEST DATA (likely from previous testing): {len(test_data)}")
        for candidate in test_data[:5]:  # Show first 5
            logger.info(f"  🧪 {candidate['name']} - {candidate['title']}")
            logger.info(f"     File: {candidate['filename']}")
            logger.info(f"     ID: {candidate['id']}")
        if len(test_data) > 5:
            logger.info(f"     ... and {len(test_data) - 5} more test candidates")

        logger.info(f"❓ OTHER DATA: {len(other_data)}")
        for candidate in other_data[:5]:  # Show first 5
            logger.info(f"  ❓ {candidate['name']} - {candidate['title']}")
            logger.info(f"     File: {candidate['filename']}")
            logger.info(f"     Source: {candidate['source']}")
            logger.info(f"     ID: {candidate['id']}")
        if len(other_data) > 5:
            logger.info(f"     ... and {len(other_data) - 5} more other candidates")

        logger.info("=" * 80)

        # Recommendations
        if len(test_data) > 0 or len(other_data) > 0:
            logger.info("💡 RECOMMENDATIONS:")
            if len(test_data) > 0:
                logger.info(
                    f"  🗑️  You have {len(test_data)} test candidates that can be removed"
                )
            if len(other_data) > 0:
                logger.info(
                    f"  🔍 You have {len(other_data)} other candidates to review"
                )
            logger.info("  ✨ Run a cleanup script to keep only your real resume data")
        else:
            logger.info("🎉 Perfect! You only have real resume data in ChromaDB!")

    except Exception as e:
        logger.error(f"💥 Error during analysis: {e}", exc_info=True)


if __name__ == "__main__":
    # Load and validate configuration
    try:
        from app.core.config import settings

        logger.info("✅ Configuration loaded successfully")
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file and ensure API_OPENAI_API_KEY is set")
        sys.exit(1)

    asyncio.run(analyze_chromadb_contents())
