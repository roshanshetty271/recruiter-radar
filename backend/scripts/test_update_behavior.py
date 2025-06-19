#!/usr/bin/env python3
"""
Test script to verify the update behavior of the upload system.

This script uploads the same resume twice to test:
1. First upload should be operation_type: "add"
2. Second upload should be operation_type: "update"
"""

import sys
import os
from pathlib import Path
import requests
import time

# Test configuration
API_BASE_URL = "http://localhost:8000"
SESSION_ID = "test-update-behavior"
TEST_FILE = "scripts/test_resumes/test_resume_1_John_Smith.pdf"


def upload_resume(session_id: str, file_path: str, description: str):
    """Upload a resume and return the response."""
    print(f"\n📄 {description}")

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            headers = {"X-Session-ID": session_id}

            response = requests.post(
                f"{API_BASE_URL}/api/v1/upload/resume",
                files=files,
                headers=headers,
                timeout=30,
            )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"📝 Message: {data['message']}")
            print(f"👤 Extracted Name: {data.get('extracted_name', 'N/A')}")
            print(f"🆔 Candidate ID: {data.get('candidate_id', 'N/A')}")
            print(f"🔄 Operation Type: {data.get('operation_type', 'N/A')}")
            print(f"⏱️  Processing Time: {data.get('processing_time_ms', 0)}ms")
            return data
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    print("🧪 Testing Upload Update Behavior")
    print("=" * 50)

    # Test 1: First upload (should be "add")
    result1 = upload_resume(SESSION_ID, TEST_FILE, "First upload (expecting 'add')")

    if not result1:
        print("❌ First upload failed, cannot continue test")
        return

    # Small delay
    time.sleep(1)

    # Test 2: Second upload of same file (should be "update")
    result2 = upload_resume(SESSION_ID, TEST_FILE, "Second upload (expecting 'update')")

    if not result2:
        print("❌ Second upload failed")
        return

    print("\n🎯 TEST RESULTS:")
    print("=" * 50)

    # Verify operation types
    op1 = result1.get("operation_type")
    op2 = result2.get("operation_type")

    print(f"First upload operation_type: {op1}")
    print(f"Second upload operation_type: {op2}")

    # Check if IDs are the same (they should be for same candidate)
    id1 = result1.get("candidate_id")
    id2 = result2.get("candidate_id")

    print(f"First upload candidate_id: {id1}")
    print(f"Second upload candidate_id: {id2}")

    # Evaluate results
    success = True
    if op1 != "add":
        print("❌ FAIL: First upload should be 'add'")
        success = False
    if op2 != "update":
        print("❌ FAIL: Second upload should be 'update'")
        success = False
    if id1 != id2:
        print("❌ FAIL: Candidate IDs should be the same")
        success = False

    if success:
        print("✅ SUCCESS: Update behavior working correctly!")
    else:
        print("❌ FAIL: Update behavior needs investigation")


if __name__ == "__main__":
    main()
