"""
Caching system for original language detection results.

Provides persistent file-based caching with TTL support and cache invalidation.
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from . import OriginalLanguageDetection, MediaSearchQuery

if TYPE_CHECKING:
    from .config import OriginalLanguageConfig

logger = logging.getLogger(__name__)


class OriginalLanguageCache(ABC):
    """Abstract base class for original language detection caches."""
    
    @abstractmethod
    async def get(self, query: MediaSearchQuery) -> Optional[OriginalLanguageDetection]:
        """
        Retrieve a cached detection result for a query.
        
        Args:
            query: The search query to look up
            
        Returns:
            Cached detection result or None if not found/expired
        """
        pass
    
    @abstractmethod
    async def set(self, query: MediaSearchQuery, result: OriginalLanguageDetection) -> None:
        """
        Store a detection result in the cache.
        
        Args:
            query: The search query key
            result: The detection result to cache
        """
        pass
    
    @abstractmethod
    async def delete(self, query: MediaSearchQuery) -> bool:
        """
        Remove a specific cache entry.
        
        Args:
            query: The search query to remove
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries removed
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of expired entries removed
        """
        pass
    
    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        pass


class FileBasedCache(OriginalLanguageCache):
    """File-based cache implementation with JSON storage."""
    
    def __init__(
        self,
        cache_dir: Path,
        ttl_seconds: int = 86400,  # 24 hours
        max_size: int = 1000,
        auto_cleanup: bool = True
    ):
        """
        Initialize file-based cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time to live for cache entries in seconds
            max_size: Maximum number of cache entries
            auto_cleanup: Whether to automatically cleanup on operations
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.auto_cleanup = auto_cleanup
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache metadata file
        self.metadata_file = self.cache_dir / "_cache_metadata.json"
        
        logger.debug(f"Initialized file cache at {self.cache_dir}")
    
    def _get_cache_key(self, query: MediaSearchQuery) -> str:
        """Generate a cache key from a query."""
        # Create a canonical representation of the query
        key_data = {
            'title': query.title,
            'year': query.year,
            'imdb_id': query.imdb_id,
            'tmdb_id': query.tmdb_id,
            'media_type': query.media_type,
            'season': query.season,
            'episode': query.episode
        }
        
        # Remove None values for consistent hashing
        key_data = {k: v for k, v in key_data.items() if v is not None}
        
        # Create hash from sorted JSON representation
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()[:16]
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get the cache file path for a key."""
        return self.cache_dir / f"{cache_key}.json"
    
    async def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            return {}
    
    async def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save cache metadata."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if auto_cleanup is enabled."""
        if self.auto_cleanup:
            await self.cleanup()
    
    async def get(self, query: MediaSearchQuery) -> Optional[OriginalLanguageDetection]:
        """Retrieve a cached detection result."""
        await self._maybe_cleanup()
        
        cache_key = self._get_cache_key(query)
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check expiration
            expiry_time = data.get('expiry_time')
            if expiry_time and time.time() > expiry_time:
                # Entry expired, remove it
                cache_file.unlink(missing_ok=True)
                logger.debug(f"Cache entry expired and removed: {cache_key}")
                return None
            
            # Deserialize the detection result
            result_data = data['result']
            
            # Convert datetime string back to datetime object
            if 'timestamp' in result_data:
                result_data['timestamp'] = datetime.fromisoformat(result_data['timestamp'])
            
            result = OriginalLanguageDetection(**result_data)
            
            logger.debug(f"Cache hit for key: {cache_key}")
            return result
            
        except (json.JSONDecodeError, KeyError, TypeError, OSError) as e:
            logger.warning(f"Failed to load cache entry {cache_key}: {e}")
            # Remove corrupted cache file
            cache_file.unlink(missing_ok=True)
            return None
    
    async def set(self, query: MediaSearchQuery, result: OriginalLanguageDetection) -> None:
        """Store a detection result in the cache."""
        await self._maybe_cleanup()
        
        cache_key = self._get_cache_key(query)
        cache_file = self._get_cache_file(cache_key)
        
        # Calculate expiry time
        expiry_time = time.time() + self.ttl_seconds
        
        # Serialize result
        result_dict = asdict(result)
        
        # Convert datetime to ISO string for JSON serialization
        if 'timestamp' in result_dict and result_dict['timestamp']:
            result_dict['timestamp'] = result_dict['timestamp'].isoformat()
        
        cache_data = {
            'cache_key': cache_key,
            'query': asdict(query),
            'result': result_dict,
            'created_time': time.time(),
            'expiry_time': expiry_time,
            'version': 1
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Cached result for key: {cache_key}")
            
            # Update metadata
            await self._update_cache_metadata(cache_key, cache_data)
            
        except OSError as e:
            logger.error(f"Failed to save cache entry {cache_key}: {e}")
    
    async def _update_cache_metadata(self, cache_key: str, cache_data: Dict[str, Any]) -> None:
        """Update cache metadata with new entry."""
        metadata = await self._load_metadata()
        
        if 'entries' not in metadata:
            metadata['entries'] = {}
        
        metadata['entries'][cache_key] = {
            'created_time': cache_data['created_time'],
            'expiry_time': cache_data['expiry_time'],
            'query_title': cache_data['query'].get('title'),
            'result_language': cache_data['result'].get('original_language'),
            'result_confidence': cache_data['result'].get('confidence')
        }
        
        await self._save_metadata(metadata)
    
    async def delete(self, query: MediaSearchQuery) -> bool:
        """Remove a specific cache entry."""
        cache_key = self._get_cache_key(query)
        cache_file = self._get_cache_file(cache_key)
        
        if cache_file.exists():
            cache_file.unlink()
            
            # Update metadata
            metadata = await self._load_metadata()
            if 'entries' in metadata and cache_key in metadata['entries']:
                del metadata['entries'][cache_key]
                await self._save_metadata(metadata)
            
            logger.debug(f"Deleted cache entry: {cache_key}")
            return True
        
        return False
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        count = 0
        
        # Remove all cache files
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name != "_cache_metadata.json":
                cache_file.unlink()
                count += 1
        
        # Clear metadata
        await self._save_metadata({'entries': {}})
        
        logger.info(f"Cleared {count} cache entries")
        return count
    
    async def cleanup(self) -> int:
        """Remove expired entries and enforce size limits."""
        current_time = time.time()
        removed_count = 0
        
        metadata = await self._load_metadata()
        entries = metadata.get('entries', {})
        
        # Remove expired entries
        expired_keys = []
        for cache_key, entry_info in entries.items():
            if entry_info['expiry_time'] < current_time:
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            cache_file = self._get_cache_file(cache_key)
            cache_file.unlink(missing_ok=True)
            del entries[cache_key]
            removed_count += 1
        
        # Enforce size limits (remove oldest entries if over limit)
        if len(entries) > self.max_size:
            # Sort by creation time (oldest first)
            sorted_entries = sorted(
                entries.items(),
                key=lambda x: x[1]['created_time']
            )
            
            # Remove oldest entries
            entries_to_remove = len(entries) - self.max_size
            for cache_key, _ in sorted_entries[:entries_to_remove]:
                cache_file = self._get_cache_file(cache_key)
                cache_file.unlink(missing_ok=True)
                del entries[cache_key]
                removed_count += 1
        
        # Update metadata
        metadata['entries'] = entries
        await self._save_metadata(metadata)
        
        if removed_count > 0:
            logger.debug(f"Cache cleanup removed {removed_count} entries")
        
        return removed_count
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        metadata = await self._load_metadata()
        entries = metadata.get('entries', {})
        
        current_time = time.time()
        active_entries = sum(1 for e in entries.values() if e['expiry_time'] > current_time)
        expired_entries = len(entries) - active_entries
        
        # Calculate cache hit rates (basic implementation)
        cache_files = list(self.cache_dir.glob("*.json"))
        actual_files = len([f for f in cache_files if f.name != "_cache_metadata.json"])
        
        return {
            'total_entries': len(entries),
            'active_entries': active_entries,
            'expired_entries': expired_entries,
            'actual_files': actual_files,
            'cache_dir': str(self.cache_dir),
            'ttl_seconds': self.ttl_seconds,
            'max_size': self.max_size,
            'disk_usage_mb': sum(f.stat().st_size for f in cache_files) / 1024 / 1024
        }


class InMemoryCache(OriginalLanguageCache):
    """In-memory cache implementation for testing and high-performance scenarios."""
    
    def __init__(self, ttl_seconds: int = 86400, max_size: int = 1000):
        """Initialize in-memory cache."""
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        
        logger.debug("Initialized in-memory cache")
    
    def _get_cache_key(self, query: MediaSearchQuery) -> str:
        """Generate a cache key from a query."""
        key_data = {
            'title': query.title,
            'year': query.year,
            'imdb_id': query.imdb_id,
            'tmdb_id': query.tmdb_id,
            'media_type': query.media_type,
            'season': query.season,
            'episode': query.episode
        }
        key_data = {k: v for k, v in key_data.items() if v is not None}
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()[:16]
    
    async def get(self, query: MediaSearchQuery) -> Optional[OriginalLanguageDetection]:
        """Retrieve a cached detection result."""
        cache_key = self._get_cache_key(query)
        
        if cache_key not in self._cache:
            return None
        
        entry = self._cache[cache_key]
        current_time = time.time()
        
        # Check expiration
        if entry['expiry_time'] < current_time:
            del self._cache[cache_key]
            self._access_times.pop(cache_key, None)
            return None
        
        # Update access time
        self._access_times[cache_key] = current_time
        
        return entry['result']
    
    async def set(self, query: MediaSearchQuery, result: OriginalLanguageDetection) -> None:
        """Store a detection result in the cache."""
        cache_key = self._get_cache_key(query)
        current_time = time.time()
        
        # Enforce size limits
        if len(self._cache) >= self.max_size and cache_key not in self._cache:
            await self._evict_oldest()
        
        self._cache[cache_key] = {
            'result': result,
            'created_time': current_time,
            'expiry_time': current_time + self.ttl_seconds
        }
        self._access_times[cache_key] = current_time
    
    async def _evict_oldest(self) -> None:
        """Evict the least recently accessed entry."""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    async def delete(self, query: MediaSearchQuery) -> bool:
        """Remove a specific cache entry."""
        cache_key = self._get_cache_key(query)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._access_times.pop(cache_key, None)
            return True
        
        return False
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._access_times.clear()
        return count
    
    async def cleanup(self) -> int:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry['expiry_time'] < current_time
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._access_times.pop(key, None)
        
        return len(expired_keys)
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = sum(
            1 for entry in self._cache.values()
            if entry['expiry_time'] > current_time
        )
        
        return {
            'total_entries': len(self._cache),
            'active_entries': active_entries,
            'expired_entries': len(self._cache) - active_entries,
            'cache_type': 'in_memory',
            'ttl_seconds': self.ttl_seconds,
            'max_size': self.max_size
        }


def create_cache_from_config(config: 'OriginalLanguageConfig') -> OriginalLanguageCache:
    """
    Create a cache instance from configuration.
    
    Args:
        config: Original language configuration
        
    Returns:
        Configured cache instance
    """
    if not config.cache_enabled:
        # Return a no-op cache that doesn't store anything
        from .no_op_cache import NoOpCache
        return NoOpCache()
    
    # Ensure cache_dir is not None
    cache_dir = config.cache_dir
    if cache_dir is None:
        import tempfile
        cache_dir = Path(tempfile.gettempdir()) / "nhkprep" / "orig_lang_cache"
    
    return FileBasedCache(
        cache_dir=cache_dir,
        ttl_seconds=config.cache_ttl,
        max_size=config.cache_max_size,
        auto_cleanup=True
    )