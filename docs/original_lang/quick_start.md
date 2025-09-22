# Quick Start Guide

Get started quickly with the Original Language Detection system.

## Installation

### Prerequisites

- Python 3.8 or later
- TMDb API key (optional but recommended)

### Install the Package

```bash
# Install from PyPI
pip install nhkprep

# Or install from source
git clone https://github.com/example/nhkprep.git
cd nhkprep
pip install -e .
```

### Set Up Environment

```bash
# Set your TMDb API key (recommended)
export TMDB_API_KEY="your_api_key_here"
```

## Basic Usage

### Command Line

```bash
# Detect language of a single file
nhkprep original-lang "Spirited Away (2001).mkv"

# Process multiple files
nhkprep original-lang "Movie1.mkv" "Movie2.mkv" "Movie3.mkv"

# Scan a directory
nhkprep original-lang --scan /path/to/media

# Output as JSON
nhkprep original-lang --json "Movie.mkv" > result.json
```

### Python API

```python
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_language():
    # Create detector with default config
    config = OriginalLanguageConfig()
    detector = OriginalLanguageDetector(config)
    
    # Detect language from filename
    result = await detector.detect_from_filename("Spirited Away (2001).mkv")
    
    if result:
        print(f"Language: {result.original_language}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Source: {result.source}")
    else:
        print("No language detected")

# Run the async function
asyncio.run(detect_language())
```

## Common Tasks

### Batch Processing

Process a directory of media files:

```bash
# Scan a directory and output JSON
nhkprep original-lang --scan /path/to/media --json > languages.json

# Process with verbose output
nhkprep original-lang --scan /path/to/media --verbose
```

### Custom Configuration

```python
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

# Create custom config
config = OriginalLanguageConfig(
    tmdb_api_key="your_api_key",
    backend_priorities=["tmdb", "imdb"],
    confidence_threshold=0.7,
    cache_enabled=True
)

# Create detector with custom config
detector = OriginalLanguageDetector(config)
```

### Working with IMDb IDs

For most accurate results, use IMDb IDs:

```python
from nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_with_imdb():
    config = OriginalLanguageConfig()
    detector = OriginalLanguageDetector(config)
    
    # Create query with IMDb ID
    query = MediaSearchQuery(imdb_id="tt0245429")  # Spirited Away
    
    # Detect language
    result = await detector.detect_from_query(query)
    
    if result:
        print(f"Language: {result.original_language}")
    else:
        print("No language detected")
```

### Managing the Cache

Control caching to improve performance:

```python
# Clear cache programmatically
await detector.clear_cache()

# Get cache statistics
stats = await detector.get_cache_stats()
print(f"Cache entries: {stats['total_entries']}")
print(f"Cache size: {stats['disk_usage_mb']:.2f} MB")

# CLI: Disable cache
nhkprep original-lang --no-cache "Movie.mkv"

# CLI: Clear cache
nhkprep original-lang --clear-cache "Movie.mkv"
```

## Next Steps

- For detailed API information, see [API Reference](api_reference.md)
- For full usage examples, see [Examples](examples.md)
- For configuration options, see [Configuration Guide](configuration.md)
- For integration help, see [Integration Guide](integration.md)
