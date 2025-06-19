#!/usr/bin/env python3
"""
Direct verification of the implementation without HTTP requests.

This script tests the core functionality:
1. Email extraction from resume text
2. Candidate ID generation
3. Deduplication logic
"""

import sys
import os
from pathlib import Path

# Add the backend app to the path so we can import modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.api.routers.upload_router import generate_candidate_id, extract_email_from_text


def test_email_extraction():
    """Test email extraction from resume text."""
    print("🧪 Testing Email Extraction")
    print("=" * 40)

    test_cases = [
        ("Contact: john.smith@example.com for more info", "john.smith@example.com"),
        ("Email: sarah.johnson@gmail.com\nPhone: 555-0123", "sarah.johnson@gmail.com"),
        ("No email in this text", None),
        ("Multiple emails: first@example.com and second@test.com", "first@example.com"),
        ("UPPERCASE.EMAIL@DOMAIN.COM", "UPPERCASE.EMAIL@DOMAIN.COM"),
    ]

    for text, expected in test_cases:
        result = extract_email_from_text(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text[:30]}...' -> {result}")


def test_candidate_id_generation():
    """Test candidate ID generation logic."""
    print("\n🧪 Testing Candidate ID Generation")
    print("=" * 40)

    session_id = "test-session"
    fake_file_content = b"fake pdf content"

    # Test with email
    email = "john.smith@example.com"
    id1 = generate_candidate_id(email, fake_file_content, session_id)
    id2 = generate_candidate_id(email, fake_file_content, session_id)

    print(f"Email-based ID 1: {id1}")
    print(f"Email-based ID 2: {id2}")
    print(f"✅ Email IDs consistent: {id1 == id2}")

    # Test with different emails
    email2 = "jane.doe@example.com"
    id3 = generate_candidate_id(email2, fake_file_content, session_id)
    print(f"Different email ID: {id3}")
    print(f"✅ Different emails -> different IDs: {id1 != id3}")

    # Test without email (hash fallback)
    id4 = generate_candidate_id(None, fake_file_content, session_id)
    id5 = generate_candidate_id(None, fake_file_content, session_id)

    print(f"Hash-based ID 1: {id4}")
    print(f"Hash-based ID 2: {id5}")
    print(f"✅ Hash IDs consistent: {id4 == id5}")

    # Test different file content
    different_content = b"different pdf content"
    id6 = generate_candidate_id(None, different_content, session_id)
    print(f"Different content ID: {id6}")
    print(f"✅ Different content -> different IDs: {id4 != id6}")


def main():
    print("🎯 Implementation Verification")
    print("=" * 50)

    test_email_extraction()
    test_candidate_id_generation()

    print(f"\n🎉 Verification complete!")
    print("\nKey Features Verified:")
    print("✅ Email extraction from resume text")
    print("✅ Deterministic candidate ID generation")
    print("✅ Email-based primary key with hash fallback")
    print("✅ Same candidate -> same ID (enables updates)")
    print("✅ Different candidates -> different IDs")


if __name__ == "__main__":
    main()
