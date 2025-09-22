# Module Structure

This document explains the structure of the Original Language Detection module.

## Package Structure

The Original Language Detection system is organized into the following module structure:

```plaintext
nhkprep/
└── original_lang/
    ├── __init__.py                 # Public API exports
    ├── detector.py                 # OriginalLanguageDetector implementation
    ├── config.py                   # Configuration classes and utilities
    ├── errors.py                   # Custom exceptions
    ├── types.py                    # Data classes and type definitions
    ├── filename_parser.py          # Filename parsing utilities
    ├── backends/
    │   ├── __init__.py             # Backend registry and interface
    │   ├── base.py                 # Abstract backend interface
    │   ├── tmdb.py                 # TMDb API backend implementation
    │   └── imdb.py                 # IMDb scraping backend implementation
    ├── cache/
    │   ├── __init__.py             # Cache exports
    │   ├── manager.py              # Cache management implementation
    │   └── storage.py              # Storage mechanisms (file, memory)
    └── cli/
        └── command.py              # CLI command implementation
```

## Core Components

### Public API (`__init__.py`)

This module exports the public API for the Original Language Detection system. It provides access to the main classes and functions that users will interact with.

```python
# Public exports
from .detector import OriginalLanguageDetector
from .types import MediaSearchQuery, OriginalLanguageResult
from .errors import OriginalLanguageError
from .config import OriginalLanguageConfig

__all__ = [
    'OriginalLanguageDetector',
    'MediaSearchQuery',
    'OriginalLanguageResult', 
    'OriginalLanguageError',
    'OriginalLanguageConfig',
]
```

### Main Detector (`detector.py`)

This module contains the `OriginalLanguageDetector` class, which is the main entry point for language detection. It orchestrates the use of different backends and caching mechanisms.

Key responsibilities:

- Initialize and manage backends based on configuration
- Coordinate detection strategies
- Handle caching of results
- Process and filter detection results

### Configuration (`config.py`)

The configuration module provides the `OriginalLanguageConfig` class for managing all settings for the detection system.

Key responsibilities:

- Store and validate configuration options
- Handle environment variable integration
- Provide defaults for optional settings

### Types (`types.py`)

This module defines the data structures used throughout the system.

Key classes:

- `MediaSearchQuery`: Container for search parameters
- `OriginalLanguageResult`: Container for detection results

### Error Handling (`errors.py`)

This module defines custom exceptions used by the detection system.

```python
class OriginalLanguageError(Exception):
    """Base exception for original language detection errors."""
    pass

class OriginalLanguageBackendError(OriginalLanguageError):
    """Error in a language detection backend."""
    pass

class OriginalLanguageConfigError(OriginalLanguageError):
    """Invalid configuration for language detection."""
    pass
```

### Filename Parser (`filename_parser.py`)

This module contains the `OriginalLanguageFilenameParser` class, which extracts information from filenames using regular expressions.

Key responsibilities:

- Parse various filename formats
- Extract title, year, and IMDb ID
- Clean and normalize extracted data

## Backend System

### Backend Interface (`backends/base.py`)

This module defines the abstract base class for all language detection backends.

```python
class OriginalLanguageBackend(ABC):
    """Abstract base class for original language detection backends."""
    
    @abstractmethod
    async def detect_language(self, query: MediaSearchQuery) -> Optional[OriginalLanguageResult]:
        """Detect the original language of media."""
        pass
    
    @abstractmethod
    def supports_query(self, query: MediaSearchQuery) -> bool:
        """Check if this backend can handle the given query."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the backend."""
        pass
```

### Backend Implementations

The system includes two main backend implementations:

1. **TMDb Backend** (`backends/tmdb.py`)
   - Uses The Movie Database API
   - Requires API key
   - Handles API request rate limiting
   - Performs intelligent search and matching

2. **IMDb Backend** (`backends/imdb.py`)
   - Scrapes IMDb website for language information
   - Serves as a fallback when TMDb is unavailable
   - Implements robust HTML parsing with BeautifulSoup

## Caching System

### Cache Manager (`cache/manager.py`)

This module implements the `OriginalLanguageCacheManager` class, which handles caching of detection results.

Key features:

- Two-level caching (memory and file)
- TTL-based expiration
- Thread-safe operations
- Size limiting and automatic cleanup

### Storage Implementation (`cache/storage.py`)

This module implements the actual storage mechanisms used by the cache manager.

Features:

- File-based JSON storage
- In-memory LRU cache
- Cache entry validation and expiration

## CLI Integration

### Command Implementation (`cli/command.py`)

This module integrates the detection system with the nhkprep CLI framework.

Key responsibilities:

- Define command-line interface
- Parse arguments
- Format and display results
- Handle error cases and user feedback

## Class Relationships

The main classes and their relationships:

```plaintext
OriginalLanguageDetector
├── Uses → OriginalLanguageConfig
├── Creates → OriginalLanguageBackend implementations
│   ├── TMDbBackend
│   └── IMDbBackend
├── Uses → OriginalLanguageFilenameParser
├── Uses → OriginalLanguageCacheManager
└── Returns → OriginalLanguageResult
```

## Import Flow

The typical import flow for using the library:

```python
# Basic usage
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

# Advanced usage
from nhkprep.original_lang import (
    OriginalLanguageDetector,
    MediaSearchQuery,
    OriginalLanguageResult
)
from nhkprep.original_lang.config import OriginalLanguageConfig
from nhkprep.original_lang.errors import OriginalLanguageError
```
