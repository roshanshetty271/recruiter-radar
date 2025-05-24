"""
ChromaDB Connector Module

This module provides a dedicated connector class for initializing and managing
the ChromaDB client and collection. It centralizes ChromaDB-specific setup,
configuration validation, and direct interaction logic, promoting separation
of concerns from the higher-level RAGService.
"""

import logging
from pathlib import Path
from typing import Any  # For settings object type hint

import chromadb
from chromadb.utils import embedding_functions

# from chromadb.api.models.Collection import Collection # For type hinting, if needed
# from chromadb.api import API # For type hinting client, if needed

logger = logging.getLogger(__name__)


class ChromaConnectionError(Exception):
    """Custom base exception for ChromaDB connection or setup errors."""

    pass


class ChromaConfigError(ChromaConnectionError):
    """Raised for configuration issues specific to ChromaDB setup."""

    pass


class ChromaCollectionError(ChromaConnectionError):
    """Raised for errors during collection management (get, create, delete)."""

    pass


class ChromaConnector:
    """
    Manages the connection and setup of a ChromaDB client and a specific collection.

    Responsibilities:
    - Validating ChromaDB-specific configurations from the settings object.
    - Initializing and holding the chromadb.PersistentClient instance.
    - Initializing (get_or_create) and holding the chromadb.Collection instance,
      configured with the appropriate embedding function.
    - Providing access to the client and collection.
    - Handling the recreation (delete and create) of the collection.
    """

    _REQUIRED_CONFIG_ATTRS = [
        "chroma_db_path",
        "chroma_collection_name",
        "openai_api_key",  # Needed for OpenAIEmbeddingFunction
        "embedding_model_name",  # Needed for OpenAIEmbeddingFunction
    ]

    def __init__(self, settings_obj: Any):
        """
        Initializes the ChromaConnector.

        Args:
            settings_obj: The application's global settings object which should have
                          attributes defined in _REQUIRED_CONFIG_ATTRS.

        Raises:
            ChromaConfigError: If essential ChromaDB configurations are missing or invalid.
            ChromaCollectionError: If client or collection initialization fails.
        """
        self.settings = settings_obj
        self._validate_configuration()

        self.collection_name: str = self.settings.chroma_collection_name
        self._client: chromadb.Client = self._initialize_client()
        self._collection: chromadb.Collection = self._initialize_collection_instance(
            self._client, self.collection_name
        )

        logger.info(
            f"ChromaConnector initialized for collection '{self.collection_name}'."
        )

    def _validate_configuration(self) -> None:
        """Validates that all required ChromaDB settings are present in the settings object."""
        logger.debug("Validating ChromaDB-specific configuration...")
        missing_attrs = []
        for attr_name in self._REQUIRED_CONFIG_ATTRS:
            setting_value = getattr(self.settings, attr_name, None)
            if not setting_value or (
                isinstance(setting_value, str) and not setting_value.strip()
            ):
                missing_attrs.append(attr_name)

        if missing_attrs:
            error_msg = (
                f"Missing/empty ChromaDB config in settings: {', '.join(missing_attrs)}"
            )
            logger.error(error_msg)
            raise ChromaConfigError(error_msg)
        logger.debug("ChromaDB configuration validated.")

    def _initialize_client(self) -> chromadb.Client:
        """Initializes and returns a persistent ChromaDB client."""
        chroma_path_str = self.settings.chroma_db_path
        logger.info(f"Initializing ChromaDB PersistentClient at: {chroma_path_str}")
        try:
            chroma_path = Path(chroma_path_str)
            chroma_path.parent.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(chroma_path))
            logger.info(
                f"ChromaDB PersistentClient initialized at '{chroma_path_str}'."
            )
            return client
        except Exception as e:
            error_msg = (
                f"Failed to initialize ChromaDB client at '{chroma_path_str}': {e}"
            )
            logger.error(error_msg, exc_info=True)
            raise ChromaConnectionError(error_msg) from e

    def _initialize_collection_instance(
        self, client: chromadb.Client, collection_name: str
    ) -> chromadb.Collection:
        """Gets or creates the specified collection using the provided client."""
        logger.info(f"Getting or creating ChromaDB collection: '{collection_name}'")
        try:
            openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.settings.openai_api_key,
                model_name=self.settings.embedding_model_name,
            )
            collection = client.get_or_create_collection(
                name=collection_name,
                embedding_function=openai_ef,
                metadata={
                    "hnsw:space": "cosine",
                    "description": "RecruiterRadar candidates",
                },
            )
            logger.info(
                f"ChromaDB collection '{collection_name}' (count: {collection.count()}) ready."
            )
            return collection
        except Exception as e:
            error_msg = (
                f"Failed to get/create ChromaDB collection '{collection_name}': {e}"
            )
            logger.error(error_msg, exc_info=True)
            raise ChromaCollectionError(error_msg) from e

    def get_client(self) -> chromadb.Client:
        """Returns the initialized ChromaDB client instance."""
        if not self._client:
            # This should not happen if __init__ completed successfully
            logger.error("ChromaDB client accessed before initialization.")
            raise ChromaConnectionError(
                "ChromaDB client not initialized. Call __init__ first."
            )
        return self._client

    def get_collection(self) -> chromadb.Collection:
        """Returns the initialized ChromaDB collection instance."""
        if not self._collection:
            # This should not happen if __init__ completed successfully
            logger.error("ChromaDB collection accessed before initialization.")
            raise ChromaConnectionError(
                "ChromaDB collection not initialized. Call __init__ first."
            )
        return self._collection

    def recreate_collection(self) -> chromadb.Collection:
        """
        Deletes the existing collection (if it exists) and creates a new one.
        This is a synchronous operation.

        Returns:
            The newly created (or re-created) chromadb.Collection instance.

        Raises:
            ChromaCollectionError: If any step in recreating the collection fails.
        """
        logger.warning(f"Recreating ChromaDB collection: '{self.collection_name}'")
        client = self.get_client()  # Ensures client is available
        try:
            # Attempt to delete if exists
            try:
                client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted existing collection: '{self.collection_name}'.")
            except Exception:  # Catch specific ChromaDB error if one for "not found"
                logger.info(
                    f"Collection '{self.collection_name}' did not exist or couldn't be deleted; proceeding to create."
                )

            # Re-initialize the collection (get_or_create_collection will create if not found)
            self._collection = self._initialize_collection_instance(
                client, self.collection_name
            )
            logger.info(f"Collection '{self.collection_name}' recreated successfully.")
            return self._collection
        except Exception as e:
            error_msg = f"Failed to recreate collection '{self.collection_name}': {e}"
            logger.error(error_msg, exc_info=True)
            raise ChromaCollectionError(error_msg) from e
