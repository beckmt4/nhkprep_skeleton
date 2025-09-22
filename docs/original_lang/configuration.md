# Configuration Guide

Complete guide to configuring the Original Language Detection system.

## Quick Start

```python
from nhkprep.original_lang.config import OriginalLanguageConfig

# Basic configuration
config = OriginalLanguageConfig(
    tmdb_api_key="your_tmdb_api_key_here",
    confidence_threshold=0.7,
    cache_enabled=True
)
```

## Configuration Methods

### 1. Direct Configuration

Create configuration objects directly:

```python
config = OriginalLanguageConfig(
    enabled=True,
    tmdb_api_key="your_api_key",
    backend_priorities=["tmdb", "imdb"],
    confidence_threshold=0.8,
    cache_enabled=True,
    cache_ttl=3600  # 1 hour
)
```

### 2. Environment Variables

Set TMDb API key via environment variable:

```bash
export TMDB_API_KEY="your_tmdb_api_key_here"
```

The system will automatically detect and use this key.

### 3. From Runtime Config

If you're using the existing nhkprep configuration system:

```python
from nhkprep.config import RuntimeConfig
from nhkprep.original_lang.config import OriginalLanguageConfig

runtime_config = RuntimeConfig()
orig_lang_config = OriginalLanguageConfig.from_runtime_config(runtime_config)
```

## Core Settings

### Backend Configuration

#### Backend Priorities

Control which backends to use and in what order:

```python
config = OriginalLanguageConfig(
    backend_priorities=["tmdb", "imdb"],  # Try TMDb first, then IMDb
    max_backends=2  # Use up to 2 backends
)
```

Available backends:
- `"tmdb"` - The Movie Database (requires API key, most accurate)
- `"imdb"` - Internet Movie Database (web scraping, no API key required)

#### TMDb API Key

Get your free API key from [The Movie Database](https://www.themoviedb.org/settings/api):

1. Create a free TMDb account
2. Go to Settings → API
3. Request an API key (choose "Developer")
4. Copy your API key

```python
config = OriginalLanguageConfig(
    tmdb_api_key="your_api_key_here"
)
```

### Confidence Threshold

Controls the minimum confidence required for a detection to be considered valid:

```python
config = OriginalLanguageConfig(
    confidence_threshold=0.7  # 70% confidence minimum
)
```

Confidence levels:
- `0.9+` - Very high confidence (excellent match)
- `0.8-0.9` - High confidence (strong match)
- `0.7-0.8` - Good confidence (reasonable match)
- `0.5-0.7` - Moderate confidence (uncertain)
- `<0.5` - Low confidence (likely incorrect)

## Rate Limiting

Protect external APIs from being overwhelmed:

### TMDb Rate Limiting

```python
config = OriginalLanguageConfig(
    tmdb_rate_limit=40,      # 40 requests
    tmdb_rate_window=10,     # per 10 seconds
)
```

TMDb's actual limits are 40 requests per 10 seconds, so the defaults are safe.

### IMDb Rate Limiting

```python
config = OriginalLanguageConfig(
    imdb_rate_limit=10,      # 10 requests  
    imdb_rate_window=60,     # per 60 seconds
)
```

IMDb rate limiting is more conservative since we're web scraping.

## Caching Configuration

### Basic Caching

```python
config = OriginalLanguageConfig(
    cache_enabled=True,
    cache_ttl=86400,        # 24 hours
    cache_max_size=1000     # 1000 entries max
)
```

### Custom Cache Directory

```python
from pathlib import Path

config = OriginalLanguageConfig(
    cache_enabled=True,
    cache_dir=Path("/custom/cache/directory")
)
```

If not specified, cache directory defaults to:
- Windows: `%TEMP%\nhkprep\orig_lang_cache`
- macOS/Linux: `/tmp/nhkprep/orig_lang_cache`

### Cache TTL (Time To Live)

Control how long cached results remain valid:

```python
config = OriginalLanguageConfig(
    cache_ttl=3600      # 1 hour
    # cache_ttl=86400   # 24 hours (default)
    # cache_ttl=604800  # 1 week
)
```

### Cache Size Limits

Control maximum cache size:

```python
config = OriginalLanguageConfig(
    cache_max_size=500   # 500 entries maximum
)
```

When the cache exceeds this size, oldest entries are removed.

### Disable Caching

```python
config = OriginalLanguageConfig(
    cache_enabled=False
)
```

## Search Settings

### Maximum Results

Control how many search results to consider:

```python
config = OriginalLanguageConfig(
    search_max_results=5  # Consider top 5 search results
)
```

More results = better accuracy but slower performance.

### Year Tolerance

Allow fuzzy year matching:

```python
config = OriginalLanguageConfig(
    year_tolerance=1  # Allow ±1 year difference
)
```

Example: A movie from 2001 will match searches for 2000, 2001, or 2002.

### Title Similarity

Control how similar titles need to be for matching:

```python
config = OriginalLanguageConfig(
    title_similarity_threshold=0.8  # 80% similarity required
)
```

Lower values = more fuzzy matching, higher values = stricter matching.

## Timeout Configuration

### Request Timeout

Timeout for individual HTTP requests:

```python
config = OriginalLanguageConfig(
    request_timeout=30.0  # 30 seconds per request
)
```

### Total Timeout

Timeout for entire detection operation:

```python
config = OriginalLanguageConfig(
    total_timeout=120.0  # 2 minutes total
)
```

## Performance Configurations

### High Performance (Fast)

```python
config = OriginalLanguageConfig(
    confidence_threshold=0.8,     # Higher threshold
    max_backends=1,               # Use only one backend
    backend_priorities=["tmdb"],  # TMDb only (fastest)
    request_timeout=10.0,         # Shorter timeout
    cache_enabled=True,           # Essential for performance
    search_max_results=3          # Fewer results to check
)
```

### High Accuracy (Slower)

```python
config = OriginalLanguageConfig(
    confidence_threshold=0.6,       # Lower threshold
    max_backends=2,                 # Use both backends
    backend_priorities=["tmdb", "imdb"],
    request_timeout=30.0,           # Longer timeout
    search_max_results=10,          # More results to check
    year_tolerance=2,               # More fuzzy year matching
    title_similarity_threshold=0.7  # More fuzzy title matching
)
```

### Offline Mode (IMDb Only)

```python
config = OriginalLanguageConfig(
    backend_priorities=["imdb"],  # No TMDb API required
    max_backends=1,
    tmdb_api_key=None            # No API key needed
)
```

## Production Configurations

### Production Defaults

```python
config = OriginalLanguageConfig(
    # Reliability
    confidence_threshold=0.7,
    max_backends=2,
    
    # Performance
    cache_enabled=True,
    cache_ttl=86400,  # 24 hours
    cache_max_size=1000,
    
    # Timeouts
    request_timeout=30.0,
    total_timeout=120.0,
    
    # Rate limiting (respect APIs)
    tmdb_rate_limit=40,
    tmdb_rate_window=10,
    imdb_rate_limit=10,
    imdb_rate_window=60
)
```

### High Volume Processing

```python
config = OriginalLanguageConfig(
    # Aggressive caching
    cache_enabled=True,
    cache_ttl=604800,    # 1 week
    cache_max_size=5000, # 5000 entries
    
    # Conservative rate limiting
    tmdb_rate_limit=30,  # Slower than max
    tmdb_rate_window=10,
    imdb_rate_limit=5,   # Very conservative
    imdb_rate_window=60,
    
    # Efficient search
    search_max_results=5,
    confidence_threshold=0.8
)
```

## Configuration Validation

Validate your configuration:

```python
config = OriginalLanguageConfig(
    confidence_threshold=1.5  # Invalid!
)

issues = config.validate()
if issues:
    for issue in issues:
        print(f"Configuration issue: {issue}")
```

Common validation issues:
- Confidence threshold not between 0 and 1
- Request timeout greater than total timeout
- Invalid backend names
- Negative cache sizes or TTL values

## Environment Integration

### Docker Environment

```dockerfile
ENV TMDB_API_KEY=your_api_key_here
ENV NHKPREP_CACHE_DIR=/app/cache
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nhkprep-config
data:
  tmdb_api_key: "your_api_key_here"
  confidence_threshold: "0.8"
  cache_ttl: "86400"
```

### CI/CD Pipeline

```bash
# Set in CI environment
export TMDB_API_KEY="${{ secrets.TMDB_API_KEY }}"
export NHKPREP_CONFIDENCE_THRESHOLD="0.8"
```

## Troubleshooting Configuration

### Common Issues

**No TMDb API Key**
```python
# Check if TMDb backend is available
if not config.is_backend_available("tmdb"):
    print("TMDb backend not available - check API key")
```

**Cache Directory Permissions**
```python
# Use a directory you have write access to
config = OriginalLanguageConfig(
    cache_dir=Path.home() / ".nhkprep_cache"
)
```

**Rate Limiting Too Aggressive**
```python
# If you're getting rate limited, reduce limits
config = OriginalLanguageConfig(
    tmdb_rate_limit=20,  # Half the default
    imdb_rate_limit=5    # Half the default
)
```

### Debug Configuration

```python
# Enable debug logging
import logging
logging.getLogger("nhkprep.original_lang").setLevel(logging.DEBUG)

# Check available backends
available = config.get_available_backends()
print(f"Available backends: {available}")

# Validate configuration
issues = config.validate()
if issues:
    print("Configuration issues:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("Configuration is valid")
```

## Best Practices

1. **Always use caching** in production for performance
2. **Set appropriate timeouts** based on your use case
3. **Use TMDb API key** when possible for best accuracy
4. **Monitor rate limits** to avoid being blocked
5. **Validate configuration** before deploying
6. **Use environment variables** for sensitive data like API keys
7. **Test configuration** with a small dataset first
8. **Monitor cache size** and cleanup regularly