#!/usr/bin/env python3
"""
One-time cleanup script to remove existing duplicates in ChromaDB.

Run this ONCE before deploying the new deduplication logic to clean up any
existing duplicate candidates in the database.

Usage:
    cd backend
    python scripts/remove_existing_duplicates.py
"""

import asyncio
import sys
import os
from collections import defaultdict
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.chroma_connector import ChromaConnector
from app.services.rag_service import RAGService
from app.core.config import settings


def normalize_email(email: str) -> str:
    """Normalize email for comparison."""
    if not email:
        return ""
    return email.lower().strip()


def normalize_name(name: str) -> str:
    """Normalize name for comparison."""
    if not name:
        return ""
    return name.lower().strip()


async def remove_duplicates():
    """Remove duplicate candidates from ChromaDB."""
    print("🧹 Starting ChromaDB duplicate cleanup...")

    try:
        # Initialize services
        connector = ChromaConnector(settings_obj=settings)
        rag_service = RAGService(settings_obj=settings, connector=connector)

        print(f"📊 Connected to collection: {rag_service.collection_name}")

        # Get all candidates
        print("📥 Fetching all candidates from ChromaDB...")
        all_results = await asyncio.to_thread(
            rag_service.collection.get,
            limit=10000,  # Should be enough for MVP
            include=["metadatas"],  # IDs are returned by default
        )

        total_candidates = len(all_results.get("ids", []))
        print(f"📋 Found {total_candidates} candidates total")

        if total_candidates == 0:
            print("✅ No candidates found - nothing to clean up!")
            return

        # Group candidates by normalized email and name
        email_groups = defaultdict(list)
        name_groups = defaultdict(list)

        for idx, metadata in enumerate(all_results.get("metadatas", [])):
            if not metadata:
                continue

            cand_id = all_results["ids"][idx]

            # Group by normalized email
            email = normalize_email(metadata.get("email", ""))
            if email:
                email_groups[email].append((cand_id, metadata))

            # Group by normalized name (for candidates without emails)
            name = normalize_name(metadata.get("name", ""))
            if name:
                name_groups[name].append((cand_id, metadata))

        # Find duplicates and decide which to keep/delete
        ids_to_delete = []

        print("\n🔍 Checking for email-based duplicates...")
        # Remove email duplicates (keep the most recent or first one)
        for email, candidates in email_groups.items():
            if len(candidates) > 1:
                print(f"📧 Found {len(candidates)} candidates with email: {email}")

                # Sort by candidate_id to ensure consistent ordering (keep first)
                candidates_sorted = sorted(candidates, key=lambda x: x[0])

                # Keep first, delete rest
                for cand_id, metadata in candidates_sorted[1:]:
                    ids_to_delete.append(cand_id)
                    print(
                        f"   ❌ Will delete: {cand_id} ({metadata.get('name', 'Unknown')})"
                    )

                # Show which one we're keeping
                kept_id, kept_meta = candidates_sorted[0]
                print(f"   ✅ Keeping: {kept_id} ({kept_meta.get('name', 'Unknown')})")

        print(f"\n🔍 Checking for name-based duplicates (no email)...")
        # Remove name duplicates (only for candidates without emails)
        for name, candidates in name_groups.items():
            # Only process candidates that don't have emails and haven't been marked for deletion
            candidates_without_email = [
                (cid, meta)
                for cid, meta in candidates
                if not normalize_email(meta.get("email", ""))
                and cid not in ids_to_delete
            ]

            if len(candidates_without_email) > 1:
                print(
                    f"👤 Found {len(candidates_without_email)} candidates named '{name}' without email"
                )

                # Sort by candidate_id for consistent ordering
                candidates_sorted = sorted(candidates_without_email, key=lambda x: x[0])

                # Keep first, delete rest
                for cand_id, metadata in candidates_sorted[1:]:
                    ids_to_delete.append(cand_id)
                    print(f"   ❌ Will delete: {cand_id}")

                # Show which one we're keeping
                kept_id, kept_meta = candidates_sorted[0]
                print(f"   ✅ Keeping: {kept_id}")

        # Delete duplicates
        if ids_to_delete:
            print(f"\n🗑️ Deleting {len(ids_to_delete)} duplicates...")
            print(
                "Duplicate IDs to delete:",
                ids_to_delete[:10],
                "..." if len(ids_to_delete) > 10 else "",
            )

            # Delete in batches to avoid overwhelming the database
            batch_size = 100
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i : i + batch_size]
                print(
                    f"   Deleting batch {i//batch_size + 1}: {len(batch)} candidates..."
                )
                await asyncio.to_thread(rag_service.collection.delete, ids=batch)

            print("✅ Cleanup complete!")
        else:
            print("✅ No duplicates found - database is clean!")

        # Show final statistics
        final_count = await asyncio.to_thread(rag_service.collection.count)
        removed_count = total_candidates - final_count

        print(f"\n📊 Cleanup Summary:")
        print(f"   Original candidates: {total_candidates}")
        print(f"   Duplicates removed: {removed_count}")
        print(f"   Final candidate count: {final_count}")
        print(f"   Space saved: {(removed_count/total_candidates)*100:.1f}%")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    print("🚀 RecruiterRadar ChromaDB Duplicate Cleanup")
    print("=" * 50)

    # Run the cleanup
    success = asyncio.run(remove_duplicates())

    if success:
        print("\n🎉 Cleanup completed successfully!")
        print("💡 You can now deploy the new deduplication logic.")
    else:
        print("\n💥 Cleanup failed - check the logs above.")
        sys.exit(1)
