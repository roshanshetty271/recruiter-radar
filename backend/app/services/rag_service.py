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

# Removed direct chromadb imports, will come from connector or be internal to RAGService if needed
# from chromadb.utils import embedding_functions # No longer needed here
from fastapi import HTTPException, status  # Keep for get_rag_service DI function

from backend.app.core.config import settings  # For get_rag_service DI function
from backend.app.models.candidate import CandidateProfile  # For type hints if needed

# Import the new connector and its exceptions
from .chroma_connector import (
    ChromaConnector,
    ChromaConnectionError,
    ChromaConfigError,
    ChromaCollectionError,
)
from backend.app.services.rag_operations.search_logic import (
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
        Initialize the RAG service with a pre-configured ChromaConnector.

        Args:
            settings_obj: The application settings object (can be used for RAG-specific settings if any).
            connector: An initialized instance of ChromaConnector.

        Raises:
            RAGServiceError: If the provided connector is invalid or collection access fails.
        """
        self.settings = settings_obj
        self.connector = connector
        try:
            logger.info("Initializing ChromaConnector for RAGService...")
            self.collection = self.connector.get_collection()
            if not self.collection:
                # This case should ideally be caught by connector.get_collection() raising an error
                raise ChromaConnectionError(
                    "ChromaConnector returned None for collection."
                )
            self.collection_name = self.collection.name
            logger.info(
                f"RAGService initialized successfully using ChromaConnector for collection '{self.collection_name}'."
            )
        except ChromaConnectionError as e:
            logger.error(
                f"Failed to initialize RAGService: Error obtaining collection from ChromaConnector: {e}",
                exc_info=True,
            )
            raise RAGServiceError(
                f"RAGService initialization failed: Connector error - {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error during RAGService initialization: {e}", exc_info=True
            )
            raise RAGServiceError(
                f"Unexpected error initializing RAGService: {e}"
            ) from e

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
            f"RAGService: Queueing add operation for candidate ID '{candidate_id}' to collection '{self.collection_name}' (via thread)."
        )
        try:
            await asyncio.to_thread(
                self.collection.add,
                ids=[candidate_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document_text] if document_text is not None else None,
            )
            logger.info(
                f"RAGService: Successfully added/updated candidate ID '{candidate_id}' in collection '{self.collection_name}'."
            )
        except Exception as e:
            logger.error(
                f"RAGService: Threaded add failed for candidate ID '{candidate_id}' to collection '{self.collection_name}': {e}",
                exc_info=True,
            )
            raise DocumentStorageError(
                f"Failed to add/update candidate '{candidate_id}' in collection: {e}"
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
            f"RAGService: Preparing batch add for {len(candidates_data)} candidates to '{self.collection_name}'."
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
                f"RAGService: Queueing batch add operation for {len(ids)} candidates to '{self.collection_name}' (via thread)."
            )
            await asyncio.to_thread(
                self.collection.add,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=(
                    documents if any(d is not None for d in documents) else None
                ),
            )
            logger.info(
                f"RAGService: Successfully batch added {len(ids)} candidates to collection '{self.collection_name}'."
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
                f"Batch insertion into collection '{self.collection_name}' failed: {e}"
            ) from e

    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs similarity search by delegating to execute_similarity_search.
        Handles exceptions from the underlying operation.
        """
        if not self.collection:
            logger.error(
                "RAGService: Collection not initialized for similarity_search."
            )
            # This should ideally be caught during RAGService initialization
            raise SearchOperationError("Collection not initialized in RAGService.")

        logger.debug(
            f"RAGService: Delegating similarity search. Query embedding type: {type(query_embedding)}"
        )
        try:
            return await execute_similarity_search(
                collection=self.collection,
                query_embedding=query_embedding,
                k=k,
                filters=filters,
            )
        except OpsSearchOperationError as e:  # Catching error from search_logic
            logger.error(
                f"RAGService: Search operation failed in search_logic: {e}",
                exc_info=True,
            )
            # Re-raise as RAGService's own SearchOperationError or a more general one
            raise SearchOperationError(f"Search operation failed: {e}") from e
        except ValueError as e:  # Catch ValueError from execute_similarity_search
            logger.error(
                f"RAGService: Invalid value during similarity search: {e}",
                exc_info=True,
            )
            raise ValueError(f"Invalid value for search: {e}") from e  # Re-raise
        except Exception as e:
            logger.error(
                f"RAGService: Unexpected error during similarity_search delegation: {e}",
                exc_info=True,
            )
            raise RAGServiceError(f"Unexpected error during search: {e}") from e

    async def get_candidate_details_by_id(
        self, candidate_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Asynchronously retrieves a document and its metadata by ID from ChromaDB.
        Uses asyncio.to_thread for the synchronous ChromaDB `get` operation.

        Args:
            candidate_id: Unique identifier for the candidate.

        Returns:
            A dictionary containing the id, document, and metadata if found, else None.

        Raises:
            SearchOperationError: If the get operation fails.
        """
        if not candidate_id or not candidate_id.strip():
            logger.error(
                "Invalid candidate_id provided for get_candidate_details_by_id."
            )
            raise ValueError("candidate_id cannot be empty.")

        logger.debug(
            f"RAGService: Attempting to retrieve candidate ID '{candidate_id}' from '{self.collection_name}' (via thread)."
        )
        try:
            result = await asyncio.to_thread(
                self.collection.get,
                ids=[candidate_id],
                include=["metadatas", "documents"],
            )

            if result and result.get("ids") and result["ids"]:
                retrieved_data = {
                    "id": result["ids"][0],
                    "document": (
                        result["documents"][0]
                        if result.get("documents") and result["documents"]
                        else None
                    ),
                    "metadata": (
                        result["metadatas"][0]
                        if result.get("metadatas") and result["metadatas"]
                        else None
                    ),
                }
                logger.info(
                    f"RAGService: Successfully retrieved candidate ID '{candidate_id}'."
                )
                return retrieved_data
            else:
                logger.warning(
                    f"RAGService: Candidate ID '{candidate_id}' not found in collection '{self.collection_name}'."
                )
                return None
        except Exception as e:
            logger.error(
                f"RAGService: Threaded retrieval for ID '{candidate_id}' failed: {e}",
                exc_info=True,
            )
            raise SearchOperationError(
                f"Failed to retrieve candidate '{candidate_id}': {e}"
            ) from e

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
