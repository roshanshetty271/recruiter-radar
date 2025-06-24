#!/usr/bin/env python3
"""
Simple test script for the new GPT-4o-mini conversational assistant.

This script tests the core functionality without requiring the full FastAPI setup.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.rag_service import get_rag_service
from app.services.session_service import SessionService
from app.models.upload_models import SessionData


class MockRAGService:
    """Mock RAG service for testing without ChromaDB."""

    async def search_candidates_with_function_params(self, **kwargs):
        # Return mock candidates
        return [
            {
                "id": "test_candidate_1",
                "name": "John Smith",
                "title": "Senior Python Developer",
                "skills": ["Python", "FastAPI", "AWS"],
                "location": "San Francisco, CA",
                "experience_years": 5,
                "email": "john@example.com",
                "relevance_score": 0.95,
            },
            {
                "id": "test_candidate_2",
                "name": "Sarah Chen",
                "title": "Full Stack Engineer",
                "skills": ["Python", "React", "Docker"],
                "location": "New York, NY",
                "experience_years": 3,
                "email": "sarah@example.com",
                "relevance_score": 0.87,
            },
        ]

    async def rank_candidates(self, **kwargs):
        # Return ranked mock candidates
        return [
            {
                "id": "test_candidate_1",
                "name": "John Smith",
                "title": "Senior Python Developer",
                "skills": ["Python", "FastAPI", "AWS"],
                "experience_years": 5,
                "relevance_score": 0.95,
            }
        ]


async def test_chat_functionality():
    """Test the conversational assistant functionality."""

    print("🚀 Testing GPT-4o-mini Conversational Assistant")
    print("=" * 50)

    # Check if OpenAI API key is set
    if not settings.openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in backend/.env file")
        return

    print(f"✅ OpenAI API key found (ends with: ...{settings.openai_api_key[-4:]})")
    print(f"✅ Using model: {settings.chat_model_name}")

    # Initialize services
    llm_service = LLMService(settings)
    rag_service = MockRAGService()
    session_service = SessionService()

    # Test session ID
    session_id = "test_session_123"

    print(f"✅ Services initialized")
    print()

    # Test conversation scenarios
    test_messages = [
        "Show me Python developers",
        "Who has the most experience?",
        "What about React developers?",
        "Compare John and Sarah",
    ]

    conversation_history = []

    for i, message in enumerate(test_messages, 1):
        print(f"🎯 Test {i}: '{message}'")
        print("-" * 30)

        try:
            # Call the conversational assistant
            result = await llm_service.chat(
                user_message=message,
                session_id=session_id,
                conversation_history=conversation_history,
                rag_service=rag_service,
            )

            print(f"🤖 AI Response: {result['ai_message']}")
            print(f"📊 Candidates Found: {result['total_candidates']}")
            print(f"⚙️  Function Calls: {len(result['function_calls'])}")

            if result["function_calls"]:
                for func_call in result["function_calls"]:
                    print(
                        f"   - {func_call['name']}() → {func_call['result_count']} results"
                    )

            # Update conversation history for next iteration
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append(
                {"role": "assistant", "content": result["ai_message"]}
            )

            print("✅ Success!")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

        print()

    print("🎉 Chat functionality test completed!")


if __name__ == "__main__":
    asyncio.run(test_chat_functionality())
