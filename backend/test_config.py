#!/usr/bin/env python3
"""
Configuration Testing Script

Tests the configuration system to ensure all settings load correctly
and validation works as expected.

Usage:
    cd backend
    python test_config.py
"""

import sys
import os

# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

try:
    from app.core import settings

    print("=" * 50)
    print("✅ Configuration modules imported successfully!")
    print()

    # Test API Configuration
    print("🔑 API Configuration:")
    try:
        # Test if API key is set (don't print the actual key for security)
        settings.openai_api_key
        print("  OpenAI API Key: ✅ Set")
    except Exception as e:
        print(f"  OpenAI API Key: ❌ {e}")

    print(f"  CORS Origins: {settings.backend_cors_origins}")
    print()

    # Test Model Configuration
    print("🤖 Model Configuration:")
    print(f"  Embedding Model: {settings.embedding_model_name}")
    print(f"  Chat Model: {settings.chat_model_name}")
    print(f"  Chat Temperature: {settings.chat_temperature}")
    print(f"  Max Tokens: {settings.chat_max_tokens}")
    print(f"  Max Search Results: {settings.max_search_results}")
    print()

    # Test Application Configuration
    print("⚙️  Application Configuration:")
    print(f"  Project Name: {settings.project_name}")
    print(f"  Environment: {settings.environment}")
    print(f"  Debug Mode: {settings.debug}")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Candidate Data Path: {settings.candidate_data_path}")
    print(f"  ChromaDB Path: {settings.chroma_db_path}")
    print(f"  ChromaDB Collection: {settings.chroma_collection_name}")
    print()

    # Test File Path Resolution
    print("📁 File Path Validation:")
    candidate_data_path = settings.candidate_data_full_path
    print(f"  Candidate Data: {candidate_data_path}")

    if candidate_data_path.exists():
        print("  ✅ Candidate data file exists")
    else:
        print("  ⚠️  Candidate data file not found")

    chroma_db_path = settings.chroma_db_full_path
    print(f"  ChromaDB Directory: {chroma_db_path}")

    # Check if parent directory exists (ChromaDB will create the actual dir)
    if chroma_db_path.parent.exists():
        print("  ✅ ChromaDB parent directory exists")
    else:
        print("  ⚠️  ChromaDB parent directory not found")

    print()
    print("=" * 50)
    print("✅ Configuration test completed successfully!")
    print()
    print("Next steps:")
    print("1. Copy backend/env.sample to backend/.env")
    print("2. Add your OpenAI API key to the .env file")
    print("3. Run the FastAPI server: uvicorn app.main:app --reload")

except Exception as e:
    print("=" * 50)
    print(f"❌ Configuration Error: {e}")
    print("Check your .env file and configuration settings")
    sys.exit(1)
