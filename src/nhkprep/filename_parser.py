"""
Filename parsing for extracting media metadata.

Supports common filename patterns for movies and TV shows, including:
- Movie Title (YEAR) {imdb-ttXXXXXXX} [quality info]
- Movie Title (YEAR) [quality info] 
- Show Name S01E01 - Episode Title
- Show Name - 01x01 - Episode Title
- Various release group and quality tags
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedFilename:
    """Represents parsed information from a media filename."""
    
    # Core identification
    title: str | None = None
    year: int | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    
    # TV show specific
    season: int | None = None
    episode: int | None = None
    episode_title: str | None = None
    
    # Quality and source info
    resolution: str | None = None  # 1080p, 720p, etc.
    source: str | None = None      # BluRay, WEB-DL, etc.
    codec: str | None = None       # x264, x265, etc.
    audio: str | None = None       # DTS, AC3, etc.
    
    # Metadata
    release_group: str | None = None
    is_tv_show: bool = False
    original_filename: str = ""
    
    def __post_init__(self):
        """Clean up extracted values."""
        if self.title:
            # Clean up title - remove trailing dashes and extra whitespace
            self.title = self.title.strip(' -')
        if self.episode_title:
            self.episode_title = self.episode_title.strip()


class FilenameParser:
    """Parser for extracting metadata from media filenames."""
    
    def __init__(self):
        """Initialize with compiled regex patterns."""
        
        # IMDb ID patterns
        self.imdb_pattern = re.compile(r'\{imdb[_-]?(tt\d{7,8})\}', re.IGNORECASE)
        self.tmdb_pattern = re.compile(r'\{tmdb[_-]?(\d+)\}', re.IGNORECASE)
        
        # Movie patterns - Title (YEAR) format
        self.movie_patterns = [
            # Movie Title (YEAR) {imdb-ttXXXXXXX} [additional info]
            re.compile(r'^(.+?)\s*\((\d{4})\)\s*(?:\{[^}]*\})?\s*(?:\[.*?\])*', re.IGNORECASE),
            # Movie Title YEAR [additional info] 
            re.compile(r'^(.+?)\s+(\d{4})\s*(?:\[.*?\])*', re.IGNORECASE),
        ]
        
        # TV Show patterns
        self.tv_patterns = [
            # Show Name (YEAR) - S01E01 - Episode Title 
            re.compile(r'^(.+?)\s*\(\d{4}\)\s*-\s*S(\d+)E(\d+)(?:\s*-\s*(.+?))?(?:\s*\[.*?\])*$', re.IGNORECASE),
            # Show Name S01E01 - Episode Title
            re.compile(r'^(.+?)\s+S(\d+)E(\d+)(?:\s*-\s*(.+?))?(?:\s*\[.*?\])*$', re.IGNORECASE),
            # Show Name - S01E01 - Episode Title  
            re.compile(r'^(.+?)\s*-\s*S(\d+)E(\d+)(?:\s*-\s*(.+?))?(?:\s*\[.*?\])*$', re.IGNORECASE),
            # Show Name 1x01 - Episode Title
            re.compile(r'^(.+?)\s+(\d+)x(\d+)(?:\s*-\s*(.+?))?(?:\s*\[.*?\])*$', re.IGNORECASE),
            # Show Name - 1x01 - Episode Title
            re.compile(r'^(.+?)\s*-\s*(\d+)x(\d+)(?:\s*-\s*(.+?))?(?:\s*\[.*?\])*$', re.IGNORECASE),
        ]
        
        # Quality/source patterns
        self.resolution_pattern = re.compile(r'\b(480p|720p|1080p|1440p|2160p|4K)\b', re.IGNORECASE)
        self.source_patterns = re.compile(r'\b(BluRay|Blu-ray|BDRip|WEB-?DL|WEBRip|DVDRip|HDTV|CAM|TS)\b', re.IGNORECASE)
        self.codec_patterns = re.compile(r'\b(x264|x265|H\.?264|H\.?265|XviD|DivX)\b', re.IGNORECASE)
        self.audio_patterns = re.compile(r'\b(DTS|AC3|AAC|MP3|FLAC|EAC3)\s*(\d\.\d)?\b', re.IGNORECASE)
        
        # Release group pattern (usually at the end)
        self.release_group_pattern = re.compile(r'[-\s]([A-Za-z0-9]+)(?:\.[mkv|mp4|avi])?$')
    
    def parse(self, filename: str) -> ParsedFilename:
        """
        Parse a filename and extract metadata.
        
        Args:
            filename: The filename to parse (with or without extension)
            
        Returns:
            ParsedFilename object with extracted metadata
        """
        logger.debug(f"Parsing filename: {filename}")
        
        # Initialize result
        result = ParsedFilename(original_filename=filename)
        
        # Remove file extension
        name = Path(filename).stem
        
        # Extract IDs first (they're most reliable)
        self._extract_ids(name, result)
        
        # Try TV show patterns first (they're more specific)
        if self._try_tv_patterns(name, result):
            result.is_tv_show = True
            logger.debug(f"Detected as TV show: {result.title} S{result.season}E{result.episode}")
        else:
            # Try movie patterns
            self._try_movie_patterns(name, result)
            logger.debug(f"Detected as movie: {result.title} ({result.year})")
        
        # Extract quality information
        self._extract_quality_info(name, result)
        
        # Extract release group
        self._extract_release_group(name, result)
        
        return result
    
    def _extract_ids(self, name: str, result: ParsedFilename) -> None:
        """Extract IMDb and TMDb IDs from filename."""
        
        # IMDb ID
        imdb_match = self.imdb_pattern.search(name)
        if imdb_match:
            result.imdb_id = imdb_match.group(1)
            logger.debug(f"Found IMDb ID: {result.imdb_id}")
        
        # TMDb ID  
        tmdb_match = self.tmdb_pattern.search(name)
        if tmdb_match:
            result.tmdb_id = tmdb_match.group(1)
            logger.debug(f"Found TMDb ID: {result.tmdb_id}")
    
    def _try_tv_patterns(self, name: str, result: ParsedFilename) -> bool:
        """Try to match TV show patterns."""
        
        for pattern in self.tv_patterns:
            match = pattern.match(name)
            if match:
                result.title = match.group(1).strip()
                result.season = int(match.group(2))
                result.episode = int(match.group(3))
                
                # Episode title is optional
                if len(match.groups()) >= 4 and match.group(4):
                    result.episode_title = match.group(4).strip()
                
                return True
        
        return False
    
    def _try_movie_patterns(self, name: str, result: ParsedFilename) -> None:
        """Try to match movie patterns."""
        
        for pattern in self.movie_patterns:
            match = pattern.match(name)
            if match:
                result.title = match.group(1).strip()
                try:
                    result.year = int(match.group(2))
                except (ValueError, IndexError):
                    pass
                break
    
    def _extract_quality_info(self, name: str, result: ParsedFilename) -> None:
        """Extract quality and source information."""
        
        # Resolution
        res_match = self.resolution_pattern.search(name)
        if res_match:
            result.resolution = res_match.group(1)
        
        # Source  
        src_match = self.source_patterns.search(name)
        if src_match:
            result.source = src_match.group(1)
        
        # Codec
        codec_match = self.codec_patterns.search(name)
        if codec_match:
            result.codec = codec_match.group(1)
        
        # Audio
        audio_match = self.audio_patterns.search(name)
        if audio_match:
            audio = audio_match.group(1)
            if audio_match.group(2):  # Channel info like "2.0"
                audio += f" {audio_match.group(2)}"
            result.audio = audio
    
    def _extract_release_group(self, name: str, result: ParsedFilename) -> None:
        """Extract release group from end of filename."""
        
        # Remove known quality tags first for better release group detection
        cleaned = name
        for pattern in [self.resolution_pattern, self.source_patterns, 
                       self.codec_patterns, self.audio_patterns]:
            cleaned = pattern.sub('', cleaned)
        
        match = self.release_group_pattern.search(cleaned)
        if match:
            result.release_group = match.group(1)
    
    def extract_search_terms(self, parsed: ParsedFilename) -> dict[str, Any]:
        """
        Extract search terms for API queries.
        
        Args:
            parsed: ParsedFilename object
            
        Returns:
            Dict with search parameters for movie/TV APIs
        """
        terms = {}
        
        if parsed.title:
            terms['title'] = parsed.title
        
        if parsed.year:
            terms['year'] = parsed.year
        
        if parsed.imdb_id:
            terms['imdb_id'] = parsed.imdb_id
        
        if parsed.tmdb_id:
            terms['tmdb_id'] = parsed.tmdb_id
        
        if parsed.is_tv_show:
            terms['media_type'] = 'tv'
            if parsed.season:
                terms['season'] = parsed.season
            if parsed.episode:
                terms['episode'] = parsed.episode
        else:
            terms['media_type'] = 'movie'
        
        return terms


def parse_filename(filename: str) -> ParsedFilename:
    """
    Convenience function to parse a filename.
    
    Args:
        filename: The filename to parse
        
    Returns:
        ParsedFilename object with extracted metadata
    """
    parser = FilenameParser()
    return parser.parse(filename)


# Example usage and testing
if __name__ == "__main__":
    # Test with some example filenames
    test_files = [
        "Kiki's Delivery Service (1989) {imdb-tt0097814} [Bluray-1080p Proper][EAC3 2.0][x265].mkv",
        "Vampire Hunter D (1985) {imdb-tt0090248} [WEBDL-1080p][AAC 2.0][x264].mkv",
        "Spirited Away (2001) [1080p BluRay x264 DTS].mkv",
        "Attack on Titan S04E01 - The Other Side of the Sea [1080p].mkv",
        "Death Note - 01x01 - Rebirth [720p WEB-DL].mkv"
    ]
    
    parser = FilenameParser()
    for filename in test_files:
        parsed = parser.parse(filename)
        print(f"\nFile: {filename}")
        print(f"Title: {parsed.title}")
        print(f"Year: {parsed.year}")
        print(f"IMDb ID: {parsed.imdb_id}")
        print(f"TV Show: {parsed.is_tv_show}")
        if parsed.is_tv_show:
            print(f"Season: {parsed.season}, Episode: {parsed.episode}")
        print(f"Quality: {parsed.resolution} {parsed.source} {parsed.codec}")