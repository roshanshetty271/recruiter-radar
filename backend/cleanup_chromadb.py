"""
Clean up ChromaDB collections to fix HNSW parameter issues.
Run this if the application fails to start due to invalid HNSW parameters.
"""

import chromadb
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_chromadb():
    """Delete all existing collections to allow fresh recreation with correct HNSW parameters."""

    # Initialize ChromaDB client
    chroma_db_path = Path("app/data/chroma_db")
    chroma_db_path.mkdir(parents=True, exist_ok=True)

    try:
        client = chromadb.PersistentClient(path=str(chroma_db_path))
        logger.info(f"Connected to ChromaDB at: {chroma_db_path}")

        # List all collections
        collections = client.list_collections()
        logger.info(f"Found {len(collections)} collections to clean up")

        # Delete all collections
        for collection in collections:
            try:
                client.delete_collection(name=collection.name)
                logger.info(f"✅ Deleted collection: {collection.name}")
            except Exception as e:
                logger.error(f"❌ Failed to delete collection {collection.name}: {e}")

        logger.info(
            "🚀 ChromaDB cleanup complete! Collections will be recreated with correct HNSW parameters."
        )

    except Exception as e:
        logger.error(f"Failed to connect to ChromaDB: {e}")
        return False

    return True


if __name__ == "__main__":
    logger.info("🧹 Starting ChromaDB cleanup for CYBER-CHEETAH HNSW fix...")
    success = cleanup_chromadb()
    if success:
        logger.info("✨ Cleanup successful! You can now start the application.")
    else:
        logger.error("💥 Cleanup failed. Check the logs above.")
