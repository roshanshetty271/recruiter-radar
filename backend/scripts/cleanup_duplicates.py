#!/usr/bin/env python3
"""
One-time script to clean up duplicate candidates in ChromaDB.

This script removes the existing 70+ duplicate vectors that were created
during testing, keeping only the collection structure intact.
"""

import sys
import os
from pathlib import Path

# Add the backend app to the path so we can import modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging
from app.core.config import settings
from app.services.chroma_connector import ChromaConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_all_candidates():
    """Remove all candidates from the collection, keeping the collection structure."""
    try:
        print("🧹 Starting ChromaDB cleanup...")

        # Initialize connector
        connector = ChromaConnector(settings_obj=settings)
        collection = connector.get_collection()

        # Get current count
        count = await asyncio.to_thread(collection.count)
        print(f"📊 Found {count} vectors in collection '{collection.name}'")

        if count == 0:
            print("✅ Collection is already empty")
            return

        # Get all IDs
        results = await asyncio.to_thread(collection.get, include=["metadatas"])

        if results and results["ids"]:
            print(f"🗑️  Deleting {len(results['ids'])} vectors...")

            # Delete all vectors
            await asyncio.to_thread(collection.delete, ids=results["ids"])

            # Verify cleanup
            new_count = await asyncio.to_thread(collection.count)
            print(f"✅ Cleanup complete! Collection now has {new_count} vectors")
        else:
            print("⚠️  No vectors found to delete")

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 ChromaDB Duplicate Cleanup Tool")
    print("This will remove ALL existing vectors from the collection.")

    response = input("Continue? (y/N): ").strip().lower()
    if response != "y":
        print("Cancelled.")
        sys.exit(0)

    asyncio.run(cleanup_all_candidates())
    print("🎉 Ready for testing with the new upload logic!")
