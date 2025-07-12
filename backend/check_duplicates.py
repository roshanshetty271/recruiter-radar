#!/usr/bin/env python3
"""
Script to check for duplicate candidates in ChromaDB.
"""

import sys

sys.path.append(".")

import asyncio
from collections import Counter
from app.services.rag_service import get_rag_service


async def check_chromadb_duplicates():
    """Check for duplicate candidates in ChromaDB."""
    try:
        rag_service = get_rag_service()

        # Get all candidate IDs
        all_ids = await rag_service.get_all_candidate_ids()
        print(f"Total candidates in ChromaDB: {len(all_ids)}")

        # Check for duplicates by counting occurrences
        id_counts = Counter(all_ids)
        duplicates = {id_val: count for id_val, count in id_counts.items() if count > 1}

        if duplicates:
            print(f"DUPLICATES FOUND: {len(duplicates)} candidates have duplicates")
            for candidate_id, count in duplicates.items():
                print(f"  - {candidate_id}: appears {count} times")
        else:
            print("No duplicate candidate IDs found in ChromaDB")

        # Also check the collection count directly
        health = await rag_service.health_check()
        print(
            f'ChromaDB collection count: {health.get("chroma_document_count", "N/A")}'
        )

        # Check if there are email duplicates too
        print("\n--- Checking for email duplicates ---")
        connector = rag_service.connector
        collection = connector.get_collection()

        # Get all documents with metadata (IDs are returned by default)
        all_docs = await asyncio.to_thread(collection.get, include=["metadatas"])

        if all_docs and all_docs.get("ids") and all_docs.get("metadatas"):
            ids = all_docs["ids"]
            metadatas = all_docs["metadatas"]

            email_to_ids = {}
            for doc_id, metadata in zip(ids, metadatas):
                email = metadata.get("email", "")
                if email:
                    if email not in email_to_ids:
                        email_to_ids[email] = []
                    email_to_ids[email].append(doc_id)

            email_duplicates = {
                email: ids for email, ids in email_to_ids.items() if len(ids) > 1
            }

            if email_duplicates:
                print(
                    f"EMAIL DUPLICATES FOUND: {len(email_duplicates)} emails have multiple entries"
                )
                for email, candidate_ids in email_duplicates.items():
                    print(f"  - {email}: IDs {candidate_ids}")
            else:
                print("No email duplicates found in ChromaDB")

    except Exception as e:
        print(f"Error checking ChromaDB: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_chromadb_duplicates())
