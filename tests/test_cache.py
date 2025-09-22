"""Tests for the original language detection caching system."""

import asyncio
import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock

import pytest

from src.nhkprep.original_lang import OriginalLanguageDetection, MediaSearchQuery
from src.nhkprep.original_lang.cache import (
    FileBasedCache, InMemoryCache, create_cache_from_config
)
from src.nhkprep.original_lang.config import OriginalLanguageConfig


@pytest.fixture
def sample_query():
    """Sample search query for testing."""
    return MediaSearchQuery(
        title="Spirited Away",
        year=2001,
        media_type="movie",
        imdb_id="tt0245429"
    )


@pytest.fixture
def sample_detection():
    """Sample detection result for testing."""
    return OriginalLanguageDetection(
        original_language="ja",
        confidence=0.95,
        source="tmdb",
        method="id_match",
        details="Found by IMDb ID lookup",
        title="Sen to Chihiro no Kamikakushi",
        year=2001,
        imdb_id="tt0245429",
        spoken_languages=["ja"],
        production_countries=["JP"],
        detection_time_ms=150.0,
        timestamp=datetime.now()
    )


@pytest.fixture
def temp_cache_dir():
    """Temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestInMemoryCache:
    """Test the in-memory cache implementation."""
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, sample_query, sample_detection):
        """Test basic cache operations."""
        cache = InMemoryCache(ttl_seconds=3600, max_size=100)
        
        # Initially empty
        result = await cache.get(sample_query)
        assert result is None
        
        # Set and get
        await cache.set(sample_query, sample_detection)
        result = await cache.get(sample_query)
        assert result is not None
        assert result.original_language == "ja"
        assert result.confidence == 0.95
        assert result.title == "Sen to Chihiro no Kamikakushi"
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, sample_query, sample_detection):
        """Test TTL expiration."""
        cache = InMemoryCache(ttl_seconds=0.1, max_size=100)  # Very short TTL
        
        await cache.set(sample_query, sample_detection)
        
        # Should be available immediately
        result = await cache.get(sample_query)
        assert result is not None
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired
        result = await cache.get(sample_query)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_max_size_eviction(self, sample_detection):
        """Test LRU eviction when max size is reached."""
        cache = InMemoryCache(ttl_seconds=3600, max_size=2)
        
        # Create multiple queries
        query1 = MediaSearchQuery(title="Movie 1", year=2001)
        query2 = MediaSearchQuery(title="Movie 2", year=2002)
        query3 = MediaSearchQuery(title="Movie 3", year=2003)
        
        # Fill cache to capacity
        await cache.set(query1, sample_detection)
        await cache.set(query2, sample_detection)
        
        # Both should be available
        assert await cache.get(query1) is not None
        assert await cache.get(query2) is not None
        
        # Add third item (should evict oldest)
        await cache.set(query3, sample_detection)
        
        # query1 should be evicted, others should remain
        assert await cache.get(query1) is None
        assert await cache.get(query2) is not None
        assert await cache.get(query3) is not None
    
    @pytest.mark.asyncio
    async def test_delete(self, sample_query, sample_detection):
        """Test cache entry deletion."""
        cache = InMemoryCache()
        
        await cache.set(sample_query, sample_detection)
        assert await cache.get(sample_query) is not None
        
        # Delete entry
        deleted = await cache.delete(sample_query)
        assert deleted is True
        assert await cache.get(sample_query) is None
        
        # Delete non-existent entry
        deleted = await cache.delete(sample_query)
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_clear(self, sample_query, sample_detection):
        """Test clearing all cache entries."""
        cache = InMemoryCache()
        
        query2 = MediaSearchQuery(title="Another Movie", year=2020)
        await cache.set(sample_query, sample_detection)
        await cache.set(query2, sample_detection)
        
        count = await cache.clear()
        assert count == 2
        assert await cache.get(sample_query) is None
        assert await cache.get(query2) is None
    
    @pytest.mark.asyncio
    async def test_cleanup(self, sample_detection):
        """Test cleanup of expired entries."""
        cache = InMemoryCache(ttl_seconds=0.1)
        
        query1 = MediaSearchQuery(title="Movie 1", year=2001)
        query2 = MediaSearchQuery(title="Movie 2", year=2002)
        
        await cache.set(query1, sample_detection)
        await asyncio.sleep(0.2)  # Let first entry expire
        await cache.set(query2, sample_detection)  # Second entry still fresh
        
        count = await cache.cleanup()
        assert count == 1  # Only first entry should be cleaned up
        
        assert await cache.get(query1) is None
        assert await cache.get(query2) is not None
    
    @pytest.mark.asyncio
    async def test_stats(self, sample_query, sample_detection):
        """Test cache statistics."""
        cache = InMemoryCache(ttl_seconds=3600, max_size=100)
        
        await cache.set(sample_query, sample_detection)
        stats = await cache.stats()
        
        assert stats['total_entries'] == 1
        assert stats['active_entries'] == 1
        assert stats['expired_entries'] == 0
        assert stats['cache_type'] == 'in_memory'
        assert stats['ttl_seconds'] == 3600
        assert stats['max_size'] == 100


class TestFileBasedCache:
    """Test the file-based cache implementation."""
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, temp_cache_dir, sample_query, sample_detection):
        """Test basic file cache operations."""
        cache = FileBasedCache(temp_cache_dir, ttl_seconds=3600, max_size=100)
        
        # Initially empty
        result = await cache.get(sample_query)
        assert result is None
        
        # Set and get
        await cache.set(sample_query, sample_detection)
        result = await cache.get(sample_query)
        assert result is not None
        assert result.original_language == "ja"
        assert result.confidence == 0.95
        assert result.title == "Sen to Chihiro no Kamikakushi"
        
        # Verify file was created
        cache_files = list(temp_cache_dir.glob("*.json"))
        assert len(cache_files) >= 1  # At least the data file, possibly metadata
    
    @pytest.mark.asyncio
    async def test_persistence(self, temp_cache_dir, sample_query, sample_detection):
        """Test that cache persists across instances."""
        # Create first cache instance and store data
        cache1 = FileBasedCache(temp_cache_dir, ttl_seconds=3600)
        await cache1.set(sample_query, sample_detection)
        
        # Create new cache instance with same directory
        cache2 = FileBasedCache(temp_cache_dir, ttl_seconds=3600)
        result = await cache2.get(sample_query)
        
        assert result is not None
        assert result.original_language == "ja"
        assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, temp_cache_dir, sample_query, sample_detection):
        """Test TTL expiration in file cache."""
        cache = FileBasedCache(temp_cache_dir, ttl_seconds=0.1)
        
        await cache.set(sample_query, sample_detection)
        
        # Should be available immediately
        result = await cache.get(sample_query)
        assert result is not None
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired and file removed
        result = await cache.get(sample_query)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_corrupted_cache_file(self, temp_cache_dir, sample_query):
        """Test handling of corrupted cache files."""
        cache = FileBasedCache(temp_cache_dir)
        
        # Create corrupted cache file
        cache_key = cache._get_cache_key(sample_query)
        cache_file = cache._get_cache_file(cache_key)
        
        with open(cache_file, 'w') as f:
            f.write("invalid json content")
        
        # Should handle gracefully and return None
        result = await cache.get(sample_query)
        assert result is None
        
        # Corrupted file should be removed
        assert not cache_file.exists()
    
    @pytest.mark.asyncio
    async def test_metadata_handling(self, temp_cache_dir, sample_query, sample_detection):
        """Test cache metadata management."""
        cache = FileBasedCache(temp_cache_dir)
        
        await cache.set(sample_query, sample_detection)
        
        # Check metadata file was created
        metadata_file = temp_cache_dir / "_cache_metadata.json"
        assert metadata_file.exists()
        
        # Check metadata content
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert 'entries' in metadata
        assert len(metadata['entries']) == 1
        
        # Metadata should contain query and result info
        entry_key = list(metadata['entries'].keys())[0]
        entry = metadata['entries'][entry_key]
        assert 'created_time' in entry
        assert 'expiry_time' in entry
        assert entry['query_title'] == "Spirited Away"
        assert entry['result_language'] == "ja"
    
    @pytest.mark.asyncio
    async def test_cleanup_size_limit(self, temp_cache_dir, sample_detection):
        """Test cleanup when size limit is exceeded."""
        cache = FileBasedCache(temp_cache_dir, max_size=2, auto_cleanup=False)
        
        # Add more entries than max_size
        query1 = MediaSearchQuery(title="Movie 1", year=2001)
        query2 = MediaSearchQuery(title="Movie 2", year=2002)
        query3 = MediaSearchQuery(title="Movie 3", year=2003)
        
        await cache.set(query1, sample_detection)
        await asyncio.sleep(0.01)  # Ensure different creation times
        await cache.set(query2, sample_detection)
        await asyncio.sleep(0.01)
        await cache.set(query3, sample_detection)
        
        # Manually trigger cleanup
        removed = await cache.cleanup()
        assert removed == 1  # Should remove oldest entry
        
        # Oldest entry should be gone
        assert await cache.get(query1) is None
        assert await cache.get(query2) is not None
        assert await cache.get(query3) is not None
    
    @pytest.mark.asyncio
    async def test_stats(self, temp_cache_dir, sample_query, sample_detection):
        """Test file cache statistics."""
        cache = FileBasedCache(temp_cache_dir)
        
        await cache.set(sample_query, sample_detection)
        stats = await cache.stats()
        
        assert stats['total_entries'] == 1
        assert stats['active_entries'] == 1
        assert stats['expired_entries'] == 0
        assert stats['cache_dir'] == str(temp_cache_dir)
        assert 'disk_usage_mb' in stats


class TestCacheFactory:
    """Test cache factory functions."""
    
    def test_create_cache_from_config_enabled(self, temp_cache_dir):
        """Test creating cache from config when enabled."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=temp_cache_dir,
            cache_ttl=7200,
            cache_max_size=500
        )
        
        cache = create_cache_from_config(config)
        
        assert isinstance(cache, FileBasedCache)
        assert cache.cache_dir == temp_cache_dir
        assert cache.ttl_seconds == 7200
        assert cache.max_size == 500
    
    def test_create_cache_from_config_disabled(self):
        """Test creating cache from config when disabled."""
        config = OriginalLanguageConfig(cache_enabled=False)
        
        cache = create_cache_from_config(config)
        
        # Should be a no-op cache, not in-memory
        from src.nhkprep.original_lang.no_op_cache import NoOpCache
        assert isinstance(cache, NoOpCache)
    
    def test_create_cache_from_config_default_dir(self):
        """Test creating cache with default directory."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=None  # Should use default
        )
        
        cache = create_cache_from_config(config)
        
        assert isinstance(cache, FileBasedCache)
        assert cache.cache_dir is not None
        assert "nhkprep" in str(cache.cache_dir)
        assert "orig_lang_cache" in str(cache.cache_dir)


class TestCacheKeyGeneration:
    """Test cache key generation consistency."""
    
    @pytest.mark.asyncio
    async def test_consistent_keys(self, temp_cache_dir):
        """Test that identical queries generate identical cache keys."""
        cache = FileBasedCache(temp_cache_dir)
        
        query1 = MediaSearchQuery(title="Movie", year=2001, imdb_id="tt123")
        query2 = MediaSearchQuery(title="Movie", year=2001, imdb_id="tt123")
        
        key1 = cache._get_cache_key(query1)
        key2 = cache._get_cache_key(query2)
        
        assert key1 == key2
    
    @pytest.mark.asyncio 
    async def test_different_keys(self, temp_cache_dir):
        """Test that different queries generate different cache keys."""
        cache = FileBasedCache(temp_cache_dir)
        
        query1 = MediaSearchQuery(title="Movie A", year=2001)
        query2 = MediaSearchQuery(title="Movie B", year=2001)
        
        key1 = cache._get_cache_key(query1)
        key2 = cache._get_cache_key(query2)
        
        assert key1 != key2
    
    @pytest.mark.asyncio
    async def test_none_values_ignored(self, temp_cache_dir):
        """Test that None values don't affect cache keys."""
        cache = FileBasedCache(temp_cache_dir)
        
        query1 = MediaSearchQuery(title="Movie", year=2001, imdb_id=None)
        query2 = MediaSearchQuery(title="Movie", year=2001)
        
        key1 = cache._get_cache_key(query1)
        key2 = cache._get_cache_key(query2)
        
        assert key1 == key2


if __name__ == "__main__":
    pytest.main([__file__])