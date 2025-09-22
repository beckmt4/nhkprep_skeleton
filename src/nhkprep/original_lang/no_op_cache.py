"""No-op cache implementation for when caching is disabled."""

from typing import Dict, Any, Optional
from . import OriginalLanguageDetection, MediaSearchQuery
from .cache import OriginalLanguageCache


class NoOpCache(OriginalLanguageCache):
    """Cache implementation that doesn't store anything."""
    
    async def get(self, query: MediaSearchQuery) -> Optional[OriginalLanguageDetection]:
        """Always return None (cache miss)."""
        return None
    
    async def set(self, query: MediaSearchQuery, result: OriginalLanguageDetection) -> None:
        """Do nothing."""
        pass
    
    async def delete(self, query: MediaSearchQuery) -> bool:
        """Always return False."""
        return False
    
    async def clear(self) -> int:
        """Always return 0."""
        return 0
    
    async def cleanup(self) -> int:
        """Always return 0."""
        return 0
    
    async def stats(self) -> Dict[str, Any]:
        """Return stats showing no entries."""
        return {
            'total_entries': 0,
            'active_entries': 0,
            'expired_entries': 0,
            'cache_type': 'no_op',
            'enabled': False
        }