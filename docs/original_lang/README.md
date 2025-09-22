# Original Language Detection

A robust, high-performance system for detecting the original production language of media files using multiple data sources including TMDb and IMDb.

## Features

✨ **Multi-Backend Support** - TMDb API and IMDb web scraping  
🚀 **High Performance** - Persistent caching with 24x speed improvement  
⚡ **Async/Await** - Non-blocking operations for better performance  
🎯 **Confidence Scoring** - Reliability metrics for all detections  
🛠️ **CLI Integration** - Complete command-line interface  
📊 **Rich Output** - Beautiful formatted tables and JSON export  
🔧 **Configurable** - Extensive configuration options  
🧹 **Cache Management** - Built-in cache cleanup and statistics  

## Quick Start

### Installation

```bash
# Install the package in development mode
pip install -e '.[dev]'
```

### Basic Usage

```python
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_language():
    # Configure with TMDb API key (optional)
    config = OriginalLanguageConfig(
        tmdb_api_key="your_tmdb_api_key",  # Optional but recommended
        confidence_threshold=0.7
    )
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Detect from filename
    result = await detector.detect_from_filename(
        "Spirited Away (2001) [1080p].mkv"
    )
    
    if result:
        print(f"Language: {result.original_language}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Source: {result.source}")
    else:
        print("No language detected")

# Run the async function
asyncio.run(detect_language())
```

### CLI Usage

```bash
# Detect language for a single file
python -m nhkprep detect-original-lang "Spirited Away (2001).mkv"

# Batch process multiple files
python -m nhkprep batch-detect-original-lang /path/to/media/files

# Manage cache
python -m nhkprep manage-original-lang-cache stats
```

## Performance

The caching system provides dramatic performance improvements:

- **First detection**: ~500ms per file (API calls)
- **Cached detection**: ~20ms per file (24x faster!)
- **Persistent storage**: Results saved between sessions
- **Smart cleanup**: Automatic TTL expiration and size limits

## Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Commands  │    │  Configuration  │    │      Cache      │
│                 │    │                 │    │                 │
│ • detect-lang   │    │ • API keys      │    │ • File-based    │
│ • batch-detect  │    │ • Thresholds    │    │ • TTL support   │
│ • cache-mgmt    │    │ • Rate limits   │    │ • Size limits   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────────┐
                    │    OriginalLanguageDetector │
                    │                             │
                    │ • Multi-backend support     │
                    │ • Confidence scoring        │
                    │ • Async operations          │
                    │ • Error handling            │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────┴───────────────┐
                    │          Backends           │
                    │                             │
┌───────────────────┼─────────────────────────────┼───────────────────┐
│                   │                             │                   │
│  ┌───────────────┴──┐                 ┌────────┴────────┐         │
│  │   TMDb Backend   │                 │  IMDb Backend   │         │
│  │                  │                 │                 │         │
│  │ • API-based      │                 │ • Web scraping  │         │
│  │ • Rate limited   │                 │ • Fallback      │         │
│  │ • High accuracy  │                 │ • No API key    │         │
│  └──────────────────┘                 └─────────────────┘         │
└───────────────────────────────────────────────────────────────────┘
```

## Documentation

- **[API Reference](api_reference.md)** - Complete API documentation
- **[Configuration Guide](configuration.md)** - Settings and options
- **[CLI Reference](cli_reference.md)** - Command-line usage
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Examples](examples.md)** - Code examples and use cases

## Configuration

Basic configuration options:

```python
config = OriginalLanguageConfig(
    # Core settings
    enabled=True,
    tmdb_api_key="your_api_key",
    backend_priorities=["tmdb", "imdb"],
    confidence_threshold=0.7,
    
    # Caching
    cache_enabled=True,
    cache_ttl=86400,  # 24 hours
    cache_max_size=1000,
    
    # Performance
    request_timeout=30.0,
    total_timeout=120.0
)
```

## Language Codes

The system returns ISO 639-1 language codes:

| Code | Language | Example Movies |
|------|----------|----------------|
| `ja` | Japanese | Spirited Away, Your Name |
| `en` | English | The Matrix, Inception |
| `fr` | French | Amélie, The Artist |
| `de` | German | Das Boot, Run Lola Run |
| `ko` | Korean | Parasite, Oldboy |
| `zh` | Chinese | Hero, Crouching Tiger |

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Add tests for new functionality**
4. **Update documentation**
5. **Submit a pull request**

### Running Tests

```bash
# Run all original language detection tests
pytest tests/ -k "original_lang or cache or backend" -v

# Run with coverage
pytest tests/ -k "original_lang or cache or backend" --cov=src/nhkprep/original_lang
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **TMDb** - The Movie Database API for comprehensive movie data
- **IMDb** - Internet Movie Database for fallback language information  
- **httpx** - Modern HTTP client for async operations
- **BeautifulSoup** - HTML parsing for web scraping
- **Rich** - Beautiful terminal formatting
- **Typer** - Modern CLI framework