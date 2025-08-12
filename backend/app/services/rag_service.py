"""
RAG (Retrieval-Augmented Generation) Service

This service manages higher-level RAG operations, utilizing ChromaDB for
vector storage and retrieval of candidate profiles.

Key responsibilities:
- Interfacing with ChromaConnector for DB client and collection access.
- Providing asynchronous interfaces for document storage and retrieval.
- Formatting data for storage and search results.
- Supporting intelligent query enhancement and semantic search.
- Integrating with QueryEnhancementService for natural language understanding.
"""

import logging
import asyncio  # Added for asyncio.to_thread
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import hashlib
import time

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

# 🧠 NEW: Import intelligent search services
from app.services.query_enhancement_service import (
    QueryEnhancementService,
    QueryEnhancementError,
)
from app.services.skills_taxonomy_service import (
    SkillsTaxonomyService,
    SkillsTaxonomyError,
)
from app.models.query_models import QueryIntent, QueryEnhancementResult

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

        # 🚀 NEW: Embedding cache for performance optimization
        self._embedding_cache: Dict[str, Tuple[List[float], float]] = (
            {}
        )  # query_hash -> (embedding, timestamp)
        self._cache_max_size = 100  # Limit cache size
        self._cache_ttl_seconds = 3600  # 1 hour TTL for embeddings

        # 🧠 NEW: Initialize intelligent search services
        try:
            self.query_enhancement_service = QueryEnhancementService()
            self.skills_taxonomy_service = SkillsTaxonomyService()
            self._intelligent_search_enabled = True
            self.logger.info("✅ Intelligent search services initialized successfully")
        except (QueryEnhancementError, SkillsTaxonomyError) as e:
            self.logger.error(
                f"❌ Failed to initialize intelligent search services: {e}"
            )
            self.query_enhancement_service = None
            self.skills_taxonomy_service = None
            self._intelligent_search_enabled = False
            self.logger.warning("⚠️ Falling back to basic search functionality")

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
        k: int,
        filters: Optional[Dict[str, Any]] = None,
        required_skills: Optional[List[str]] = None,
        preferred_skills: Optional[List[str]] = None,
        query_intent: Optional[QueryIntent] = None,  # 🚀 NEW: Accept pre-parsed intent
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Performs a similarity search against the ChromaDB collection.

        Uses intelligent query enhancement when available, otherwise falls back
        to the basic search logic.

        Args:
            query_embedding: The embedding vector of the search query.
            query_text: The original query string (for logging and context).
            k: The number of top results to return after all filtering.
            filters: Optional dictionary of metadata filters to apply.
            required_skills: DEPRECATED - Use query_text for intelligent parsing
            preferred_skills: DEPRECATED - Use query_text for intelligent parsing
            query_intent: 🚀 NEW - Pre-parsed query intent to avoid redundant AI calls

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

        # 🧠 Use intelligent search if available
        if (
            self._intelligent_search_enabled
            and self.query_enhancement_service
            and self.skills_taxonomy_service
        ):
            return await self._intelligent_similarity_search(
                query_embedding=query_embedding,
                query_text=query_text,
                k=k,
                filters=filters,
                query_intent=query_intent,  # 🚀 NEW: Pass pre-parsed intent
            )
        else:
            # Fallback to legacy search with warning
            if required_skills or preferred_skills:
                logger.warning(
                    "⚠️ Using deprecated skills parameters - intelligent search not available. "
                    "Query text should contain skill requirements for best results."
                )

            return await self._legacy_similarity_search(
                query_embedding=query_embedding,
                query_text=query_text,
                k=k,
                filters=filters,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
            )

    async def _intelligent_similarity_search(
        self,
        query_embedding: List[float],
        query_text: str,
        k: int,
        filters: Optional[Dict[str, Any]] = None,
        query_intent: Optional[QueryIntent] = None,  # 🚀 NEW: Accept pre-parsed intent
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        🚀 OPTIMIZED INTELLIGENT SIMILARITY SEARCH (No redundant AI calls!)

        This method:
        1. Uses pre-parsed query intent (if provided) OR parses query using LLM
        2. Performs semantic search with ChromaDB
        3. Applies intelligent skills filtering
        4. Returns properly filtered candidates
        """
        logger.info(f"🧠 Starting intelligent similarity search for: '{query_text}'")
        search_start_time = time.time()

        try:
            # Step 1: Use pre-parsed intent OR parse query intent using LLM
            if query_intent:
                # 🚀 OPTIMIZED: Use already-parsed intent (no redundant AI call!)
                logger.info("⚡ Step 1: Using pre-parsed query intent (FAST PATH)")
                logger.info(
                    f"✅ Using cached intent - Role: {query_intent.role_type}, "
                    f"Skills: {len(query_intent.required_skills)} required, "
                    f"{len(query_intent.preferred_skills)} preferred, "
                    f"Confidence: {query_intent.confidence_score:.2f}"
                )
            else:
                # 🐌 FALLBACK: Parse query intent using LLM (only if not provided)
                logger.info("🔍 Step 1: Parsing query intent (fallback path)...")
                enhancement_result = await self.query_enhancement_service.enhance_query(
                    query_text
                )
                query_intent = enhancement_result.query_intent

                logger.info(
                    f"✅ Query parsed - Role: {query_intent.role_type}, "
                    f"Skills: {len(query_intent.required_skills)} required, "
                    f"{len(query_intent.preferred_skills)} preferred, "
                    f"Confidence: {query_intent.confidence_score:.2f}"
                )

            # Step 2: Perform basic semantic search with ChromaDB
            logger.info("🔍 Step 2: Performing semantic search...")

            # Use legacy search logic for ChromaDB retrieval (no skills filtering yet)
            enhanced_filters = filters.copy() if filters else {}

            results, count_before_skills_filter = await execute_similarity_search(
                collection=self.collection,
                query_embedding=query_embedding,
                query_text=query_text,
                k=k * 3,  # Get more results for better filtering
                filters=enhanced_filters,
            )

            logger.info(
                f"📊 ChromaDB returned {len(results)} candidates for intelligent filtering"
            )

            # Step 3: Apply intelligent skills filtering - ALWAYS TRY TO FILTER
            if results and query_intent:
                logger.info("🔍 Step 3: Applying intelligent skills filtering...")

                # Import here to avoid circular imports
                from app.services.search_utils import apply_intelligent_skills_filter

                filtered_results = await apply_intelligent_skills_filter(
                    candidates=results,
                    query_intent=query_intent,
                    skills_taxonomy_service=self.skills_taxonomy_service,
                    strict_filtering=True,
                    min_skill_match_score=0.6,
                )

                logger.info(
                    f"📊 Intelligent filtering: {len(filtered_results)}/{len(results)} candidates passed skills filter"
                )

                # If filtering removed too many candidates, log the issue
                if len(filtered_results) == 0 and len(results) > 0:
                    logger.warning(
                        f"⚠️ Skills filter removed ALL candidates! Query: '{query_text}'"
                    )
                    # For now, keep some results rather than showing none
                    filtered_results = results[:5]
                    logger.info(f"🔄 Fallback: Showing top 5 semantic matches instead")
            else:
                filtered_results = results
                logger.info(
                    "🔍 Step 3: No query intent or results - returning all semantic matches"
                )

            # Step 4: Apply final result sorting (by relevance desc, then distance asc) and limiting
            def _final_sort_key(item: Dict[str, Any]):
                try:
                    if (
                        "relevance_score" in item
                        and item.get("relevance_score") is not None
                    ):
                        return (
                            -float(item.get("relevance_score", 0.0)),
                            float(item.get("distance", 1.0)),
                        )
                    # Fallback: sort by distance ascending if relevance not present
                    return (0.0, float(item.get("distance", 1.0)))
                except Exception:
                    return (0.0, 1.0)

            sorted_results = sorted(filtered_results, key=_final_sort_key)
            final_results = sorted_results[:k]

            # Step 5: Enhanced logging
            search_time = (time.time() - search_start_time) * 1000
            logger.info(
                f"🎯 Intelligent search completed in {search_time:.1f}ms: "
                f"{len(final_results)} final candidates"
            )

            # 📊 Log TOP-10 FINAL results (post-filter)
            try:
                # Sort by relevance score if present, else by distance ascending
                def _final_sort_key(item):
                    if "relevance_score" in item:
                        # Higher relevance is better
                        return (
                            -float(item.get("relevance_score", 0.0)),
                            float(item.get("distance", 1.0)),
                        )
                    return (0.0, float(item.get("distance", 1.0)))

                top_final = sorted(final_results, key=_final_sort_key)[:10]
                logger.info("📊 FINAL TOP (post-filter):")
                final_top_ids = []
                for rank, cand in enumerate(top_final, start=1):
                    meta = cand.get("metadata", {})
                    name = meta.get("name", "Unknown")
                    cid = meta.get("candidate_id") or meta.get("id") or "Unknown"
                    dist = cand.get("distance", 1.0)
                    rel = cand.get("relevance_score")
                    expl = cand.get("match_explanation", "-")
                    if rel is not None:
                        logger.info(
                            f"   {rank:>2}. {name} | id={cid} | rel={float(rel):.3f} | dist={float(dist):.3f} | {expl}"
                        )
                    else:
                        logger.info(
                            f"   {rank:>2}. {name} | id={cid} | dist={float(dist):.3f} | {expl}"
                        )
                    final_top_ids.append(str(cid))
                if final_top_ids:
                    logger.info(f"📦 FINAL_TOP_IDS: {', '.join(final_top_ids)}")
            except Exception as e:
                logger.warning(f"Failed to log FINAL TOP results: {e}")

            if final_results:
                top_result = final_results[0]
                metadata = top_result.get("metadata", {})
                relevance = 1.0 - float(top_result.get("distance", 1.0))
                match_explanation = top_result.get(
                    "match_explanation", "No explanation"
                )
                logger.info(
                    f"   Top match: {metadata.get('name', 'Unknown')} "
                    f"(relevance: {relevance:.3f}) - {match_explanation}"
                )

            return final_results, count_before_skills_filter

        except Exception as e:
            logger.error(f"❌ Intelligent search failed: {e}", exc_info=True)
            # Fallback to legacy search
            logger.info("🔄 Falling back to legacy search...")
            return await self._legacy_similarity_search(
                query_embedding=query_embedding,
                query_text=query_text,
                k=k,
                filters=filters,
                required_skills=None,
                preferred_skills=None,
            )

    async def _legacy_similarity_search(
        self,
        query_embedding: List[float],
        query_text: str,
        k: int,
        filters: Optional[Dict[str, Any]] = None,
        required_skills: Optional[List[str]] = None,
        preferred_skills: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        🔄 LEGACY SIMILARITY SEARCH (original implementation)

        This is the original search logic kept for backward compatibility
        and as a fallback when intelligent search fails.
        """
        logger.debug(
            f"RAGService: Initiating legacy similarity search in collection '{self.collection_name}' with k={k}, filters={filters is not None}."
        )
        try:
            # Add skills to filters for post-filtering
            enhanced_filters = filters.copy() if filters else {}
            if required_skills:
                enhanced_filters["skills_query"] = required_skills
                logger.info(f"🔍 RAG: Added skills to filters: {required_skills}")
            else:
                logger.info(f"🔍 RAG: No required_skills provided")

            logger.info(f"🔍 RAG: Enhanced filters: {enhanced_filters}")

            # execute_similarity_search is already async
            results, count_before_post_filter = await execute_similarity_search(
                collection=self.collection,
                query_embedding=query_embedding,
                query_text=query_text,
                k=k,
                filters=enhanced_filters,
            )

            # 🔍 CONCISE SEARCH RESULTS LOGGING
            logger.info(f"🔍 Legacy search completed: {len(results)} candidates found")
            if results:
                top_result = results[0]
                metadata = top_result.get("metadata", {})
                relevance = 1.0 - float(top_result.get("distance", 1.0))
                logger.info(
                    f"   Top: {metadata.get('name', 'Unknown')} (relevance: {relevance:.3f})"
                )

            logger.info(
                f"RAGService: Legacy similarity search completed. Candidates found (after post-filter, limited by k): {len(results)}. Candidates before post-filter: {count_before_post_filter}."
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
        load_start_time = time.time()

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

            # Check file size and modification time for monitoring
            file_stat = candidates_path.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            logger.info(
                f"Loading candidates from: {candidates_path} ({file_size_mb:.2f} MB)"
            )

            with open(candidates_path, "r", encoding="utf-8") as f:
                candidates_data = json.load(f)

            # Validate and cache each candidate
            self._candidates_cache: Dict[str, CandidateProfile] = (
                {}
            )  # Initialize with type hint
            load_errors = []
            validation_warnings = []

            for idx, candidate_dict in enumerate(candidates_data):
                try:
                    candidate = CandidateProfile.model_validate(candidate_dict)
                    self._candidates_cache[candidate.id] = candidate

                    # Basic validation checks
                    if not candidate.name or candidate.name.strip() == "":
                        validation_warnings.append(
                            f"Candidate {candidate.id} has empty name"
                        )
                    if not candidate.skills or len(candidate.skills) == 0:
                        validation_warnings.append(
                            f"Candidate {candidate.id} has no skills"
                        )
                    if candidate.experience_years < 0:
                        validation_warnings.append(
                            f"Candidate {candidate.id} has negative experience"
                        )

                except Exception as e:
                    load_errors.append(
                        f"Index {idx}, ID '{candidate_dict.get('id', 'N/A')}': {str(e)}"
                    )
                    logger.error(
                        f"Failed to load/validate candidate at index {idx} (ID: '{candidate_dict.get('id', 'N/A')}'): {e}"
                    )

            load_time = time.time() - load_start_time
            cache_size = len(self._candidates_cache)

            logger.info(
                f"Successfully loaded {cache_size} out of {len(candidates_data)} candidates into cache in {load_time:.2f}s."
            )

            # Set cache loaded flag for future checks
            self._cache_loaded = True

            # Log performance metrics
            logger.info(
                f"📊 Cache metrics: {cache_size} candidates, {file_size_mb:.2f}MB file, {load_time:.2f}s load time"
            )

            if load_errors:
                logger.warning(
                    f"Failed to load {len(load_errors)} candidates due to validation/processing errors. Details: {load_errors[:3]}{'...' if len(load_errors) > 3 else ''}"
                )

            if validation_warnings:
                logger.warning(
                    f"Data quality issues found in {len(validation_warnings)} candidates. First few: {validation_warnings[:3]}{'...' if len(validation_warnings) > 3 else ''}"
                )

            # Additional cache health checks
            if cache_size == 0:
                logger.error(
                    "🚨 CRITICAL: Cache is empty after loading - this will cause performance issues!"
                )
                raise RAGServiceError("Candidate cache is empty after loading")
            elif cache_size < 5:
                logger.warning(
                    f"⚠️ Cache size ({cache_size}) is very small - expected more candidates for production"
                )
            elif cache_size > 1000:
                logger.info(
                    f"📈 Large cache size ({cache_size}) - consider performance optimization"
                )

        except FileNotFoundError as e:  # Specifically catch FileNotFoundError
            logger.error(f"Critical error loading candidates cache: {e}", exc_info=True)
            self._candidates_cache = {}  # Ensure cache is empty
            self._cache_loaded = False
            raise RAGServiceError(
                f"Failed to initialize candidate data cache - File Not Found: {e}"
            ) from e
        except json.JSONDecodeError as e:
            logger.error(
                f"Critical error loading candidates cache - JSON decode error: {e}",
                exc_info=True,
            )
            self._candidates_cache = {}  # Ensure cache is empty
            self._cache_loaded = False
            raise RAGServiceError(
                f"Failed to initialize candidate data cache - JSON Decode Error: {e}"
            ) from e
        except (
            Exception
        ) as e:  # Catch other RAGServiceError or Pydantic validation from model_validate if it bubbles up unexpectedly
            logger.error(f"Critical error loading candidates cache: {e}", exc_info=True)
            self._candidates_cache = {}  # Ensure cache is empty
            self._cache_loaded = False
            raise RAGServiceError(
                f"Failed to initialize candidate data cache: {e}"
            ) from e

    def _get_query_hash(self, query: str) -> str:
        """
        🔑 Generate a hash for the query to use as cache key
        """
        return hashlib.md5(query.strip().lower().encode()).hexdigest()[:16]

    def _cleanup_expired_cache(self) -> None:
        """
        🧹 Remove expired entries from embedding cache
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._embedding_cache.items()
            if current_time - timestamp > self._cache_ttl_seconds
        ]

        for key in expired_keys:
            del self._embedding_cache[key]

        if expired_keys:
            logger.info(
                f"🧹 Cleaned up {len(expired_keys)} expired embedding cache entries"
            )

    def _evict_oldest_cache_entries(self) -> None:
        """
        📦 Evict oldest entries if cache is too large
        """
        if len(self._embedding_cache) <= self._cache_max_size:
            return

        # Sort by timestamp and remove oldest entries
        sorted_entries = sorted(
            self._embedding_cache.items(), key=lambda x: x[1][1]  # Sort by timestamp
        )

        num_to_remove = (
            len(self._embedding_cache) - self._cache_max_size + 10
        )  # Remove extra for buffer
        for key, _ in sorted_entries[:num_to_remove]:
            del self._embedding_cache[key]

        logger.info(f"📦 Evicted {num_to_remove} old embedding cache entries")

    async def get_cached_embedding(self, query: str) -> Optional[List[float]]:
        """
        🚀 Get cached embedding for query, return None if not found or expired
        """
        query_hash = self._get_query_hash(query)

        # Cleanup expired entries periodically
        if len(self._embedding_cache) > 50:  # Only cleanup when cache is getting large
            self._cleanup_expired_cache()

        if query_hash not in self._embedding_cache:
            return None

        embedding, timestamp = self._embedding_cache[query_hash]

        # Check if expired
        if time.time() - timestamp > self._cache_ttl_seconds:
            del self._embedding_cache[query_hash]
            return None

        logger.info("🎯 Cache HIT")
        return embedding

    async def cache_embedding(self, query: str, embedding: List[float]) -> None:
        """
        💾 Cache embedding for future use
        """
        query_hash = self._get_query_hash(query)
        current_time = time.time()

        # Evict old entries if needed
        self._evict_oldest_cache_entries()

        self._embedding_cache[query_hash] = (embedding, current_time)
        logger.info(f"💾 Embedding cached (size: {len(self._embedding_cache)})")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        📊 Get comprehensive cache statistics including candidate and embedding caches
        """
        current_time = time.time()

        # Embedding cache stats
        active_embedding_entries = sum(
            1
            for _, timestamp in self._embedding_cache.values()
            if current_time - timestamp <= self._cache_ttl_seconds
        )

        # Candidate cache stats
        candidate_cache_size = (
            len(self._candidates_cache) if hasattr(self, "_candidates_cache") else 0
        )
        candidate_cache_loaded = getattr(self, "_cache_loaded", False)

        # Calculate cache quality metrics
        quality_score = 0.0
        if candidate_cache_size > 0:
            valid_candidates = sum(
                1
                for candidate in self._candidates_cache.values()
                if candidate.name
                and candidate.name.strip()
                and len(candidate.skills) > 0
            )
            quality_score = valid_candidates / candidate_cache_size

        return {
            # Embedding cache metrics
            "embedding_cache": {
                "total_entries": len(self._embedding_cache),
                "active_entries": active_embedding_entries,
                "expired_entries": len(self._embedding_cache)
                - active_embedding_entries,
                "max_size": self._cache_max_size,
                "ttl_seconds": self._cache_ttl_seconds,
                "hit_rate": getattr(self, "_cache_hits", 0)
                / max(getattr(self, "_cache_attempts", 1), 1),
            },
            # Candidate cache metrics
            "candidate_cache": {
                "total_candidates": candidate_cache_size,
                "cache_loaded": candidate_cache_loaded,
                "quality_score": round(quality_score, 3),
                "status": (
                    "healthy"
                    if candidate_cache_size > 10 and quality_score > 0.8
                    else "warning" if candidate_cache_size > 0 else "critical"
                ),
            },
            # Overall health
            "overall_health": (
                "healthy"
                if candidate_cache_loaded and candidate_cache_size > 10
                else "degraded"
            ),
        }

    async def refresh_candidate_cache(self) -> Dict[str, Any]:
        """
        🔄 Refresh the candidate cache and return refresh results
        """
        logger.info("🔄 Refreshing candidate cache...")
        old_cache_size = (
            len(self._candidates_cache) if hasattr(self, "_candidates_cache") else 0
        )

        try:
            await self._load_candidates_cache()
            new_cache_size = len(self._candidates_cache)

            refresh_result = {
                "success": True,
                "old_size": old_cache_size,
                "new_size": new_cache_size,
                "improvement": new_cache_size - old_cache_size,
                "message": f"Cache refreshed: {old_cache_size} → {new_cache_size} candidates",
            }

            logger.info(f"✅ {refresh_result['message']}")
            return refresh_result

        except Exception as e:
            logger.error(f"❌ Cache refresh failed: {e}")
            return {
                "success": False,
                "old_size": old_cache_size,
                "new_size": (
                    len(self._candidates_cache)
                    if hasattr(self, "_candidates_cache")
                    else 0
                ),
                "error": str(e),
                "message": f"Cache refresh failed: {str(e)}",
            }

    def is_cache_healthy(self) -> bool:
        """
        🏥 Check if the candidate cache is in a healthy state
        """
        if not hasattr(self, "_candidates_cache") or not self._candidates_cache:
            return False

        if not getattr(self, "_cache_loaded", False):
            return False

        cache_size = len(self._candidates_cache)
        if cache_size < 5:  # Minimum viable cache size
            return False

        # Check data quality
        valid_candidates = sum(
            1
            for candidate in self._candidates_cache.values()
            if candidate.name and candidate.name.strip() and len(candidate.skills) > 0
        )

        quality_ratio = valid_candidates / cache_size
        return quality_ratio > 0.8  # At least 80% of candidates should have valid data

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

        # Check cache health and refresh if needed
        if not self.is_cache_healthy():
            logger.warning("🚨 Cache is unhealthy, attempting refresh...")
            try:
                refresh_result = await self.refresh_candidate_cache()
                if refresh_result["success"]:
                    logger.info(
                        f"✅ Cache refreshed successfully: {refresh_result['message']}"
                    )
                else:
                    logger.error(
                        f"❌ Cache refresh failed: {refresh_result['message']}"
                    )
            except Exception as e:
                logger.error(f"💥 Cache refresh attempt failed: {e}")

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
            cache_size = len(self._candidates_cache)
            logger.warning(
                f"Candidate ID '{cleaned_candidate_id}' not found in cache of {cache_size} candidates."
            )

            # If cache seems too small, suggest refresh
            if cache_size < 10:
                logger.info(
                    "💡 Cache size is very small - consider refreshing the cache"
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
            # Handle empty email strings by converting to None for EmailStr validation
            email_value = metadata.get("email")
            if email_value == "":
                email_value = None

            candidate_data = {
                "id": metadata.get("candidate_id", candidate_id),
                "name": metadata.get("name"),
                "email": email_value,
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
