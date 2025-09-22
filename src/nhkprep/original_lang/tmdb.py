"""
TMDb (The Movie Database) backend for original language detection.

This backend uses TMDb's API v3 to detect original languages for movies and TV shows.
It supports both ID-based lookups (when available) and title/year searches.
"""

import asyncio
import os
import time
from typing import Any
from urllib.parse import quote

import httpx
from anyio import sleep

from ..config import RuntimeConfig
from . import OriginalLanguageDetection, MediaSearchQuery
from .base import BaseOriginalLanguageBackend


class TMDbBackend(BaseOriginalLanguageBackend):
    """TMDb API backend for original language detection."""
    
    # API configuration
    BASE_URL = "https://api.themoviedb.org/3"
    SEARCH_MOVIE_URL = f"{BASE_URL}/search/movie"
    SEARCH_TV_URL = f"{BASE_URL}/search/tv"
    MOVIE_DETAILS_URL = f"{BASE_URL}/movie"
    TV_DETAILS_URL = f"{BASE_URL}/tv"
    FIND_URL = f"{BASE_URL}/find"
    
    # Rate limiting (TMDb allows 40 requests per 10 seconds)
    RATE_LIMIT_REQUESTS = 40
    RATE_LIMIT_WINDOW = 10.0  # seconds
    
    def __init__(self, api_key: str | None = None, timeout: float = 10.0,
                 request_timeout: float | None = None, **kwargs):
        """
        Initialize TMDb backend.
        
        Args:
            api_key: TMDb API key. If None, will try to get from config/environment
            timeout: HTTP request timeout in seconds (legacy parameter)
            request_timeout: HTTP request timeout in seconds (new parameter from config)
            **kwargs: Additional config parameters (ignored for compatibility)
        """
        super().__init__("tmdb")
        
        self.api_key = api_key or self._get_api_key()
        # Use request_timeout if provided, otherwise fall back to timeout
        self.timeout = request_timeout if request_timeout is not None else timeout
        
        # Rate limiting state
        self._request_times: list[float] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # HTTP client configuration
        self._client: httpx.AsyncClient | None = None
    
    def _get_api_key(self) -> str | None:
        """Get API key from config or environment."""
        # Try to get from config first
        api_key = None
        try:
            config = RuntimeConfig()
            api_key = getattr(config, 'tmdb_api_key', None)
        except Exception:
            pass
        
        # If not found in config, try environment variable
        if api_key is None:
            api_key = os.environ.get('TMDB_API_KEY')
        
        return api_key
    
    def is_available(self) -> bool:
        """Check if TMDb backend is available (has API key)."""
        return self.api_key is not None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    'User-Agent': 'nhkprep/0.1.0 (https://github.com/beckmt4/nhkprep)',
                    'Accept': 'application/json',
                }
            )
        return self._client
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting before making requests."""
        async with self._rate_limit_lock:
            now = time.time()
            
            # Remove old request times outside the window
            self._request_times = [
                t for t in self._request_times 
                if now - t < self.RATE_LIMIT_WINDOW
            ]
            
            # If we're at the limit, wait
            if len(self._request_times) >= self.RATE_LIMIT_REQUESTS:
                oldest_request = min(self._request_times)
                wait_time = self.RATE_LIMIT_WINDOW - (now - oldest_request)
                if wait_time > 0:
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self._request_times.append(time.time())
    
    async def _make_request(self, url: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """
        Make rate-limited HTTP request to TMDb API.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            JSON response data or None on error
        """
        if not self.api_key:
            self.logger.error("No TMDb API key available")
            return None
        
        # Add API key to params
        params = {**params, 'api_key': self.api_key}
        
        # Apply rate limiting
        await self._rate_limit()
        
        try:
            client = await self._get_client()
            
            self.logger.debug(f"TMDb API request: {url} with params: {params}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"TMDb API response: {len(str(data))} chars")
            
            return data
            
        except httpx.HTTPError as e:
            self.logger.error(f"TMDb API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in TMDb request: {e}")
            return None
    
    async def _search_by_id(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Search using external IDs (IMDb, TMDb).
        
        Args:
            query: Search parameters with IDs
            
        Returns:
            Detection result or None
        """
        # Try IMDb ID first (more reliable)
        if query.imdb_id:
            params = {'external_source': 'imdb_id'}
            data = await self._make_request(f"{self.FIND_URL}/{query.imdb_id}", params)
            
            if data:
                # Check movie results
                movie_results = data.get('movie_results', [])
                if movie_results:
                    movie = movie_results[0]
                    return await self._get_movie_details(movie['id'], query, method="imdb_id_match")
                
                # Check TV results  
                tv_results = data.get('tv_results', [])
                if tv_results:
                    tv_show = tv_results[0]
                    return await self._get_tv_details(tv_show['id'], query, method="imdb_id_match")
        
        # Try TMDb ID directly
        if query.tmdb_id:
            try:
                tmdb_id = int(query.tmdb_id)
                
                # Try as movie first
                movie_result = await self._get_movie_details(tmdb_id, query, method="tmdb_id_match")
                if movie_result:
                    return movie_result
                
                # Try as TV show
                tv_result = await self._get_tv_details(tmdb_id, query, method="tmdb_id_match")
                if tv_result:
                    return tv_result
                    
            except ValueError:
                self.logger.warning(f"Invalid TMDb ID format: {query.tmdb_id}")
        
        return None
    
    async def _search_by_title(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Search by title and year.
        
        Args:
            query: Search parameters
            
        Returns:
            Detection result or None
        """
        if not query.title:
            return None
        
        # Search movies and TV shows sequentially for now
        movie_result = await self._search_movies(query)
        tv_result = await self._search_tv(query)
        
        # Return the result with higher confidence
        if movie_result and tv_result:
            return movie_result if movie_result.confidence >= tv_result.confidence else tv_result
        elif movie_result:
            return movie_result
        elif tv_result:
            return tv_result
        
        return None
    
    async def _search_movies(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """Search for movies by title."""
        params = {
            'query': query.title,
            'include_adult': 'true',  # Include all results
        }
        
        if query.year:
            params['year'] = str(query.year)
        
        data = await self._make_request(self.SEARCH_MOVIE_URL, params)
        if not data or not data.get('results'):
            return None
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for movie in data['results'][:5]:  # Check top 5 results
            movie_title = movie.get('title', '')
            if not movie_title or not query.title:
                continue
                
            title_score = self.calculate_title_similarity(
                query.title, 
                movie_title
            )
            
            # Boost score if year matches
            year_boost = 0.0
            if query.year and movie.get('release_date'):
                try:
                    movie_year = int(movie['release_date'][:4])
                    if movie_year == query.year:
                        year_boost = 0.2
                except (ValueError, IndexError):
                    pass
            
            total_score = title_score + year_boost
            
            if total_score > best_score:
                best_score = total_score
                best_match = movie
        
        if best_match and best_score > 0.3:  # Minimum similarity threshold
            return await self._get_movie_details(
                best_match['id'], 
                query, 
                method="title_search",
                found_title=best_match.get('title'),
                found_year=self._extract_year(best_match.get('release_date'))
            )
        
        return None
    
    async def _search_tv(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """Search for TV shows by title."""
        params = {
            'query': query.title,
            'include_adult': 'true',
        }
        
        if query.year:
            params['first_air_date_year'] = str(query.year)
        
        data = await self._make_request(self.SEARCH_TV_URL, params)
        if not data or not data.get('results'):
            return None
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for show in data['results'][:5]:  # Check top 5 results
            show_name = show.get('name', '')
            if not show_name or not query.title:
                continue
                
            title_score = self.calculate_title_similarity(
                query.title, 
                show_name
            )
            
            # Boost score if year matches
            year_boost = 0.0
            if query.year and show.get('first_air_date'):
                try:
                    show_year = int(show['first_air_date'][:4])
                    if show_year == query.year:
                        year_boost = 0.2
                except (ValueError, IndexError):
                    pass
            
            total_score = title_score + year_boost
            
            if total_score > best_score:
                best_score = total_score
                best_match = show
        
        if best_match and best_score > 0.3:  # Minimum similarity threshold
            return await self._get_tv_details(
                best_match['id'], 
                query, 
                method="title_search",
                found_title=best_match.get('name'),
                found_year=self._extract_year(best_match.get('first_air_date'))
            )
        
        return None
    
    async def _get_movie_details(
        self, 
        movie_id: int, 
        query: MediaSearchQuery, 
        method: str = "details_lookup",
        found_title: str | None = None,
        found_year: int | None = None
    ) -> OriginalLanguageDetection | None:
        """Get detailed movie information."""
        data = await self._make_request(f"{self.MOVIE_DETAILS_URL}/{movie_id}", {})
        if not data:
            return None
        
        original_language = data.get('original_language')
        if not original_language:
            return None
        
        # Calculate confidence
        confidence = self.determine_confidence(
            query=query,
            found_title=found_title or data.get('title'),
            found_year=found_year or self._extract_year(data.get('release_date')),
            match_type=method
        )
        
        # Extract additional metadata
        spoken_languages = [
            lang.get('iso_639_1') for lang in data.get('spoken_languages', [])
            if lang.get('iso_639_1')
        ]
        
        production_countries = [
            country.get('iso_3166_1') for country in data.get('production_countries', [])
            if country.get('iso_3166_1')
        ]
        
        return OriginalLanguageDetection(
            original_language=self.normalize_language_code(original_language),
            confidence=confidence,
            source="tmdb",
            method=method,
            details=f"Movie: {data.get('title')} ({self._extract_year(data.get('release_date'))})",
            title=data.get('title'),
            year=self._extract_year(data.get('release_date')),
            tmdb_id=str(movie_id),
            imdb_id=data.get('imdb_id'),
            spoken_languages=spoken_languages,
            production_countries=production_countries,
            api_response=data
        )
    
    async def _get_tv_details(
        self, 
        tv_id: int, 
        query: MediaSearchQuery, 
        method: str = "details_lookup",
        found_title: str | None = None,
        found_year: int | None = None
    ) -> OriginalLanguageDetection | None:
        """Get detailed TV show information."""
        data = await self._make_request(f"{self.TV_DETAILS_URL}/{tv_id}", {})
        if not data:
            return None
        
        original_language = data.get('original_language')
        if not original_language:
            return None
        
        # Calculate confidence
        confidence = self.determine_confidence(
            query=query,
            found_title=found_title or data.get('name'),
            found_year=found_year or self._extract_year(data.get('first_air_date')),
            match_type=method
        )
        
        # Extract additional metadata
        spoken_languages = [
            lang.get('iso_639_1') for lang in data.get('spoken_languages', [])
            if lang.get('iso_639_1')
        ]
        
        production_countries = [
            country.get('iso_3166_1') for country in data.get('production_countries', [])
            if country.get('iso_3166_1')
        ]
        
        return OriginalLanguageDetection(
            original_language=self.normalize_language_code(original_language),
            confidence=confidence,
            source="tmdb",
            method=method,
            details=f"TV: {data.get('name')} ({self._extract_year(data.get('first_air_date'))})",
            title=data.get('name'),
            year=self._extract_year(data.get('first_air_date')),
            tmdb_id=str(tv_id),
            spoken_languages=spoken_languages,
            production_countries=production_countries,
            api_response=data
        )
    
    def _extract_year(self, date_string: str | None) -> int | None:
        """Extract year from date string like '2016-08-26'."""
        if not date_string:
            return None
        
        try:
            return int(date_string[:4])
        except (ValueError, IndexError):
            return None
    
    async def detect_original_language(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Main detection method that tries multiple approaches.
        
        Priority:
        1. ID-based lookup (IMDb/TMDb ID)
        2. Title + year search
        
        Args:
            query: Media search parameters
            
        Returns:
            Detection result or None
        """
        if not self.is_available():
            self.logger.warning("TMDb backend not available (no API key)")
            return None
        
        start_time = time.time()
        
        try:
            # Try ID-based lookup first (most accurate)
            if query.imdb_id or query.tmdb_id:
                result = await self._search_by_id(query)
                if result:
                    result.detection_time_ms = (time.time() - start_time) * 1000
                    return result
            
            # Fall back to title search
            if query.title:
                result = await self._search_by_title(query)
                if result:
                    result.detection_time_ms = (time.time() - start_time) * 1000
                    return result
            
            self.logger.debug(f"No results found for query: {query.title}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in TMDb detection: {e}")
            return None
    
    async def close(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None