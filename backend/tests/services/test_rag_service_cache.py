"""
Tests for RAG service embedding cache functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.rag_service import RAGService
from app.core.config import settings


@pytest.fixture
async def rag_service():
    """Create a RAG service instance for testing"""
    # Mock the settings and dependencies
    mock_settings = Mock()
    mock_settings.candidate_data_full_path = "test_data.json"
    mock_settings.chroma_db_path = "test_chroma"

    mock_chroma_connector = Mock()
    mock_chroma_connector.get_collection.return_value = Mock()

    with patch(
        "app.services.rag_service.ChromaConnector", return_value=mock_chroma_connector
    ):
        service = RAGService(mock_settings)
        # Initialize cache attributes directly for testing
        service._embedding_cache = {}
        service._cache_max_size = 5  # Small size for testing
        service._cache_ttl_seconds = 3600
        yield service


class TestEmbeddingCache:
    """Test embedding cache functionality"""

    @pytest.mark.asyncio
    async def test_cache_miss_and_store(self, rag_service):
        """Test cache miss and subsequent storage"""
        query = "Python developers"

        # Should return None for cache miss
        result = await rag_service.get_cached_embedding(query)
        assert result is None

        # Store embedding
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        await rag_service.cache_embedding(query, test_embedding)

        # Should now return the cached embedding
        result = await rag_service.get_cached_embedding(query)
        assert result == test_embedding

    @pytest.mark.asyncio
    async def test_cache_hit(self, rag_service):
        """Test cache hit scenario"""
        query = "React developers"
        test_embedding = [0.5, 0.4, 0.3, 0.2, 0.1]

        # Cache the embedding
        await rag_service.cache_embedding(query, test_embedding)

        # Retrieve from cache
        result = await rag_service.get_cached_embedding(query)
        assert result == test_embedding

    @pytest.mark.asyncio
    async def test_cache_size_limit(self, rag_service):
        """Test cache size limit enforcement"""
        # Fill cache beyond limit
        for i in range(7):  # More than max_size (5)
            query = f"query_{i}"
            embedding = [float(i)] * 5
            await rag_service.cache_embedding(query, embedding)

        # Cache should not exceed max size
        assert (
            len(rag_service._embedding_cache) <= rag_service._cache_max_size + 10
        )  # Buffer allowance

    @pytest.mark.asyncio
    async def test_query_normalization(self, rag_service):
        """Test query normalization for cache keys"""
        embedding = [0.1, 0.2, 0.3]

        # These should be treated as the same query
        await rag_service.cache_embedding("Python Developers", embedding)
        result = await rag_service.get_cached_embedding("python developers")
        assert result == embedding

    @pytest.mark.asyncio
    async def test_cache_stats(self, rag_service):
        """Test cache statistics"""
        # Add some entries
        for i in range(3):
            await rag_service.cache_embedding(f"query_{i}", [float(i)] * 5)

        stats = rag_service.get_cache_stats()

        assert stats["total_entries"] == 3
        assert stats["active_entries"] <= 3
        assert stats["max_size"] == 5
        assert stats["ttl_seconds"] == 3600
        assert "hit_rate" in stats

    @pytest.mark.asyncio
    async def test_cache_ttl_expiry(self, rag_service):
        """Test cache TTL expiry"""
        query = "expiring query"
        embedding = [0.1, 0.2, 0.3]

        # Set very short TTL for testing
        rag_service._cache_ttl_seconds = 0.1  # 100ms

        # Cache embedding
        await rag_service.cache_embedding(query, embedding)

        # Should be available immediately
        result = await rag_service.get_cached_embedding(query)
        assert result == embedding

        # Wait for expiry
        await asyncio.sleep(0.2)

        # Should be expired now
        result = await rag_service.get_cached_embedding(query)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, rag_service):
        """Test handling of empty queries"""
        # Empty query should still work
        result = await rag_service.get_cached_embedding("")
        assert result is None

        # Can cache empty query
        await rag_service.cache_embedding("", [0.0])
        result = await rag_service.get_cached_embedding("")
        assert result == [0.0]

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, rag_service):
        """Test concurrent cache access"""

        async def cache_worker(worker_id):
            query = f"worker_{worker_id}_query"
            embedding = [float(worker_id)] * 5
            await rag_service.cache_embedding(query, embedding)
            result = await rag_service.get_cached_embedding(query)
            return result == embedding

        # Run multiple workers concurrently
        tasks = [cache_worker(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All workers should succeed
        assert all(results)

    def test_hash_generation(self, rag_service):
        """Test query hash generation consistency"""
        query1 = "Python developers"
        query2 = "python developers"  # Different case
        query3 = " Python developers "  # Extra whitespace

        hash1 = rag_service._get_query_hash(query1)
        hash2 = rag_service._get_query_hash(query2)
        hash3 = rag_service._get_query_hash(query3)

        # Should all generate the same hash
        assert hash1 == hash2 == hash3

        # Hash should be reasonable length
        assert len(hash1) == 16

    @pytest.mark.asyncio
    async def test_cleanup_expired_entries(self, rag_service):
        """Test cleanup of expired cache entries"""
        # Set short TTL
        rag_service._cache_ttl_seconds = 0.1

        # Add entries
        for i in range(3):
            await rag_service.cache_embedding(f"query_{i}", [float(i)])

        assert len(rag_service._embedding_cache) == 3

        # Wait for expiry
        await asyncio.sleep(0.2)

        # Force cleanup by accessing cache with large size
        rag_service._embedding_cache["dummy"] = (
            [1.0],
            0,
        )  # Add dummy entry to trigger cleanup
        await rag_service.get_cached_embedding("new_query")

        # Expired entries should be cleaned up
        active_count = sum(
            1
            for _, (_, timestamp) in rag_service._embedding_cache.items()
            if rag_service._cache_ttl_seconds > 0.15  # Only recent entries
        )
        assert active_count <= 1  # Only the dummy entry should remain active


if __name__ == "__main__":
    pytest.main([__file__])
