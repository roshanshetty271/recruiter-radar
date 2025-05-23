"""
RAG (Retrieval-Augmented Generation) Service

This service manages the ChromaDB vector store integration for candidate profiles,
providing the foundation for semantic search functionality in RecruiterRadar MVP.

Key responsibilities:
- Initialize and manage persistent ChromaDB client and collection
- Provide interfaces for document storage and retrieval
- Handle embedding storage with proper metadata
- Support future RAG pipeline operations

The service integrates with:
- LLMService (BE-3) for embedding generation
- CandidateProfile models (BE-2) for data structure
- Configuration system (BE-1) for paths and settings
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.candidate import CandidateProfile

logger = logging.getLogger(__name__)


class RAGServiceError(Exception):
    """Custom exception for RAG service operations."""

    pass


class RAGService:
    """
    RAG Service for managing ChromaDB vector store operations.

    This service provides a clean interface for:
    - ChromaDB client and collection management
    - Document storage with embeddings and metadata
    - Similarity search operations
    - Integration with existing LLM and configuration systems

    The service is designed to be instantiated once and reused across
    the application, typically through FastAPI dependency injection.
    """

    def __init__(self, llm_service=None):
        """
        Initialize the RAG service with ChromaDB client and collection.

        Args:
            llm_service: Optional LLMService instance for embedding generation.
                        If None, embeddings must be provided externally.

        Raises:
            RAGServiceError: If ChromaDB initialization fails.
            ValueError: If configuration is invalid.
        """
        self.llm_service = llm_service
        self._chroma_client = None
        self.collection = None

        # Validate configuration
        self._validate_configuration()

        # Initialize ChromaDB client and collection
        try:
            self._initialize_client()
            self._initialize_collection()
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise RAGServiceError(f"RAG service initialization failed: {e}")

    def _validate_configuration(self) -> None:
        """Validate required configuration settings."""
        required_settings = [
            ("chroma_db_path", settings.chroma_db_path),
            ("chroma_collection_name", settings.chroma_collection_name),
            ("openai_api_key", settings.openai_api_key),
            ("embedding_model_name", settings.embedding_model_name),
        ]

        for setting_name, setting_value in required_settings:
            if not setting_value or (
                isinstance(setting_value, str) and not setting_value.strip()
            ):
                raise ValueError(
                    f"Configuration error: {setting_name} is required but not set"
                )

    def _initialize_client(self) -> None:
        """Initialize the persistent ChromaDB client."""
        try:
            # Ensure the ChromaDB directory exists
            chroma_path = Path(settings.chroma_db_full_path)
            chroma_path.mkdir(parents=True, exist_ok=True)

            # Initialize persistent client
            self._chroma_client = chromadb.PersistentClient(path=str(chroma_path))

            logger.info(f"ChromaDB client initialized at: {chroma_path}")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise RAGServiceError(f"ChromaDB client initialization failed: {e}")

    def _initialize_collection(self) -> None:
        """Initialize or get the ChromaDB collection with proper embedding function."""
        try:
            # Create OpenAI embedding function for collection configuration
            openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name=settings.embedding_model_name,
            )

            # Get or create collection with proper configuration
            self.collection = self._chroma_client.get_or_create_collection(
                name=settings.chroma_collection_name,
                embedding_function=openai_ef,
                metadata={
                    "hnsw:space": "cosine",  # Use cosine similarity
                    "description": "RecruiterRadar candidate profiles collection",
                    "created_by": "RAGService",
                    "version": "1.0",
                },
            )

            # Log collection status
            collection_count = self.collection.count()
            if collection_count > 0:
                logger.info(
                    f"Connected to existing collection '{settings.chroma_collection_name}' with {collection_count} documents"
                )
            else:
                logger.info(
                    f"Created new collection '{settings.chroma_collection_name}'"
                )

        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise RAGServiceError(f"Collection initialization failed: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the RAG service.

        Returns:
            Dict containing health status and service information.
        """
        try:
            # Check ChromaDB client
            if not self._chroma_client:
                return {
                    "status": "unhealthy",
                    "error": "ChromaDB client not initialized",
                }

            # Check collection
            if not self.collection:
                return {"status": "unhealthy", "error": "Collection not initialized"}

            # Get collection statistics
            collection_count = self.collection.count()

            return {
                "status": "healthy",
                "chroma_client": "connected",
                "collection_name": settings.chroma_collection_name,
                "document_count": collection_count,
                "chroma_db_path": str(settings.chroma_db_full_path),
                "embedding_model": settings.embedding_model_name,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    # ===============================================================================
    # PLACEHOLDER METHODS FOR FUTURE FEATURES
    # ===============================================================================

    async def add_candidate_to_collection(
        self,
        candidate_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        document_text: Optional[str] = None,
    ) -> bool:
        """
        Add a candidate profile to the ChromaDB collection.

        Args:
            candidate_id: Unique identifier for the candidate
            embedding: Pre-computed embedding vector from LLMService
            metadata: Candidate metadata (name, skills, visa_status, etc.)
            document_text: Optional raw text that was embedded

        Returns:
            bool: True if successfully added, False otherwise

        Raises:
            RAGServiceError: If collection is not initialized or other errors occur
        """
        if not self.collection:
            raise RAGServiceError("Collection not initialized")

        if not candidate_id or not candidate_id.strip():
            logger.error("Invalid candidate_id provided")
            return False

        if not embedding or len(embedding) == 0:
            logger.error(f"Invalid embedding provided for candidate {candidate_id}")
            return False

        try:
            logger.debug(f"Adding candidate {candidate_id} to collection")
            logger.debug(f"Embedding dimension: {len(embedding)}")
            logger.debug(f"Metadata: {metadata}")

            # Prepare data for ChromaDB
            ids = [candidate_id]
            embeddings = [embedding]
            metadatas = [metadata] if metadata else [{}]
            documents = [document_text] if document_text else None

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )

            logger.info(f"Successfully added candidate {candidate_id} to collection")
            return True

        except Exception as e:
            logger.error(f"Failed to add candidate {candidate_id} to collection: {e}")
            raise RAGServiceError(f"Failed to add candidate to collection: {e}")

    async def similarity_search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search against candidate profiles.

        This method will be implemented in BE-6/BE-7 (Search functionality).

        Args:
            query_embedding: Pre-computed query embedding from LLMService
            n_results: Number of top results to return
            where_filter: Optional metadata filter for refined search

        Returns:
            List of dictionaries containing candidate matches with scores

        Note:
            This is a placeholder for BE-6/BE-7 implementation.
        """
        logger.info(f"[PLACEHOLDER] Searching for {n_results} similar candidates")
        logger.debug(
            f"Query embedding dimension: {len(query_embedding) if query_embedding else 'None'}"
        )
        logger.debug(f"Applied filters: {where_filter}")

        # TODO: Implement in BE-6/BE-7
        # - Query ChromaDB collection with embedding
        # - Apply metadata filters if provided
        # - Format results for API response
        # - Handle errors and edge cases

        return []

    async def get_candidate_details_by_id(
        self, candidate_id: str
    ) -> Optional[CandidateProfile]:
        """
        Retrieve full candidate profile by ID.

        This method will be implemented when candidate data loading is built.

        Args:
            candidate_id: Unique identifier for the candidate

        Returns:
            CandidateProfile object if found, None otherwise

        Note:
            This is a placeholder for future implementation.
        """
        logger.info(f"[PLACEHOLDER] Getting details for candidate {candidate_id}")

        # TODO: Implement candidate data loading
        # - Load candidate data from static file or database
        # - Parse into CandidateProfile model
        # - Cache for performance if needed
        # - Handle missing candidates gracefully

        return None

    async def batch_add_candidates(
        self, candidates_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add multiple candidates to the collection in batch.

        Args:
            candidates_data: List of candidate data with embeddings and metadata
                Each item should have: {
                    'candidate_id': str,
                    'embedding': List[float],
                    'metadata': Dict[str, Any],
                    'document_text': Optional[str]
                }

        Returns:
            Dict with batch operation results and statistics

        Raises:
            RAGServiceError: If collection is not initialized
        """
        if not self.collection:
            raise RAGServiceError("Collection not initialized")

        if not candidates_data:
            logger.warning("No candidates provided for batch add")
            return {
                "total_candidates": 0,
                "successful": 0,
                "failed": 0,
                "errors": [],
            }

        logger.info(f"Batch adding {len(candidates_data)} candidates")

        successful = 0
        failed = 0
        errors = []

        # Prepare batch data
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for i, candidate_data in enumerate(candidates_data):
            try:
                candidate_id = candidate_data.get("candidate_id")
                embedding = candidate_data.get("embedding")
                metadata = candidate_data.get("metadata", {})
                document_text = candidate_data.get("document_text")

                # Validate required fields
                if not candidate_id or not embedding:
                    error_msg = f"Missing required fields for candidate at index {i}"
                    errors.append(error_msg)
                    failed += 1
                    continue

                ids.append(candidate_id)
                embeddings.append(embedding)
                metadatas.append(metadata)
                documents.append(document_text)

            except Exception as e:
                error_msg = f"Error preparing candidate at index {i}: {str(e)}"
                errors.append(error_msg)
                failed += 1
                logger.error(error_msg)

        # Attempt batch insertion if we have valid candidates
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents if any(documents) else None,
                )
                successful = len(ids)
                logger.info(f"Successfully batch added {successful} candidates")

            except Exception as e:
                # If batch fails, all candidates in this batch are marked as failed
                error_msg = f"Batch insertion failed: {str(e)}"
                errors.append(error_msg)
                failed += len(ids)
                successful = 0
                logger.error(error_msg)

        return {
            "total_candidates": len(candidates_data),
            "successful": successful,
            "failed": failed,
            "errors": errors,
        }

    def reset_collection(self) -> bool:
        """
        Reset the collection by deleting all documents.

        This method provides a way to clear the collection for testing
        or data refresh scenarios.

        Returns:
            bool: True if successful, False otherwise

        Warning:
            This will delete all stored candidate data!
        """
        try:
            if not self.collection:
                logger.warning("Cannot reset collection: not initialized")
                return False

            # Delete the collection and recreate it
            self._chroma_client.delete_collection(settings.chroma_collection_name)
            self._initialize_collection()

            logger.warning("Collection reset successfully - all data deleted!")
            return True

        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False


# Convenience function for dependency injection
def get_rag_service(llm_service=None) -> RAGService:
    """
    Factory function for creating RAGService instances.

    This function can be used with FastAPI's dependency injection system.

    Args:
        llm_service: Optional LLMService instance

    Returns:
        RAGService: Configured RAG service instance
    """
    return RAGService(llm_service=llm_service)
