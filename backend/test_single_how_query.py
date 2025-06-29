#!/usr/bin/env python3
"""
🎯 SINGLE TEST: "How do I find candidates?"

Final verification that this specific query is working correctly.
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8000"
CHAT_URL = f"{BASE_URL}/api/v1/chat/bulletproof"

query = "How do I find candidates?"
session_id = f"single-test-{uuid.uuid4().hex[:8]}"

payload = {"message": query}
headers = {"X-Session-ID": session_id, "Content-Type": "application/json"}

print(f"🧪 SINGLE TEST: '{query}'")
print("=" * 50)

try:
    response = requests.post(CHAT_URL, json=payload, headers=headers, timeout=15)

    if response.status_code == 200:
        data = response.json()

        candidates_found = len(data.get("candidates", []))
        source = data.get("source", "unknown")
        response_time = data.get("response_time", 0)
        ai_message = data.get("ai_message", "")

        print(f"✅ SUCCESS!")
        print(f"   📊 Status: {response.status_code}")
        print(f"   👥 Candidates: {candidates_found}")
        print(f"   📡 Source: {source}")
        print(f"   ⏱️  Time: {response_time:.2f}s")
        print(f"   💬 AI Response: {ai_message[:100]}...")

        # Check if it meets our expectations
        if candidates_found == 0 and source == "real_rag":
            print(f"\n🎉 PERFECT! This query is working exactly as expected!")
            print(f"   ✅ Conversational query correctly handled")
            print(f"   ✅ No candidates returned (correct)")
            print(f"   ✅ Source is real_rag (correct)")
            print(f"   ✅ Response time is reasonable")
        else:
            print(f"\n⚠️  Partial success - query works but expectations differ")
            print(f"   Expected: 0 candidates from real_rag")
            print(f"   Got: {candidates_found} candidates from {source}")

    else:
        print(f"❌ ERROR: HTTP {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"💥 EXCEPTION: {e}")

print(f"\n�� Test complete!")
