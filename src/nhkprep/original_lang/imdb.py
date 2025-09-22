"""
IMDb web scraping backend for original language detection.

This backend scrapes IMDb pages to extract original language information
when API-based solutions are unavailable or insufficient.
"""

import asyncio
import re
import time
from typing import Any, cast
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from . import OriginalLanguageDetection, MediaSearchQuery
from .base import BaseOriginalLanguageBackend


class IMDbBackend(BaseOriginalLanguageBackend):
    """IMDb web scraping backend for original language detection."""
    
    # IMDb URLs
    BASE_URL = "https://www.imdb.com"
    SEARCH_URL = f"{BASE_URL}/find"
    TITLE_URL = f"{BASE_URL}/title"
    
    # Rate limiting (be respectful to IMDb)
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW = 60.0  # 10 requests per minute
    
    # Common language mappings found on IMDb
    LANGUAGE_MAPPINGS = {
        'japanese': 'ja',
        'english': 'en', 
        'spanish': 'es',
        'french': 'fr',
        'german': 'de',
        'italian': 'it',
        'portuguese': 'pt',
        'russian': 'ru',
        'chinese': 'zh',
        'korean': 'ko',
        'hindi': 'hi',
        'arabic': 'ar',
        'dutch': 'nl',
        'swedish': 'sv',
        'norwegian': 'no',
        'danish': 'da',
        'finnish': 'fi',
        'polish': 'pl',
        'czech': 'cs',
        'hungarian': 'hu',
        'turkish': 'tr',
        'greek': 'el',
        'thai': 'th',
        'vietnamese': 'vi',
        'indonesian': 'id',
        'malay': 'ms',
        'filipino': 'fil',
        'tagalog': 'tl',
        'mandarin': 'zh',
        'cantonese': 'zh',
        'hebrew': 'he',
        'persian': 'fa',
        'urdu': 'ur',
        'bengali': 'bn',
        'tamil': 'ta',
        'telugu': 'te',
        'marathi': 'mr',
        'gujarati': 'gu',
        'punjabi': 'pa',
        'ukrainian': 'uk',
        'romanian': 'ro',
        'bulgarian': 'bg',
        'croatian': 'hr',
        'serbian': 'sr',
        'slovenian': 'sl',
        'slovak': 'sk',
        'estonian': 'et',
        'latvian': 'lv',
        'lithuanian': 'lt',
    }
    
    def __init__(self, timeout: float = 15.0, max_retries: int = 3, 
                 request_timeout: float | None = None, **kwargs):
        """
        Initialize IMDb backend.
        
        Args:
            timeout: HTTP request timeout in seconds (legacy parameter)
            max_retries: Maximum number of retries for failed requests
            request_timeout: HTTP request timeout in seconds (new parameter from config)
            **kwargs: Additional config parameters (ignored for compatibility)
        """
        super().__init__("imdb")
        
        # Use request_timeout if provided, otherwise fall back to timeout
        self.timeout = request_timeout if request_timeout is not None else timeout
        self.max_retries = max_retries
        
        # Rate limiting state
        self._request_times: list[float] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # HTTP client configuration
        self._client: httpx.AsyncClient | None = None
    
    def is_available(self) -> bool:
        """IMDb backend is always available (no API key needed)."""
        return True
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with appropriate headers."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
        return self._client
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting before making requests."""
        async with self._rate_limit_lock:
            now = time.time()
            
            # Remove old request times outside the window
            self._request_times = [
                t for t in self._request_times 
                if now - t < self.RATE_LIMIT_WINDOW
            ]
            
            # If we're at the limit, wait
            if len(self._request_times) >= self.RATE_LIMIT_REQUESTS:
                oldest_request = min(self._request_times)
                wait_time = self.RATE_LIMIT_WINDOW - (now - oldest_request)
                if wait_time > 0:
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self._request_times.append(time.time())
    
    async def _make_request(self, url: str, params: dict[str, Any] | None = None) -> str | None:
        """
        Make rate-limited HTTP request to IMDb.
        
        Args:
            url: URL to request
            params: Query parameters
            
        Returns:
            HTML content or None on error
        """
        await self._rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                client = await self._get_client()
                
                self.logger.debug(f"IMDb request: {url}")
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                content = response.text
                self.logger.debug(f"IMDb response: {len(content)} chars")
                
                return content
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    self.logger.debug(f"IMDb page not found: {url}")
                    return None
                elif e.response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"HTTP error {e.response.status_code}: {url}")
                    
            except httpx.HTTPError as e:
                self.logger.error(f"Request failed: {e}")
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))
        
        return None
    
    def _parse_imdb_id(self, imdb_id: str) -> str:
        """Normalize IMDb ID format."""
        if not imdb_id.startswith('tt'):
            imdb_id = f'tt{imdb_id}'
        return imdb_id
    
    async def _search_by_id(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Search using IMDb ID directly.
        
        Args:
            query: Search parameters with IMDb ID
            
        Returns:
            Detection result or None
        """
        if not query.imdb_id:
            return None
        
        imdb_id = self._parse_imdb_id(query.imdb_id)
        url = f"{self.TITLE_URL}/{imdb_id}/"
        
        html = await self._make_request(url)
        if not html:
            return None
        
        return await self._parse_title_page(html, query, method="imdb_id_match")
    
    async def _search_by_title(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Search by title using IMDb's find functionality.
        
        Args:
            query: Search parameters
            
        Returns:
            Detection result or None
        """
        if not query.title:
            return None
        
        # Build search query
        search_term = query.title
        if query.year:
            search_term = f"{search_term} {query.year}"
        
        params = {
            'q': search_term,
            's': 'tt',  # Search titles
            'ref_': 'fn_al_tt_mr'
        }
        
        html = await self._make_request(self.SEARCH_URL, params)
        if not html:
            return None
        
        # Parse search results
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for title results
        results_section = soup.find('section', {'data-testid': 'find-results-section-title'})
        if not results_section:
            # Try alternative structure
            results_section = soup.find('div', class_='findSection')
        
        if not results_section or not isinstance(results_section, Tag):
            return None
        
        # Find the best matching result
        best_match = await self._find_best_search_match(results_section, query)
        if not best_match:
            return None
        
        # Extract IMDb ID from the best match
        link = best_match.find('a')
        if not link or not isinstance(link, Tag) or not link.get('href'):
            return None
        
        # Extract IMDb ID from URL like "/title/tt1234567/"
        href = str(link['href'])
        imdb_match = re.search(r'/title/(tt\d+)/', href)
        if not imdb_match:
            return None
        
        imdb_id = imdb_match.group(1)
        
        # Fetch the actual title page
        title_url = urljoin(self.BASE_URL, href)
        title_html = await self._make_request(title_url)
        if not title_html:
            return None
        
        return await self._parse_title_page(title_html, query, method="title_search", found_imdb_id=imdb_id)
    
    async def _find_best_search_match(self, results_section: Tag, query: MediaSearchQuery) -> Tag | None:
        """Find the best matching result from search results."""
        results = results_section.find_all('li') or results_section.find_all('tr')
        
        best_match = None
        best_score = 0.0
        
        for result in results[:5]:  # Check top 5 results
            if not isinstance(result, Tag):
                continue
                
            # Extract title
            title_link = result.find('a')
            if not title_link or not isinstance(title_link, Tag):
                continue
            
            title_text = title_link.get_text(strip=True)
            
            # Extract year if present
            year_match = re.search(r'\((\d{4})\)', result.get_text())
            found_year = int(year_match.group(1)) if year_match else None
            
            # Calculate similarity
            if not query.title:
                continue
                
            title_score = self.calculate_title_similarity(query.title, title_text)
            
            # Boost score for year match
            year_boost = 0.0
            if query.year and found_year and query.year == found_year:
                year_boost = 0.3
            
            total_score = title_score + year_boost
            
            if total_score > best_score and total_score > 0.3:
                best_score = total_score
                best_match = result
        
        return best_match
    
    async def _parse_title_page(
        self, 
        html: str, 
        query: MediaSearchQuery, 
        method: str = "page_scraping",
        found_imdb_id: str | None = None
    ) -> OriginalLanguageDetection | None:
        """
        Parse IMDb title page to extract original language information.
        
        Args:
            html: HTML content of the title page
            query: Original search query
            method: Detection method used
            found_imdb_id: IMDb ID if found during search
            
        Returns:
            Detection result or None
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract basic title information
        title_element = soup.find('h1', {'data-testid': 'hero-title-block__title'})
        if not title_element:
            title_element = soup.find('h1', class_='titleBar')
        
        found_title = title_element.get_text(strip=True) if title_element else None
        
        # Extract year
        year_element = soup.find('span', class_='titleBar__year') or \
                     soup.find('a', href=re.compile(r'/year/\d+/'))
        found_year = None
        if year_element:
            year_match = re.search(r'(\d{4})', year_element.get_text())
            if year_match:
                found_year = int(year_match.group(1))
        
        # Extract language information - try multiple approaches
        original_language = await self._extract_language_info(soup)
        
        if not original_language:
            return None
        
        # Calculate confidence
        confidence = self.determine_confidence(
            query=query,
            found_title=found_title,
            found_year=found_year,
            match_type=method
        )
        
        # Extract additional metadata
        spoken_languages = await self._extract_spoken_languages(soup)
        production_countries = await self._extract_production_countries(soup)
        
        return OriginalLanguageDetection(
            original_language=self.normalize_language_code(original_language),
            confidence=confidence,
            source="imdb",
            method=method,
            details=f"IMDb: {found_title} ({found_year})" if found_title and found_year else "IMDb scraping",
            title=found_title,
            year=found_year,
            imdb_id=found_imdb_id or query.imdb_id,
            spoken_languages=spoken_languages,
            production_countries=production_countries,
            api_response={"scraped_from": "imdb_title_page"}
        )
    
    async def _extract_language_info(self, soup: BeautifulSoup) -> str | None:
        """Extract original language from various page sections."""
        
        # Method 1: Look for "Language" in technical specs
        language = await self._extract_from_tech_specs(soup)
        if language:
            return language
        
        # Method 2: Look in details section
        language = await self._extract_from_details_section(soup)
        if language:
            return language
        
        # Method 3: Look for language information in structured data
        language = await self._extract_from_structured_data(soup)
        if language:
            return language
        
        # Method 4: Look in storyline section
        language = await self._extract_from_storyline(soup)
        if language:
            return language
        
        return None
    
    async def _extract_from_tech_specs(self, soup: BeautifulSoup) -> str | None:
        """Extract language from technical specifications section."""
        # Look for technical specs section
        tech_specs = soup.find('section', {'data-testid': 'TechSpecs'}) or \
                    soup.find('div', {'id': 'titleDetails'})
        
        if not tech_specs or not isinstance(tech_specs, Tag):
            return None
        
        # Find language row
        language_rows = tech_specs.find_all(['dt', 'div'], string=re.compile(r'Language', re.I))
        
        for lang_row in language_rows:
            # Find the corresponding value
            value_element = lang_row.find_next_sibling() or lang_row.find_next(['dd', 'div'])
            
            if value_element:
                language_text = value_element.get_text(strip=True)
                # Extract first language (usually the original)
                first_lang = language_text.split(',')[0].split('|')[0].strip()
                return first_lang.lower()
        
        return None
    
    async def _extract_from_details_section(self, soup: BeautifulSoup) -> str | None:
        """Extract language from details/storyline section."""
        details_section = soup.find('section', {'data-testid': 'Details'}) or \
                         soup.find('div', class_='article')
        
        if not details_section:
            return None
        
        # Look for language mentions
        text = details_section.get_text().lower()
        
        # Check for common patterns
        for language, code in self.LANGUAGE_MAPPINGS.items():
            if f'language: {language}' in text or f'original language: {language}' in text:
                return language
        
        return None
    
    async def _extract_from_structured_data(self, soup: BeautifulSoup) -> str | None:
        """Extract language from JSON-LD structured data."""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            if not isinstance(script, Tag) or not script.string:
                continue
                
            try:
                import json
                data = json.loads(str(script.string))
                
                if isinstance(data, dict):
                    # Look for language information
                    if 'inLanguage' in data:
                        lang = data['inLanguage']
                        if isinstance(lang, str):
                            return lang.lower()
                        elif isinstance(lang, list) and lang:
                            return lang[0].lower()
                    
                    # Look for original language
                    if 'originalLanguage' in data:
                        return data['originalLanguage'].lower()
                
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue
        
        return None
    
    async def _extract_from_storyline(self, soup: BeautifulSoup) -> str | None:
        """Extract language hints from storyline section."""
        storyline = soup.find('section', {'data-testid': 'Storyline'}) or \
                   soup.find('div', class_='summary_text')
        
        if not storyline:
            return None
        
        text = storyline.get_text().lower()
        
        # Look for language clues in common phrases
        patterns = [
            r'originally (?:made |filmed |produced )?in (\w+)',
            r'(\w+) language film',
            r'(\w+)-language',
            r'spoken in (\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                potential_lang = match.group(1)
                if potential_lang in self.LANGUAGE_MAPPINGS:
                    return potential_lang
        
        return None
    
    async def _extract_spoken_languages(self, soup: BeautifulSoup) -> list[str]:
        """Extract all spoken languages from the page."""
        languages = []
        
        # Look in tech specs
        tech_specs = soup.find('section', {'data-testid': 'TechSpecs'})
        if tech_specs and isinstance(tech_specs, Tag):
            lang_rows = tech_specs.find_all(['dt', 'div'], string=re.compile(r'Language', re.I))
            for lang_row in lang_rows:
                value_element = lang_row.find_next_sibling() or lang_row.find_next(['dd', 'div'])
                if value_element:
                    lang_text = value_element.get_text(strip=True)
                    for lang in lang_text.split(','):
                        lang = lang.strip().lower()
                        normalized = self.normalize_language_code(lang)
                        if normalized and normalized not in languages:
                            languages.append(normalized)
        
        return languages
    
    async def _extract_production_countries(self, soup: BeautifulSoup) -> list[str]:
        """Extract production countries from the page."""
        countries = []
        
        # Look for country information in various sections
        country_patterns = [
            r'Country of origin:\s*([^<\n]+)',
            r'Production countries:\s*([^<\n]+)',
            r'Countries:\s*([^<\n]+)',
        ]
        
        page_text = soup.get_text()
        for pattern in country_patterns:
            matches = re.findall(pattern, page_text, re.I)
            for match in matches:
                for country in match.split(','):
                    country = country.strip()
                    if country and len(country) <= 50:  # Reasonable country name length
                        countries.append(country)
        
        return countries[:5]  # Limit to top 5
    
    def normalize_language_code(self, language: str | None) -> str | None:
        """Normalize language name to ISO 639-1 code."""
        if not language:
            return None
        
        language = language.lower().strip()
        
        # Direct mapping
        if language in self.LANGUAGE_MAPPINGS:
            return self.LANGUAGE_MAPPINGS[language]
        
        # Try base class normalization
        return super().normalize_language_code(language)
    
    async def detect_original_language(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """
        Main detection method for IMDb backend.
        
        Priority:
        1. Direct IMDb ID lookup
        2. Title + year search
        
        Args:
            query: Media search parameters
            
        Returns:
            Detection result or None
        """
        start_time = time.time()
        
        try:
            # Try IMDb ID lookup first (most accurate)
            if query.imdb_id:
                result = await self._search_by_id(query)
                if result:
                    result.detection_time_ms = (time.time() - start_time) * 1000
                    return result
            
            # Fall back to title search
            if query.title:
                result = await self._search_by_title(query)
                if result:
                    result.detection_time_ms = (time.time() - start_time) * 1000
                    return result
            
            self.logger.debug(f"No results found for query: {query.title}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in IMDb detection: {e}")
            return None
    
    async def close(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None