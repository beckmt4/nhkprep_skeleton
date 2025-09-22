"""
Demonstration of the original language detection caching system.

This script shows how caching improves performance by avoiding repeated API calls.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

from src.nhkprep.original_lang import OriginalLanguageDetection, MediaSearchQuery, OriginalLanguageDetector, OriginalLanguageBackend
from src.nhkprep.original_lang.config import OriginalLanguageConfig


class DemoBackend(OriginalLanguageBackend):
    """Mock backend that simulates API calls with delays."""
    
    def __init__(self, name="demo", delay=0.5):
        self.name = name
        self.delay = delay  # Simulate API call delay
        self.call_count = 0
        
    def is_available(self):
        return True
    
    async def detect_original_language(self, query):
        self.call_count += 1
        print(f"  🌐 {self.name} backend called (#{self.call_count})")
        print(f"     Simulating API delay of {self.delay}s...")
        
        await asyncio.sleep(self.delay)  # Simulate network delay
        
        # Return a mock result
        return OriginalLanguageDetection(
            original_language="ja",
            confidence=0.9,
            source=self.name,
            method="api_lookup",
            details=f"Found via {self.name} API",
            title=query.title or "Unknown Title",
            year=query.year
        )


async def demo_caching_benefits():
    """Demonstrate the performance benefits of caching."""
    
    print("🎬 Original Language Detection Caching Demo")
    print("=" * 50)
    
    # Create temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        
        # Configure detector with caching enabled
        config = OriginalLanguageConfig(
            cache_enabled=True,
            cache_dir=cache_dir,
            cache_ttl=3600,  # 1 hour TTL
            confidence_threshold=0.7
        )
        
        detector = OriginalLanguageDetector(config)
        demo_backend = DemoBackend("demo", delay=0.5)  # 500ms delay per call
        detector.add_backend(demo_backend)
        
        # Test queries
        queries = [
            MediaSearchQuery(title="Spirited Away", year=2001, media_type="movie"),
            MediaSearchQuery(title="Your Name", year=2016, media_type="movie"),
            MediaSearchQuery(title="Princess Mononoke", year=1997, media_type="movie")
        ]
        
        print("\n🔍 Phase 1: Initial detections (cache misses)")
        print("-" * 40)
        
        start_time = time.time()
        results = []
        for i, query in enumerate(queries, 1):
            print(f"\n{i}. Detecting: {query.title} ({query.year})")
            result = await detector.detect_from_query(query)
            results.append(result)
            if result:
                print(f"   ✅ Found: {result.original_language} (confidence: {result.confidence:.2f})")
                print(f"   ⏱️  Time: {result.detection_time_ms:.0f}ms")
        
        phase1_time = time.time() - start_time
        print(f"\n📊 Phase 1 completed in {phase1_time:.2f} seconds")
        print(f"   Backend calls: {demo_backend.call_count}")
        
        # Check cache stats
        stats = await detector.get_cache_stats()
        print(f"   Cache entries: {stats['active_entries']}")
        
        print("\n🚀 Phase 2: Repeated detections (cache hits)")
        print("-" * 40)
        
        start_time = time.time()
        initial_call_count = demo_backend.call_count
        
        for i, query in enumerate(queries, 1):
            print(f"\n{i}. Detecting: {query.title} ({query.year}) [CACHED]")
            result = await detector.detect_from_query(query)
            if result:
                print(f"   ✅ Found: {result.original_language} (confidence: {result.confidence:.2f})")
                print(f"   ⏱️  Time: {result.detection_time_ms:.0f}ms")
        
        phase2_time = time.time() - start_time
        print(f"\n📊 Phase 2 completed in {phase2_time:.2f} seconds")
        print(f"   Backend calls: {demo_backend.call_count - initial_call_count}")
        print(f"   Speed improvement: {(phase1_time / phase2_time):.1f}x faster")
        
        # Show cache management
        print("\n🗂️  Cache Management Demo")
        print("-" * 30)
        
        final_stats = await detector.get_cache_stats()
        print(f"Cache statistics:")
        print(f"  • Total entries: {final_stats['total_entries']}")
        print(f"  • Active entries: {final_stats['active_entries']}")
        print(f"  • Disk usage: {final_stats['disk_usage_mb']:.2f} MB")
        print(f"  • Cache directory: {final_stats['cache_dir']}")
        
        # Demonstrate cache cleanup
        cleanup_count = await detector.cleanup_cache()
        print(f"  • Cleanup removed: {cleanup_count} expired entries")
        
        # Clear cache
        clear_count = await detector.clear_cache()
        print(f"  • Clear removed: {clear_count} entries")


async def demo_cache_types():
    """Demonstrate different cache types."""
    
    print("\n🔧 Cache Types Comparison")
    print("=" * 30)
    
    from src.nhkprep.original_lang.cache import FileBasedCache, InMemoryCache
    from src.nhkprep.original_lang.no_op_cache import NoOpCache
    
    query = MediaSearchQuery(title="Test Movie", year=2020)
    detection = OriginalLanguageDetection(
        original_language="en",
        confidence=0.8,
        source="demo",
        method="test"
    )
    
    # File-based cache
    with tempfile.TemporaryDirectory() as temp_dir:
        file_cache = FileBasedCache(Path(temp_dir))
        await file_cache.set(query, detection)
        result = await file_cache.get(query)
        stats = await file_cache.stats()
        print(f"📁 File Cache: {result is not None}, {stats['total_entries']} entries")
    
    # In-memory cache
    memory_cache = InMemoryCache()
    await memory_cache.set(query, detection)
    result = await memory_cache.get(query)
    stats = await memory_cache.stats()
    print(f"💾 Memory Cache: {result is not None}, {stats['total_entries']} entries")
    
    # No-op cache (disabled)
    noop_cache = NoOpCache()
    await noop_cache.set(query, detection)
    result = await noop_cache.get(query)
    stats = await noop_cache.stats()
    print(f"🚫 No-op Cache: {result is not None}, {stats['total_entries']} entries")


async def main():
    """Run the caching demonstrations."""
    try:
        await demo_caching_benefits()
        await demo_cache_types()
        
        print("\n🎉 Caching Demo Complete!")
        print("\nKey Benefits:")
        print("✅ Dramatically faster repeat lookups")
        print("✅ Reduced API usage and costs")
        print("✅ Improved user experience")
        print("✅ Configurable TTL and size limits")
        print("✅ Persistent storage across sessions")
        print("✅ Automatic cleanup and management")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")


if __name__ == "__main__":
    asyncio.run(main())