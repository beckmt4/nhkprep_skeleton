"""Configuration management for original language detection."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING
import os
import tempfile

if TYPE_CHECKING:
    from ..config import RuntimeConfig
    from .detector import OriginalLanguageDetector


@dataclass
class OriginalLanguageConfig:
    """Configuration for original language detection system."""
    
    # Core settings
    enabled: bool = True
    tmdb_api_key: Optional[str] = None
    backend_priorities: List[str] = field(default_factory=lambda: ["tmdb", "imdb"])
    confidence_threshold: float = 0.7
    max_backends: int = 2
    
    # Rate limiting
    tmdb_rate_limit: int = 40
    tmdb_rate_window: int = 10
    imdb_rate_limit: int = 10
    imdb_rate_window: int = 60
    
    # Caching
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None
    cache_ttl: int = 86400
    cache_max_size: int = 1000
    
    # Search settings
    search_max_results: int = 10
    year_tolerance: int = 1
    title_similarity_threshold: float = 0.8
    
    # Timeouts
    request_timeout: float = 30.0
    total_timeout: float = 120.0
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.cache_dir is None:
            self.cache_dir = Path(tempfile.gettempdir()) / "nhkprep" / "orig_lang_cache"
        
        # Create cache directory if it doesn't exist
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_runtime_config(cls, config: 'RuntimeConfig') -> 'OriginalLanguageConfig':
        """Create OriginalLanguageConfig from RuntimeConfig."""
        return cls(
            enabled=config.orig_lang_enabled,
            tmdb_api_key=config.orig_lang_tmdb_api_key or os.getenv("TMDB_API_KEY"),
            backend_priorities=config.orig_lang_backend_priorities.copy(),
            confidence_threshold=config.orig_lang_confidence_threshold,
            max_backends=config.orig_lang_max_backends,
            tmdb_rate_limit=config.orig_lang_tmdb_rate_limit,
            tmdb_rate_window=config.orig_lang_tmdb_rate_window,
            imdb_rate_limit=config.orig_lang_imdb_rate_limit,
            imdb_rate_window=config.orig_lang_imdb_rate_window,
            cache_enabled=config.orig_lang_cache_enabled,
            cache_dir=config.orig_lang_cache_dir,
            cache_ttl=config.orig_lang_cache_ttl,
            cache_max_size=config.orig_lang_cache_max_size,
            search_max_results=config.orig_lang_search_max_results,
            year_tolerance=config.orig_lang_year_tolerance,
            title_similarity_threshold=config.orig_lang_title_similarity_threshold,
            request_timeout=config.orig_lang_request_timeout,
            total_timeout=config.orig_lang_total_timeout,
        )
    
    def get_backend_config(self, backend_name: str) -> Dict:
        """Get configuration for a specific backend."""
        if backend_name == "tmdb":
            return {
                "api_key": self.tmdb_api_key,
                "rate_limit": self.tmdb_rate_limit,
                "rate_window": self.tmdb_rate_window,
                "max_results": self.search_max_results,
                "year_tolerance": self.year_tolerance,
                "request_timeout": self.request_timeout,
            }
        elif backend_name == "imdb":
            return {
                "rate_limit": self.imdb_rate_limit,
                "rate_window": self.imdb_rate_window,
                "max_results": self.search_max_results,
                "year_tolerance": self.year_tolerance,
                "request_timeout": self.request_timeout,
            }
        else:
            raise ValueError(f"Unknown backend: {backend_name}")
    
    def is_backend_available(self, backend_name: str) -> bool:
        """Check if a backend is available and properly configured."""
        if not self.enabled:
            return False
        
        if backend_name == "tmdb":
            return self.tmdb_api_key is not None
        elif backend_name == "imdb":
            return True  # IMDb backend doesn't require API key
        else:
            return False
    
    def get_available_backends(self) -> List[str]:
        """Get list of available backends in priority order."""
        if not self.enabled:
            return []
        
        available = []
        for backend in self.backend_priorities:
            if self.is_backend_available(backend):
                available.append(backend)
        
        return available[:self.max_backends]
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            issues.append("confidence_threshold must be between 0 and 1")
        
        if self.max_backends < 1:
            issues.append("max_backends must be at least 1")
        
        if self.title_similarity_threshold < 0 or self.title_similarity_threshold > 1:
            issues.append("title_similarity_threshold must be between 0 and 1")
        
        if self.year_tolerance < 0:
            issues.append("year_tolerance must be non-negative")
        
        if self.cache_ttl < 0:
            issues.append("cache_ttl must be non-negative")
        
        if self.request_timeout <= 0:
            issues.append("request_timeout must be positive")
        
        if self.total_timeout <= 0:
            issues.append("total_timeout must be positive")
        
        if self.total_timeout < self.request_timeout:
            issues.append("total_timeout should be greater than request_timeout")
        
        valid_backends = {"tmdb", "imdb"}
        invalid_backends = set(self.backend_priorities) - valid_backends
        if invalid_backends:
            issues.append(f"Invalid backends: {invalid_backends}")
        
        if not self.get_available_backends() and self.enabled:
            issues.append("No available backends (check API keys and configuration)")
        
        return issues


def create_detector_from_runtime_config(runtime_config: 'RuntimeConfig') -> 'OriginalLanguageDetector':
    """Create and configure an OriginalLanguageDetector from RuntimeConfig."""
    orig_config = OriginalLanguageConfig.from_runtime_config(runtime_config)
    
    # Import here to avoid circular imports
    from . import OriginalLanguageDetector
    
    # Validate configuration
    issues = orig_config.validate()
    if issues:
        raise ValueError(f"Configuration validation failed: {', '.join(issues)}")
    
    return OriginalLanguageDetector(config=orig_config)