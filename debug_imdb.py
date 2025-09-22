#!/usr/bin/env python3
"""
Debug IMDb backend for Vampire Hunter D detection.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nhkprep.original_lang import MediaSearchQuery
from nhkprep.original_lang.imdb import IMDbBackend

async def main():
    """Test IMDb backend directly."""
    
    print("🐞 IMDb Backend Debug Test")
    print("=" * 40)
    
    # Create IMDb backend
    backend = IMDbBackend(request_timeout=30.0, max_retries=3)
    
    print(f"Backend available: {backend.is_available()}")
    print()
    
    # Test query
    query = MediaSearchQuery(
        title="Vampire Hunter D",
        year=1985,
        imdb_id="tt0090248",
        media_type="movie"
    )
    
    print("🔍 Query details:")
    print(f"  Title: {query.title}")
    print(f"  Year: {query.year}")
    print(f"  IMDb ID: {query.imdb_id}")
    print(f"  Media type: {query.media_type}")
    print()
    
    print("🚀 Testing direct IMDb page access...")
    
    # Test direct page access first
    imdb_url = f"https://www.imdb.com/title/tt0090248/"
    try:
        client = await backend._get_client()
        response = await client.get(imdb_url)
        print(f"Direct page status: {response.status_code}")
        if response.status_code == 200:
            print(f"Page content length: {len(response.text)} chars")
            # Check if we can find basic info
            if "Vampire Hunter D" in response.text:
                print("✅ Found title in page content")
            else:
                print("⚠️  Title not found in page content")
        else:
            print(f"❌ Failed to load page: {response.status_code}")
    except Exception as e:
        print(f"❌ Direct page access failed: {e}")
    
    print()
    print("🎯 Running full detection...")
    
    try:
        result = await backend.detect_original_language(query)
        
        if result:
            print("✅ DETECTION SUCCESS:")
            print(f"  Language: {result.original_language}")
            print(f"  Confidence: {result.confidence:.3f}")
            print(f"  Source: {result.source}")
            print(f"  Method: {result.method}")
            print(f"  Details: {result.details}")
            print(f"  Title: {result.title}")
            print(f"  Year: {result.year}")
            print(f"  IMDb ID: {result.imdb_id}")
            if result.spoken_languages:
                print(f"  Spoken Languages: {result.spoken_languages}")
            if result.production_countries:
                print(f"  Production Countries: {result.production_countries}")
        else:
            print("❌ No detection result")
            
    except Exception as e:
        print(f"❌ Detection failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    await backend.close()
    print("\n🏁 Debug test complete!")

if __name__ == "__main__":
    asyncio.run(main())