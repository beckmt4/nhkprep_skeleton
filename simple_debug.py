#!/usr/bin/env python3
"""
Simple IMDb page content analysis.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nhkprep.original_lang.imdb import IMDbBackend

async def main():
    """Analyze IMDb page content."""
    
    print("🔍 Simple IMDb Content Analysis")
    print("=" * 40)
    
    backend = IMDbBackend(request_timeout=30.0)
    
    # Get the page content
    imdb_url = f"https://www.imdb.com/title/tt0090248/"
    client = await backend._get_client()
    response = await client.get(imdb_url)
    html = response.text
    
    print(f"Page loaded: {len(html)} characters")
    
    # Simple text search
    search_terms = ['language', 'japanese', 'japan', 'Language']
    
    for term in search_terms:
        count = html.lower().count(term.lower())
        print(f"'{term}' appears {count} times")
        
        if count > 0:
            # Find some context
            import re
            pattern = re.compile(f'.{{0,50}}{re.escape(term)}.{{0,50}}', re.IGNORECASE)
            matches = pattern.findall(html)
            print(f"  Sample contexts:")
            for i, match in enumerate(matches[:3]):
                clean_match = ' '.join(match.split())
                print(f"    {i+1}. {clean_match}")
        print()
    
    # Check if the actual detection method finds anything
    print("🎯 Testing language extraction methods...")
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Test the actual methods from the backend
    try:
        lang1 = await backend._extract_from_tech_specs(soup)
        print(f"Tech specs method: {lang1}")
        
        lang2 = await backend._extract_from_details_section(soup)
        print(f"Details section method: {lang2}")
        
        lang3 = await backend._extract_from_structured_data(soup)
        print(f"Structured data method: {lang3}")
        
        lang4 = await backend._extract_from_storyline(soup)
        print(f"Storyline method: {lang4}")
        
    except Exception as e:
        print(f"Error in extraction methods: {e}")
    
    await backend.close()
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    asyncio.run(main())