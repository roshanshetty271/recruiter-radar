#!/usr/bin/env python3

"""
Test Script for RAG Service

This script tests the RAGService implementation with various scenarios:
1. Service initialization and configuration validation
2. ChromaDB client and collection setup
3. Health check functionality
4. Placeholder method interfaces
5. Error handling scenarios

Usage:
    python test_rag_service.py

Note: This script requires a valid OpenAI API key in your environment
or .env file for the integration tests.
"""

import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the backend directory to the Python path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables early
from dotenv import load_dotenv

load_dotenv()

try:
    from app.services.rag_service import RAGService, RAGServiceError, get_rag_service
    from app.services.llm_service import LLMService
    from app.core.config import settings
    from app.models.candidate import CandidateProfile
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this script from the backend directory")
    print("and all dependencies are installed.")
    sys.exit(1)


class TestResults:
    """Track test results and provide summary."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_result(self, test_name: str, passed: bool, error_msg: str = None):
        self.total += 1
        if passed:
            self.passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed += 1
            self.errors.append(f"{test_name}: {error_msg}")
            print(f"❌ {test_name}: {error_msg}")

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"RAG SERVICE TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total tests: {self.total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")

        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")

        if self.failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"❌ {self.failed} test(s) failed")


def test_imports():
    """Test that all required modules can be imported."""
    try:
        # Test direct imports
        from app.services.rag_service import RAGService, RAGServiceError
        from app.services import RAGService as RAGServiceFromPackage

        # Test that imports are the same
        assert RAGService is RAGServiceFromPackage
        return True, None
    except Exception as e:
        return False, str(e)


def test_configuration_access():
    """Test that configuration settings are accessible."""
    try:
        # Test required settings with fallback for missing attributes
        required_settings = {
            "openai_api_key": getattr(settings, "openai_api_key", None),
            "embedding_model_name": getattr(settings, "embedding_model_name", None),
            "chroma_db_path": getattr(settings, "chroma_db_path", None),
            "chroma_collection_name": getattr(settings, "chroma_collection_name", None),
        }

        missing_settings = []
        for setting_name, setting_value in required_settings.items():
            if setting_value is None or (
                isinstance(setting_value, str) and not setting_value.strip()
            ):
                missing_settings.append(setting_name)

        if missing_settings:
            return (
                False,
                f"Missing configuration settings: {', '.join(missing_settings)}",
            )

        # Test path property if it exists
        if hasattr(settings, "chroma_db_full_path"):
            path = settings.chroma_db_full_path
            if not isinstance(path, Path):
                return False, "chroma_db_full_path should be a Path object"
        else:
            # Try to construct the path manually for testing
            try:
                test_path = Path("backend") / settings.chroma_db_path
                if not isinstance(test_path, Path):
                    return False, "Cannot construct chroma db path"
            except Exception as e:
                return False, f"Cannot construct chroma db path: {e}"

        return True, None
    except Exception as e:
        return False, str(e)


def test_rag_service_initialization_validation():
    """Test RAGService initialization with configuration validation."""
    try:
        # Check if we can patch the settings
        if not hasattr(settings, "openai_api_key"):
            return (
                False,
                "Settings object missing openai_api_key attribute - check .env file",
            )

        # Test with missing API key using proper attribute name
        original_key = settings.api_openai_api_key  # Access the actual field
        with patch.object(settings, "api_openai_api_key", ""):
            try:
                rag_service = RAGService()
                return False, "Should have failed with empty API key"
            except (ValueError, RAGServiceError) as e:
                if "openai_api_key" not in str(e).lower():
                    return False, f"Wrong error message: {e}"

        # Test with missing collection name
        if hasattr(settings, "chroma_collection_name"):
            original_collection = (
                settings.app_chroma_collection_name
            )  # Access the actual field
            with patch.object(settings, "app_chroma_collection_name", ""):
                try:
                    rag_service = RAGService()
                    return False, "Should have failed with empty collection name"
                except (ValueError, RAGServiceError) as e:
                    if "chroma_collection_name" not in str(e).lower():
                        return False, f"Wrong error message: {e}"

        return True, None
    except Exception as e:
        return False, str(e)


@patch("chromadb.PersistentClient")
@patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
def test_rag_service_mocked_initialization(mock_embedding_fn, mock_client):
    """Test RAGService initialization with mocked ChromaDB."""
    try:
        # Setup mocks properly
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0  # Return int, not MagicMock

        mock_chroma_instance = MagicMock()
        mock_chroma_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_chroma_instance

        # Create service
        rag_service = RAGService()

        # Verify mocks were called correctly
        mock_client.assert_called_once()
        mock_embedding_fn.assert_called_once()
        mock_chroma_instance.get_or_create_collection.assert_called_once()

        # Verify service state
        assert rag_service._chroma_client is not None
        assert rag_service.collection is not None

        return True, None
    except Exception as e:
        return False, str(e)


def test_health_check():
    """Test health check functionality."""
    try:
        # Test with mocked successful service
        with patch("chromadb.PersistentClient") as mock_client:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 42  # Return int, not MagicMock

            mock_chroma_instance = MagicMock()
            mock_chroma_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma_instance

            rag_service = RAGService()
            health = rag_service.health_check()

            # Verify health check response
            assert health["status"] == "healthy"
            assert health["document_count"] == 42
            assert "collection_name" in health
            assert "chroma_db_path" in health
            assert "embedding_model" in health

        return True, None
    except Exception as e:
        return False, str(e)


def test_placeholder_methods():
    """Test that placeholder methods exist and have correct signatures."""
    try:
        with patch("chromadb.PersistentClient") as mock_client:
            # Setup mock properly
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0

            mock_chroma_instance = MagicMock()
            mock_chroma_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma_instance

            rag_service = RAGService()

            # Test method existence and basic functionality
            methods_to_test = [
                (
                    "add_candidate_to_collection",
                    ["cand1", [1.0, 2.0], {"name": "Test"}],
                    True,  # is_async
                ),
                ("similarity_search", [[1.0, 2.0], 5], True),  # is_async
                ("get_candidate_details_by_id", ["cand1"], True),  # is_async
                ("batch_add_candidates", [[]], True),  # is_async
            ]

            for method_name, args, is_async in methods_to_test:
                method = getattr(rag_service, method_name)
                assert callable(method), f"{method_name} should be callable"

                # Test that methods can be called without errors
                if is_async:
                    # Don't actually call async methods in a sync context
                    # Just verify they are coroutine functions
                    assert asyncio.iscoroutinefunction(
                        method
                    ), f"{method_name} should be async"
                else:
                    result = method(*args)

                    # Verify placeholder methods return expected types
                    if method_name in ["add_candidate_to_collection"]:
                        assert isinstance(result, bool)
                    elif method_name in ["similarity_search", "batch_add_candidates"]:
                        assert isinstance(result, (list, dict))

        return True, None
    except Exception as e:
        return False, str(e)


def test_factory_function():
    """Test the get_rag_service factory function."""
    try:
        with patch("chromadb.PersistentClient") as mock_client:
            # Setup mock properly
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0

            mock_chroma_instance = MagicMock()
            mock_chroma_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma_instance

            # Test without LLM service
            rag_service1 = get_rag_service()
            assert isinstance(rag_service1, RAGService)
            assert rag_service1.llm_service is None

            # Test with LLM service (mocked)
            mock_llm_service = MagicMock()
            rag_service2 = get_rag_service(llm_service=mock_llm_service)
            assert isinstance(rag_service2, RAGService)
            assert rag_service2.llm_service is mock_llm_service

        return True, None
    except Exception as e:
        return False, str(e)


def test_reset_collection():
    """Test collection reset functionality."""
    try:
        with patch("chromadb.PersistentClient") as mock_client:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0

            mock_chroma_instance = MagicMock()
            mock_chroma_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma_instance

            rag_service = RAGService()

            # Test reset
            result = rag_service.reset_collection()
            assert result is True

            # Verify delete was called
            mock_chroma_instance.delete_collection.assert_called_once()

        return True, None
    except Exception as e:
        return False, str(e)


def test_integration_basic_initialization():
    """Integration test: Test actual ChromaDB initialization with default settings."""
    try:
        # For integration test, we'll use the real settings but test it carefully
        # This avoids complex patching issues while still testing real ChromaDB

        # First, ensure the default ChromaDB directory exists
        chroma_path = settings.chroma_db_full_path
        chroma_path.mkdir(parents=True, exist_ok=True)

        # Initialize the service with real ChromaDB
        rag_service = RAGService()

        # Verify service is initialized
        health = rag_service.health_check()
        assert health["status"] == "healthy"
        assert isinstance(health["document_count"], int)  # Should be a number

        # Verify the service has the expected attributes
        assert rag_service._chroma_client is not None
        assert rag_service.collection is not None

        # Test that we can call health check multiple times
        health2 = rag_service.health_check()
        assert health2["status"] == "healthy"

        return True, None
    except Exception as e:
        return False, str(e)


async def main():
    """Run all tests and display results."""
    print("🧪 Starting RAG Service Tests...")
    print(f"Backend directory: {backend_dir}")
    print(f"Settings loaded from: {settings.__class__.__module__}")

    # Check if .env file exists
    env_file = backend_dir / ".env"
    print(f".env file exists: {env_file.exists()}")

    # Show some configuration info (without secrets)
    print(
        f"Has openai_api_key: {hasattr(settings, 'openai_api_key') and bool(getattr(settings, 'openai_api_key', None))}"
    )
    print(
        f"Has embedding_model_name: {hasattr(settings, 'embedding_model_name') and bool(getattr(settings, 'embedding_model_name', None))}"
    )
    print()

    results = TestResults()

    # Define tests
    tests = [
        ("Import and Module Structure", test_imports),
        ("Configuration Access", test_configuration_access),
        (
            "Service Initialization Validation",
            test_rag_service_initialization_validation,
        ),
        ("Mocked Service Initialization", test_rag_service_mocked_initialization),
        ("Health Check Functionality", test_health_check),
        ("Placeholder Methods Interface", test_placeholder_methods),
        ("Factory Function", test_factory_function),
        ("Collection Reset", test_reset_collection),
        ("Integration - Basic Initialization", test_integration_basic_initialization),
    ]

    # Run tests
    for test_name, test_func in tests:
        try:
            passed, error_msg = test_func()
            results.add_result(test_name, passed, error_msg)
        except Exception as e:
            results.add_result(test_name, False, f"Test exception: {e}")

    # Print summary
    results.print_summary()

    return results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
