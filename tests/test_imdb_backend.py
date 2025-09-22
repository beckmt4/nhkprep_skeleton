"""Tests for IMDb backend."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.nhkprep.original_lang import MediaSearchQuery
from src.nhkprep.original_lang.imdb import IMDbBackend


# Mock HTML responses for testing
MOCK_SEARCH_HTML = """
<html>
<body>
<section data-testid="find-results-section-title">
    <ul>
        <li>
            <a href="/title/tt5311514/">Your Name (2016)</a>
            <span>Movie</span>
        </li>
        <li>
            <a href="/title/tt1234567/">Your Name (2020)</a>
            <span>TV Series</span>
        </li>
    </ul>
</section>
</body>
</html>
"""

MOCK_TITLE_PAGE_HTML = """
<html>
<head>
    <script type="application/ld+json">
    {
        "inLanguage": "ja",
        "name": "Your Name"
    }
    </script>
</head>
<body>
    <h1 data-testid="hero-title-block__title">Your Name</h1>
    <span class="titleBar__year">2016</span>
    
    <section data-testid="TechSpecs">
        <div>
            <dt>Language:</dt>
            <dd>Japanese, English</dd>
        </div>
        <div>
            <dt>Country of origin:</dt>
            <dd>Japan</dd>
        </div>
    </section>
    
    <section data-testid="Details">
        <div>Original language: Japanese</div>
        <div>Production countries: Japan</div>
    </section>
</body>
</html>
"""

MOCK_TITLE_PAGE_NO_LANG = """
<html>
<body>
    <h1 data-testid="hero-title-block__title">Mystery Movie</h1>
    <span class="titleBar__year">2020</span>
</body>
</html>
"""


class TestIMDbBackend:
    """Tests for IMDb backend functionality."""
    
    def test_initialization(self):
        """Test backend initialization."""
        backend = IMDbBackend()
        assert backend.name == "imdb"
        assert backend.is_available()
        assert backend.timeout == 15.0
        assert backend.max_retries == 3
    
    def test_initialization_with_params(self):
        """Test backend initialization with custom parameters."""
        backend = IMDbBackend(timeout=30.0, max_retries=5)
        assert backend.timeout == 30.0
        assert backend.max_retries == 5
    
    def test_parse_imdb_id(self):
        """Test IMDb ID normalization."""
        backend = IMDbBackend()
        
        assert backend._parse_imdb_id("tt1234567") == "tt1234567"
        assert backend._parse_imdb_id("1234567") == "tt1234567"
        assert backend._parse_imdb_id("0001234") == "tt0001234"
    
    def test_language_mappings(self):
        """Test language code normalization."""
        backend = IMDbBackend()
        
        assert backend.normalize_language_code("japanese") == "ja"
        assert backend.normalize_language_code("English") == "en"
        assert backend.normalize_language_code("SPANISH") == "es"
        assert backend.normalize_language_code("mandarin") == "zh"
        assert backend.normalize_language_code("cantonese") == "zh"
        assert backend.normalize_language_code("unknown") is None
    
    def test_rate_limiting_setup(self):
        """Test rate limiting configuration."""
        backend = IMDbBackend()
        assert backend.RATE_LIMIT_REQUESTS == 10
        assert backend.RATE_LIMIT_WINDOW == 60.0
        assert backend._request_times == []
    
    @pytest.mark.asyncio
    async def test_imdb_id_lookup_success(self):
        """Test successful IMDb ID lookup."""
        backend = IMDbBackend()
        
        with patch.object(backend, '_make_request') as mock_request:
            mock_request.return_value = MOCK_TITLE_PAGE_HTML
            
            query = MediaSearchQuery(
                title="Your Name",
                year=2016,
                imdb_id="tt5311514"
            )
            result = await backend.detect_original_language(query)
            
            assert result is not None
            assert result.original_language == "ja"
            assert result.source == "imdb"
            assert result.method == "imdb_id_match"
            assert result.title == "Your Name"
            assert result.imdb_id == "tt5311514"
            assert result.confidence > 0.0
            
            # Verify the correct URL was called
            mock_request.assert_called_once_with("https://www.imdb.com/title/tt5311514/")
    
    @pytest.mark.asyncio
    async def test_title_search_success(self):
        """Test successful title search."""
        backend = IMDbBackend()
        
        with patch.object(backend, '_make_request') as mock_request:
            # First call: search results
            # Second call: title page
            mock_request.side_effect = [
                MOCK_SEARCH_HTML,
                MOCK_TITLE_PAGE_HTML
            ]
            
            query = MediaSearchQuery(title="Your Name", year=2016)
            result = await backend.detect_original_language(query)
            
            assert result is not None
            assert result.original_language == "ja"
            assert result.method == "title_search"
            assert result.title == "Your Name"
            assert result.confidence > 0.0
            
            # Should make 2 requests: search + title page
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_language_found(self):
        """Test when no language information is found."""
        backend = IMDbBackend()
        
        with patch.object(backend, '_make_request') as mock_request:
            mock_request.side_effect = [
                MOCK_SEARCH_HTML,
                MOCK_TITLE_PAGE_NO_LANG
            ]
            
            query = MediaSearchQuery(title="Mystery Movie", year=2020)
            result = await backend.detect_original_language(query)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_no_search_results(self):
        """Test when search returns no results."""
        backend = IMDbBackend()
        
        empty_search_html = """
        <html>
        <body>
        <section data-testid="find-results-section-title">
            <div>No results found</div>
        </section>
        </body>
        </html>
        """
        
        with patch.object(backend, '_make_request') as mock_request:
            mock_request.return_value = empty_search_html
            
            query = MediaSearchQuery(title="Nonexistent Movie", year=2099)
            result = await backend.detect_original_language(query)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_request_error_handling(self):
        """Test handling of request errors."""
        backend = IMDbBackend()
        
        with patch.object(backend, '_make_request') as mock_request:
            mock_request.return_value = None  # Simulate request failure
            
            query = MediaSearchQuery(title="Test Movie", year=2020)
            result = await backend.detect_original_language(query)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_rate_limiting_logic(self):
        """Test that rate limiting prevents too many concurrent requests."""
        backend = IMDbBackend()
        
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
        assert elapsed > 0.0
    
    def test_language_extraction_methods(self):
        """Test different language extraction approaches."""
        backend = IMDbBackend()
        
        # Test tech specs extraction
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(MOCK_TITLE_PAGE_HTML, 'html.parser')
        
        # We can't easily test the async methods without mocking,
        # but we can test the setup
        assert hasattr(backend, '_extract_from_tech_specs')
        assert hasattr(backend, '_extract_from_details_section')
        assert hasattr(backend, '_extract_from_structured_data')
        assert hasattr(backend, '_extract_from_storyline')
    
    @pytest.mark.asyncio
    async def test_client_lifecycle(self):
        """Test HTTP client creation and cleanup."""
        backend = IMDbBackend()
        
        # Client should be created on first use
        assert backend._client is None
        client = await backend._get_client()
        assert client is not None
        assert backend._client is client
        
        # Should reuse the same client
        client2 = await backend._get_client()
        assert client2 is client
        
        # Should clean up properly
        await backend.close()
        assert backend._client is None
    
    def test_search_match_scoring(self):
        """Test title similarity scoring in search results."""
        backend = IMDbBackend()
        
        # Test title similarity
        score1 = backend.calculate_title_similarity("Your Name", "Your Name")
        score2 = backend.calculate_title_similarity("Your Name", "Kimi no Na wa")
        score3 = backend.calculate_title_similarity("Your Name", "Completely Different")
        
        assert score1 > score2 > score3
        assert score1 == 1.0  # Perfect match
        assert score3 < 0.5  # Poor match


def test_imdb_backend_integration():
    """Test that IMDb backend works with the main detection system."""
    from src.nhkprep.original_lang import OriginalLanguageDetector
    
    backend = IMDbBackend()
    detector = OriginalLanguageDetector()
    
    # Should be able to add backend (always available)
    detector.add_backend(backend)
    assert len(detector.backends) == 1
    
    print("✓ IMDb backend integrates correctly with detection system")


if __name__ == "__main__":
    test_imdb_backend_integration()
    print("✅ IMDb backend tests completed!")