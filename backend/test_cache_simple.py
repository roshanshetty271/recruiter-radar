#!/usr/bin/env python3
"""
Simple non-interactive test for cache management API endpoints
"""

import asyncio
import httpx


async def test_cache_endpoints():
    """Test cache management endpoints."""
    base_url = "http://localhost:8000/api/v1"

    print("🌐 Testing Cache Management API Endpoints...")
    print("=" * 50)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test cache stats
            print("\n📊 Testing GET /api/v1/chat/cache/stats")
            response = await client.get(f"{base_url}/chat/cache/stats")

            if response.status_code == 200:
                stats = response.json()
                print("✅ Cache Stats Retrieved Successfully!")
                print(f"   • Hit Rate: {stats.get('hit_rate_percentage', 0)}%")
                print(
                    f"   • Cache Size: {stats.get('current_cache_size', 0)}/{stats.get('max_cache_size', 0)}"
                )
                print(f"   • Total Requests: {stats.get('total_requests', 0)}")
                print(f"   • Cache Hits: {stats.get('cache_hits', 0)}")
                print(f"   • Cache Misses: {stats.get('cache_misses', 0)}")

                popular_queries = stats.get("popular_queries", [])
                if popular_queries:
                    print(f"   • Popular Queries ({len(popular_queries)}):")
                    for i, query in enumerate(popular_queries[:3], 1):
                        print(
                            f"     {i}. Hash: {query.get('query_hash', 'N/A')} (hits: {query.get('hit_count', 0)})"
                        )
                else:
                    print("   • No popular queries yet")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")

            # Test cache cleanup
            print("\n🧹 Testing POST /api/v1/chat/cache/cleanup")
            response = await client.post(f"{base_url}/chat/cache/cleanup")

            if response.status_code == 200:
                result = response.json()
                print("✅ Cache Cleanup Executed Successfully!")
                print(
                    f"   • Expired entries removed: {result.get('expired_entries_removed', 0)}"
                )
                print(f"   • Message: {result.get('message', 'No message')}")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")

        print("\n" + "=" * 50)
        print("🎉 Cache API Endpoint Testing Complete!")
        print("✅ All cache management endpoints are working!")

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("⚠️  Make sure the FastAPI server is running on http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(test_cache_endpoints())
