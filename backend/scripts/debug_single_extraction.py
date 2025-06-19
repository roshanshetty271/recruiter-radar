#!/usr/bin/env python3
"""
Debug tool to test extraction on a single PDF with detailed output.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from openai import AsyncOpenAI
from dotenv import load_dotenv
import pypdf
import json

from app.core.prompts import EXTRACTION_PROMPT_V2

# Load environment variables
load_dotenv()


async def debug_single_pdf(pdf_path: str):
    """Debug extraction for a single PDF."""

    print(f"=== Debugging PDF Extraction ===")
    print(f"File: {pdf_path}\n")

    # Step 1: Check if file exists
    if not Path(pdf_path).exists():
        print(f"[ERROR] File not found: {pdf_path}")
        return

    # Step 2: Extract text from PDF
    print("Step 1: Extracting text from PDF...")
    try:
        with open(pdf_path, "rb") as file:
            reader = pypdf.PdfReader(file)
            print(f"  - Number of pages: {len(reader.pages)}")

            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text_parts.append(page_text)
                print(f"  - Page {i+1}: {len(page_text)} characters")

            full_text = "\n".join(text_parts)
            # Clean and truncate
            full_text = " ".join(full_text.split())[:15000]

            print(f"  - Total text length: {len(full_text)} characters")
            print(f"  - First 200 chars: {full_text[:200]}...")

    except Exception as e:
        print(f"[ERROR] PDF extraction failed: {type(e).__name__}: {str(e)}")
        return

    # Step 3: Test OpenAI API
    print("\nStep 2: Testing OpenAI API...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in .env")
        return

    client = AsyncOpenAI(api_key=api_key)

    # Step 4: Try extraction with detailed error handling
    print("\nStep 3: Attempting LLM extraction...")

    # Build the prompt
    prompt = EXTRACTION_PROMPT_V2.format(text=full_text)
    print(f"  - Prompt length: {len(prompt)} characters")

    try:
        print("  - Calling OpenAI API...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume parser. Always return valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        print(f"  - API call successful!")
        print(
            f"  - Tokens used: {response.usage.total_tokens if response.usage else 'Unknown'}"
        )

        result_text = response.choices[0].message.content
        print(f"  - Response length: {len(result_text)} characters")

        # Try to parse JSON
        print("\nStep 4: Parsing JSON response...")
        result = json.loads(result_text)

        print("[SUCCESS] Extraction completed!")
        print("\nExtracted data:")
        print(json.dumps(result, indent=2))

        # Validate fields
        print("\nValidation:")
        required_fields = [
            "name",
            "title",
            "skills",
            "location",
            "experience_years",
            "email",
            "phone",
            "summary",
        ]
        for field in required_fields:
            if field in result:
                value = result[field]
                if value is None:
                    print(f"  - {field}: null")
                elif field == "skills" and isinstance(value, list):
                    print(f"  - {field}: {len(value)} items")
                else:
                    print(f"  - {field}: ✓")
            else:
                print(f"  - {field}: MISSING")

    except Exception as e:
        print(f"\n[ERROR] Extraction failed!")
        print(f"  - Error type: {type(e).__name__}")
        print(f"  - Error message: {str(e)}")

        # Try without JSON mode as fallback
        print("\nTrying without JSON mode...")
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert resume parser."},
                    {"role": "user", "content": prompt + "\n\nReturn only valid JSON."},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            result_text = response.choices[0].message.content
            print(f"Fallback response:\n{result_text[:500]}...")

        except Exception as e2:
            print(f"Fallback also failed: {type(e2).__name__}: {str(e2)}")


async def main():
    # Default to first PDF in standard category
    default_pdf = Path("test_resumes/standard/software_engineer_clean.pdf")

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = str(default_pdf)

    await debug_single_pdf(pdf_path)


if __name__ == "__main__":
    print("Single PDF Extraction Debugger\n")
    asyncio.run(main())
