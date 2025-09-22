#!/usr/bin/env python3
"""
Debug IMDb page parsing for language extraction.
"""

import asyncio
import sys
from pathlib import Path
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nhkprep.original_lang import MediaSearchQuery
from nhkprep.original_lang.imdb import IMDbBackend
from bs4 import BeautifulSoup

async def main():
    """Test IMDb page parsing in detail."""
    
    print("🔍 IMDb Page Parsing Debug")
    print("=" * 40)
    
    backend = IMDbBackend(request_timeout=30.0)
    
    # Get the page content
    imdb_url = f"https://www.imdb.com/title/tt0090248/"
    client = await backend._get_client()
    response = await client.get(imdb_url)
    html = response.text
    
    print(f"Page loaded: {len(html)} characters")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n🔍 Looking for language information...")
    
    # Method 1: Search for "Language" text in the page
    lang_mentions = soup.find_all(text=re.compile(r'Language', re.I))
    print(f"\nFound {len(lang_mentions)} 'Language' mentions:")
    for i, mention in enumerate(lang_mentions[:5]):  # Show first 5
        context = str(mention).strip()[:100]
        print(f"  {i+1}. {context}")
    
    # Method 2: Look for specific language keywords
    japanese_patterns = ['japanese', 'japan', '日本語', 'ja-JP', 'ja_JP']
    for pattern in japanese_patterns:
        if pattern.lower() in html.lower():
            print(f"\n✅ Found '{pattern}' in page content")
            # Find context around the match
            import re
            matches = list(re.finditer(re.escape(pattern), html, re.I))
            for match in matches[:3]:  # Show first 3 contexts
                start = max(0, match.start() - 50)
                end = min(len(html), match.end() + 50)
                context = html[start:end].replace('\n', ' ').strip()
                print(f"    Context: ...{context}...")
        else:
            print(f"❌ '{pattern}' not found")
    
    # Method 3: Look at structured data
    print(f"\n🔍 Searching for JSON-LD structured data...")
    scripts = soup.find_all('script', type='application/ld+json')
    print(f"Found {len(scripts)} JSON-LD scripts")
    
    for i, script in enumerate(scripts):
        if script.string:
            try:
                import json
                data = json.loads(script.string)
                print(f"\n  Script {i+1} keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict):
                    # Look for language-related fields
                    for key in data.keys():
                        if 'lang' in key.lower():
                            print(f"    Language field '{key}': {data[key]}")
            except:
                print(f"    Script {i+1}: Invalid JSON")
    
    # Method 4: Look in technical specifications
    print(f"\n🔍 Looking for technical specifications...")
    
    # Try new IMDb layout
    tech_section = soup.find('section', {'data-testid': 'TechSpecs'})
    if tech_section:
        print("✅ Found TechSpecs section")
        tech_text = tech_section.get_text()[:500]
        print(f"Tech specs content: {tech_text}")
        
        # Look for language entries
        lang_items = tech_section.find_all(text=re.compile(r'Language', re.I))
        print(f"Language items in tech specs: {len(lang_items)}")
        for item in lang_items:
            print(f"  - {str(item).strip()}")
    else:
        print("❌ No TechSpecs section found")
        
        # Try old layout
        details_div = soup.find('div', {'id': 'titleDetails'})
        if details_div:
            print("✅ Found titleDetails section (old layout)")
            details_text = details_div.get_text()[:500]
            print(f"Details content: {details_text}")
        else:
            print("❌ No titleDetails section found either")
    
    # Method 5: Manual search through all text
    print(f"\n🔍 Manual search through page text...")
    page_text = soup.get_text().lower()
    
    # Search for various language patterns
    patterns_to_check = [
        r'language[:\s]*japanese',
        r'original[:\s]*japanese', 
        r'japanese[:\s]*language',
        r'spoken[:\s]*languages?[:\s]*[^.]*japanese',
        r'languages?[:\s]*[^.]*japanese',
    ]
    
    for pattern in patterns_to_check:
        matches = re.findall(pattern, page_text)
        if matches:
            print(f"✅ Pattern '{pattern}' found: {matches[:3]}")
        else:
            print(f"❌ Pattern '{pattern}' not found")
    
    # Clean up
    await backend.close()
    
    print("\n🏁 Page parsing debug complete!")

if __name__ == "__main__":
    asyncio.run(main())