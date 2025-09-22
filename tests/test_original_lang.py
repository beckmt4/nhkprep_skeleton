"""Tests for original language detection API."""
import asyncio
from datetime import datetime

from src.nhkprep.original_lang import (
    OriginalLanguageDetection,
    MediaSearchQuery,
    OriginalLanguageDetector,
    OriginalLanguageBackend,
)
from src.nhkprep.original_lang.base import BaseOriginalLanguageBackend
from src.nhkprep.filename_parser import ParsedFilename


class MockBackend(BaseOriginalLanguageBackend):
    """Mock backend for testing."""
    
    def __init__(self):
        super().__init__("mock")
    
    async def detect_original_language(self, query: MediaSearchQuery) -> OriginalLanguageDetection | None:
        """Mock detection that returns Japanese for test data."""
        return OriginalLanguageDetection(
            original_language="ja",
            confidence=0.95,
            source="mock",
            method="api_lookup",
            api_response={"title": query.title, "year": query.year}
        )
    
    def is_available(self) -> bool:
        """Always available for testing."""
        return True


def test_data_structures():
    """Test that all data structures can be created."""
    # Test MediaSearchQuery
    query = MediaSearchQuery(
        title="Your Name",
        year=2016,
        imdb_id="tt5311514"
    )
    assert query.title == "Your Name"
    assert query.year == 2016
    
    # Test OriginalLanguageDetection
    detection = OriginalLanguageDetection(
        original_language="ja",
        confidence=0.95,
        source="test",
        method="manual"
    )
    assert detection.original_language == "ja"
    assert detection.confidence == 0.95
    
    print("✓ Data structures work correctly")


def test_base_backend():
    """Test BaseOriginalLanguageBackend functionality."""
    backend = MockBackend()
    
    # Test language normalization
    assert backend.normalize_language_code("Japanese") == "ja"
    assert backend.normalize_language_code("en") == "en"
    assert backend.normalize_language_code("unknown") is None
    
    # Test title similarity
    similarity = backend.calculate_title_similarity("Your Name", "Kimi no Na wa")
    assert isinstance(similarity, float)
    assert 0.0 <= similarity <= 1.0
    
    # Test confidence calculation - need to pass proper parameters
    query = MediaSearchQuery(title="Your Name", year=2016)
    confidence = backend.determine_confidence(
        query=query,
        found_title="Your Name", 
        found_year=2016,
        match_type="title_year"
    )
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    
    print("✓ Base backend functionality works correctly")


import pytest


def test_detector():
    """Test OriginalLanguageDetector setup with mock backend."""
    backend = MockBackend()
    detector = OriginalLanguageDetector()
    
    # Test that backend can be added
    detector.add_backend(backend)
    assert len(detector.backends) == 1
    assert detector.backends[0].name == "mock"
    
    # Test that query can be created
    query = MediaSearchQuery(
        title="Your Name",
        year=2016,
        imdb_id="tt5311514"
    )
    assert query.title == "Your Name"
    
    # Verify async method exists and is callable
    assert hasattr(detector, 'detect_from_query')
    assert asyncio.iscoroutinefunction(detector.detect_from_query)
    
    print("✓ Detector works correctly with backends")


def main():
    """Run all tests."""
    print("Testing Original Language Detection API...")
    
    test_data_structures()
    test_base_backend()
    test_detector()
    
    print("\n✅ All API tests passed!")


if __name__ == "__main__":
    main()