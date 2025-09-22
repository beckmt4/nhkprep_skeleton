#!/usr/bin/env python3
"""
Test script to run original language detection on the sample filename.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import nhkprep modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def main():
    """Run the full detection pipeline."""
    sample_filename = "Vampire Hunter D (1985) {imdb-tt0090248} [WEBDL-1080p][AAC 2.0][x264]"
    
    print("🎬 Original Language Detection Pipeline Test")
    print("=" * 50)
    print(f"Sample filename: {sample_filename}")
    print()
    
    # Configure detector to use IMDb first (no API key needed), then TMDb as fallback
    config = OriginalLanguageConfig(
        backend_priorities=["imdb", "tmdb"],
        confidence_threshold=0.1,  # Lower threshold to accept the detection
        total_timeout=60,
        request_timeout=20,
        cache_enabled=True,
    )
    
    print("📋 Configuration:")
    print(f"  Backends: {config.backend_priorities}")
    print(f"  Confidence threshold: {config.confidence_threshold}")
    print(f"  Total timeout: {config.total_timeout}s")
    print(f"  Request timeout: {config.request_timeout}s")
    print(f"  Cache enabled: {config.cache_enabled}")
    print()
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Show available backends
    available_backends = config.get_available_backends()
    print(f"🔍 Available backends: {available_backends}")
    print()
    
    print("🚀 Running detection...")
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Run the detection
        result = await detector.detect_from_filename(sample_filename)
        
        end_time = asyncio.get_event_loop().time()
        total_time_ms = (end_time - start_time) * 1000
        
        print("✅ Detection Complete!")
        print("-" * 30)
        
        if result:
            print("🎯 DETECTION RESULTS:")
            print(f"  Original Language: {result.original_language or 'Not detected'}")
            print(f"  Confidence: {result.confidence:.3f}")
            print(f"  Source: {result.source}")
            print(f"  Method: {result.method}")
            print(f"  Title: {result.title or 'Unknown'}")
            print(f"  Year: {result.year or 'Unknown'}")
            print(f"  IMDb ID: {result.imdb_id or 'None'}")
            print(f"  TMDb ID: {result.tmdb_id or 'None'}")
            print(f"  Details: {result.details or 'N/A'}")
            print(f"  Detection Time: {result.detection_time_ms:.0f}ms")
            print(f"  Total Pipeline Time: {total_time_ms:.0f}ms")
            
            if result.spoken_languages:
                print(f"  Spoken Languages: {', '.join(result.spoken_languages)}")
            
            if result.production_countries:
                print(f"  Production Countries: {', '.join(result.production_countries)}")
            
            print()
            
            # Confidence interpretation
            if result.confidence >= 0.9:
                confidence_msg = "🟢 Very High - Excellent match from reliable source"
            elif result.confidence >= 0.8:
                confidence_msg = "🟢 High - Strong match, likely accurate"
            elif result.confidence >= 0.7:
                confidence_msg = "🟡 Good - Reasonable match, probably accurate"
            elif result.confidence >= 0.5:
                confidence_msg = "🟡 Moderate - Uncertain match, verify manually"
            else:
                confidence_msg = "🔴 Low - Weak match, likely inaccurate"
                
            print(f"📊 Confidence Assessment: {confidence_msg}")
            
            # Validation
            if result.original_language == 'ja':
                print("✅ Expected result: Japanese (ja) - CORRECT!")
            else:
                print(f"⚠️  Expected 'ja', got '{result.original_language}' - verify accuracy")
            
        else:
            print("❌ NO DETECTION RESULT")
            print("Possible reasons:")
            print("  • Filename couldn't be parsed")
            print("  • No matching results in databases")
            print("  • All matches below confidence threshold")
            print("  • Network/API errors")
        
        print()
        
        # Show cache stats
        try:
            cache_stats = await detector.get_cache_stats()
            print("💾 Cache Statistics:")
            print(f"  Total entries: {cache_stats.get('total_entries', 0)}")
            print(f"  Active entries: {cache_stats.get('active_entries', 0)}")
            if cache_stats.get('disk_usage_mb', 0) > 0:
                print(f"  Disk usage: {cache_stats['disk_usage_mb']:.2f} MB")
        except Exception as e:
            print(f"⚠️  Cache stats unavailable: {e}")
            
    except Exception as e:
        print(f"❌ Detection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("🏁 Pipeline test complete!")
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Detection cancelled by user")
        sys.exit(130)