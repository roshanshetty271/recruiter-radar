#!/usr/bin/env python3
"""
Quick diagnostic tool to test OpenAI API connection.
Run this before the main test harness to ensure API is working.
"""

import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_connection():
    """Test OpenAI API connection with various models."""

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")

    print("=== OpenAI API Connection Test ===\n")

    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found!")
        print("\nPlease create a .env file with:")
        print("OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx")
        return

    # Mask the key for security
    masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
    print(f"API Key found: {masked_key}")
    print(f"Key length: {len(api_key)} characters")

    # Test different models
    models_to_test = [
        "gpt-4o-mini",  # Newest, cheapest
        "gpt-3.5-turbo",  # Older but reliable
        "gpt-4-turbo-preview",  # More expensive but powerful
    ]

    client = AsyncOpenAI(api_key=api_key)

    for model in models_to_test:
        print(f"\nTesting model: {model}")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'Hello World'"}],
                max_tokens=10,
            )

            content = response.choices[0].message.content
            print(f"✓ SUCCESS: {content}")

            # If gpt-4o-mini doesn't work, suggest using working model
            if model != "gpt-4o-mini" and models_to_test[0] == "gpt-4o-mini":
                print(
                    f"\nSuggestion: Update llm_extraction_harness.py to use model='{model}'"
                )

        except Exception as e:
            print(f"✗ FAILED: {type(e).__name__}: {str(e)}")

    # Test JSON mode specifically
    print("\n\nTesting JSON response format:")
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use most reliable model
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that outputs JSON.",
                },
                {
                    "role": "user",
                    "content": "Return a JSON object with name='John' and age=30",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=50,
        )

        content = response.choices[0].message.content
        print(f"✓ JSON mode works: {content}")

    except Exception as e:
        print(f"✗ JSON mode failed: {type(e).__name__}: {str(e)}")
        if "response_format" in str(e):
            print("\nNote: Your API/model may not support JSON mode.")
            print("The extraction harness will need to be modified.")


if __name__ == "__main__":
    print("Running OpenAI API diagnostics...\n")
    asyncio.run(test_connection())
    print("\n\nDiagnostics complete!")
