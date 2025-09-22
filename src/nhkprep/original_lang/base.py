"""
Base backend implementation with common functionality for original language detection.
"""

import logging
import re
from typing import Any

from . import OriginalLanguageBackend, OriginalLanguageDetection, MediaSearchQuery

logger = logging.getLogger(__name__)


class BaseOriginalLanguageBackend(OriginalLanguageBackend):
    """Base implementation with common functionality for language detection backends."""
    
    # Common language code mappings
    LANGUAGE_MAPPINGS = {
        # ISO 639-2 to ISO 639-1 mappings
        'jpn': 'ja', 'eng': 'en', 'fra': 'fr', 'deu': 'de', 'spa': 'es',
        'ita': 'it', 'por': 'pt', 'rus': 'ru', 'kor': 'ko', 'chi': 'zh',
        'zho': 'zh', 'cmn': 'zh', 'hin': 'hi', 'ara': 'ar', 'tha': 'th',
        # Common variations
        'japanese': 'ja', 'english': 'en', 'french': 'fr', 'german': 'de',
        'spanish': 'es', 'italian': 'it', 'portuguese': 'pt', 'russian': 'ru',
        'korean': 'ko', 'chinese': 'zh', 'mandarin': 'zh', 'cantonese': 'zh'
    }
    
    # Confidence scoring weights
    CONFIDENCE_WEIGHTS = {
        'exact_id_match': 1.0,      # Perfect IMDb/TMDb ID match
        'title_year_exact': 0.95,   # Exact title + year match
        'title_exact': 0.85,        # Exact title match (no year)
        'fuzzy_title_year': 0.75,   # Fuzzy title + year match
        'fuzzy_title': 0.65,        # Fuzzy title match only
        'partial_match': 0.4,       # Partial/weak match
        'fallback': 0.2            # Last resort fallback
    }
    
    def __init__(self, name: str):
        """Initialize with base functionality."""
        super().__init__(name)
        self.session = None  # To be set by subclasses if needed
    
    def normalize_language_code(self, lang_code: str | None) -> str | None:
        """
        Normalize language code to ISO 639-1 format.
        
        Args:
            lang_code: Raw language code from API
            
        Returns:
            Normalized ISO 639-1 code or None
        """
        if not lang_code:
            return None
        
        # Clean and normalize
        clean_code = lang_code.lower().strip()
        
        # Direct mapping
        if clean_code in self.LANGUAGE_MAPPINGS:
            return self.LANGUAGE_MAPPINGS[clean_code]
        
        # If it's already a 2-letter code, validate it
        if len(clean_code) == 2 and clean_code.isalpha():
            return clean_code
        
        # Unknown language code
        self.logger.debug(f"Unknown language code: {lang_code}")
        return None
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles.
        
        Args:
            title1: First title to compare
            title2: Second title to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles for comparison
        norm1 = self._normalize_title(title1)
        norm2 = self._normalize_title(title2)
        
        if norm1 == norm2:
            return 1.0
        
        # Simple character-based similarity
        longer = max(len(norm1), len(norm2))
        if longer == 0:
            return 1.0
        
        # Count matching characters (simple approach)
        matches = sum(c1 == c2 for c1, c2 in zip(norm1, norm2))
        max_len = max(len(norm1), len(norm2))
        return matches / max_len if max_len > 0 else 0.0
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison by removing special characters and normalizing case."""
        if not title:
            return ""
        
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def determine_confidence(
        self, 
        query: MediaSearchQuery, 
        found_title: str | None,
        found_year: int | None,
        match_type: str = "unknown"
    ) -> float:
        """
        Determine confidence score based on how well the result matches the query.
        
        Args:
            query: Original search query
            found_title: Title found in API
            found_year: Year found in API  
            match_type: Type of match ('id', 'title_year', etc.)
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # ID matches are always high confidence
        if match_type == "id" and (query.imdb_id or query.tmdb_id):
            return self.CONFIDENCE_WEIGHTS['exact_id_match']
        
        # Title-based matching
        if query.title and found_title:
            title_sim = self.calculate_title_similarity(query.title, found_title)
            
            # Exact title match
            if title_sim >= 0.95:
                if query.year and found_year and abs(query.year - found_year) <= 1:
                    return self.CONFIDENCE_WEIGHTS['title_year_exact']
                elif not query.year or not found_year:
                    return self.CONFIDENCE_WEIGHTS['title_exact'] 
                else:
                    # Title matches but year differs significantly
                    return self.CONFIDENCE_WEIGHTS['fuzzy_title']
            
            # Fuzzy title match
            elif title_sim >= 0.7:
                if query.year and found_year and abs(query.year - found_year) <= 1:
                    return self.CONFIDENCE_WEIGHTS['fuzzy_title_year']
                else:
                    return self.CONFIDENCE_WEIGHTS['fuzzy_title']
            
            # Partial match
            elif title_sim >= 0.5:
                return self.CONFIDENCE_WEIGHTS['partial_match']
        
        # Fallback confidence for any result
        if match_type != "unknown":
            return self.CONFIDENCE_WEIGHTS['fallback']
        
        return 0.0
    
    def create_detection_from_api_data(
        self,
        query: MediaSearchQuery,
        api_data: dict[str, Any],
        original_language: str | None,
        match_type: str = "unknown",
        additional_details: str = ""
    ) -> OriginalLanguageDetection:
        """
        Create a detection result from API response data.
        
        Args:
            query: Original search query
            api_data: Raw API response data
            original_language: Detected original language
            match_type: How the match was found
            additional_details: Extra details for the user
            
        Returns:
            Complete detection result
        """
        # Extract common fields from API data
        found_title = api_data.get('title') or api_data.get('name')
        found_year = None
        
        # Try to extract year from different API formats
        if 'release_date' in api_data and api_data['release_date']:
            try:
                found_year = int(api_data['release_date'][:4])
            except (ValueError, TypeError):
                pass
        elif 'first_air_date' in api_data and api_data['first_air_date']:
            try:
                found_year = int(api_data['first_air_date'][:4])
            except (ValueError, TypeError):
                pass
        elif 'year' in api_data:
            found_year = api_data.get('year')
        
        # Calculate confidence
        confidence = self.determine_confidence(query, found_title, found_year, match_type)
        
        # Extract additional language information
        spoken_languages = []
        production_countries = []
        
        if 'spoken_languages' in api_data:
            for lang in api_data['spoken_languages']:
                if isinstance(lang, dict) and 'iso_639_1' in lang:
                    normalized = self.normalize_language_code(lang['iso_639_1'])
                    if normalized:
                        spoken_languages.append(normalized)
        
        if 'production_countries' in api_data:
            for country in api_data['production_countries']:
                if isinstance(country, dict) and 'iso_3166_1' in country:
                    production_countries.append(country['iso_3166_1'])
        
        # Create detection result
        method_details = {
            'id': 'Direct ID lookup',
            'title_year': f'Title and year match',
            'title': 'Title match',
            'search': 'Search result match'
        }.get(match_type, 'API lookup')
        
        details = f"{method_details} - {found_title}"
        if found_year:
            details += f" ({found_year})"
        if additional_details:
            details += f" - {additional_details}"
        
        return self._create_detection_result(
            original_language=self.normalize_language_code(original_language),
            confidence=confidence,
            method=match_type,
            details=details,
            title=found_title,
            year=found_year,
            imdb_id=query.imdb_id,
            tmdb_id=query.tmdb_id,
            spoken_languages=spoken_languages,
            production_countries=production_countries,
            api_response=api_data
        )


# Language validation utilities

def is_valid_language_code(code: str | None) -> bool:
    """Check if a language code is valid ISO 639-1 format."""
    if not code:
        return False
    return len(code) == 2 and code.isalpha() and code.islower()


def get_language_display_name(code: str | None) -> str:
    """Get display name for a language code."""
    if not code:
        return "Unknown"
    
    DISPLAY_NAMES = {
        'ja': 'Japanese', 'en': 'English', 'fr': 'French', 'de': 'German',
        'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian',
        'ko': 'Korean', 'zh': 'Chinese', 'hi': 'Hindi', 'ar': 'Arabic',
        'th': 'Thai', 'vi': 'Vietnamese', 'tr': 'Turkish', 'pl': 'Polish'
    }
    
    return DISPLAY_NAMES.get(code.lower(), code.upper())


# Example usage
if __name__ == "__main__":
    # Test language normalization with a concrete implementation
    
    class TestBackend(BaseOriginalLanguageBackend):
        async def detect_original_language(self, query):
            return None  # Test implementation
        
        def is_available(self):
            return True
    
    backend = TestBackend("test")
    
    # Test language normalization
    test_codes = ['jpn', 'eng', 'ja', 'en', 'japanese', 'english', 'xyz']
    for code in test_codes:
        normalized = backend.normalize_language_code(code)
        print(f"{code} -> {normalized}")
    
    # Test title similarity
    titles = [
        ("Spirited Away", "Sen to Chihiro no Kamikakushi"),
        ("Spirited Away", "Spirited Away"),
        ("Attack on Titan", "Shingeki no Kyojin"),
        ("Your Name", "Kimi no Na wa")
    ]
    
    for title1, title2 in titles:
        similarity = backend.calculate_title_similarity(title1, title2)
        print(f"'{title1}' vs '{title2}': {similarity:.2f}")