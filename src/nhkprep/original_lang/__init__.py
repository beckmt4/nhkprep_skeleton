"""
Original Language Detection API

Core data structures and interfaces for detecting the original language of media content
using external APIs like TMDb and IMDb.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..filename_parser import ParsedFilename

logger = logging.getLogger(__name__)


@dataclass
class OriginalLanguageDetection:
    """Result of original language detection for a media file."""
    
    # Primary result
    original_language: str | None = None  # ISO 639-1 code (e.g., 'ja', 'en')
    confidence: float = 0.0  # 0.0 to 1.0
    
    # Source information
    source: str = ""  # 'tmdb', 'imdb', 'filename', etc.
    method: str = ""  # 'id_match', 'title_year_match', 'fuzzy_match', etc.
    details: str = ""  # Human-readable explanation
    
    # Media metadata
    title: str | None = None
    year: int | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    
    # Additional languages (for multi-language content)
    spoken_languages: list[str] = field(default_factory=list)  # All languages spoken in the content
    production_countries: list[str] = field(default_factory=list)  # ISO country codes
    
    # API response metadata
    api_response: dict[str, Any] = field(default_factory=dict)  # Raw API response for debugging
    detection_time_ms: float = 0.0  # Time taken for detection
    timestamp: datetime = field(default_factory=datetime.now)  # When detection was performed
    
    def __post_init__(self):
        """Validate and normalize the detection result."""
        if self.original_language:
            # Normalize language code to lowercase ISO 639-1 format
            self.original_language = self.original_language.lower()
        
        # Ensure confidence is in valid range
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def is_reliable(self, threshold: float = 0.7) -> bool:
        """Check if the detection result is reliable above the given threshold."""
        return self.confidence >= threshold
    
    def matches_expected_language(self, expected: str) -> bool:
        """Check if the detected language matches an expected language."""
        if not self.original_language or not expected:
            return False
        return self.original_language.lower() == expected.lower()


@dataclass 
class MediaSearchQuery:
    """Query parameters for searching media in external APIs."""
    
    # Core search terms
    title: str | None = None
    year: int | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    
    # Media type
    media_type: str = "movie"  # 'movie' or 'tv'
    
    # TV-specific
    season: int | None = None
    episode: int | None = None
    
    # Search options
    fuzzy_match: bool = True  # Allow fuzzy title matching
    include_adult: bool = False  # Include adult content in search
    
    @classmethod
    def from_parsed_filename(cls, parsed: ParsedFilename) -> "MediaSearchQuery":
        """Create a search query from a parsed filename."""
        return cls(
            title=parsed.title,
            year=parsed.year,
            imdb_id=parsed.imdb_id,
            tmdb_id=parsed.tmdb_id,
            media_type="tv" if parsed.is_tv_show else "movie",
            season=parsed.season,
            episode=parsed.episode
        )
    
    def has_id(self) -> bool:
        """Check if the query has a direct ID (IMDb or TMDb)."""
        return bool(self.imdb_id or self.tmdb_id)
    
    def has_title(self) -> bool:
        """Check if the query has searchable title information."""
        return bool(self.title)


class OriginalLanguageBackend(ABC):
    """Abstract base class for original language detection backends."""
    
    def __init__(self, name: str):
        """Initialize backend with a name identifier."""
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def detect_original_language(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Detect the original language for a media query.
        
        Args:
            query: Media search parameters
            
        Returns:
            Detection result or None if not found/error
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available and properly configured."""
        pass
    
    def _create_detection_result(
        self, 
        original_language: str | None = None,
        confidence: float = 0.0,
        method: str = "",
        details: str = "",
        **kwargs
    ) -> OriginalLanguageDetection:
        """Helper to create a detection result with this backend as source."""
        return OriginalLanguageDetection(
            original_language=original_language,
            confidence=confidence,
            source=self.name,
            method=method,
            details=details,
            **kwargs
        )


class OriginalLanguageDetector:
    """Main detector that orchestrates multiple backends."""
    
    def __init__(self, config=None):
        """Initialize with optional configuration."""
        from .config import OriginalLanguageConfig
        from .cache import create_cache_from_config
        
        self.config = config if config is not None else OriginalLanguageConfig()
        self.backends: list[OriginalLanguageBackend] = []
        self.cache = create_cache_from_config(self.config)
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        issues = self.config.validate()
        if issues:
            self.logger.warning(f"Configuration issues: {', '.join(issues)}")
    
    def add_backend(self, backend: OriginalLanguageBackend) -> None:
        """Add a backend to the detection pipeline."""
        if backend.is_available():
            self.backends.append(backend)
            self.logger.debug(f"Added backend: {backend.name}")
        else:
            self.logger.warning(f"Backend not available: {backend.name}")
    
    def setup_default_backends(self) -> None:
        """Set up backends based on configuration."""
        if not self.config.enabled:
            self.logger.info("Original language detection is disabled")
            return
        
        available_backends = self.config.get_available_backends()
        self.logger.debug(f"Setting up backends: {available_backends}")
        
        for backend_name in available_backends:
            try:
                if backend_name == "tmdb":
                    from .tmdb import TMDbBackend
                    backend_config = self.config.get_backend_config("tmdb")
                    backend = TMDbBackend(**backend_config)
                    self.add_backend(backend)
                elif backend_name == "imdb":
                    from .imdb import IMDbBackend
                    backend_config = self.config.get_backend_config("imdb")
                    backend = IMDbBackend(**backend_config)
                    self.add_backend(backend)
            except Exception as e:
                self.logger.error(f"Failed to initialize {backend_name} backend: {e}")
    
    async def detect_from_filename(
        self, 
        filename: str,
        min_confidence: float | None = None
    ) -> OriginalLanguageDetection | None:
        """
        Detect original language from a filename.
        
        Args:
            filename: Media filename to analyze
            min_confidence: Minimum confidence threshold (uses config default if None)
            
        Returns:
            Best detection result above threshold or None
        """
        from ..filename_parser import parse_filename
        
        if not self.config.enabled:
            return None
        
        effective_min_confidence = min_confidence if min_confidence is not None else self.config.confidence_threshold
        
        start_time = time.time()
        
        # Parse filename to extract search terms
        parsed = parse_filename(filename)
        query = MediaSearchQuery.from_parsed_filename(parsed)
        
        self.logger.debug(f"Detecting original language for: {filename}")
        self.logger.debug(f"Parsed as: {parsed.title} ({parsed.year}) - {query.media_type}")
        
        return await self._detect_with_timeout(query, effective_min_confidence, start_time)
    
    async def detect_from_query(
        self,
        query: MediaSearchQuery,
        min_confidence: float | None = None
    ) -> OriginalLanguageDetection | None:
        """
        Detect original language from a search query.
        
        Args:
            query: Media search parameters
            min_confidence: Minimum confidence threshold (uses config default if None)
            
        Returns:
            Best detection result above threshold or None
        """
        if not self.config.enabled:
            return None
        
        effective_min_confidence = min_confidence if min_confidence is not None else self.config.confidence_threshold
        
        start_time = time.time()
        
        self.logger.debug(f"Detecting from query: {query.title} ({query.year})")
        
        return await self._detect_with_timeout(query, effective_min_confidence, start_time)
    
    async def _detect_with_timeout(
        self,
        query: MediaSearchQuery,
        min_confidence: float,
        start_time: float
    ) -> OriginalLanguageDetection | None:
        """Internal method to handle detection with timeout and caching."""
        import asyncio
        
        # Try cache first
        cached_result = await self.cache.get(query)
        if cached_result and cached_result.confidence >= min_confidence:
            self.logger.debug(f"Using cached result for query: {query.title}")
            cached_result.detection_time_ms = (time.time() - start_time) * 1000
            return cached_result
        
        try:
            # Create detection task with timeout
            detection_task = asyncio.create_task(
                self._try_backends(query, min_confidence)
            )
            
            result = await asyncio.wait_for(
                detection_task, 
                timeout=self.config.total_timeout
            )
            
            # Add timing information
            if result:
                result.detection_time_ms = (time.time() - start_time) * 1000
                
                # Cache the result
                try:
                    await self.cache.set(query, result)
                    self.logger.debug(f"Cached detection result for: {query.title}")
                except Exception as e:
                    self.logger.warning(f"Failed to cache result: {e}")
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Detection timed out after {self.config.total_timeout}s")
            return None
    
    async def _try_backends(
        self,
        query: MediaSearchQuery,
        min_confidence: float
    ) -> OriginalLanguageDetection | None:
        """Try backends in order until we get a good result."""
        # Ensure we have backends set up
        if not self.backends:
            self.setup_default_backends()
        
        best_result = None
        
        for backend in self.backends[:self.config.max_backends]:
            try:
                result = await backend.detect_original_language(query)
                if result and result.confidence >= min_confidence:
                    if not best_result or result.confidence > best_result.confidence:
                        best_result = result
                        # If we get a perfect match, stop searching
                        if result.confidence >= 1.0:
                            break
            except Exception as e:
                self.logger.error(f"Backend {backend.name} failed: {e}")
        
        return best_result
    
    def get_available_backends(self) -> list[str]:
        """Get list of available backend names."""
        return [backend.name for backend in self.backends if backend.is_available()]
    
    async def clear_cache(self) -> int:
        """Clear all cached detection results."""
        count = await self.cache.clear()
        self.logger.info(f"Cleared {count} cached entries")
        return count
    
    async def cleanup_cache(self) -> int:
        """Remove expired cache entries."""
        count = await self.cache.cleanup()
        if count > 0:
            self.logger.info(f"Cleaned up {count} expired cache entries")
        return count
    
    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return await self.cache.stats()
    
    async def delete_from_cache(self, query: MediaSearchQuery) -> bool:
        """Delete a specific query from cache."""
        return await self.cache.delete(query)


# Convenience functions for common use cases

def detect_original_language_from_filename(
    filename: str,
    backends: list[OriginalLanguageBackend] | None = None,
    min_confidence: float = 0.5
) -> OriginalLanguageDetection | None:
    """
    Convenience function to detect original language from a filename.
    
    Args:
        filename: Media filename to analyze
        backends: List of backends to use (None for default)
        min_confidence: Minimum confidence threshold
        
    Returns:
        Detection result or None
    """
    import asyncio
    
    detector = OriginalLanguageDetector()
    
    if backends:
        for backend in backends:
            detector.add_backend(backend)
    
    return asyncio.run(detector.detect_from_filename(filename, min_confidence))


# Example usage and testing
if __name__ == "__main__":
    # This will be extended when we add actual backends
    
    # Test data structure creation
    query = MediaSearchQuery(
        title="Spirited Away",
        year=2001,
        media_type="movie"
    )
    
    print(f"Query: {query}")
    print(f"Has ID: {query.has_id()}")
    print(f"Has title: {query.has_title()}")
    
    # Test detection result creation
    detection = OriginalLanguageDetection(
        original_language="ja",
        confidence=0.95,
        source="tmdb",
        method="exact_match",
        details="Found exact match by title and year",
        title="Sen to Chihiro no Kamikakushi",
        year=2001,
        spoken_languages=["ja"],
        production_countries=["JP"]
    )
    
    print(f"\nDetection: {detection}")
    print(f"Is reliable: {detection.is_reliable()}")
    print(f"Matches 'ja': {detection.matches_expected_language('ja')}")
    print(f"Matches 'en': {detection.matches_expected_language('en')}")