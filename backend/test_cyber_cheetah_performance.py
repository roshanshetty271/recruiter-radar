#!/usr/bin/env python3
"""
🚀 CYBER-CHEETAH PERFORMANCE VALIDATION

Tests performance improvements: connection pooling, caching, orjson, batched LLM calls
Target: <1s median response time
"""

import asyncio
import time
import statistics
import httpx
import json

BASE_URL = "http://localhost:8000"
SESSION_ID = "cyber-cheetah-test"

TEST_QUERIES = [
    "Python developers with 5+ years",
    "React engineers",
    "Senior full-stack developers",
    "DevOps engineers with AWS",
]


class CyberCheetahTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.response_times = []
        self.cache_hits = 0
        self.errors = 0

    async def test_query(self, query: str):
        """Test single query performance."""
        start_time = time.time()

        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/bulletproof",
                headers={"X-Session-ID": SESSION_ID},
                json={"message": query},
            )

            response_time = time.time() - start_time
            self.response_times.append(response_time)

            if response.status_code == 200:
                data = response.json()
                candidates = len(data.get("candidates", []))
                source = data.get("source", "unknown")

                # Check for cache indicators
                if response_time < 0.5 or "cache" in source.lower():
                    self.cache_hits += 1

                print(
                    f"✅ {query[:30]}... | {response_time:.3f}s | {candidates} candidates | {source}"
                )
                return True
            else:
                print(f"❌ Error {response.status_code}: {query}")
                self.errors += 1
                return False

        except Exception as e:
            print(f"❌ Exception: {e}")
            self.errors += 1
            return False

    async def run_test(self):
        """Run full performance test."""
        print("🚀 CYBER-CHEETAH PERFORMANCE TEST")
        print("=" * 50)

        # Warm up
        await self.test_query("warmup")
        await asyncio.sleep(1)

        # Test all queries
        for query in TEST_QUERIES:
            await self.test_query(query)
            await asyncio.sleep(0.2)

        # Test caching with repeat
        print("\n🧪 Cache test...")
        await self.test_query("Python developers")  # Repeat
        await self.test_query("React engineers")  # Repeat

        # Results
        if self.response_times:
            median = statistics.median(self.response_times)
            mean = statistics.mean(self.response_times)
            sub_1s = len([t for t in self.response_times if t < 1.0])
            sub_1s_pct = sub_1s / len(self.response_times) * 100

            print(f"\n📊 RESULTS:")
            print(f"   Median: {median:.3f}s")
            print(f"   Mean: {mean:.3f}s")
            print(f"   Sub-1s: {sub_1s_pct:.1f}%")
            print(f"   Cache hits: {self.cache_hits}")
            print(f"   Errors: {self.errors}")

            # Success criteria
            success = median < 1.0 and sub_1s_pct >= 80 and self.errors == 0
            print(
                f"\n🏆 CYBER-CHEETAH: {'ACHIEVED! 🚀' if success else 'IN PROGRESS ⚠️'}"
            )

        await self.client.aclose()


async def main():
    tester = CyberCheetahTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
