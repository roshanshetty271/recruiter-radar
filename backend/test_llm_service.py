#!/usr/bin/env python3
"""
Test Script for LLM Service

This script tests the LLMService implementation with various scenarios:
1. Basic functionality tests
2. Configuration validation
3. Error handling
4. Input validation

Usage:
    python test_llm_service.py

Note: This script requires a valid OpenAI API key in your environment
or .env file for the full integration tests.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from app.services.llm_service import LLMService, LLMServiceError
    from app.core.config import settings
    from fastapi import HTTPException
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)


class TestLLMService:
    """Test suite for LLMService functionality."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test results."""
        self.total += 1
        if passed:
            self.passed += 1
            print(f"✅ {test_name}: PASSED {details}")
        else:
            self.failed += 1
            print(f"❌ {test_name}: FAILED {details}")

    async def test_service_initialization(self):
        """Test LLMService initialization with different configurations."""
        print("\n--- Testing Service Initialization ---")

        # Test 1: Default initialization (using settings)
        try:
            service = LLMService()
            has_client = hasattr(service, "client") and service.client is not None
            has_model = hasattr(service, "embedding_model") and service.embedding_model
            self.log_test(
                "Default initialization",
                has_client and has_model,
                f"(model: {service.embedding_model})",
            )
        except Exception as e:
            self.log_test("Default initialization", False, f"(error: {e})")

        # Test 2: Custom initialization
        try:
            custom_service = LLMService(
                api_key="test-key", embedding_model_name="text-embedding-3-small"
            )
            self.log_test(
                "Custom initialization",
                custom_service.embedding_model == "text-embedding-3-small",
                "(with custom parameters)",
            )
        except Exception as e:
            self.log_test("Custom initialization", False, f"(error: {e})")

        # Test 3: Initialization with missing API key
        try:
            LLMService(api_key="", embedding_model_name="test-model")
            self.log_test("Missing API key validation", False, "(should have failed)")
        except ValueError:
            self.log_test(
                "Missing API key validation", True, "(correctly rejected empty API key)"
            )
        except Exception as e:
            self.log_test(
                "Missing API key validation", False, f"(unexpected error: {e})"
            )

    async def test_input_validation(self):
        """Test input validation for the get_embedding method."""
        print("\n--- Testing Input Validation ---")

        try:
            service = LLMService(api_key="test-key", embedding_model_name="test-model")

            # Test empty string
            try:
                await service.get_embedding("")
                self.log_test("Empty string validation", False, "(should have failed)")
            except ValueError:
                self.log_test(
                    "Empty string validation", True, "(correctly rejected empty string)"
                )
            except Exception as e:
                self.log_test(
                    "Empty string validation", False, f"(unexpected error: {e})"
                )

            # Test whitespace-only string
            try:
                await service.get_embedding("   \n\t  ")
                self.log_test(
                    "Whitespace string validation", False, "(should have failed)"
                )
            except ValueError:
                self.log_test(
                    "Whitespace string validation",
                    True,
                    "(correctly rejected whitespace)",
                )
            except Exception as e:
                self.log_test(
                    "Whitespace string validation", False, f"(unexpected error: {e})"
                )

            # Test None input
            try:
                await service.get_embedding(None)
                self.log_test("None input validation", False, "(should have failed)")
            except (ValueError, TypeError):
                self.log_test(
                    "None input validation", True, "(correctly rejected None)"
                )
            except Exception as e:
                self.log_test(
                    "None input validation", False, f"(unexpected error: {e})"
                )

        except Exception as e:
            self.log_test("Input validation setup", False, f"(setup error: {e})")

    async def test_configuration_access(self):
        """Test that configuration is properly accessible."""
        print("\n--- Testing Configuration Access ---")

        # Test settings access
        try:
            has_openai_key = hasattr(settings, "openai_api_key")
            has_embedding_model = hasattr(settings, "embedding_model_name")

            self.log_test(
                "Settings configuration",
                has_openai_key and has_embedding_model,
                f"(API key configured: {bool(settings.openai_api_key)}, "
                f"Model: {getattr(settings, 'embedding_model_name', 'not set')})",
            )
        except Exception as e:
            self.log_test("Settings configuration", False, f"(error: {e})")

    async def test_embedding_generation(self):
        """Test actual embedding generation (requires valid API key)."""
        print("\n--- Testing Embedding Generation (Integration) ---")

        # Check if we have a valid API key
        if not settings.openai_api_key or settings.openai_api_key.startswith("your-"):
            self.log_test(
                "Integration test setup",
                False,
                "(no valid API key found - skipping integration tests)",
            )
            return

        try:
            service = LLMService()

            # Test basic embedding generation
            test_text = "This is a test sentence for embedding generation."
            embedding = await service.get_embedding(test_text)

            # Validate embedding properties
            is_list = isinstance(embedding, list)
            has_correct_length = len(embedding) in [
                1536,
                3072,
            ]  # Common OpenAI embedding dimensions
            all_floats = all(
                isinstance(x, (int, float)) for x in embedding[:10]
            )  # Check first 10

            self.log_test(
                "Basic embedding generation",
                is_list and has_correct_length and all_floats,
                f"(dimension: {len(embedding)}, type: {type(embedding).__name__})",
            )

            # Test with longer text
            long_text = "This is a longer test sentence. " * 20  # About 140 words
            long_embedding = await service.get_embedding(long_text)

            self.log_test(
                "Long text embedding",
                isinstance(long_embedding, list)
                and len(long_embedding) == len(embedding),
                f"(same dimension: {len(long_embedding)})",
            )

        except HTTPException as e:
            self.log_test(
                "Embedding generation",
                False,
                f"(HTTP error: {e.status_code} - {e.detail})",
            )
        except Exception as e:
            self.log_test("Embedding generation", False, f"(unexpected error: {e})")

    async def test_imports_and_exports(self):
        """Test that all necessary imports work correctly."""
        print("\n--- Testing Imports and Module Structure ---")

        # Test service import from package
        try:
            from app.services import LLMService as PackageLLMService

            self.log_test(
                "Package import",
                PackageLLMService is not None,
                "(LLMService imported from package)",
            )
        except ImportError as e:
            self.log_test("Package import", False, f"(import error: {e})")

        # Test direct module import
        try:
            from app.services.llm_service import LLMService as DirectLLMService

            self.log_test(
                "Direct module import",
                DirectLLMService is not None,
                "(LLMService imported directly)",
            )
        except ImportError as e:
            self.log_test("Direct module import", False, f"(import error: {e})")

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total tests: {self.total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {self.failed} test(s) failed")

        success_rate = (self.passed / self.total) * 100 if self.total > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")


async def main():
    """Run all tests."""
    print("🚀 Starting LLMService Test Suite")
    print("=" * 50)

    tester = TestLLMService()

    # Run all test categories
    await tester.test_imports_and_exports()
    await tester.test_configuration_access()
    await tester.test_service_initialization()
    await tester.test_input_validation()
    await tester.test_embedding_generation()

    # Print final summary
    tester.print_summary()

    # Exit with appropriate code
    sys.exit(0 if tester.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
