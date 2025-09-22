# API Reference

Complete API documentation for the Original Language Detection system.

## Core Classes

### OriginalLanguageDetector

The main detector class that orchestrates language detection across multiple backends.

```python
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

# Create detector
config = OriginalLanguageConfig()
detector = OriginalLanguageDetector(config)
```

#### Methods

##### `__init__(config: OriginalLanguageConfig)`

Initialize the detector with configuration.

**Parameters:**
- `config` - Configuration object with backend and cache settings

##### `async detect_from_filename(filename: str, min_confidence: float | None = None) -> OriginalLanguageDetection | None`

Detect original language from a media filename.

**Parameters:**
- `filename` - Media filename to analyze (e.g., "Spirited Away (2001).mkv")
- `min_confidence` - Minimum confidence threshold (overrides config default)

**Returns:**
- `OriginalLanguageDetection` object if successful, `None` if no detection

**Example:**
```python
result = await detector.detect_from_filename("Your Name (2016).mkv")
if result:
    print(f"Language: {result.original_language}")
    print(f"Confidence: {result.confidence}")
```

##### `async detect_from_query(query: MediaSearchQuery, min_confidence: float | None = None) -> OriginalLanguageDetection | None`

Detect original language from a structured query.

**Parameters:**
- `query` - MediaSearchQuery object with title, year, IMDb ID, etc.
- `min_confidence` - Minimum confidence threshold

**Returns:**
- `OriginalLanguageDetection` object if successful, `None` if no detection

**Example:**
```python
from nhkprep.original_lang import MediaSearchQuery

query = MediaSearchQuery(
    title="Spirited Away",
    year=2001,
    imdb_id="tt0245429"
)
result = await detector.detect_from_query(query)
```

##### `add_backend(backend: OriginalLanguageBackend) -> None`

Add a backend to the detector.

**Parameters:**
- `backend` - Backend instance (TMDbBackend, IMDbBackend, etc.)

##### `async get_cache_stats() -> dict`

Get cache statistics.

**Returns:**
- Dictionary with cache stats (entries, disk usage, etc.)

##### `async cleanup_cache() -> int`

Clean up expired cache entries.

**Returns:**
- Number of entries removed

##### `async clear_cache() -> int`

Clear all cache entries.

**Returns:**
- Number of entries removed

---

### OriginalLanguageDetection

Data class representing a language detection result.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `original_language` | `str \| None` | ISO 639-1 language code (e.g., 'ja', 'en') |
| `confidence` | `float` | Confidence score (0.0 to 1.0) |
| `source` | `str` | Backend source ('tmdb', 'imdb') |
| `method` | `str` | Detection method ('id_match', 'title_year_match') |
| `details` | `str` | Human-readable explanation |
| `title` | `str \| None` | Media title |
| `year` | `int \| None` | Release year |
| `imdb_id` | `str \| None` | IMDb ID |
| `tmdb_id` | `str \| None` | TMDb ID |
| `spoken_languages` | `list[str]` | All languages spoken in content |
| `production_countries` | `list[str]` | Production country codes |
| `detection_time_ms` | `float` | Detection time in milliseconds |
| `timestamp` | `datetime` | When detection was performed |

#### Methods

##### `is_reliable(threshold: float = 0.7) -> bool`

Check if detection is reliable above threshold.

##### `matches_expected_language(expected: str) -> bool`

Check if detected language matches expected language.

---

### MediaSearchQuery

Data class for media search parameters.

```python
from nhkprep.original_lang import MediaSearchQuery

query = MediaSearchQuery(
    title="Spirited Away",
    year=2001,
    media_type="movie"
)
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str \| None` | `None` | Media title |
| `year` | `int \| None` | `None` | Release year |
| `imdb_id` | `str \| None` | `None` | IMDb ID (e.g., "tt0245429") |
| `tmdb_id` | `str \| None` | `None` | TMDb ID |
| `media_type` | `str` | `"movie"` | Media type ('movie' or 'tv') |
| `season` | `int \| None` | `None` | TV season number |
| `episode` | `int \| None` | `None` | TV episode number |
| `fuzzy_match` | `bool` | `True` | Allow fuzzy title matching |
| `include_adult` | `bool` | `False` | Include adult content |

#### Class Methods

##### `from_parsed_filename(parsed: ParsedFilename) -> MediaSearchQuery`

Create query from parsed filename.

---

### OriginalLanguageConfig

Configuration class for the detection system.

```python
from nhkprep.original_lang.config import OriginalLanguageConfig

config = OriginalLanguageConfig(
    tmdb_api_key="your_api_key",
    confidence_threshold=0.8,
    cache_enabled=True
)
```

#### Core Settings

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable/disable detection system |
| `tmdb_api_key` | `str \| None` | `None` | TMDb API key |
| `backend_priorities` | `list[str]` | `["tmdb", "imdb"]` | Backend priority order |
| `confidence_threshold` | `float` | `0.7` | Minimum confidence threshold |
| `max_backends` | `int` | `2` | Maximum backends to try |

#### Rate Limiting

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `tmdb_rate_limit` | `int` | `40` | TMDb requests per window |
| `tmdb_rate_window` | `int` | `10` | TMDb rate window (seconds) |
| `imdb_rate_limit` | `int` | `10` | IMDb requests per window |
| `imdb_rate_window` | `int` | `60` | IMDb rate window (seconds) |

#### Caching

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_enabled` | `bool` | `True` | Enable result caching |
| `cache_dir` | `Path \| None` | `None` | Cache directory (auto-generated if None) |
| `cache_ttl` | `int` | `86400` | Cache TTL in seconds (24 hours) |
| `cache_max_size` | `int` | `1000` | Maximum cache entries |

#### Search Settings

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_max_results` | `int` | `10` | Maximum search results to consider |
| `year_tolerance` | `int` | `1` | Year matching tolerance |
| `title_similarity_threshold` | `float` | `0.8` | Title similarity threshold |

#### Timeouts

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `request_timeout` | `float` | `30.0` | HTTP request timeout |
| `total_timeout` | `float` | `120.0` | Total operation timeout |

#### Methods

##### `get_backend_config(backend_name: str) -> dict`

Get configuration dict for specific backend.

##### `is_backend_available(backend_name: str) -> bool`

Check if backend is available and configured.

##### `get_available_backends() -> list[str]`

Get list of available backends in priority order.

##### `validate() -> list[str]`

Validate configuration and return list of issues.

---

## Backend Classes

### TMDbBackend

The Movie Database API backend.

```python
from nhkprep.original_lang.tmdb import TMDbBackend

backend = TMDbBackend(api_key="your_api_key")
```

#### Methods

##### `async detect_original_language(query: MediaSearchQuery) -> OriginalLanguageDetection | None`

Detect language using TMDb API.

##### `is_available() -> bool`

Check if backend is available (has API key).

---

### IMDbBackend

Internet Movie Database web scraping backend.

```python
from nhkprep.original_lang.imdb import IMDbBackend

backend = IMDbBackend(timeout=15.0)
```

#### Methods

##### `async detect_original_language(query: MediaSearchQuery) -> OriginalLanguageDetection | None`

Detect language using IMDb web scraping.

##### `is_available() -> bool`

Check if backend is available (always True).

---

## Cache System

### FileBasedCache

Persistent file-based cache implementation.

```python
from nhkprep.original_lang.cache import FileBasedCache
from pathlib import Path

cache = FileBasedCache(cache_dir=Path("cache"), ttl=3600, max_size=1000)
```

#### Methods

##### `async get(query: MediaSearchQuery) -> OriginalLanguageDetection | None`

Retrieve cached result.

##### `async set(query: MediaSearchQuery, detection: OriginalLanguageDetection) -> None`

Store result in cache.

##### `async delete(query: MediaSearchQuery) -> bool`

Delete cached result.

##### `async clear() -> int`

Clear all cache entries.

##### `async cleanup() -> int`

Remove expired entries.

##### `async stats() -> dict`

Get cache statistics.

---

### InMemoryCache

In-memory cache implementation for testing.

Same interface as FileBasedCache but stores data in memory only.

---

### NoOpCache

No-operation cache that doesn't store anything.

Used when caching is disabled.

---

## Utility Functions

### create_cache_from_config

```python
from nhkprep.original_lang.cache import create_cache_from_config

cache = create_cache_from_config(config)
```

Create appropriate cache instance from configuration.

---

## Error Handling

All async methods may raise:

- `asyncio.TimeoutError` - Operation timed out
- `httpx.HTTPError` - Network/HTTP errors
- `ValueError` - Invalid parameters
- `RuntimeError` - Backend initialization errors

Example error handling:

```python
try:
    result = await detector.detect_from_filename("movie.mkv")
except asyncio.TimeoutError:
    print("Detection timed out")
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Performance Tips

1. **Use caching** - Enable cache for 24x performance improvement
2. **Set appropriate timeouts** - Balance accuracy vs speed
3. **Use batch processing** - Process multiple files efficiently
4. **TMDb API key** - More reliable than web scraping
5. **Confidence thresholds** - Higher thresholds for reliability

---

## Examples

See [examples.md](examples.md) for complete code examples and use cases.