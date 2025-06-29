#!/usr/bin/env python3
"""
Simple test for persistent save/compare functionality only.
"""

import requests
import time

BASE_URL = "http://localhost:8000"


def test_save_compare():
    """Test just the save/compare functionality"""
    print("🔍 Testing Save/Compare Functionality...")

    session_id = f"test_session_{int(time.time())}"

    try:
        # Test 1: Save candidates
        print("💾 Testing save candidates...")
        save_response = requests.post(
            f"{BASE_URL}/api/v1/session/saved-candidates",
            json={"candidate_ids": ["candidate_1", "candidate_2"], "action": "add"},
            headers={"X-Session-ID": session_id},
            timeout=10,
        )

        print(f"Save Status: {save_response.status_code}")
        if save_response.status_code != 200:
            print(f"Save Error: {save_response.text}")
            return False

        save_data = save_response.json()
        print(f"Save Response: {save_data}")

        # Test 2: Get saved candidates
        print("📋 Testing get saved candidates...")
        get_response = requests.get(
            f"{BASE_URL}/api/v1/session/saved-candidates",
            headers={"X-Session-ID": session_id},
            timeout=10,
        )

        print(f"Get Status: {get_response.status_code}")
        if get_response.status_code != 200:
            print(f"Get Error: {get_response.text}")
            return False

        get_data = get_response.json()
        print(f"Get Response: {get_data}")

        # Test 3: Comparison list
        print("🔄 Testing comparison list...")
        compare_response = requests.post(
            f"{BASE_URL}/api/v1/session/comparison-list",
            json={"candidate_ids": ["candidate_1", "candidate_2"], "action": "set"},
            headers={"X-Session-ID": session_id},
            timeout=10,
        )

        print(f"Compare Status: {compare_response.status_code}")
        if compare_response.status_code != 200:
            print(f"Compare Error: {compare_response.text}")
            return False

        compare_data = compare_response.json()
        print(f"Compare Response: {compare_data}")

        print("✅ All save/compare tests passed!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Save/Compare Focused Test")
    print("=" * 40)

    # Wait for server
    print("⏳ Waiting for server...")
    time.sleep(5)

    success = test_save_compare()

    if success:
        print("\n🎉 SAVE/COMPARE FUNCTIONALITY: WORKING!")
    else:
        print("\n❌ SAVE/COMPARE FUNCTIONALITY: FAILED!")
