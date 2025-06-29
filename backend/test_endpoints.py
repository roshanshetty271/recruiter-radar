#!/usr/bin/env python3

import requests
import json

BASE_URL = "http://localhost:8000"


def test_save_endpoint():
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/session/saved-candidates",
            json={"candidate_ids": ["test_candidate_1"], "action": "add"},
            headers={"X-Session-ID": "test_session"},
        )

        print(f"Save endpoint status: {response.status_code}")
        print(f"Save endpoint response: {response.text}")

        if response.status_code == 200:
            print("✅ Save endpoint working")
        else:
            print("❌ Save endpoint failed")

    except Exception as e:
        print(f"❌ Save endpoint error: {e}")


def test_get_endpoint():
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/session/saved-candidates",
            headers={"X-Session-ID": "test_session"},
        )

        print(f"Get endpoint status: {response.status_code}")
        print(f"Get endpoint response: {response.text}")

        if response.status_code == 200:
            print("✅ Get endpoint working")
        else:
            print("❌ Get endpoint failed")

    except Exception as e:
        print(f"❌ Get endpoint error: {e}")


if __name__ == "__main__":
    print("Testing save/compare endpoints...")
    test_save_endpoint()
    print()
    test_get_endpoint()
