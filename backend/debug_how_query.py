#!/usr/bin/env python3
"""
🔍 DEBUG: "How do I find candidates?" Query

Quick debug to see exactly what's happening with this specific query.
"""

import requests
import json

# Test the specific problematic query
BASE_URL = "http://localhost:8000"
CHAT_URL = f"{BASE_URL}/api/v1/chat/bulletproof"

query = "How do I find candidates?"
session_id = "debug-session-001"

payload = {"message": query}

headers = {"X-Session-ID": session_id, "Content-Type": "application/json"}

print(f"🔍 DEBUGGING: '{query}'")
print("=" * 50)
print(f"📡 Sending to: {CHAT_URL}")
print(f"📦 Payload: {json.dumps(payload, indent=2)}")
print(f"📋 Headers: {json.dumps(headers, indent=2)}")
print()
print("⏳ Waiting for response...")

try:
    response = requests.post(CHAT_URL, json=payload, headers=headers, timeout=30)

    print(f"📊 Status Code: {response.status_code}")
    print(f"📋 Response Headers: {dict(response.headers)}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS! Response data:")
        print(json.dumps(data, indent=2))

        print()
        print("🎯 KEY FIELDS:")
        print(f"   Source: {data.get('source', 'MISSING')}")
        print(f"   Candidates: {len(data.get('candidates', []))}")
        print(f"   Response Time: {data.get('response_time', 'MISSING')}")
        print(f"   AI Message: {data.get('ai_message', 'MISSING')[:100]}...")

    else:
        print("❌ ERROR Response:")
        print(f"Status: {response.status_code}")
        print(f"Text: {response.text}")

except requests.exceptions.Timeout:
    print("⏰ TIMEOUT! Request took longer than 30 seconds")
except Exception as e:
    print(f"💥 EXCEPTION: {e}")

print()
print("🔍 Debug complete!")
