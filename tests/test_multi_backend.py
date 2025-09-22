"""Integration test for multiple backends working together."""
import asyncio
from unittest.mock import patch

import pytest

from src.nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from src.nhkprep.original_lang.tmdb import TMDbBackend
from src.nhkprep.original_lang.imdb import IMDbBackend


# Mock responses
MOCK_TMDB_SEARCH = {
    "results": [{
        "id": 12345,
        "title": "Your Name", 
        "release_date": "2016-08-26"
    }]
}

MOCK_TMDB_DETAILS = {
    "id": 12345,
    "title": "Your Name",
    "original_language": "ja",
    "release_date": "2016-08-26",
    "imdb_id": "tt5311514"
}

MOCK_IMDB_HTML = """
<html>
<body>
    <h1 data-testid="hero-title-block__title">Your Name</h1>
    <section data-testid="TechSpecs">
        <dt>Language:</dt>
        <dd>Japanese</dd>
    </section>
</body>
</html>
"""


class TestMultiBackendIntegration:
    """Test multiple backends working together."""
    
    @pytest.mark.asyncio
    async def test_tmdb_primary_imdb_fallback(self):
        """Test TMDb as primary with IMDb as fallback."""
        detector = OriginalLanguageDetector()
        
        # Add both backends - TMDb first (higher priority)
        tmdb_backend = TMDbBackend(api_key="test_key")
        imdb_backend = IMDbBackend()
        detector.add_backend(tmdb_backend)
        detector.add_backend(imdb_backend)
        
        assert len(detector.backends) == 2
        
        # Mock TMDb to succeed
        with patch.object(tmdb_backend, '_make_request') as mock_tmdb:
            mock_tmdb.side_effect = [MOCK_TMDB_SEARCH, MOCK_TMDB_DETAILS, {"results": []}]
            
            query = MediaSearchQuery(title="Your Name", year=2016)
            result = await detector.detect_from_query(query)
            
            # Should get result from TMDb (first backend)
            assert result is not None
            assert result.source == "tmdb"
            assert result.original_language == "ja"
            assert result.confidence > 0.0
    
    @pytest.mark.asyncio 
    async def test_imdb_fallback_when_tmdb_fails(self):
        """Test IMDb fallback when TMDb fails."""
        detector = OriginalLanguageDetector()
        
        # Add both backends
        tmdb_backend = TMDbBackend(api_key="test_key")
        imdb_backend = IMDbBackend()
        detector.add_backend(tmdb_backend)
        detector.add_backend(imdb_backend)
        
        # Mock TMDb to fail, IMDb to succeed
        with patch.object(tmdb_backend, '_make_request') as mock_tmdb, \
             patch.object(imdb_backend, '_make_request') as mock_imdb:
            
            # TMDb returns no results
            mock_tmdb.return_value = {"results": []}
            
            # IMDb returns results
            mock_imdb.return_value = MOCK_IMDB_HTML
            
            query = MediaSearchQuery(title="Your Name", year=2016, imdb_id="tt5311514")
            result = await detector.detect_from_query(query)
            
            # Should get result from IMDb (fallback)
            assert result is not None
            assert result.source == "imdb"
            assert result.original_language == "ja"
    
    @pytest.mark.asyncio
    async def test_no_api_key_tmdb_fallback_to_imdb(self):
        """Test fallback to IMDb when TMDb has no API key."""
        detector = OriginalLanguageDetector()
        
        # TMDb backend without API key (not available)
        tmdb_backend = TMDbBackend()  # No API key
        imdb_backend = IMDbBackend()
        
        # Only IMDb should be added (TMDb not available)
        detector.add_backend(tmdb_backend)
        detector.add_backend(imdb_backend)
        
        # Only IMDb should be available
        assert len(detector.backends) == 1
        assert detector.backends[0].name == "imdb"
        
        # Mock IMDb to succeed
        with patch.object(imdb_backend, '_make_request') as mock_imdb:
            mock_imdb.return_value = MOCK_IMDB_HTML
            
            query = MediaSearchQuery(title="Your Name", imdb_id="tt5311514")
            result = await detector.detect_from_query(query)
            
            assert result is not None
            assert result.source == "imdb"
    
    @pytest.mark.asyncio
    async def test_confidence_based_selection(self):
        """Test that higher confidence results are preferred."""
        detector = OriginalLanguageDetector()
        
        tmdb_backend = TMDbBackend(api_key="test_key") 
        imdb_backend = IMDbBackend()
        detector.add_backend(tmdb_backend)
        detector.add_backend(imdb_backend)
        
        # Mock both backends to return results with different confidence
        with patch.object(tmdb_backend, 'detect_original_language') as mock_tmdb, \
             patch.object(imdb_backend, 'detect_original_language') as mock_imdb:
            
            from src.nhkprep.original_lang import OriginalLanguageDetection
            
            # TMDb returns lower confidence
            mock_tmdb.return_value = OriginalLanguageDetection(
                original_language="ja",
                confidence=0.6, 
                source="tmdb",
                method="title_search"
            )
            
            # IMDb returns higher confidence
            mock_imdb.return_value = OriginalLanguageDetection(
                original_language="ja",
                confidence=0.9,
                source="imdb", 
                method="imdb_id_match"
            )
            
            query = MediaSearchQuery(title="Your Name", year=2016)
            result = await detector.detect_from_query(query, min_confidence=0.5)
            
            # Should prefer the higher confidence result (IMDb)
            assert result is not None
            assert result.source == "imdb"
            assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_both_backends_fail(self):
        """Test when both backends fail to find results."""
        detector = OriginalLanguageDetector()
        
        tmdb_backend = TMDbBackend(api_key="test_key")
        imdb_backend = IMDbBackend()
        detector.add_backend(tmdb_backend)
        detector.add_backend(imdb_backend)
        
        # Mock both to return None
        with patch.object(tmdb_backend, 'detect_original_language') as mock_tmdb, \
             patch.object(imdb_backend, 'detect_original_language') as mock_imdb:
            
            mock_tmdb.return_value = None
            mock_imdb.return_value = None
            
            query = MediaSearchQuery(title="Nonexistent Movie", year=2099)
            result = await detector.detect_from_query(query)
            
            assert result is None
    
    def test_backend_priority_order(self):
        """Test that backends maintain priority order."""
        detector = OriginalLanguageDetector()
        
        tmdb_backend = TMDbBackend(api_key="test_key")
        imdb_backend = IMDbBackend()
        
        # Add in specific order
        detector.add_backend(tmdb_backend)
        detector.add_backend(imdb_backend)
        
        # Should maintain order
        assert len(detector.backends) == 2
        assert detector.backends[0].name == "tmdb"
        assert detector.backends[1].name == "imdb"


def test_multi_backend_setup():
    """Test setting up multiple backends."""
    detector = OriginalLanguageDetector()
    
    # Add both backends
    tmdb_backend = TMDbBackend(api_key="test_api_key")
    imdb_backend = IMDbBackend()
    
    detector.add_backend(tmdb_backend)
    detector.add_backend(imdb_backend)
    
    assert len(detector.backends) == 2
    assert detector.backends[0].name == "tmdb"
    assert detector.backends[1].name == "imdb"
    
    print("✓ Multiple backend integration works correctly")


if __name__ == "__main__":
    test_multi_backend_setup()
    print("✅ Multi-backend integration tests completed!")