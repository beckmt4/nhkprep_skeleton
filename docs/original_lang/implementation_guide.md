# Implementation Guide

This document provides an in-depth guide to implementing the Original Language Detection system in your own projects.

## Overview

The Original Language Detection system consists of several components that work together to detect the original production language of media files. This guide will walk through implementing each component.

## Prerequisite Knowledge

Before starting implementation, you should have:

1. Basic understanding of Python async/await patterns
2. Familiarity with HTTP requests and API consumption
3. Understanding of regex patterns for filename parsing
4. Knowledge of caching strategies

## Implementation Steps

### Step 1: Create Core Data Structures

Start by creating the basic data structures that represent queries and results:

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class MediaSearchQuery:
    """Container for media search parameters."""
    title: Optional[str] = None
    year: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    media_type: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if the query has valid search parameters."""
        return any([
            self.title is not None,
            self.imdb_id is not None,
            self.tmdb_id is not None
        ])

@dataclass
class OriginalLanguageResult:
    """Container for language detection results."""
    original_language: str
    confidence: float
    source: str
    method: str
    title: Optional[str] = None
    year: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    detection_time_ms: Optional[float] = None
```

### Step 2: Define Exceptions

Create custom exceptions for error handling:

```python
class OriginalLanguageError(Exception):
    """Base exception for original language detection errors."""
    pass

class OriginalLanguageBackendError(OriginalLanguageError):
    """Error in a language detection backend."""
    pass

class OriginalLanguageConfigError(OriginalLanguageError):
    """Invalid configuration for language detection."""
    pass

class OriginalLanguageParseError(OriginalLanguageError):
    """Error parsing filename or other data."""
    pass
```

### Step 3: Implement Configuration

Create the configuration class:

```python
import os
from typing import List, Optional

class OriginalLanguageConfig:
    """Configuration for original language detection."""
    
    def __init__(
        self,
        tmdb_api_key: Optional[str] = None,
        backend_priorities: Optional[List[str]] = None,
        max_backends: int = 2,
        confidence_threshold: float = 0.5,
        cache_enabled: bool = True,
        cache_ttl: int = 86400,  # 1 day
        cache_dir: Optional[str] = None,
        max_cache_size_mb: Optional[int] = None,
        request_timeout: float = 10.0
    ):
        """Initialize configuration."""
        # Store API key
        self._tmdb_api_key = tmdb_api_key
        
        # Set backend priorities
        self.backend_priorities = backend_priorities or ["tmdb", "imdb"]
        
        # Validate backend names
        for backend in self.backend_priorities:
            if backend not in ["tmdb", "imdb"]:
                raise OriginalLanguageConfigError(f"Invalid backend: {backend}")
        
        # Store other settings
        self.max_backends = max(1, min(max_backends, len(self.backend_priorities)))
        self.confidence_threshold = max(0.0, min(confidence_threshold, 1.0))
        self.cache_enabled = cache_enabled and not os.environ.get("NHKPREP_CACHE_DISABLED") == "1"
        self.cache_ttl = max(1, cache_ttl)
        self.max_cache_size_mb = max_cache_size_mb
        self.request_timeout = max(1.0, request_timeout)
        
        # Set cache directory
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            home = os.path.expanduser("~")
            base_cache = os.environ.get("NHKPREP_CACHE_DIR", os.path.join(home, ".cache", "nhkprep"))
            self.cache_dir = os.environ.get("NHKPREP_ORIGINAL_LANG_CACHE_DIR", 
                                          os.path.join(base_cache, "original_lang"))
    
    def get_tmdb_api_key(self) -> Optional[str]:
        """Get TMDb API key from config or environment."""
        return self._tmdb_api_key or os.environ.get("TMDB_API_KEY")
```

### Step 4: Implement Filename Parser

Create the parser for extracting information from filenames:

```python
import re
from typing import Optional

class OriginalLanguageFilenameParser:
    """Parses media filenames to extract useful information."""
    
    # Regex patterns for different filename formats
    PATTERNS = [
        # Movie Title (2023).mkv
        re.compile(r"^(.*?) \((\d{4})\)\..*$"),
        
        # Movie.Title.2023.1080p.mkv
        re.compile(r"^(.*?)\.(\d{4})\..*$"),
        
        # Movie_Title_[2023].mkv
        re.compile(r"^(.*?)_\[(\d{4})\]\..*$"),
    ]
    
    # IMDb ID pattern - matches tt0123456 in various formats
    IMDB_PATTERNS = [
        re.compile(r"tt(\d{7,8})"),  # Basic IMDb ID
        re.compile(r"\[tt(\d{7,8})\]"),  # [tt1234567]
        re.compile(r"\(tt(\d{7,8})\)"),  # (tt1234567)
    ]
    
    @staticmethod
    def parse(filename: str) -> MediaSearchQuery:
        """Parse a filename to extract media information."""
        # Try to extract IMDb ID first (most reliable)
        imdb_id = OriginalLanguageFilenameParser.extract_imdb_id(filename)
        
        # Try to match patterns for title and year
        for pattern in OriginalLanguageFilenameParser.PATTERNS:
            match = pattern.match(filename)
            if match:
                title = OriginalLanguageFilenameParser.clean_title(match.group(1))
                try:
                    year = int(match.group(2))
                    return MediaSearchQuery(title=title, year=year, imdb_id=imdb_id)
                except (ValueError, IndexError):
                    pass  # Continue to next pattern
        
        # If we get here, try just extracting the title
        if "." in filename:
            parts = filename.split(".")
            if len(parts) > 1:
                title = OriginalLanguageFilenameParser.clean_title(".".join(parts[:-1]))
                return MediaSearchQuery(title=title, imdb_id=imdb_id)
        
        # Last resort: use filename without extension as title
        title = OriginalLanguageFilenameParser.clean_title(
            os.path.splitext(filename)[0]
        )
        
        if not title and not imdb_id:
            raise OriginalLanguageParseError(f"Could not parse filename: {filename}")
        
        return MediaSearchQuery(title=title, imdb_id=imdb_id)
    
    @staticmethod
    def clean_title(title: str) -> str:
        """Clean a title extracted from filename."""
        # Replace dots, underscores with spaces
        title = title.replace(".", " ").replace("_", " ")
        
        # Remove common tags and quality indicators
        patterns = [
            r"\b(720p|1080p|2160p|4K|HDTV|WEB-DL|BluRay|x264|x265|HEVC)\b",
            r"\b(REPACK|PROPER|EXTENDED|UNRATED|DIRECTORS|CUT)\b",
        ]
        
        for pattern in patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)
        
        # Remove extra spaces and trim
        title = " ".join(title.split())
        
        return title
    
    @staticmethod
    def extract_imdb_id(filename: str) -> Optional[str]:
        """Extract IMDb ID from filename if present."""
        for pattern in OriginalLanguageFilenameParser.IMDB_PATTERNS:
            match = pattern.search(filename)
            if match:
                return f"tt{match.group(1)}"
        return None
```

### Step 5: Define Backend Interface

Create the abstract base class for backends:

```python
from abc import ABC, abstractmethod
from typing import Optional

class OriginalLanguageBackend(ABC):
    """Abstract base class for original language detection backends."""
    
    @abstractmethod
    async def detect_language(
        self, 
        query: MediaSearchQuery
    ) -> Optional[OriginalLanguageResult]:
        """Detect the original language of media."""
        pass
    
    @abstractmethod
    def supports_query(self, query: MediaSearchQuery) -> bool:
        """Check if this backend can handle the given query."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the backend."""
        pass
```

### Step 6: Implement TMDb Backend

Create the TMDb API backend:

```python
import httpx
import time
import asyncio
from typing import Dict, Any, Optional, List

class TMDbBackend(OriginalLanguageBackend):
    """Backend that uses TMDb API for language detection."""
    
    # Base URLs for TMDb API
    BASE_URL = "https://api.themoviedb.org/3"
    
    # Language confidence scores (higher for more reliable sources)
    CONFIDENCE = {
        "tmdb_id": 0.95,  # Direct TMDb ID lookup
        "imdb_id": 0.90,  # IMDb ID lookup via TMDb
        "title_year": 0.80,  # Title + year match
        "title_only": 0.70,  # Title-only match
    }
    
    def __init__(self, config: OriginalLanguageConfig):
        """Initialize TMDb backend."""
        self.api_key = config.get_tmdb_api_key()
        if not self.api_key:
            raise OriginalLanguageConfigError("No TMDb API key provided")
        
        self.timeout = config.request_timeout
        self._last_request = 0
        self._request_delay = 0.25  # Minimum 250ms between requests
    
    @property
    def name(self) -> str:
        """Get backend name."""
        return "tmdb"
    
    def supports_query(self, query: MediaSearchQuery) -> bool:
        """Check if query can be handled by TMDb."""
        return (
            query.tmdb_id is not None or
            query.imdb_id is not None or
            query.title is not None
        )
    
    async def detect_language(
        self, 
        query: MediaSearchQuery
    ) -> Optional[OriginalLanguageResult]:
        """Detect language using TMDb API."""
        if not self.supports_query(query):
            return None
        
        start_time = time.time()
        item = None
        method = "unknown"
        confidence = 0.0
        
        try:
            # Try TMDb ID if available (most accurate)
            if query.tmdb_id:
                media_type = query.media_type or "movie"
                item = await self._get_by_id(query.tmdb_id, media_type)
                method = "tmdb_id"
                confidence = self.CONFIDENCE["tmdb_id"]
            
            # Try IMDb ID if available and TMDb ID failed
            elif query.imdb_id:
                item = await self._find_by_imdb_id(query.imdb_id)
                method = "imdb_id"
                confidence = self.CONFIDENCE["imdb_id"]
            
            # Try title search as last resort
            elif query.title:
                item = await self._search_by_title(query.title, query.year, query.media_type)
                if item:
                    method = "title_year" if query.year else "title_only"
                    confidence = self.CONFIDENCE[method]
            
            # Extract and return result
            if item and "original_language" in item:
                detection_time = (time.time() - start_time) * 1000
                
                # Create result
                return OriginalLanguageResult(
                    original_language=item["original_language"],
                    confidence=confidence,
                    source="tmdb",
                    method=method,
                    title=item.get("title") or item.get("name"),
                    year=self._extract_year(item),
                    tmdb_id=item.get("id"),
                    imdb_id=item.get("imdb_id") or query.imdb_id,
                    details={"tmdb_data": item},
                    detection_time_ms=detection_time
                )
            
            return None
        
        except httpx.HTTPError as e:
            raise OriginalLanguageBackendError(f"TMDb API error: {e}")
    
    async def _search_by_title(
        self, 
        title: str, 
        year: Optional[int] = None,
        media_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Search TMDb by title."""
        # Default to movie search
        endpoint = "/search/movie" if media_type != "tv" else "/search/tv"
        
        # Build params
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "en-US"
        }
        
        # Add year if available
        if year:
            if media_type != "tv":
                params["year"] = year
            else:
                params["first_air_date_year"] = year
        
        # Make request
        results = await self._make_request(endpoint, params)
        if not results or not results.get("results"):
            return None
        
        # Get first result
        result = results["results"][0]
        
        # Get full details
        if result.get("id"):
            item_type = "movie" if media_type != "tv" else "tv"
            return await self._get_by_id(result["id"], item_type)
        
        return result
    
    async def _get_by_id(
        self, 
        tmdb_id: int,
        media_type: Optional[str] = "movie"
    ) -> Optional[Dict[str, Any]]:
        """Get TMDb item by ID."""
        item_type = "movie" if media_type != "tv" else "tv"
        endpoint = f"/{item_type}/{tmdb_id}"
        
        params = {
            "api_key": self.api_key,
            "language": "en-US",
            "append_to_response": "external_ids"
        }
        
        return await self._make_request(endpoint, params)
    
    async def _find_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """Find TMDb item by IMDb ID."""
        endpoint = f"/find/{imdb_id}"
        
        params = {
            "api_key": self.api_key,
            "language": "en-US",
            "external_source": "imdb_id"
        }
        
        results = await self._make_request(endpoint, params)
        if not results:
            return None
        
        # Check movie results first
        if results.get("movie_results") and len(results["movie_results"]) > 0:
            tmdb_id = results["movie_results"][0]["id"]
            return await self._get_by_id(tmdb_id, "movie")
        
        # Then check TV results
        if results.get("tv_results") and len(results["tv_results"]) > 0:
            tmdb_id = results["tv_results"][0]["id"]
            return await self._get_by_id(tmdb_id, "tv")
        
        return None
    
    async def _make_request(
        self, 
        endpoint: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Make an API request with rate limiting."""
        # Rate limiting
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self._request_delay:
            await asyncio.sleep(self._request_delay - elapsed)
        
        url = f"{self.BASE_URL}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            self._last_request = time.time()
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get("Retry-After", "1"))
                raise OriginalLanguageBackendError(
                    f"TMDb rate limit exceeded. Retry after {retry_after} seconds."
                )
            elif response.status_code == 401:
                raise OriginalLanguageBackendError("Invalid TMDb API key")
            elif response.status_code == 404:
                return None  # Not found
            else:
                raise OriginalLanguageBackendError(
                    f"TMDb API error: {response.status_code} - {response.text}"
                )
    
    @staticmethod
    def _extract_year(item: Dict[str, Any]) -> Optional[int]:
        """Extract release year from TMDb item."""
        # For movies
        if "release_date" in item and item["release_date"]:
            try:
                return int(item["release_date"].split("-")[0])
            except (ValueError, IndexError):
                pass
        
        # For TV shows
        if "first_air_date" in item and item["first_air_date"]:
            try:
                return int(item["first_air_date"].split("-")[0])
            except (ValueError, IndexError):
                pass
        
        return None
```

### Step 7: Implement IMDb Backend

Create the IMDb scraping backend:

```python
import httpx
import time
import asyncio
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

class IMDbBackend(OriginalLanguageBackend):
    """Backend that scrapes IMDb for language detection."""
    
    # Base URLs for IMDb
    BASE_URL = "https://www.imdb.com"
    TITLE_URL = "https://www.imdb.com/title/"
    SEARCH_URL = "https://www.imdb.com/find"
    
    # Language confidence scores
    CONFIDENCE = {
        "imdb_id": 0.85,  # Direct IMDb ID lookup
        "search": 0.70,   # Search result
    }
    
    # Map of common language names to ISO codes
    LANGUAGE_MAP = {
        "english": "en",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "japanese": "ja",
        "korean": "ko",
        "mandarin": "zh",
        "cantonese": "zh",
        "russian": "ru",
        # Add more as needed
    }
    
    def __init__(self, config: OriginalLanguageConfig):
        """Initialize IMDb backend."""
        self.timeout = config.request_timeout
        self._last_request = 0
        self._request_delay = 1.0  # 1 second between requests to avoid rate limiting
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    @property
    def name(self) -> str:
        """Get backend name."""
        return "imdb"
    
    def supports_query(self, query: MediaSearchQuery) -> bool:
        """Check if query can be handled by IMDb."""
        return (
            query.imdb_id is not None or
            query.title is not None
        )
    
    async def detect_language(
        self, 
        query: MediaSearchQuery
    ) -> Optional[OriginalLanguageResult]:
        """Detect language by scraping IMDb."""
        if not self.supports_query(query):
            return None
        
        start_time = time.time()
        method = "unknown"
        confidence = 0.0
        data = None
        
        try:
            # Direct IMDb ID lookup (more reliable)
            if query.imdb_id:
                data = await self._get_by_imdb_id(query.imdb_id)
                method = "imdb_id"
                confidence = self.CONFIDENCE["imdb_id"]
            
            # Search by title if no IMDb ID
            elif query.title:
                data = await self._search_by_title(query.title, query.year)
                method = "search"
                confidence = self.CONFIDENCE["search"]
            
            # Process result
            if data and data.get("language"):
                detection_time = (time.time() - start_time) * 1000
                
                return OriginalLanguageResult(
                    original_language=data["language"],
                    confidence=confidence,
                    source="imdb",
                    method=method,
                    title=data.get("title"),
                    year=data.get("year"),
                    imdb_id=data.get("imdb_id") or query.imdb_id,
                    details={"imdb_data": data},
                    detection_time_ms=detection_time
                )
            
            return None
        
        except httpx.HTTPError as e:
            raise OriginalLanguageBackendError(f"IMDb request error: {e}")
    
    async def _get_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """Get IMDb details by ID."""
        # Ensure proper format
        if not imdb_id.startswith("tt"):
            imdb_id = f"tt{imdb_id}"
        
        url = f"{self.TITLE_URL}{imdb_id}/"
        html = await self._make_request(url)
        
        if not html:
            return None
        
        # Extract info from HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract data
        result = {
            "imdb_id": imdb_id
        }
        
        # Extract title
        title_elem = soup.select_one("h1")
        if title_elem:
            result["title"] = title_elem.get_text().strip()
        
        # Extract year
        year_pattern = re.compile(r"\b(19\d{2}|20\d{2})\b")
        year_elem = soup.select_one("span.TitleBlockMetaData__StyledTextLink-sc-*")
        if year_elem:
            year_match = year_pattern.search(year_elem.get_text())
            if year_match:
                try:
                    result["year"] = int(year_match.group(1))
                except ValueError:
                    pass
        
        # Extract language from details section
        language = await self._extract_language(html)
        if language:
            result["language"] = language
        
        return result
    
    async def _search_by_title(
        self, 
        title: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Search IMDb by title."""
        params = {
            "q": f"{title}" + (f" {year}" if year else ""),
            "s": "tt",  # Search titles
            "ttype": "ft"  # Feature films
        }
        
        url = f"{self.SEARCH_URL}"
        html = await self._make_request(url, params)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Find first result
        result_elem = soup.select_one("li.ipc-metadata-list-summary-item")
        if not result_elem:
            return None
        
        # Extract IMDb ID
        link_elem = result_elem.select_one("a")
        if not link_elem or not link_elem.get("href"):
            return None
        
        href = link_elem["href"]
        imdb_id_match = re.search(r"/title/(tt\d+)", href)
        if not imdb_id_match:
            return None
        
        imdb_id = imdb_id_match.group(1)
        
        # Get full details
        return await self._get_by_imdb_id(imdb_id)
    
    async def _extract_language(self, html_content: str) -> Optional[str]:
        """Extract language from IMDb HTML."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Look for language information in details section
        language_section = None
        
        # Try different selectors based on IMDb layout
        detail_items = soup.select("li[data-testid='title-details-languages'], li.ipc-inline-list__item")
        for item in detail_items:
            text = item.get_text().lower()
            if "language" in text:
                language_section = item
                break
        
        if not language_section:
            return None
        
        # Extract language text
        language_text = language_section.get_text().lower()
        
        # Try to find one of our known languages
        for lang_name, lang_code in self.LANGUAGE_MAP.items():
            if lang_name in language_text:
                return lang_code
        
        # If we can't map it, try to extract the language name
        # and return as-is (limited fallback)
        lang_match = re.search(r"language[s]?\s*:\s*(\w+)", language_text)
        if lang_match:
            lang_name = lang_match.group(1).lower()
            return self.LANGUAGE_MAP.get(lang_name, lang_name[:2])
        
        return None
    
    async def _make_request(
        self, 
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Make an HTTP request with rate limiting."""
        # Rate limiting
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self._request_delay:
            await asyncio.sleep(self._request_delay - elapsed)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            self._last_request = time.time()
            response = await client.get(url, params=params, headers=self._headers)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get("Retry-After", "5"))
                raise OriginalLanguageBackendError(
                    f"IMDb rate limit exceeded. Retry after {retry_after} seconds."
                )
            elif response.status_code == 404:
                return None  # Not found
            else:
                raise OriginalLanguageBackendError(
                    f"IMDb request error: {response.status_code}"
                )
```

### Step 8: Implement Cache Manager

Create the cache management system:

```python
import os
import json
import time
from typing import Dict, Any, Optional
import asyncio

class OriginalLanguageCacheManager:
    """Manages caching of language detection results."""
    
    def __init__(self, config: OriginalLanguageConfig):
        """Initialize cache manager."""
        self.enabled = config.cache_enabled
        self.ttl = config.cache_ttl
        self.cache_dir = config.cache_dir
        self.max_size_mb = config.max_cache_size_mb
        
        # Create cache directory if it doesn't exist
        if self.enabled and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # In-memory cache for faster lookups
        self._memory_cache = {}
        
        # Cache stats
        self._hits = 0
        self._misses = 0
        
        # Cache file
        self._cache_file = os.path.join(self.cache_dir, "language_cache.json")
        
        # Cache lock
        self._lock = asyncio.Lock()
    
    async def get(
        self, 
        query: MediaSearchQuery
    ) -> Optional[OriginalLanguageResult]:
        """Get cached result for query."""
        if not self.enabled:
            return None
        
        key = query.get_cache_key()
        
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() < entry.get("expires_at", 0):
                self._hits += 1
                return entry.get("result")
        
        # Load from disk cache
        async with self._lock:
            cache_data = await self._load_cache_file()
            entries = cache_data.get("entries", {})
            
            if key in entries:
                entry = entries[key]
                
                # Check if expired
                if time.time() < entry.get("expires_at", 0):
                    # Update memory cache
                    self._memory_cache[key] = entry
                    
                    # Convert to result object
                    result_dict = entry.get("result", {})
                    if result_dict:
                        self._hits += 1
                        return OriginalLanguageResult(**result_dict)
            
        # Cache miss
        self._misses += 1
        return None
    
    async def set(
        self, 
        query: MediaSearchQuery,
        result: OriginalLanguageResult
    ) -> None:
        """Cache a detection result."""
        if not self.enabled:
            return
        
        key = query.get_cache_key()
        expires_at = time.time() + self.ttl
        
        # Convert result to dict
        result_dict = result.__dict__
        
        # Create cache entry
        entry = {
            "key": key,
            "query": {k: v for k, v in query.__dict__.items()},
            "result": result_dict,
            "created_at": time.time(),
            "expires_at": expires_at
        }
        
        # Update memory cache
        self._memory_cache[key] = entry
        
        # Update disk cache
        async with self._lock:
            cache_data = await self._load_cache_file()
            entries = cache_data.get("entries", {})
            entries[key] = entry
            cache_data["entries"] = entries
            await self._save_cache_file(cache_data)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {
                "enabled": False,
                "total_entries": 0,
                "active_entries": 0,
                "disk_usage_mb": 0,
                "hit_count": 0,
                "miss_count": 0
            }
        
        async with self._lock:
            cache_data = await self._load_cache_file()
            entries = cache_data.get("entries", {})
            
            # Count active entries
            now = time.time()
            active_entries = sum(
                1 for entry in entries.values() 
                if now < entry.get("expires_at", 0)
            )
            
            # Get file size if exists
            size_mb = 0
            if os.path.exists(self._cache_file):
                size_mb = os.path.getsize(self._cache_file) / (1024 * 1024)
            
            return {
                "enabled": self.enabled,
                "total_entries": len(entries),
                "active_entries": active_entries,
                "disk_usage_mb": size_mb,
                "hit_count": self._hits,
                "miss_count": self._misses
            }
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        if not self.enabled:
            return 0
        
        async with self._lock:
            cache_data = await self._load_cache_file()
            entries = cache_data.get("entries", {})
            count = len(entries)
            
            # Clear entries
            cache_data["entries"] = {}
            await self._save_cache_file(cache_data)
            
            # Clear memory cache
            self._memory_cache.clear()
            
            return count
    
    async def _load_cache_file(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if not os.path.exists(self._cache_file):
            return {"entries": {}, "version": 1}
        
        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If cache file is corrupt or can't be read, return empty cache
            return {"entries": {}, "version": 1}
    
    async def _save_cache_file(self, data: Dict[str, Any]) -> None:
        """Save cache to disk."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            
            # Cleanup old entries if max size is specified
            if self.max_size_mb:
                entries = data.get("entries", {})
                now = time.time()
                
                # Remove expired entries
                for key, entry in list(entries.items()):
                    if now >= entry.get("expires_at", 0):
                        del entries[key]
                
                # Check if we need to clean up further based on size
                estimated_size = len(json.dumps(data)) / (1024 * 1024)
                if estimated_size > self.max_size_mb:
                    # Sort by expiration time (closest first)
                    sorted_entries = sorted(
                        entries.items(),
                        key=lambda x: x[1].get("expires_at", 0)
                    )
                    
                    # Remove older entries until we're under the limit
                    while estimated_size > self.max_size_mb * 0.8 and sorted_entries:
                        key, _ = sorted_entries.pop(0)
                        del entries[key]
                        # Recalculate estimated size
                        estimated_size = len(json.dumps(data)) / (1024 * 1024)
            
            # Write cache file
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except IOError:
            # If we can't write to the cache file, just continue without caching
            pass
```

### Step 9: Implement Main Detector

Finally, create the main detector class:

```python
import time
from typing import List, Dict, Any, Optional

class OriginalLanguageDetector:
    """Detects the original language of media files using various backends."""
    
    def __init__(self, config: OriginalLanguageConfig):
        """Initialize the detector with configuration."""
        self.config = config
        
        # Initialize cache manager
        self.cache_manager = OriginalLanguageCacheManager(config)
        
        # Initialize backends based on configuration
        self._backends = []
        self._initialize_backends()
    
    async def detect_from_filename(self, filename: str) -> Optional[OriginalLanguageResult]:
        """Detect the original language of a media file based on its filename."""
        try:
            # Parse filename to get query parameters
            query = OriginalLanguageFilenameParser.parse(filename)
            
            # Detect using query
            return await self.detect_from_query(query)
            
        except OriginalLanguageParseError as e:
            raise ValueError(f"Failed to parse filename: {e}")
    
    async def detect_from_query(self, query: MediaSearchQuery) -> Optional[OriginalLanguageResult]:
        """Detect the original language based on a media search query."""
        if not query.is_valid():
            raise ValueError("Invalid query: no search parameters provided")
        
        # Check cache first
        cached_result = await self.cache_manager.get(query)
        if cached_result:
            return cached_result
        
        # Try each backend in priority order
        results = []
        used_backends = 0
        
        for backend in self._backends:
            if used_backends >= self.config.max_backends:
                break
            
            if backend.supports_query(query):
                try:
                    result = await backend.detect_language(query)
                    if result:
                        results.append(result)
                        used_backends += 1
                except Exception as e:
                    # Log error but continue with other backends
                    print(f"Error in {backend.name} backend: {e}")
        
        # Find best result based on confidence
        best_result = None
        for result in results:
            if (not best_result or result.confidence > best_result.confidence):
                best_result = result
        
        # Only return results above threshold
        if best_result and best_result.confidence >= self.config.confidence_threshold:
            # Cache result
            await self.cache_manager.set(query, best_result)
            return best_result
        
        return None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.cache_manager.get_stats()
    
    async def clear_cache(self) -> int:
        """Clear all cache entries."""
        return await self.cache_manager.clear()
    
    def _initialize_backends(self) -> None:
        """Initialize backends based on configuration."""
        backends = []
        
        for backend_name in self.config.backend_priorities:
            if backend_name == "tmdb":
                try:
                    backends.append(TMDbBackend(self.config))
                except OriginalLanguageConfigError:
                    # Skip if API key not available
                    pass
            elif backend_name == "imdb":
                backends.append(IMDbBackend(self.config))
        
        self._backends = backends
```

### Step 10: Implement CLI Integration

Create the CLI command implementation:

```python
import argparse
import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

class OriginalLanguageCommand:
    """CLI command for original language detection."""
    
    @staticmethod
    def add_parser(subparsers):
        """Add parser for the original-lang command."""
        parser = subparsers.add_parser(
            "original-lang",
            help="Detect original language of media files"
        )
        
        # File arguments
        parser.add_argument(
            "files",
            nargs="*",
            help="Media files to analyze"
        )
        
        # Scan directory
        parser.add_argument(
            "--scan",
            metavar="DIR",
            help="Scan a directory for media files"
        )
        
        # Configuration options
        parser.add_argument(
            "--tmdb-key",
            help="TMDb API key (overrides environment variable)"
        )
        parser.add_argument(
            "--backend",
            choices=["tmdb", "imdb", "both"],
            help="Backend to use (default: both)"
        )
        parser.add_argument(
            "--confidence",
            type=float,
            help="Confidence threshold (0.0-1.0)"
        )
        
        # Cache options
        parser.add_argument(
            "--no-cache",
            action="store_true",
            help="Disable caching"
        )
        parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Clear cache before detection"
        )
        
        # Output options
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results in JSON format"
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show more detailed information"
        )
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Minimize output"
        )
        
        parser.set_defaults(func=OriginalLanguageCommand.run)
        return parser
    
    @staticmethod
    async def run(args):
        """Run the command with parsed arguments."""
        # Get files list
        files = args.files
        
        # Scan directory if requested
        if args.scan:
            if not args.quiet:
                print(f"Scanning directory: {args.scan}")
            
            path = Path(args.scan)
            if not path.is_dir():
                print(f"Error: {args.scan} is not a directory", file=sys.stderr)
                return 1
            
            for ext in ['mkv', 'mp4', 'avi', 'mov', 'm4v']:
                files.extend([str(f) for f in path.glob(f"*.{ext}")])
            
            if not args.quiet:
                print(f"Found {len(files)} media files")
        
        # Read from stdin if no files specified
        if not files:
            if not sys.stdin.isatty():
                files = [line.strip() for line in sys.stdin if line.strip()]
        
        if not files:
            print("Error: No files specified", file=sys.stderr)
            return 1
        
        # Create configuration
        from nhkprep.original_lang.config import OriginalLanguageConfig
        
        config_args = {}
        
        if args.tmdb_key:
            config_args["tmdb_api_key"] = args.tmdb_key
        
        if args.backend:
            if args.backend == "tmdb":
                config_args["backend_priorities"] = ["tmdb"]
                config_args["max_backends"] = 1
            elif args.backend == "imdb":
                config_args["backend_priorities"] = ["imdb"]
                config_args["max_backends"] = 1
            else:  # both
                config_args["backend_priorities"] = ["tmdb", "imdb"]
                config_args["max_backends"] = 2
        
        if args.confidence is not None:
            config_args["confidence_threshold"] = args.confidence
        
        if args.no_cache:
            config_args["cache_enabled"] = False
        
        config = OriginalLanguageConfig(**config_args)
        
        # Create detector
        from nhkprep.original_lang import OriginalLanguageDetector
        detector = OriginalLanguageDetector(config)
        
        # Clear cache if requested
        if args.clear_cache:
            removed = await detector.clear_cache()
            if not args.quiet:
                print(f"Cleared {removed} cache entries")
        
        # Process files
        results = []
        failure = False
        
        for file in files:
            try:
                filename = os.path.basename(file)
                result = await detector.detect_from_filename(filename)
                
                if result:
                    results.append({
                        "file": file,
                        "filename": filename,
                        "language": result.original_language,
                        "confidence": result.confidence,
                        "source": result.source,
                        "title": result.title,
                        "year": result.year,
                        "imdb_id": result.imdb_id
                    })
                    
                    if not args.json and not args.quiet:
                        print(f"File: {filename}")
                        print(f"  Language: {result.original_language}")
                        print(f"  Confidence: {result.confidence:.3f}")
                        print(f"  Source: {result.source}")
                        
                        if args.verbose:
                            print(f"  Title: {result.title}")
                            if result.year:
                                print(f"  Year: {result.year}")
                            if result.imdb_id:
                                print(f"  IMDb ID: {result.imdb_id}")
                        
                        print()
                else:
                    results.append({
                        "file": file,
                        "filename": filename,
                        "error": "No language detected"
                    })
                    
                    if not args.json and not args.quiet:
                        print(f"File: {filename}")
                        print("  No language detected")
                        print()
                    
                    failure = True
            
            except Exception as e:
                results.append({
                    "file": file,
                    "filename": os.path.basename(file),
                    "error": str(e)
                })
                
                if not args.json and not args.quiet:
                    print(f"Error: {file}: {e}")
                
                failure = True
        
        # Output summary
        if args.json:
            # Calculate statistics
            languages = {}
            detected_count = 0
            
            for result in results:
                if "language" in result:
                    lang = result["language"]
                    languages[lang] = languages.get(lang, 0) + 1
                    detected_count += 1
            
            # Create output
            output = {
                "results": results,
                "summary": {
                    "total_files": len(files),
                    "detected_languages": detected_count,
                    "language_distribution": languages
                }
            }
            
            # Output JSON
            print(json.dumps(output, indent=2))
        
        elif not args.quiet and len(files) > 1:
            # Count languages
            languages = {}
            detected = 0
            
            for result in results:
                if "language" in result:
                    lang = result["language"]
                    languages[lang] = languages.get(lang, 0) + 1
                    detected += 1
            
            # Print summary
            print("Summary:")
            print(f"- Total files: {len(files)}")
            print(f"- Detected languages: {detected}")
            
            if languages:
                print("- Language distribution:")
                for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {lang}: {count}")
        
        return 1 if failure else 0
```

### Step 11: Register Command with CLI

Register the command in your CLI system:

```python
# In your CLI entry point
def register_commands(subparsers):
    from nhkprep.original_lang.cli.command import OriginalLanguageCommand
    OriginalLanguageCommand.add_parser(subparsers)
```

## Testing and Validation

After implementing the components, test the system with these steps:

1. **Unit Testing**: Create tests for individual components
2. **Integration Testing**: Test the full pipeline with various filenames
3. **Performance Testing**: Verify caching works and improves performance
4. **Error Handling**: Test with invalid inputs and error conditions

## Performance Optimization Tips

1. Use async/await for all I/O operations
2. Implement proper rate limiting for API requests
3. Use the cache effectively
4. Prioritize backends based on reliability and performance
5. Implement intelligent fallbacks

## Security Considerations

1. Store API keys securely, preferably in environment variables
2. Sanitize all user inputs before using in API requests
3. Implement proper error handling for all network operations
4. Be respectful of API rate limits

## Common Implementation Challenges

1. **IMDb Layout Changes**: IMDb often changes its HTML structure, which can break scraping. Keep your selectors flexible.
2. **Rate Limiting**: Both TMDb and IMDb enforce rate limits. Implement proper backoff strategies.
3. **Cache Invalidation**: Decide when to invalidate cache entries when new information is available.
4. **Filename Parsing Complexity**: Media filenames come in many formats. Test with a wide variety of real-world examples.

## Conclusion

By following this implementation guide, you can create a robust Original Language Detection system that efficiently detects the original language of media files using multiple data sources and intelligent fallbacks.