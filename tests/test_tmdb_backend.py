"""Tests for TMDb backend."""
import os
from unittest.mock import AsyncMock, patch

import pytest

from src.nhkprep.original_lang import MediaSearchQuery
from src.nhkprep.original_lang.tmdb import TMDbBackend


# Mock response data for testing
MOCK_MOVIE_SEARCH_RESPONSE = {
    "results": [
        {
            "id": 12345,
            "title": "Your Name",
            "release_date": "2016-08-26",
            "original_language": "ja"
        }
    ]
}

MOCK_MOVIE_DETAILS_RESPONSE = {
    "id": 12345,
    "title": "Your Name",
    "original_title": "君の名は。",
    "release_date": "2016-08-26",
    "original_language": "ja",
    "imdb_id": "tt5311514",
    "spoken_languages": [
        {"iso_639_1": "ja", "name": "Japanese"}
    ],
    "production_countries": [
        {"iso_3166_1": "JP", "name": "Japan"}
    ]
}

MOCK_FIND_BY_IMDB_RESPONSE = {
    "movie_results": [
        {
            "id": 12345,
            "title": "Your Name",
            "release_date": "2016-08-26"
        }
    ]
}


class TestTMDbBackend:
    """Tests for TMDb backend functionality."""
    
    def test_initialization_with_api_key(self):
        """Test backend initialization with API key."""
        backend = TMDbBackend(api_key="test_key")
        assert backend.api_key == "test_key"
        assert backend.name == "tmdb"
        assert backend.is_available()
    
    def test_initialization_without_api_key(self):
        """Test backend initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            backend = TMDbBackend()
            assert not backend.is_available()
    
    def test_initialization_with_env_var(self):
        """Test backend gets API key from environment variable."""
        with patch.dict(os.environ, {'TMDB_API_KEY': 'env_key'}):
            backend = TMDbBackend()
            assert backend.api_key == "env_key"
            assert backend.is_available()
    
    def test_rate_limiting_setup(self):
        """Test rate limiting is properly configured."""
        backend = TMDbBackend(api_key="test")
        assert backend.RATE_LIMIT_REQUESTS == 40
        assert backend.RATE_LIMIT_WINDOW == 10.0
        assert backend._request_times == []
    
    @pytest.mark.asyncio
    async def test_movie_search_success(self):
        """Test successful movie search and details retrieval."""
        backend = TMDbBackend(api_key="test_key")
        
        # Mock the HTTP requests
        with patch.object(backend, '_make_request') as mock_request:
            # First call: search movies
            # Second call: get movie details
            # Third call: search TV (no results)
            mock_request.side_effect = [
                MOCK_MOVIE_SEARCH_RESPONSE,
                MOCK_MOVIE_DETAILS_RESPONSE,
                {"results": []}  # Empty TV search results
            ]
            
            query = MediaSearchQuery(title="Your Name", year=2016)
            result = await backend.detect_original_language(query)
            
            assert result is not None
            assert result.original_language == "ja"
            assert result.source == "tmdb"
            assert result.method == "title_search"
            assert result.title == "Your Name"
            assert result.year == 2016
            assert result.confidence > 0.0
            assert "ja" in result.spoken_languages
            assert "JP" in result.production_countries
    
    @pytest.mark.asyncio
    async def test_imdb_id_lookup_success(self):
        """Test successful IMDb ID lookup."""
        backend = TMDbBackend(api_key="test_key")
        
        with patch.object(backend, '_make_request') as mock_request:
            # First call: find by IMDb ID
            # Second call: get movie details
            mock_request.side_effect = [
                MOCK_FIND_BY_IMDB_RESPONSE,
                MOCK_MOVIE_DETAILS_RESPONSE
            ]
            
            query = MediaSearchQuery(
                title="Your Name", 
                year=2016, 
                imdb_id="tt5311514"
            )
            result = await backend.detect_original_language(query)
            
            assert result is not None
            assert result.original_language == "ja"
            assert result.method == "imdb_id_match"
            assert result.imdb_id == "tt5311514"
            # ID matches should have higher confidence
            assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_no_results_found(self):
        """Test handling when no results are found."""
        backend = TMDbBackend(api_key="test_key")
        
        with patch.object(backend, '_make_request') as mock_request:
            # Return empty search results
            mock_request.return_value = {"results": []}
            
            query = MediaSearchQuery(title="Nonexistent Movie", year=2999)
            result = await backend.detect_original_language(query)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors."""
        backend = TMDbBackend(api_key="test_key")
        
        with patch.object(backend, '_make_request') as mock_request:
            # Simulate API error
            mock_request.return_value = None
            
            query = MediaSearchQuery(title="Test Movie", year=2020)
            result = await backend.detect_original_language(query)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_no_api_key_handling(self):
        """Test handling when no API key is available."""
        backend = TMDbBackend()  # No API key
        
        query = MediaSearchQuery(title="Test Movie", year=2020)
        result = await backend.detect_original_language(query)
        
        assert result is None
    
    def test_year_extraction(self):
        """Test year extraction from date strings."""
        backend = TMDbBackend(api_key="test")
        
        assert backend._extract_year("2016-08-26") == 2016
        assert backend._extract_year("2020-01-01") == 2020
        assert backend._extract_year("invalid") is None
        assert backend._extract_year(None) is None
        assert backend._extract_year("") is None
    
    @pytest.mark.asyncio
    async def test_rate_limiting_logic(self):
        """Test that rate limiting prevents too many concurrent requests."""
        backend = TMDbBackend(api_key="test_key")
        
        # Fill up the rate limit
        import time
        current_time = time.time()
        backend._request_times = [current_time] * backend.RATE_LIMIT_REQUESTS
        
        # This should trigger rate limiting
        start_time = time.time()
        await backend._rate_limit()
        end_time = time.time()
        
        # Should have waited some time
        elapsed = end_time - start_time
        assert elapsed > 0.0  # Should have waited at least a little
    
    @pytest.mark.asyncio
    async def test_client_cleanup(self):
        """Test HTTP client cleanup."""
        backend = TMDbBackend(api_key="test_key")
        
        # Create client
        client = await backend._get_client()
        assert client is not None
        assert backend._client is client
        
        # Close client
        await backend.close()
        assert backend._client is None


def test_mock_backend_integration():
    """Test that TMDb backend works with the main detection system."""
    from src.nhkprep.original_lang import OriginalLanguageDetector
    
    backend = TMDbBackend(api_key="test_key")
    detector = OriginalLanguageDetector()
    
    # Should be able to add backend
    detector.add_backend(backend)
    assert len(detector.backends) == 1
    
    print("✓ TMDb backend integrates correctly with detection system")


if __name__ == "__main__":
    test_mock_backend_integration()
    print("✅ TMDb backend tests completed!")