#!/usr/bin/env python3
"""
Extract language info from current IMDb page structure.
"""

import asyncio
import sys
import json
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nhkprep.original_lang.imdb import IMDbBackend
from bs4 import BeautifulSoup

async def main():
    """Extract language using modern IMDb structure."""
    
    print("🎯 Modern IMDb Language Extraction")
    print("=" * 40)
    
    backend = IMDbBackend(request_timeout=30.0)
    
    # Get the page content
    imdb_url = f"https://www.imdb.com/title/tt0090248/"
    client = await backend._get_client()
    response = await client.get(imdb_url)
    html = response.text
    
    soup = BeautifulSoup(html, 'html.parser')
    print(f"Page parsed successfully")
    
    # Method 1: Look for the details section with modern data-testid
    print("\n🔍 Method 1: Modern details section...")
    details_section = soup.find('section', {'data-testid': 'Details'})
    if details_section:
        print("✅ Found Details section")
        # Look for language info
        detail_items = details_section.find_all('li', class_='ipc-metadata-list-summary-item')
        for item in detail_items[:10]:  # Check first 10 items
            item_text = item.get_text(strip=True).lower()
            if 'language' in item_text:
                print(f"    Language item: {item_text}")
    else:
        print("❌ No Details section found")
    
    # Method 2: Look in all li elements for language
    print("\n🔍 Method 2: All list items...")
    all_lis = soup.find_all('li')
    lang_lis = []
    for li in all_lis:
        li_text = li.get_text(strip=True).lower()
        if 'language' in li_text and len(li_text) < 100:  # Reasonable length
            lang_lis.append(li_text)
    
    print(f"Found {len(lang_lis)} language-related list items:")
    for li in lang_lis[:5]:  # Show first 5
        print(f"    {li}")
    
    # Method 3: Look for span elements with language info
    print("\n🔍 Method 3: Span elements...")
    spans = soup.find_all('span')
    lang_spans = []
    for span in spans:
        span_text = span.get_text(strip=True)
        if span_text.lower() in ['japanese', 'english', 'french', 'german', 'spanish'] and len(span_text) < 20:
            lang_spans.append(span_text)
    
    if lang_spans:
        print(f"Found language spans: {set(lang_spans)}")
    else:
        print("No direct language spans found")
    
    # Method 4: Regex search for common patterns
    print("\n🔍 Method 4: Regex patterns...")
    patterns = [
        r'Language[:\s]*([A-Za-z]+)',
        r'Original language[:\s]*([A-Za-z]+)',
        r'Languages?[:\s]*([A-Za-z]+(?:\s*,\s*[A-Za-z]+)*)',
    ]
    
    page_text = soup.get_text()
    for pattern in patterns:
        matches = re.findall(pattern, page_text, re.IGNORECASE)
        if matches:
            print(f"Pattern '{pattern}' found: {matches[:5]}")
    
    # Method 5: Check for Japanese content indicators
    print("\n🔍 Method 5: Japanese content indicators...")
    japanese_indicators = [
        'japanese',
        'japan', 
        'anime',
        'animation',
        'studio',
        'manga'
    ]
    
    page_lower = soup.get_text().lower()
    japanese_score = 0
    found_indicators = []
    
    for indicator in japanese_indicators:
        count = page_lower.count(indicator)
        if count > 0:
            japanese_score += count
            found_indicators.append(f"{indicator}({count})")
    
    print(f"Japanese indicators: {', '.join(found_indicators)}")
    print(f"Japanese score: {japanese_score}")
    
    # If we have high Japanese indicators, we can infer it's Japanese
    if japanese_score > 10:  # Threshold
        print("🎯 HIGH CONFIDENCE: This appears to be Japanese content")
        
        # Create a manual detection result
        from nhkprep.original_lang import OriginalLanguageDetection
        result = OriginalLanguageDetection(
            original_language="ja",
            confidence=0.8,  # High confidence based on indicators
            source="imdb",
            method="content_inference",
            details=f"Japanese content inferred from {japanese_score} indicators: {', '.join(found_indicators[:3])}",
            title="Vampire Hunter D",
            year=1985,
            imdb_id="tt0090248"
        )
        
        print(f"\n✅ MANUAL DETECTION RESULT:")
        print(f"  Language: {result.original_language}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Method: {result.method}")
        print(f"  Details: {result.details}")
    
    await backend.close()
    print("\n🏁 Modern extraction complete!")

if __name__ == "__main__":
    asyncio.run(main())