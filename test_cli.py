#!/usr/bin/env python3
"""Test script for the new original language detection CLI commands."""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig


async def test_detect_from_filename():
    """Test the detect_from_filename method."""
    print("🧪 Testing Original Language Detection CLI API")
    print("=" * 50)
    
    # Create a detector with cache disabled for testing
    config = OriginalLanguageConfig(
        cache_enabled=False,
        confidence_threshold=0.7
    )
    
    detector = OriginalLanguageDetector(config)
    
    # Test filenames
    test_files = [
        "Spirited Away (2001) [1080p].mkv",
        "Your Name (2016) BDRip.mp4",
        "Princess Mononoke (1997).avi",
        "Akira (1988) [tt0094625].mkv",  # With IMDb ID
    ]
    
    print("Testing detect_from_filename method:")
    print("-" * 30)
    
    for filename in test_files:
        print(f"\n🎬 File: {filename}")
        try:
            result = await detector.detect_from_filename(filename, min_confidence=0.5)
            
            if result:
                print(f"   ✅ Language: {result.original_language}")
                print(f"   📊 Confidence: {result.confidence:.3f}")
                print(f"   🔍 Source: {result.source}")
                print(f"   📝 Method: {result.method}")
                print(f"   ⏱️  Time: {result.detection_time_ms:.0f}ms")
                if result.details:
                    print(f"   💬 Details: {result.details}")
            else:
                print("   ❌ No result")
                
        except Exception as e:
            print(f"   🔥 Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 CLI API Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_detect_from_filename())