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

    def __init__(self, settings_obj: Any, connector: ChromaConnector):
        """
        Initialize the RAGService with the provided settings and ChromaDB connector.

        Args:
            settings_obj: Configuration object containing OPENAI_API_KEY, model names, ChromaDB settings, etc.
            connector: An initialized ChromaConnector instance.
        """
        self.settings = settings_obj
        self.connector = connector
        self.collection = connector.get_collection()  # Obtain collection via connector
        self.collection_name = connector.collection_name
        self.logger = logging.getLogger(__name__)
        # Use a dict keyed by candidate_id → CandidateProfile for O(1) look-ups.
        # An empty list (previous implementation) broke `.get()` calls and downstream fallbacks.
        self._candidates_cache: Dict[str, CandidateProfile] = {}
        self._cache_loaded = False

        self.logger.info(
            f"RAGService initialized with collection '{self.collection_name}'"
        )

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata for ChromaDB storage - remove None values and ensure proper types.

        ChromaDB only accepts str, int, float, bool values in metadata.
        Any None values will cause TypeErrors during storage.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Cleaned metadata dictionary safe for ChromaDB storage
        """
        sanitized = {}

        for key, value in metadata.items():
            if value is not None:
                # ChromaDB only accepts str, int, float, bool
                if isinstance(value, (list, dict)):
                    # Convert complex types to string
                    sanitized[key] = str(value) if value else ""
                elif isinstance(value, bool):
                    sanitized[key] = value
                elif isinstance(value, (int, float)):
                    sanitized[key] = value
                else:
                    # Everything else as string
                    sanitized[key] = str(value) if value else ""
            # Skip None values entirely - don't include them in metadata

        # Add source tracking if not present
        if "source" not in sanitized:
            sanitized["source"] = "demo"

        # Add upload timestamp for uploaded candidates
        if sanitized.get("source") == "uploaded_resume_batch":
            from datetime import datetime

            sanitized["uploaded_at"] = datetime.utcnow().isoformat()

        return sanitized

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the RAG service and its underlying ChromaDB connection.

        Returns:
            Dict containing health status and service information.
        """
        service_status = "healthy"
        details = {
            "rag_service_status": "initialized",
            "chroma_collection_name": self.collection_name,
            "chroma_db_path": str(Path(self.settings.chroma_db_path)),
            "embedding_model_name_for_collection": self.settings.embedding_model_name,
        }
        try:
            if not self.collection:
                service_status = "unhealthy"
                details["error"] = (
                    "ChromaDB collection object not available in RAGService."
                )
            else:
                count = await asyncio.to_thread(self.collection.count)
                details["chroma_document_count"] = count
                logger.debug(
                    f"RAGService health check: collection '{self.collection_name}' has {count} documents."
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

    async def add_candidate_to_collection(
        self,
        candidate_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        document_text: Optional[str] = None,
    ):
        """
        Asynchronously adds a single candidate profile to the ChromaDB collection with robust deduplication.
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

        # --- ROBUST DEDUPLICATION LOGIC ---
        # Normalize email and name for comparison
        email = (
            metadata.get("email", "").lower().strip() if metadata.get("email") else None
        )
        name = metadata.get("name", "").lower().strip() if metadata.get("name") else ""

        # Update metadata with normalized email
        if email:
            metadata["email"] = email

        existing_id = None

        # 1. Try email match (most reliable)
        if email:
            try:
                results = await asyncio.to_thread(
                    self.collection.get,
                    where={"email": email},
                    # IDs are returned by default, no need to include them
                )
                ids = results.get("ids", [])
                if ids and len(ids) > 0:
                    existing_id = ids[0]
                    logger.info(
                        f"🔍 DEDUP: Found existing candidate by email '{email}' -> ID: {existing_id}"
                    )
            except Exception as e:
                logger.warning(f"Email deduplication check failed for {email}: {e}")

        # 2. If no email match, try name-based deduplication (fallback)
        if not existing_id and name:
            try:
                # Get all candidates to check names (ChromaDB doesn't support case-insensitive search)
                all_candidates = await asyncio.to_thread(
                    self.collection.get,
                    limit=2000,  # Reasonable limit for MVP
                    include=["metadatas"],  # IDs are returned by default
                )

                for idx, cand_metadata in enumerate(
                    all_candidates.get("metadatas", [])
                ):
                    if not cand_metadata:
                        continue

                    cand_name = cand_metadata.get("name", "").lower().strip()
                    cand_email = (
                        cand_metadata.get("email", "").lower().strip()
                        if cand_metadata.get("email")
                        else None
                    )

                    # Check if same person by name and email combo
                    if email and cand_email == email:
                        # This should have been caught in email check, but safety net
                        existing_id = all_candidates["ids"][idx]
                        logger.info(
                            f"🔍 DEDUP: Found existing candidate by backup email check '{email}' -> ID: {existing_id}"
                        )
                        break
                    elif name and cand_name == name and not email and not cand_email:
                        # Only match by name if neither has email (avoid false positives)
                        existing_id = all_candidates["ids"][idx]
                        logger.info(
                            f"🔍 DEDUP: Found existing candidate by name '{name}' (no emails) -> ID: {existing_id}"
                        )
                        break

            except Exception as e:
                logger.warning(
                    f"Name-based deduplication check failed for '{name}': {e}"
                )

        # 3. Sanitize metadata before storage (CRITICAL FIX for ChromaDB None values)
        clean_metadata = self._sanitize_metadata(metadata)
        logger.info(
            f"🧹 Sanitized metadata for candidate {candidate_id}: source={clean_metadata.get('source')}"
        )

        # 4. Perform update or add operation
        try:
            if existing_id:
                # UPDATE existing candidate
                logger.info(
                    f"📝 UPDATING existing candidate {existing_id} instead of creating duplicate"
                )
                await asyncio.to_thread(
                    self.collection.update,
                    ids=[existing_id],
                    embeddings=[embedding],
                    metadatas=[clean_metadata],
                    documents=[document_text] if document_text is not None else None,
                )
                logger.info(
                    f"✅ RAGService: Successfully updated candidate ID '{existing_id}' in collection '{self.collection_name}'"
                )
            else:
                # ADD new candidate
                logger.info(f"➕ ADDING new candidate {candidate_id}")
                await asyncio.to_thread(
                    self.collection.add,
                    ids=[candidate_id],
                    embeddings=[embedding],
                    metadatas=[clean_metadata],
                    documents=[document_text] if document_text is not None else None,
                )
                logger.info(
                    f"✅ RAGService: Successfully added candidate ID '{candidate_id}' in collection '{self.collection_name}'"
                )
        except Exception as e:
            logger.error(
                f"❌ RAGService: Failed to add/update candidate ID '{candidate_id}' to collection '{self.collection_name}': {e}",
                exc_info=True,
            )
            raise DocumentStorageError(
                f"Failed to add/update candidate '{candidate_id}' in collection: {e}"
            ) from e

    async def batch_add_candidates(
        self, candidates_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Asynchronously adds multiple candidates to the collection, applying
        robust, individual deduplication logic for each.

        This method iterates through the provided candidate data and calls
        the `add_candidate_to_collection` method for each one, ensuring
        that the same email/name-based upsert logic is applied consistently.

        Args:
            candidates_data: A list of dictionaries, where each dictionary
                             contains the data for a single candidate, including
                             'candidate_id', 'embedding', 'metadata', and 'document_text'.

        Returns:
            A dictionary summarizing the batch operation, including counts of
            successful additions/updates and any failures.
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
            f"RAGService: Starting batch add for {len(candidates_data)} candidates, applying individual deduplication..."
        )

        tasks = []
        for i, data_item in enumerate(candidates_data):
            # Create a task for each candidate addition/update
            task = self.add_candidate_to_collection(
                candidate_id=data_item.get("candidate_id", f"missing_id_{i}"),
                embedding=data_item.get("embedding", []),
                metadata=data_item.get("metadata", {}),
                document_text=data_item.get("document_text"),
            )
            tasks.append(task)

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_count = 0
        failed_count = 0
        errors = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                error_msg = f"Failed to process candidate {i} (ID: {candidates_data[i].get('candidate_id', 'N/A')}): {str(result)}"
                logger.error(error_msg, exc_info=result)
                errors.append(error_msg)
            else:
                successful_count += 1

        logger.info(
            f"Batch processing complete. Successful: {successful_count}, Failed: {failed_count}"
        )

        return {
            "total_candidates": len(candidates_data),
            "successful": successful_count,
            "failed": failed_count,
            "errors": errors,
        }

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
        if not self.collection:
            logger.error(
                "RAGService.similarity_search: ChromaDB collection is not available."
            )
            raise RAGServiceError("ChromaDB collection not initialized or accessible.")

        logger.debug(
            f"RAGService: Initiating similarity search in collection '{self.collection_name}' with k={k}, filters={filters is not None}."
        )
        try:
            # execute_similarity_search is already async
            results, count_before_post_filter = await execute_similarity_search(
                collection=self.collection,
                query_embedding=query_embedding,
                query_text=query_text,
                k=k,
                filters=filters,
            )

            # 🔍 RAW SEARCH RESULTS LOGGING
            logger.info(f"🔍 RAW SEARCH RESULTS from ChromaDB (query: '{query_text}'):")
            logger.info(
                f"   📊 Found {len(results)} candidates (from {count_before_post_filter} before post-filtering)"
            )
            for i, result in enumerate(results, 1):
                metadata = result.get("metadata", {})
                distance = result.get("distance", 1.0)
                relevance = 1.0 - float(distance) if distance is not None else 0.0
                logger.info(
                    f"   {i:2d}. {metadata.get('name', 'Unknown')} (ID: {result.get('id', 'N/A')}) "
                    f"- Distance: {distance:.4f}, Relevance: {relevance:.3f}"
                )
                logger.info(f"       Skills: {metadata.get('skills', 'N/A')}")
                logger.info(
                    f"       Location: {metadata.get('location', 'N/A')} | Experience: {metadata.get('experience_years', 'N/A')} years"
                )
            logger.info("-" * 60)

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
                f"RAGService._load_candidates_cache: self.settings.candidate_data_full_path = {self.settings.candidate_data_full_path}"
            )
            candidates_path = Path(self.settings.candidate_data_full_path)

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

        # If, for any reason, the cache was corrupted into a non-dict structure, reload it once.
        if not isinstance(self._candidates_cache, dict):
            logger.warning(
                "_candidates_cache had unexpected type – reloading candidates JSON file."
            )
            await self._load_candidates_cache()

        # Retrieve candidate (dict lookup)
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

    async def get_candidate_from_chroma_by_id(
        self, candidate_id: str
    ) -> Optional[CandidateProfile]:
        """
        Fetch a single candidate's details directly from ChromaDB by their ID.

        Args:
            candidate_id: The unique ID of the candidate.

        Returns:
            A CandidateProfile object if found, otherwise None.

        Raises:
            RAGServiceError: If data from ChromaDB is inconsistent or a database error occurs.
        """
        try:
            logger.info(f"Querying ChromaDB for candidate_id: {candidate_id}")
            results = await asyncio.to_thread(
                self.collection.get,
                ids=[candidate_id],
                include=["metadatas", "documents"],
            )

            logger.debug(
                f"Raw ChromaDB results for {candidate_id}: {results}"
            )  # Added debug log

            if not results or not results.get("ids"):
                logger.warning(f"No results from ChromaDB for ID: {candidate_id}")
                return None

            # --- Data Consistency Check ---
            # ChromaDB should return parallel lists. If we got an ID, we must get metadata.
            metadatas = results.get("metadatas", [])
            ids = results.get("ids", [])
            if not metadatas or len(metadatas) != len(ids):
                error_msg = f"Inconsistent data from ChromaDB for ID '{candidate_id}': Found {len(ids)} IDs but {len(metadatas)} metadatas."
                logger.error(error_msg)
                return None  # Changed: Return None instead of raising

            # Assuming one result is returned for the given ID
            metadata = metadatas[0]
            # Use .get with a default for documents list for extra safety
            document = (
                results.get("documents", [""])[0] if results.get("documents") else ""
            )

            # Reconstruct the CandidateProfile object from ChromaDB data
            candidate_data = {
                "id": metadata.get("candidate_id", candidate_id),
                "name": metadata.get("name"),
                "email": metadata.get("email"),
                "location": metadata.get("location"),
                "experience_years": int(metadata.get("experience_years", 0)),
                "skills": (
                    metadata.get("skills", "").split(",")
                    if metadata.get("skills")
                    else []
                ),
                "raw_resume_text": document,
                "github_url": metadata.get("github_url"),
                "linkedin_url": metadata.get("linkedin_url"),
                "visa_status": metadata.get("visa_status"),
            }
            return CandidateProfile(**candidate_data)

        except Exception as e:
            logger.error(
                f"Unexpected error fetching candidate from ChromaDB by ID '{candidate_id}': {e}",
                exc_info=True,
            )
            raise RAGServiceError(
                f"A database error occurred while fetching candidate '{candidate_id}'."
            ) from e

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
            f"RAGService: Attempting to reset collection '{self.collection_name}' via ChromaConnector (in thread)."
        )
        try:
            new_collection_instance = await asyncio.to_thread(
                self.connector.recreate_collection
            )

            self.collection = new_collection_instance
            self.collection_name = self.collection.name

            logger.info(
                f"RAGService: Collection '{self.collection_name}' reset. RAGService now uses the new collection instance."
            )
        except ChromaCollectionError as e:
            logger.error(
                f"RAGService: Failed to reset collection '{self.collection_name}' due to ChromaConnector error: {e}",
                exc_info=True,
            )
            raise CollectionManagementError(
                f"Failed to reset collection '{self.collection_name}': Connector - {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"RAGService: Unexpected error during threaded collection reset: {e}",
                exc_info=True,
            )
            raise CollectionManagementError(
                f"Unexpected error resetting collection '{self.collection_name}': {e}"
            ) from e


# Dependency Injection for FastAPI
def get_rag_service() -> RAGService:
    """
    FastAPI dependency to create and return a RAGService instance.
    Initializes ChromaConnector and injects it into RAGService.
    """
    try:
        connector = ChromaConnector(settings_obj=settings)

        rag_service_instance = RAGService(settings_obj=settings, connector=connector)
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
