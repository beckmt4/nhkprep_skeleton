"""Integration tests for detector with caching."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.nhkprep.original_lang import OriginalLanguageDetection, MediaSearchQuery
from src.nhkprep.original_lang.config import OriginalLanguageConfig, create_detector_from_runtime_config
from src.nhkprep.config import RuntimeConfig


@pytest.fixture
def temp_cache_dir():
    """Temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_detection():
    """Sample detection result."""
    return OriginalLanguageDetection(
        original_language="ja",
        confidence=0.95,
        source="test",
        method="mock",
        details="Test detection",
        title="Test Movie",
        year=2001
    )


class MockBackend:
    """Mock backend for testing."""
    
    def __init__(self, name="mock", available=True, detection_result=None):
        self.name = name
        self.available = available
        self.detection_result = detection_result
        self.call_count = 0
    
    def is_available(self):
        return self.available
    
    async def detect_original_language(self, query):
        self.call_count += 1
        return self.detection_result


@pytest.mark.asyncio
class TestDetectorCaching:
    """Test detector behavior with caching enabled."""

    async def test_cache_hit_avoids_backend_calls(self, temp_cache_dir, sample_detection):
        """Test that cache hits avoid calling backends."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=temp_cache_dir,
            cache_ttl=3600
        )
        
        # Create detector and mock backend
        from src.nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        mock_backend = MockBackend("mock", available=True, detection_result=sample_detection)
        detector.add_backend(mock_backend)
        
        query = MediaSearchQuery(title="Test Movie", year=2001)
        
        # First call should hit backend
        result1 = await detector.detect_from_query(query)
        assert result1 is not None
        assert result1.original_language == "ja"
        assert mock_backend.call_count == 1
        
        # Second call should hit cache
        result2 = await detector.detect_from_query(query)
        assert result2 is not None
        assert result2.original_language == "ja"
        assert mock_backend.call_count == 1  # No additional backend calls

    async def test_cache_miss_calls_backend(self, temp_cache_dir, sample_detection):
        """Test that cache misses still call backends."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=temp_cache_dir,
            cache_ttl=3600
        )
        
        from src.nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        mock_backend = MockBackend("mock", available=True, detection_result=sample_detection)
        detector.add_backend(mock_backend)
        
        query1 = MediaSearchQuery(title="Movie 1", year=2001)
        query2 = MediaSearchQuery(title="Movie 2", year=2002)
        
        # Different queries should both hit backend
        result1 = await detector.detect_from_query(query1)
        result2 = await detector.detect_from_query(query2)
        
        assert result1 is not None
        assert result2 is not None
        assert mock_backend.call_count == 2

    async def test_cache_disabled_always_calls_backend(self, sample_detection):
        """Test behavior when caching is disabled."""
        config = OriginalLanguageConfig(cache_enabled=False)
        
        from src.nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        mock_backend = MockBackend("mock", available=True, detection_result=sample_detection)
        detector.add_backend(mock_backend)
        
        query = MediaSearchQuery(title="Test Movie", year=2001)
        
        # Multiple calls should all hit backend when caching disabled
        await detector.detect_from_query(query)
        await detector.detect_from_query(query)
        await detector.detect_from_query(query)
        
        assert mock_backend.call_count == 3

    async def test_low_confidence_not_cached(self, temp_cache_dir):
        """Test that low confidence results are not cached."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=temp_cache_dir,
            confidence_threshold=0.8
        )
        
        from src.nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        low_confidence_result = OriginalLanguageDetection(
            original_language="en",
            confidence=0.3,  # Below threshold
            source="mock",
            method="test"
        )
        
        mock_backend = MockBackend("mock", available=True, detection_result=low_confidence_result)
        detector.add_backend(mock_backend)
        
        query = MediaSearchQuery(title="Test Movie", year=2001)
        
        # First call returns None due to low confidence
        result1 = await detector.detect_from_query(query)
        assert result1 is None
        assert mock_backend.call_count == 1
        
        # Second call should still hit backend (no caching of low confidence)
        result2 = await detector.detect_from_query(query)
        assert result2 is None
        assert mock_backend.call_count == 2

    async def test_cache_management_methods(self, temp_cache_dir, sample_detection):
        """Test cache management methods."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=temp_cache_dir
        )
        
        from src.nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        mock_backend = MockBackend("mock", available=True, detection_result=sample_detection)
        detector.add_backend(mock_backend)
        
        query = MediaSearchQuery(title="Test Movie", year=2001)
        
        # Add something to cache
        await detector.detect_from_query(query)
        
        # Test cache stats
        stats = await detector.get_cache_stats()
        assert stats['total_entries'] >= 1
        assert stats['active_entries'] >= 1
        
        # Test delete from cache
        deleted = await detector.delete_from_cache(query)
        assert deleted is True
        
        # Test cleanup
        cleanup_count = await detector.cleanup_cache()
        assert cleanup_count >= 0
        
        # Test clear cache
        await detector.detect_from_query(query)  # Add back to cache
        clear_count = await detector.clear_cache()
        assert clear_count >= 1

    async def test_cache_with_runtime_config(self, temp_cache_dir):
        """Test detector created from runtime config uses caching."""
        runtime_config = RuntimeConfig(
            orig_lang_cache_enabled=True,
            orig_lang_cache_dir=temp_cache_dir,
            orig_lang_cache_ttl=1800
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        # Verify cache is properly configured
        stats = await detector.get_cache_stats()
        assert 'cache_dir' in stats
        assert str(temp_cache_dir) in stats['cache_dir']

    async def test_filename_detection_with_caching(self, temp_cache_dir, sample_detection):
        """Test that filename-based detection also uses caching."""
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=temp_cache_dir
        )
        
        from src.nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        mock_backend = MockBackend("mock", available=True, detection_result=sample_detection)
        detector.add_backend(mock_backend)
        
        filename = "Spirited Away (2001).mkv"
        
        # First call should hit backend
        result1 = await detector.detect_from_filename(filename)
        assert result1 is not None
        assert mock_backend.call_count == 1
        
        # Second call should hit cache
        result2 = await detector.detect_from_filename(filename)
        assert result2 is not None
        assert mock_backend.call_count == 1  # No additional calls


if __name__ == "__main__":
    pytest.main([__file__])