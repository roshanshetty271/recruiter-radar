#!/usr/bin/env python3
"""
Database Cleanup Script for RecruiterRadar

This script provides two options for cleaning up test data from ChromaDB:
1. Full Reset: Clear everything and reload demo data
2. Selective Removal: Remove only uploaded candidates (source=async_upload)

Usage:
    python cleanup_database.py --full-reset    # Clear all and reload demo data
    python cleanup_database.py --remove-uploads # Remove only uploaded candidates
    python cleanup_database.py --help          # Show help
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv

# Try to load .env from backend or project root
env_in_backend = backend_dir / ".env"
env_in_project_root = backend_dir.parent / ".env"

if env_in_backend.exists():
    load_dotenv(env_in_backend)
    print(f"Loaded .env from: {env_in_backend}")
elif env_in_project_root.exists():
    load_dotenv(env_in_project_root)
    print(f"Loaded .env from: {env_in_project_root}")
else:
    print("No .env file found, using system environment variables")

# Import services
from app.services.chroma_connector import ChromaConnector, ChromaConnectionError
from app.services.rag_service import RAGService, RAGServiceError
from app.services.llm_service import LLMService, LLMServiceError
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def full_reset():
    """
    Full reset: Clear ChromaDB collection and reload demo data from candidate_profiles.json
    """
    print("🔄 Starting full database reset...")

    try:
        # Initialize services
        print("🔧 Initializing services...")
        llm_service = LLMService(settings)
        connector = ChromaConnector(settings)
        rag_service = RAGService(settings, connector)

        # Reset the collection (delete and recreate)
        print("🗑️  Clearing ChromaDB collection...")
        connector.recreate_collection()
        print("✅ Collection cleared and recreated")

        # Load demo data
        candidate_file = backend_dir / "app" / "data" / "candidate_profiles.json"
        if not candidate_file.exists():
            raise FileNotFoundError(f"Demo data file not found: {candidate_file}")

        print(f"📁 Loading demo data from: {candidate_file}")

        # Re-run the ingestion process using the ingest_data script
        import subprocess
        import sys

        print("🔄 Running data ingestion...")
        result = subprocess.run(
            [sys.executable, "ingest_data.py"], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ Demo data loaded successfully")
        else:
            print(f"❌ Data ingestion failed: {result.stderr}")
            raise Exception("Data ingestion failed")

        print("✅ Full reset completed successfully!")
        print("🎯 Database now contains only demo candidates")

    except Exception as e:
        print(f"❌ Full reset failed: {e}")
        logger.error(f"Full reset error: {e}", exc_info=True)
        return False

    return True


async def remove_uploaded_candidates():
    """
    Selective removal: Remove only candidates with source=async_upload metadata
    """
    print("🔄 Starting selective removal of uploaded candidates...")

    try:
        # Initialize services
        print("🔧 Initializing services...")
        connector = ChromaConnector(settings)
        collection = connector.get_collection()

        # Get all documents with their metadata
        print("🔍 Scanning for uploaded candidates...")
        all_data = collection.get(include=["metadatas"])

        if not all_data or not all_data.get("ids"):
            print("ℹ️  No candidates found in database")
            return True

        # Find uploaded candidates (those with source=async_upload)
        uploaded_ids = []
        for i, metadata in enumerate(all_data["metadatas"]):
            if metadata and metadata.get("source") == "async_upload":
                uploaded_ids.append(all_data["ids"][i])

        if not uploaded_ids:
            print("ℹ️  No uploaded candidates found to remove")
            return True

        print(f"🗑️  Found {len(uploaded_ids)} uploaded candidates to remove:")
        for candidate_id in uploaded_ids:
            # Get candidate info for display
            candidate_data = collection.get(ids=[candidate_id], include=["metadatas"])
            if candidate_data["metadatas"] and candidate_data["metadatas"][0]:
                name = candidate_data["metadatas"][0].get("name", "Unknown")
                email = candidate_data["metadatas"][0].get("email", "No email")
                print(f"   - {name} ({email})")

        # Ask for confirmation
        response = input(
            f"\n❓ Remove these {len(uploaded_ids)} uploaded candidates? (y/N): "
        )
        if response.lower() not in ["y", "yes"]:
            print("❌ Operation cancelled")
            return False

        # Remove the uploaded candidates
        print("🗑️  Removing uploaded candidates...")
        collection.delete(ids=uploaded_ids)

        print(f"✅ Successfully removed {len(uploaded_ids)} uploaded candidates!")
        print("🎯 Database now contains only demo candidates")

    except Exception as e:
        print(f"❌ Selective removal failed: {e}")
        logger.error(f"Selective removal error: {e}", exc_info=True)
        return False

    return True


async def show_database_status():
    """
    Show current database status (total candidates, demo vs uploaded)
    """
    print("📊 Current Database Status:")
    print("-" * 40)

    try:
        connector = ChromaConnector(settings)
        collection = connector.get_collection()

        # Get all documents with metadata
        all_data = collection.get(include=["metadatas"])

        if not all_data or not all_data.get("ids"):
            print("📭 Database is empty")
            return

        total_count = len(all_data["ids"])
        demo_count = 0
        uploaded_count = 0

        # Count demo vs uploaded
        for metadata in all_data["metadatas"]:
            if metadata and metadata.get("source") == "async_upload":
                uploaded_count += 1
            else:
                demo_count += 1

        print(f"📈 Total Candidates: {total_count}")
        print(f"🎭 Demo Candidates: {demo_count}")
        print(f"📤 Uploaded Candidates: {uploaded_count}")

        if uploaded_count > 0:
            print(f"\n📋 Uploaded Candidates:")
            for i, metadata in enumerate(all_data["metadatas"]):
                if metadata and metadata.get("source") == "async_upload":
                    name = metadata.get("name", "Unknown")
                    email = metadata.get("email", "No email")
                    print(f"   - {name} ({email})")

    except Exception as e:
        print(f"❌ Failed to get database status: {e}")
        logger.error(f"Database status error: {e}", exc_info=True)


async def main():
    parser = argparse.ArgumentParser(
        description="Clean up RecruiterRadar test data from ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_database.py --full-reset      # Clear all data and reload demo candidates
  python cleanup_database.py --remove-uploads  # Remove only uploaded test candidates
  python cleanup_database.py --status         # Show current database status
        """,
    )

    parser.add_argument(
        "--full-reset",
        action="store_true",
        help="Clear all data and reload demo candidates from candidate_profiles.json",
    )

    parser.add_argument(
        "--remove-uploads",
        action="store_true",
        help="Remove only uploaded candidates (keeps demo data)",
    )

    parser.add_argument(
        "--status", action="store_true", help="Show current database status"
    )

    args = parser.parse_args()

    # Show status if requested or if no action specified
    if args.status or not any([args.full_reset, args.remove_uploads]):
        await show_database_status()
        if not any([args.full_reset, args.remove_uploads]):
            print("\n💡 Use --help to see cleanup options")
            return

    success = True

    if args.full_reset:
        success = await full_reset()
    elif args.remove_uploads:
        success = await remove_uploaded_candidates()

    if success:
        print("\n📊 Final Status:")
        await show_database_status()

    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
