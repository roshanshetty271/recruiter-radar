"""
RAG (Retrieval-Augmented Generation) Service

This service manages higher-level RAG operations, utilizing ChromaDB for
vector storage and retrieval of candidate profiles.

Key responsibilities:
- Interfacing with ChromaConnector for DB client and collection access.
- Providing asynchronous interfaces for document storage and retrieval.
- Formatting data for storage and search results.
- Supporting future RAG pipeline operations (e.g., query expansion, result synthesis).
"""

import logging
import asyncio  # Added for asyncio.to_thread
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# Removed direct chromadb imports, will come from connector or be internal to RAGService if needed
# from chromadb.utils import embedding_functions # No longer needed here
from fastapi import HTTPException, status  # Keep for get_rag_service DI function

from app.core.config import settings  # For get_rag_service DI function
from app.models.candidate import CandidateProfile  # For type hints if needed

# Import the new connector and its exceptions
from .chroma_connector import (
    ChromaConnector,
    ChromaConnectionError,
    ChromaConfigError,
    ChromaCollectionError,
)
from app.services.rag_operations.search_logic import (
    execute_similarity_search,
    SearchOperationError as OpsSearchOperationError,
)

logger = logging.getLogger(__name__)


class RAGServiceError(Exception):
    """Custom base exception for RAG service operations."""

    pass


class CollectionManagementError(RAGServiceError):
    """Raised for errors during high-level collection management (e.g., reset via connector)."""

    pass


class DocumentStorageError(RAGServiceError):
    """Raised when adding/updating documents fails at the RAGService level."""

    pass


class SearchOperationError(RAGServiceError):
    """Raised for errors during search/query operations."""

    pass


class RAGService:
    """
    RAG Service for managing vector store operations via ChromaConnector.

    This service provides a clean asynchronous interface for:
    - Adding candidate data to the vector store.
    - Performing similarity searches.
    - Resetting the underlying data collection.
    """

    def __init__(self):
        """Initialize RAGService with ChromaConnector."""
        logger.info("Initializing ChromaConnector for RAGService...")
        from app.core.config import settings

        self.chroma_connector = ChromaConnector(settings_obj=settings)
        logger.info(
            f"RAGService initialized successfully using ChromaConnector for collection '{self.chroma_connector.collection_name}'."
        )

        # 🚀 PERFORMANCE: Create shared LLMService instance to avoid recreation
        from app.services.llm_service import LLMService

        self.llm_service = LLMService(settings)
        logger.info("Shared LLMService instance created for RAGService.")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the RAG service and its underlying ChromaDB connection.

        Returns:
            Dict containing health status and service information.
        """
        service_status = "healthy"
        details = {
            "rag_service_status": "initialized",
            "chroma_collection_name": self.chroma_connector.collection_name,
            "chroma_db_path": str(Path(settings.chroma_db_path)),
            "embedding_model_name_for_collection": settings.embedding_model_name,
        }
        try:
            if not self.chroma_connector.collection:
                service_status = "unhealthy"
                details["error"] = (
                    "ChromaDB collection object not available in RAGService."
                )
            else:
                collection = self.chroma_connector.get_collection()
                count = await asyncio.to_thread(collection.count)
                details["chroma_document_count"] = count
                logger.debug(
                    f"RAGService health check: collection '{self.chroma_connector.collection_name}' has {count} documents."
                )
        except Exception as e:
            logger.error(
                f"RAGService health check failed during collection count: {e}",
                exc_info=True,
            )
            service_status = "unhealthy"
            details["error"] = f"Health check failed to get collection count: {str(e)}"

        details["status"] = service_status
        return details

    async def get_session_collection(self, session_id: str):
        """
        Get or create a session-specific collection for proper user isolation.

        This method eliminates the need for complex where clauses and provides
        perfect data isolation between users.

        Args:
            session_id: The session identifier

        Returns:
            ChromaDB collection instance for the session
        """
        try:
            return self.chroma_connector.get_or_create_session_collection(session_id)
        except Exception as e:
            logger.error(
                f"Failed to get session collection for {session_id}: {e}", exc_info=True
            )
            raise RAGServiceError(f"Session collection access failed: {e}") from e

    async def add_candidate_to_session_collection(
        self,
        session_id: str,
        candidate_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        document_text: Optional[str] = None,
    ):
        """
        Add a candidate to the session-specific collection.

        This eliminates the need for session_id in metadata and provides
        clean isolation between users.

        Args:
            session_id: The session identifier
            candidate_id: Unique identifier for the candidate
            embedding: Pre-computed embedding vector
            metadata: Candidate metadata (no session_id needed)
            document_text: Optional raw text that was embedded
        """
        if not candidate_id or not candidate_id.strip():
            logger.error(
                "Invalid candidate_id provided for add_candidate_to_session_collection."
            )
            raise ValueError("candidate_id cannot be empty.")
        if not embedding:
            logger.error(
                f"Invalid or empty embedding provided for candidate {candidate_id}."
            )
            raise ValueError(f"Embedding for candidate {candidate_id} cannot be empty.")

        try:
            # Get session-specific collection
            session_collection = await self.get_session_collection(session_id)

            # Add to session collection (no session_id in metadata needed!)
            await asyncio.to_thread(
                session_collection.add,
                ids=[candidate_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document_text] if document_text is not None else None,
            )

            logger.info(
                f"Successfully added candidate ID '{candidate_id}' to session '{session_id}' collection."
            )
        except Exception as e:
            logger.error(
                f"Failed to add candidate '{candidate_id}' to session '{session_id}': {e}",
                exc_info=True,
            )
            raise DocumentStorageError(
                f"Failed to add candidate '{candidate_id}' to session collection: {e}"
            ) from e

    async def add_candidate_to_collection(
        self,
        candidate_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        document_text: Optional[str] = None,
    ):
        """
        Asynchronously adds a single candidate profile to the ChromaDB collection.
        Uses asyncio.to_thread for the synchronous ChromaDB `add` operation.

        Args:
            candidate_id: Unique identifier for the candidate.
            embedding: Pre-computed embedding vector.
            metadata: Candidate metadata.
            document_text: Optional raw text that was embedded.

        Raises:
            DocumentStorageError: If adding the document fails.
            ValueError: If input arguments are invalid (e.g., empty ID or embedding).
        """
        if not candidate_id or not candidate_id.strip():
            logger.error(
                "Invalid candidate_id provided for add_candidate_to_collection."
            )
            raise ValueError("candidate_id cannot be empty.")
        if not embedding:
            logger.error(
                f"Invalid or empty embedding provided for candidate {candidate_id}."
            )
            raise ValueError(f"Embedding for candidate {candidate_id} cannot be empty.")

        logger.debug(
            f"RAGService: Queueing add operation for candidate ID '{candidate_id}' to collection '{self.chroma_connector.collection_name}' (via thread)."
        )
        try:
            collection = self.chroma_connector.get_collection()
            await asyncio.to_thread(
                collection.add,
                ids=[candidate_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document_text] if document_text is not None else None,
            )
            logger.info(
                f"RAGService: Successfully added/updated candidate ID '{candidate_id}' in collection '{self.chroma_connector.collection_name}'."
            )
        except Exception as e:
            logger.error(
                f"RAGService: Threaded add failed for candidate ID '{candidate_id}' to collection '{self.chroma_connector.collection_name}': {e}",
                exc_info=True,
            )
            raise DocumentStorageError(
                f"Failed to add/update candidate '{candidate_id}' in collection: {e}"
            ) from e

    async def delete_candidate_if_exists(
        self, candidate_id: str, session_id: str
    ) -> bool:
        """
        Delete a candidate from the session collection if it exists.

        With session-based collections, this is much simpler - we just need
        to check if the candidate_id exists in the session's collection.

        Args:
            candidate_id: The candidate ID to delete
            session_id: Session ID for scoping the deletion

        Returns:
            True if candidate was found and deleted, False if not found

        Raises:
            DocumentStorageError: If deletion fails
        """
        try:
            # Get session-specific collection
            session_collection = await self.get_session_collection(session_id)

            # Check if candidate exists (simple query - no complex where clause!)
            results = await asyncio.to_thread(
                session_collection.get,
                ids=[candidate_id],
                include=["metadatas"],
            )

            if not results or not results.get("ids"):
                logger.debug(
                    f"Candidate {candidate_id} not found for deletion in session {session_id}"
                )
                return False

            # Delete the candidate
            await asyncio.to_thread(session_collection.delete, ids=[candidate_id])

            logger.info(
                f"Successfully deleted candidate {candidate_id} from session {session_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete candidate {candidate_id} from session {session_id}: {e}",
                exc_info=True,
            )
            raise DocumentStorageError(
                f"Failed to delete candidate '{candidate_id}' from session collection: {e}"
            ) from e

    async def batch_add_candidates(
        self, candidates_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Asynchronously adds multiple candidates to the collection in batch.
        Uses asyncio.to_thread for the synchronous ChromaDB `add` operation.
        Performs initial validation on input data before batching.

        Args:
            candidates_data: List of candidate data dictionaries.

        Returns:
            Dict with batch operation results and statistics.

        Raises:
            DocumentStorageError: If the batch addition fails at the ChromaDB level.
        """
        if not candidates_data:
            logger.warning("RAGService: No candidates provided for batch add.")
            return {
                "total_candidates": 0,
                "successful": 0,
                "failed": 0,
                "errors": ["No data provided"],
            }

        logger.info(
            f"RAGService: Preparing batch add for {len(candidates_data)} candidates to '{self.chroma_connector.collection_name}'."
        )
        ids, embeddings, metadatas, documents = [], [], [], []
        initial_processing_errors = []
        valid_for_db_batch = 0

        for i, data_item in enumerate(candidates_data):
            candidate_id = data_item.get("candidate_id")
            embedding = data_item.get("embedding")
            if (
                not candidate_id
                or not isinstance(candidate_id, str)
                or not candidate_id.strip()
            ):
                err_msg = f"Batch item {i}: Missing or invalid candidate_id."
                logger.error(err_msg)
                initial_processing_errors.append(err_msg)
                continue
            if not embedding or not isinstance(embedding, list) or len(embedding) == 0:
                err_msg = f"Batch item {i} (ID: {candidate_id}): Missing or invalid embedding."
                logger.error(err_msg)
                initial_processing_errors.append(err_msg)
                continue

            ids.append(candidate_id)
            embeddings.append(embedding)
            metadatas.append(data_item.get("metadata", {}))
            documents.append(data_item.get("document_text"))
            valid_for_db_batch += 1

        if not ids:
            logger.warning(
                "RAGService: No valid candidates to batch add after initial validation."
            )
            return {
                "total_candidates_received": len(candidates_data),
                "successfully_added_to_db": 0,
                "initial_processing_errors_count": len(initial_processing_errors),
                "db_errors_count": 0,
                "error_details": initial_processing_errors
                or ["No valid candidates after validation"],
            }

        try:
            logger.debug(
                f"RAGService: Queueing batch add operation for {len(ids)} candidates to '{self.chroma_connector.collection_name}' (via thread)."
            )
            collection = self.chroma_connector.get_collection()
            await asyncio.to_thread(
                collection.add,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=(
                    documents if any(d is not None for d in documents) else None
                ),
            )
            logger.info(
                f"RAGService: Successfully batch added {len(ids)} candidates to collection '{self.chroma_connector.collection_name}'."
            )
            return {
                "total_candidates_received": len(candidates_data),
                "valid_for_db_batch": valid_for_db_batch,
                "successfully_added_to_db": len(ids),
                "initial_processing_errors_count": len(initial_processing_errors),
                "db_errors_count": 0,
                "error_details": initial_processing_errors,
            }
        except Exception as e:
            logger.error(
                f"RAGService: Threaded batch DB insertion failed for {len(ids)} candidates: {e}",
                exc_info=True,
            )
            raise DocumentStorageError(
                f"Batch insertion into collection '{self.chroma_connector.collection_name}' failed: {e}"
            ) from e

    async def similarity_search(
        self,
        query_embedding: List[float],
        query_text: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Performs a similarity search against the ChromaDB collection.

        Uses the core `execute_similarity_search` logic and handles potential
        errors, re-raising them as RAGService-specific exceptions.

        Args:
            query_embedding: The embedding vector of the search query.
            query_text: The original query string (for logging and context).
            k: The number of top results to return after all filtering.
            filters: Optional dictionary of metadata filters to apply.
                     Expected to include `skills_query` if skills post-filtering is desired.

        Returns:
            A tuple containing:
                - A list of candidate data dictionaries matching the search criteria, capped at k.
                - An integer count of candidates retrieved before any post-filtering (e.g., skills) was applied.

        Raises:
            ValueError: If query_embedding is invalid.
            SearchOperationError: If the underlying search operation fails.
            RAGServiceError: For other RAG service issues (e.g., collection not available).
        """
        if not self.chroma_connector.collection:
            logger.error(
                "RAGService.similarity_search: ChromaDB collection is not available."
            )
            raise RAGServiceError("ChromaDB collection not initialized or accessible.")

        logger.debug(
            f"RAGService: Initiating similarity search in collection '{self.chroma_connector.collection_name}' with k={k}, filters={filters is not None}."
        )
        try:
            # execute_similarity_search is already async
            results, count_before_post_filter = await execute_similarity_search(
                collection=self.chroma_connector.collection,
                query_embedding=query_embedding,
                query_text=query_text,
                k=k,
                filters=filters,
            )
            logger.info(
                f"RAGService: Similarity search completed. Candidates found (after post-filter, limited by k): {len(results)}. Candidates before post-filter: {count_before_post_filter}."
            )
            return results, count_before_post_filter
        except OpsSearchOperationError as e:
            logger.error(
                f"RAGService: Search operation failed in execute_similarity_search: {e}",
                exc_info=True,
            )
            # Re-raise as a RAGService specific error, or let it propagate if it's already an HTTPException
            raise SearchOperationError(
                f"Similarity search failed due to an operation error: {e}"
            ) from e
        except ValueError as e:
            logger.error(
                f"RAGService: Invalid arguments for similarity search: {e}",
                exc_info=True,
            )
            raise  # Re-raise ValueError as it's a client-side input issue
        except Exception as e:
            logger.error(
                f"RAGService: Unexpected error during similarity search: {e}",
                exc_info=True,
            )
            raise RAGServiceError(
                f"An unexpected error occurred during similarity search: {e}"
            ) from e

    async def _load_candidates_cache(self) -> None:
        """
        Load candidate profiles from the JSON file into an in-memory cache.
        This cache is used by get_candidate_details_by_id.
        """
        logger.info("Attempting to load candidates into cache...")
        try:
            # Get path from settings
            logger.info(
                f"RAGService._load_candidates_cache: self.settings.candidate_data_full_path = {settings.candidate_data_full_path}"
            )
            candidates_path = Path(settings.candidate_data_full_path)

            if not candidates_path.exists():
                logger.error(f"Candidate data file not found: {candidates_path}")
                raise FileNotFoundError(
                    f"Candidate data file not found: {candidates_path}"
                )

            logger.info(f"Loading candidates from: {candidates_path}")

            with open(candidates_path, "r", encoding="utf-8") as f:
                candidates_data = json.load(f)

            # Validate and cache each candidate
            self._candidates_cache: Dict[str, CandidateProfile] = (
                {}
            )  # Initialize with type hint
            load_errors = []

            for idx, candidate_dict in enumerate(candidates_data):
                try:
                    candidate = CandidateProfile.model_validate(candidate_dict)
                    self._candidates_cache[candidate.id] = candidate
                except Exception as e:
                    load_errors.append(
                        f"Index {idx}, ID '{candidate_dict.get('id', 'N/A')}': {str(e)}"
                    )
                    logger.error(
                        f"Failed to load/validate candidate at index {idx} (ID: '{candidate_dict.get('id', 'N/A')}'): {e}"
                    )

            logger.info(
                f"Successfully loaded {len(self._candidates_cache)} out of {len(candidates_data)} candidates into cache."
            )

            if load_errors:
                logger.warning(
                    f"Failed to load {len(load_errors)} candidates due to validation/processing errors. Details: {load_errors}"
                )
                # Depending on strictness, could raise an error here if some failed, or just log.
                # For now, we proceed with successfully loaded candidates.

        except FileNotFoundError as e:  # Specifically catch FileNotFoundError
            logger.error(f"Critical error loading candidates cache: {e}", exc_info=True)
            self._candidates_cache = {}  # Ensure cache is empty
            raise RAGServiceError(
                f"Failed to initialize candidate data cache - File Not Found: {e}"
            ) from e
        except json.JSONDecodeError as e:
            logger.error(
                f"Critical error loading candidates cache - JSON decode error: {e}",
                exc_info=True,
            )
            self._candidates_cache = {}  # Ensure cache is empty
            raise RAGServiceError(
                f"Failed to initialize candidate data cache - JSON Decode Error: {e}"
            ) from e
        except (
            Exception
        ) as e:  # Catch other RAGServiceError or Pydantic validation from model_validate if it bubbles up unexpectedly
            logger.error(f"Critical error loading candidates cache: {e}", exc_info=True)
            self._candidates_cache = {}  # Ensure cache is empty
            raise RAGServiceError(
                f"Failed to initialize candidate data cache: {e}"
            ) from e

    async def get_candidate_details_by_id(self, candidate_id: str) -> CandidateProfile:
        """
        Retrieve full candidate profile by ID from memory cache.

        Args:
            candidate_id: Unique candidate identifier

        Returns:
            CandidateProfile object

        Raises:
            ValueError: If candidate_id is empty or candidate not found
            RAGServiceError: If cache not initialized or loading failed
        """
        # Validate input
        if not candidate_id or not candidate_id.strip():
            logger.warning(
                "get_candidate_details_by_id called with empty candidate_id."
            )
            raise ValueError("Candidate ID cannot be empty")

        # Ensure cache is loaded
        # hasattr check is good, also check if _candidates_cache is None or empty in some failure scenarios
        if not hasattr(self, "_candidates_cache") or self._candidates_cache is None:
            logger.info(
                "First access to candidate cache or cache is None, loading data..."
            )
            try:
                await self._load_candidates_cache()
            except RAGServiceError as e:  # Catch specific RAGServiceError from loading
                logger.error(
                    f"Failed to load candidate cache during get_candidate_details_by_id: {e}"
                )
                raise  # Re-raise the RAGServiceError to indicate cache problem

        # Retrieve candidate
        # Ensure candidate_id is stripped for lookup, consistent with how it might be stored if IDs have whitespace
        cleaned_candidate_id = candidate_id.strip()
        candidate = self._candidates_cache.get(cleaned_candidate_id)

        if not candidate:
            logger.warning(
                f"Candidate ID '{cleaned_candidate_id}' not found in cache of {len(self._candidates_cache)} candidates."
            )
            raise ValueError(f"Candidate with ID '{cleaned_candidate_id}' not found")

        logger.debug(
            f"Retrieved candidate '{candidate.name}' (ID: {cleaned_candidate_id})"
        )
        return candidate

    async def get_all_candidate_ids(self) -> List[str]:
        """Get list of all available candidate IDs (useful for testing/validation)."""
        if not hasattr(self, "_candidates_cache") or self._candidates_cache is None:
            logger.info(
                "Candidate cache not available for get_all_candidate_ids, loading data..."
            )
            await self._load_candidates_cache()
        return list(self._candidates_cache.keys())

    async def reset_collection(self):
        """
        Asynchronously resets the ChromaDB collection by deleting and re-initializing it.
        Delegates the synchronous recreation logic to ChromaConnector.recreate_collection
        via asyncio.to_thread. Updates its own collection reference afterwards.

        Raises:
            CollectionManagementError: If any step in resetting the collection fails.
        """
        logger.warning(
            f"RAGService: Attempting to reset collection '{self.chroma_connector.collection_name}' via ChromaConnector (in thread)."
        )
        try:
            new_collection_instance = await asyncio.to_thread(
                self.chroma_connector.recreate_collection
            )

            # Note: ChromaConnector doesn't need collection reassignment as recreate_collection handles it internally
            # The collection_name is already set in ChromaConnector constructor

            logger.info(
                f"RAGService: Collection '{self.chroma_connector.collection_name}' reset. RAGService now uses the new collection instance."
            )
        except ChromaCollectionError as e:
            logger.error(
                f"RAGService: Failed to reset collection '{self.chroma_connector.collection_name}' due to ChromaConnector error: {e}",
                exc_info=True,
            )
            raise CollectionManagementError(
                f"Failed to reset collection '{self.chroma_connector.collection_name}': Connector - {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"RAGService: Unexpected error during threaded collection reset: {e}",
                exc_info=True,
            )
            raise CollectionManagementError(
                f"Unexpected error resetting collection '{self.chroma_connector.collection_name}': {e}"
            ) from e

    async def get_parent_candidate_ids(self, chunk_ids: List[str]) -> List[str]:
        """
        Get unique parent candidate IDs from chunk IDs.

        Used for deduplicating search results when multiple chunks
        from the same resume match a query.

        Args:
            chunk_ids: List of chunk IDs from search results

        Returns:
            List of unique parent candidate IDs
        """
        parent_ids = []
        seen = set()

        for chunk_id in chunk_ids:
            # Extract parent ID from chunk ID
            # Format: "upload_session_hash" or "upload_session_hash_chunk_0"
            if "_chunk_" in chunk_id:
                parent_id = chunk_id.split("_chunk_")[0]
            else:
                parent_id = chunk_id

            # Add only unique parent IDs maintaining order
            if parent_id not in seen:
                seen.add(parent_id)
                parent_ids.append(parent_id)

        logger.debug(
            f"Deduplicated {len(chunk_ids)} chunk IDs to "
            f"{len(parent_ids)} unique parent candidates"
        )

        return parent_ids

    def _metadata_matches(self, metadata: Dict[str, Any], flt: Dict[str, Any]) -> bool:
        """Recursively evaluate a filter dictionary against a single metadata dict."""
        import re

        if "$and" in flt:
            return all(self._metadata_matches(metadata, sub) for sub in flt["$and"])
        if "$or" in flt:
            return any(self._metadata_matches(metadata, sub) for sub in flt["$or"])

        # leaf-level conditions
        for field, cond in flt.items():
            value = metadata.get(field)
            if isinstance(cond, dict):
                for op, op_val in cond.items():
                    if op == "$contains":
                        if value is None or op_val.lower() not in str(value).lower():
                            return False
                    elif op == "$regex":
                        if value is None or not re.search(
                            op_val, str(value), re.IGNORECASE
                        ):
                            return False
                    elif op == "$gte":
                        if value is None or not (float(value) >= float(op_val)):
                            return False
                    elif op == "$lte":
                        if value is None or not (float(value) <= float(op_val)):
                            return False
                    else:  # unsupported op treated as fail
                        return False
            else:
                # equality check (case-insensitive for strings)
                if isinstance(cond, str):
                    if str(value).lower() != cond.lower():
                        return False
                else:
                    if value != cond:
                        return False
        return True

    async def search_resumes_by_filters(
        self,
        session_id: str,
        filters: Dict[str, Any],
        limit: int = 50,
        include_demo: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve resumes using session-based collections for perfect user isolation.

        Args:
            session_id: User's session ID
            filters: Search filters to apply
            limit: Maximum number of results
            include_demo: Whether to include demo data when user has no uploads
        """
        try:
            # Step 1: Get user's session collection and check for uploads
            user_session_collection = await self.get_session_collection(session_id)

            # Check if user has any uploaded candidates
            user_results = await asyncio.to_thread(
                user_session_collection.get,
                include=["metadatas", "documents"],
                limit=100,  # Get all user uploads
            )

            all_results = {"ids": [], "metadatas": [], "documents": []}

            # Add user's results if any
            if user_results and user_results["ids"]:
                all_results["ids"].extend(user_results["ids"])
                all_results["metadatas"].extend(user_results["metadatas"])
                if user_results.get("documents"):
                    all_results["documents"].extend(user_results["documents"])
                else:
                    all_results["documents"].extend([None] * len(user_results["ids"]))
                logger.info(
                    f"Found {len(user_results['ids'])} user uploads for session {session_id}"
                )

            # Step 2: Include demo data if requested and user has no uploads
            if include_demo and (not user_results or not user_results["ids"]):
                try:
                    demo_collection = await self.get_session_collection("demo_static")
                    demo_results = await asyncio.to_thread(
                        demo_collection.get,
                        include=["metadatas", "documents"],
                        limit=50,  # Limit demo results
                    )

                    if demo_results and demo_results["ids"]:
                        all_results["ids"].extend(demo_results["ids"])
                        all_results["metadatas"].extend(demo_results["metadatas"])
                        if demo_results.get("documents"):
                            all_results["documents"].extend(demo_results["documents"])
                        else:
                            all_results["documents"].extend(
                                [None] * len(demo_results["ids"])
                            )
                        logger.info(
                            f"Including {len(demo_results['ids'])} demo candidates"
                        )
                except Exception as e:
                    logger.warning(f"Failed to load demo data: {e}")

            # Use the combined results for the rest of the processing
            results = all_results

            if not results or not results["ids"]:
                return []

            candidates = []
            seen_candidate_ids = set()  # Deduplication by candidate_id

            for idx, vector_id in enumerate(results["ids"]):
                metadata = results["metadatas"][idx]

                # Apply filter if provided
                if filters and not self._metadata_matches(metadata, filters):
                    continue

                # Get the candidate_id for deduplication
                candidate_id = metadata.get("candidate_id", vector_id)

                # Skip if we've already seen this candidate
                if candidate_id in seen_candidate_ids:
                    continue
                seen_candidate_ids.add(candidate_id)

                candidate = {
                    "id": candidate_id,
                    "name": metadata.get("name", "Unknown"),
                    "title": metadata.get("title", ""),
                    "skills": (
                        metadata.get("skills", "").split(",")
                        if metadata.get("skills")
                        else []
                    ),
                    "location": metadata.get("location", ""),
                    "experience_years": metadata.get("experience_years", 0),
                    "email": metadata.get("email"),
                    "phone": metadata.get("phone"),
                    "summary": metadata.get("summary"),
                    "visa_status": metadata.get("visa_status"),
                    "filename": metadata.get("filename"),
                    "relevance_score": 1.0,
                }
                doc_list = results.get("documents")
                if doc_list and idx < len(doc_list) and doc_list[idx]:
                    candidate["match_context"] = doc_list[idx][:200] + "..."
                candidates.append(candidate)
                if len(candidates) >= limit:
                    break
            return candidates
        except Exception as e:
            logger.error(f"Error filtering resumes: {e}", exc_info=True)
            return []

    async def get_all_unique_skills(self, session_id: str) -> List[str]:
        """
        Get all unique skills from uploaded resumes for a given session.

        Used to provide context for chat query parsing.
        """
        try:
            # Get session-specific collection
            session_collection = await self.get_session_collection(session_id)

            # Get all candidates from session collection (no complex where clause!)
            results = await asyncio.to_thread(
                session_collection.get,
                include=["metadatas"],  # We only need metadata to extract skills
            )

            all_skills = set()
            if results and results["metadatas"]:
                for metadata in results["metadatas"]:
                    skills_str = metadata.get("skills", "")
                    if skills_str and isinstance(skills_str, str):
                        skills = {s.strip() for s in skills_str.split(",") if s.strip()}
                        all_skills.update(skills)

            logger.info(
                f"Found {len(all_skills)} unique skills for session {session_id}."
            )
            return sorted(list(all_skills))

        except Exception as e:
            logger.error(
                f"Error getting unique skills for session {session_id}: {e}",
                exc_info=True,
            )
            return []

    # =============================================================================
    # Function Calling Methods for GPT-4o-mini
    # =============================================================================

    async def search_candidates_with_function_params(
        self,
        session_id: str,
        skills: Optional[List[str]] = None,
        title_keywords: Optional[List[str]] = None,
        name_keywords: Optional[List[str]] = None,
        min_experience: Optional[int] = None,
        max_experience: Optional[int] = None,
        location_keywords: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search candidates using structured function parameters from GPT-4o-mini.

        This method translates function call parameters into our existing filter format
        and delegates to search_resumes_by_filters.

        Args:
            session_id: User's session ID
            skills: Array of required skills
            title_keywords: Keywords that should appear in job titles
            name_keywords: Keywords that should appear in candidate names
            min_experience: Minimum years of experience
            max_experience: Maximum years of experience
            location_keywords: Location keywords to match
            limit: Maximum number of candidates to return

        Returns:
            List of candidate dictionaries matching the criteria
        """
        # Build filters from function parameters
        filters = {}
        filter_conditions = []

        # Skills filter (array contains any of the specified skills)
        if skills:
            skills_conditions = []
            for skill in skills:
                skills_conditions.append({"skills": {"$regex": f"(?i){skill}"}})
            filter_conditions.append({"$or": skills_conditions})

        # Title keywords filter
        if title_keywords:
            title_conditions = []
            for keyword in title_keywords:
                title_conditions.append({"title": {"$regex": f"(?i){keyword}"}})
            if len(title_conditions) == 1:
                filter_conditions.append(title_conditions[0])
            else:
                filter_conditions.append({"$and": title_conditions})

        # Name keywords filter
        if name_keywords:
            name_conditions = []
            for keyword in name_keywords:
                name_conditions.append({"name": {"$regex": f"(?i){keyword}"}})
            if len(name_conditions) == 1:
                filter_conditions.append(name_conditions[0])
            else:
                filter_conditions.append({"$and": name_conditions})

        # Experience range filters
        if min_experience is not None:
            filter_conditions.append({"experience_years": {"$gte": min_experience}})

        if max_experience is not None:
            filter_conditions.append({"experience_years": {"$lte": max_experience}})

        # Location filter
        if location_keywords:
            location_conditions = []
            for location in location_keywords:
                location_conditions.append({"location": {"$regex": f"(?i){location}"}})
            filter_conditions.append({"$or": location_conditions})

        # Combine all conditions with $and
        if filter_conditions:
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}

        logger.info(
            f"Function search with parameters: skills={skills}, title_keywords={title_keywords}, "
            f"name_keywords={name_keywords}, experience={min_experience}-{max_experience}, location={location_keywords}"
        )
        logger.debug(f"Generated filters: {filters}")

        # Use existing search method
        return await self.search_resumes_by_filters(
            session_id=session_id, filters=filters, limit=limit, include_demo=True
        )

    async def rank_candidates(
        self,
        session_id: str,
        candidate_ids: List[str],
        ranking_criteria: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank a set of candidates based on specific criteria.

        This method retrieves the specified candidates and applies custom ranking logic
        based on the provided criteria string.

        Args:
            session_id: User's session ID
            candidate_ids: List of candidate IDs to rank
            ranking_criteria: Natural language description of ranking criteria
            limit: Number of top candidates to return

        Returns:
            List of top-ranked candidates
        """
        if not candidate_ids:
            return []

        try:
            # First, retrieve all specified candidates
            all_candidates = []

            for candidate_id in candidate_ids:
                # Get candidates from ChromaDB by candidate_id
                collection = self.chroma_connector.get_collection()
                results = await asyncio.to_thread(
                    collection.get,
                    where={"candidate_id": candidate_id, "session_id": session_id},
                    include=["metadatas", "documents"],
                )

                if results and results["ids"]:
                    metadata = results["metadatas"][0]
                    candidate = {
                        "id": candidate_id,
                        "name": metadata.get("name", "Unknown"),
                        "title": metadata.get("title", ""),
                        "skills": (
                            metadata.get("skills", "").split(",")
                            if metadata.get("skills")
                            else []
                        ),
                        "location": metadata.get("location", ""),
                        "experience_years": metadata.get("experience_years", 0),
                        "email": metadata.get("email"),
                        "phone": metadata.get("phone"),
                        "summary": metadata.get("summary"),
                        "relevance_score": 1.0,
                    }
                    all_candidates.append(candidate)

            if not all_candidates:
                return []

            # Apply ranking logic based on criteria
            ranked_candidates = self._apply_ranking_criteria(
                all_candidates, ranking_criteria
            )

            # Return top N candidates
            return ranked_candidates[:limit]

        except Exception as e:
            logger.error(f"Error ranking candidates: {e}", exc_info=True)
            return []

    def _apply_ranking_criteria(
        self, candidates: List[Dict[str, Any]], criteria: str
    ) -> List[Dict[str, Any]]:
        """
        Apply ranking logic based on natural language criteria.

        This is a simplified ranking system for MVP. In production, this could
        use another LLM call or more sophisticated ranking algorithms.
        """
        criteria_lower = criteria.lower()

        # Simple keyword-based ranking for common criteria
        if "experience" in criteria_lower or "senior" in criteria_lower:
            # Rank by experience (descending)
            candidates.sort(key=lambda c: c.get("experience_years", 0), reverse=True)

        elif "aws" in criteria_lower:
            # Rank by AWS experience
            def has_aws(candidate):
                skills = candidate.get("skills", [])
                return any("aws" in skill.lower() for skill in skills)

            candidates.sort(key=has_aws, reverse=True)

        elif "python" in criteria_lower:
            # Rank by Python experience
            def has_python(candidate):
                skills = candidate.get("skills", [])
                return any("python" in skill.lower() for skill in skills)

            candidates.sort(key=has_python, reverse=True)

        elif "junior" in criteria_lower or "entry" in criteria_lower:
            # Rank by less experience (ascending)
            candidates.sort(key=lambda c: c.get("experience_years", 0))

        elif "leadership" in criteria_lower or "lead" in criteria_lower:
            # Rank by leadership indicators in title
            def has_leadership(candidate):
                title = candidate.get("title", "").lower()
                return any(
                    word in title
                    for word in ["lead", "senior", "principal", "director", "manager"]
                )

            candidates.sort(key=has_leadership, reverse=True)

        else:
            # Default: rank by experience
            candidates.sort(key=lambda c: c.get("experience_years", 0), reverse=True)

        logger.info(f"Ranked {len(candidates)} candidates by criteria: '{criteria}'")
        return candidates


# Dependency Injection for FastAPI
def get_rag_service() -> RAGService:
    """
    FastAPI dependency to create and return a RAGService instance.
    Initializes ChromaConnector and injects it into RAGService.
    """
    try:
        rag_service_instance = RAGService()
        return rag_service_instance

    except ChromaConfigError as e:
        logger.critical(
            f"Fatal: ChromaDB configuration error for RAGService: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG Service init failed: ChromaDB configuration error - {str(e)}",
        )
    except ChromaConnectionError as e:
        logger.critical(
            f"Fatal: ChromaDB connection error for RAGService: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG Service init failed: ChromaDB connection error - {str(e)}",
        )
    except RAGServiceError as e:
        logger.critical(f"Fatal: RAGService initialization error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize RAG Service: {str(e)}",
        )
    except Exception as e:
        logger.critical(
            f"Fatal: Unexpected error during RAGService setup: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error initializing RAG Service: {str(e)}",
        )
