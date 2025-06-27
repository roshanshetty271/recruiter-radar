#!/usr/bin/env python3
"""
Simple test for cache management API endpoints
"""

import asyncio
import httpx
import json


async def test_cache_endpoints():
    """Test all cache management endpoints."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🌐 Testing Cache Management API Endpoints...")
        print("=" * 50)

        # Test cache stats
        print("\n📊 Testing GET /chat/cache/stats")
        try:
            response = await client.get(f"{base_url}/chat/cache/stats")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                stats = response.json()
                print("✅ Cache Stats Retrieved:")
                print(f"   • Hit Rate: {stats.get('hit_rate_percentage', 0)}%")
                print(
                    f"   • Cache Size: {stats.get('current_cache_size', 0)}/{stats.get('max_cache_size', 0)}"
                )
                print(f"   • Total Requests: {stats.get('total_requests', 0)}")
                print(f"   • Cache Hits: {stats.get('cache_hits', 0)}")
                print(f"   • Cache Misses: {stats.get('cache_misses', 0)}")
                print(f"   • Popular Queries: {len(stats.get('popular_queries', []))}")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test cache cleanup
        print("\n🧹 Testing POST /chat/cache/cleanup")
        try:
            response = await client.post(f"{base_url}/chat/cache/cleanup")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("✅ Cache Cleanup Executed:")
                print(
                    f"   • Expired entries removed: {result.get('expired_entries_removed', 0)}"
                )
                print(f"   • Message: {result.get('message', '')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test cache clear (optional - use with caution)
        print("\n🗑️  Testing POST /chat/cache/clear (OPTIONAL)")
        user_input = input("Do you want to clear ALL cache? (y/N): ").strip().lower()
        if user_input in ["y", "yes"]:
            try:
                response = await client.post(f"{base_url}/chat/cache/clear")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print("✅ Cache Cleared:")
                    print(f"   • Entries cleared: {result.get('entries_cleared', 0)}")
                    print(f"   • Message: {result.get('message', '')}")
                else:
                    print(f"❌ Failed: {response.status_code}")
                    print(response.text)
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("⏭️  Skipping cache clear")

        # Final stats check
        print("\n📊 Final Cache Stats Check")
        try:
            response = await client.get(f"{base_url}/chat/cache/stats")
            if response.status_code == 200:
                stats = response.json()
                print("✅ Final Stats:")
                print(f"   • Hit Rate: {stats.get('hit_rate_percentage', 0)}%")
                print(f"   • Cache Size: {stats.get('current_cache_size', 0)}")
                print(f"   • Total Requests: {stats.get('total_requests', 0)}")
        except Exception as e:
            print(f"❌ Error getting final stats: {e}")

        print("\n" + "=" * 50)
        print("🎉 Cache API Endpoint Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_cache_endpoints())
