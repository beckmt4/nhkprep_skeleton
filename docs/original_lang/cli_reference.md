# CLI Reference

Complete command-line interface reference for Original Language Detection.

## Overview

The nhkprep CLI provides three commands for original language detection:

- `detect-original-lang` - Detect language for a single file
- `batch-detect-original-lang` - Process multiple files in batch
- `manage-original-lang-cache` - Manage detection cache

## Commands

### detect-original-lang

Detect the original language of a single media file.

#### Syntax

```bash
python -m nhkprep detect-original-lang [OPTIONS] MEDIA_FILE
```

#### Arguments

- `MEDIA_FILE` - Path to media file to analyze (required)

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json` | flag | False | Output results as JSON |
| `--title TEXT` | string | None | Override title from filename |
| `--year INTEGER` | int | None | Override year from filename |
| `--imdb-id TEXT` | string | None | Override IMDb ID from filename |
| `--tmdb-key TEXT` | string | None | TMDb API key (overrides config) |
| `--backends TEXT` | string | "tmdb,imdb" | Comma-separated backend list |
| `--confidence FLOAT` | float | 0.7 | Minimum confidence threshold (0.0-1.0) |
| `--timeout INTEGER` | int | 10 | Timeout per backend in seconds |
| `--cache/--no-cache` | flag | True | Enable/disable result caching |
| `--cache-ttl INTEGER` | int | 3600 | Cache TTL in seconds |
| `--cache-stats` | flag | False | Show cache statistics |
| `--help` | flag | - | Show help message |

#### Examples

**Basic usage:**
```bash
python -m nhkprep detect-original-lang "Spirited Away (2001).mkv"
```

**With custom confidence threshold:**
```bash
python -m nhkprep detect-original-lang --confidence 0.8 "Your Name (2016).mp4"
```

**JSON output:**
```bash
python -m nhkprep detect-original-lang --json "Princess Mononoke (1997).avi"
```

**Override filename parsing:**
```bash
python -m nhkprep detect-original-lang \
  --title "Spirited Away" \
  --year 2001 \
  --imdb-id "tt0245429" \
  "movie_file.mkv"
```

**Use only TMDb backend:**
```bash
python -m nhkprep detect-original-lang \
  --backends "tmdb" \
  --tmdb-key "your_api_key" \
  "movie.mkv"
```

**Disable caching:**
```bash
python -m nhkprep detect-original-lang --no-cache "movie.mkv"
```

**Show cache statistics:**
```bash
python -m nhkprep detect-original-lang --cache-stats "movie.mkv"
```

#### Output Format

**Human-readable output:**
```text
Original Language Detection Results
File: Spirited Away (2001).mkv

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property          ┃ Value                       ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Original Language │ ja                          │
│ Confidence        │ 0.950                       │
│ Source            │ tmdb                        │
│ Method            │ title_year_exact            │
│ Title             │ Spirited Away               │
│ Year              │ 2001                        │
│ IMDb ID           │ tt0245429                   │
│ TMDb ID           │ 129                         │
│ Details           │ Exact match via TMDb API    │
│ Detection Time    │ 485ms                       │
└───────────────────┴─────────────────────────────┘

Confidence Level: Very High - Excellent match from reliable source
```

**JSON output:**
```json
{
  "file": "Spirited Away (2001).mkv",
  "detection": {
    "original_language": "ja",
    "confidence": 0.95,
    "source": "tmdb",
    "method": "title_year_exact",
    "details": "Exact match via TMDb API",
    "title": "Spirited Away",
    "year": 2001,
    "imdb_id": "tt0245429",
    "tmdb_id": 129,
    "spoken_languages": ["ja"],
    "production_countries": ["JP"],
    "detection_time_ms": 485.2,
    "timestamp": "2024-01-15T14:30:45.123456"
  }
}
```

---

### batch-detect-original-lang

Process multiple media files in batch.

#### Syntax

```bash
python -m nhkprep batch-detect-original-lang [OPTIONS] DIRECTORY
```

#### Arguments

- `DIRECTORY` - Directory containing media files (required)

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--pattern TEXT` | string | "*.{mkv,mp4,avi,mov,m4v}" | File pattern to match |
| `--json` | flag | False | Output results as JSON |
| `--tmdb-key TEXT` | string | None | TMDb API key |
| `--backends TEXT` | string | "tmdb,imdb" | Comma-separated backend list |
| `--confidence FLOAT` | float | 0.7 | Minimum confidence threshold |
| `--timeout INTEGER` | int | 10 | Timeout per backend in seconds |
| `--cache/--no-cache` | flag | True | Enable/disable caching |
| `--max-files INTEGER` | int | 100 | Maximum files to process |
| `--progress/--no-progress` | flag | True | Show progress information |
| `--output PATH` | path | None | Save results to file |
| `--help` | flag | - | Show help message |

#### Examples

**Basic batch processing:**
```bash
python -m nhkprep batch-detect-original-lang /path/to/movies
```

**Custom file pattern:**
```bash
python -m nhkprep batch-detect-original-lang \
  --pattern "*.mkv" \
  /path/to/movies
```

**JSON output with file save:**
```bash
python -m nhkprep batch-detect-original-lang \
  --json \
  --output results.json \
  /path/to/movies
```

**High confidence threshold:**
```bash
python -m nhkprep batch-detect-original-lang \
  --confidence 0.9 \
  --max-files 50 \
  /path/to/movies
```

**Silent processing:**
```bash
python -m nhkprep batch-detect-original-lang \
  --no-progress \
  --json \
  /path/to/movies
```

#### Output Format

**Human-readable output:**
```text
Batch Original Language Detection
Directory: /path/to/movies
Files found: 25
Backends: tmdb, imdb

Processing 1/25: Spirited Away (2001).mkv
  ✅ ja (confidence: 0.950)

Processing 2/25: Your Name (2016).mp4
  ✅ ja (confidence: 0.920)

Processing 3/25: The Matrix (1999).avi
  ✅ en (confidence: 0.880)

...

Batch Detection Complete
✅ Successful: 23/25 (92.0%)
❌ Failed: 2/25 (8.0%)
💾 Cache entries: 23

Language Distribution:
  ja: 12 files
  en: 8 files
  fr: 2 files
  de: 1 file

💾 Results saved to: results.json
```

**JSON output:**
```json
{
  "summary": {
    "total_files": 25,
    "successful_detections": 23,
    "failed_detections": 2,
    "success_rate": 92.0
  },
  "cache_stats": {
    "total_entries": 23,
    "active_entries": 23,
    "disk_usage_mb": 0.15
  },
  "files": [
    {
      "file": "/path/to/movies/Spirited Away (2001).mkv",
      "filename": "Spirited Away (2001).mkv",
      "detection": {
        "original_language": "ja",
        "confidence": 0.95,
        "source": "tmdb",
        "method": "title_year_exact",
        "detection_time_ms": 485.2
      },
      "success": true
    }
  ]
}
```

---

### manage-original-lang-cache

Manage the original language detection cache.

#### Syntax

```bash
python -m nhkprep manage-original-lang-cache [OPTIONS] ACTION
```

#### Arguments

- `ACTION` - Action to perform: `stats`, `cleanup`, or `clear` (required)

#### Actions

- `stats` - Show cache statistics and usage
- `cleanup` - Remove expired cache entries
- `clear` - Remove all cache entries

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--cache-dir PATH` | path | None | Cache directory (uses default if not specified) |
| `--json` | flag | False | Output results as JSON |
| `--help` | flag | - | Show help message |

#### Examples

**Show cache statistics:**
```bash
python -m nhkprep manage-original-lang-cache stats
```

**Cleanup expired entries:**
```bash
python -m nhkprep manage-original-lang-cache cleanup
```

**Clear all cache entries:**
```bash
python -m nhkprep manage-original-lang-cache clear
```

**JSON output:**
```bash
python -m nhkprep manage-original-lang-cache --json stats
```

**Custom cache directory:**
```bash
python -m nhkprep manage-original-lang-cache \
  --cache-dir /custom/cache/path \
  stats
```

#### Output Format

**Stats (human-readable):**
```text
Original Language Detection Cache Statistics

Cache Directory: /tmp/nhkprep/orig_lang_cache
Total Entries: 1247
Active Entries: 1189
Expired Entries: 58
Disk Usage: 2.34 MB
Oldest Entry: 2024-01-10T09:15:23
Newest Entry: 2024-01-15T16:42:11
```

**Cleanup (human-readable):**
```text
Cache cleanup complete
Removed 58 expired entries
```

**Clear (human-readable):**
```text
Cache cleared
Removed 1247 total entries
```

**JSON output (stats):**
```json
{
  "cache_dir": "/tmp/nhkprep/orig_lang_cache",
  "total_entries": 1247,
  "active_entries": 1189,
  "expired_entries": 58,
  "disk_usage_mb": 2.34,
  "oldest_entry": "2024-01-10T09:15:23.456789",
  "newest_entry": "2024-01-15T16:42:11.987654"
}
```

## Global Options

These options are available for all nhkprep commands:

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--help` | Show help message and exit |

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TMDB_API_KEY` | TMDb API key | `your_tmdb_api_key_here` |
| `NHKPREP_CACHE_DIR` | Cache directory | `/path/to/cache` |
| `NHKPREP_CONFIDENCE_THRESHOLD` | Default confidence | `0.8` |

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 130 | Interrupted by user (Ctrl+C) |

## Common Usage Patterns

### Single File Quick Check

```bash
# Quick language detection
python -m nhkprep detect-original-lang "movie.mkv"
```

### Batch Processing Workflow

```bash
# 1. Process all movies
python -m nhkprep batch-detect-original-lang \
  --output movie_languages.json \
  /path/to/movies

# 2. Check cache usage
python -m nhkprep manage-original-lang-cache stats

# 3. Cleanup old entries
python -m nhkprep manage-original-lang-cache cleanup
```

### High Accuracy Mode

```bash
python -m nhkprep detect-original-lang \
  --confidence 0.9 \
  --backends "tmdb,imdb" \
  --timeout 30 \
  "movie.mkv"
```

### Fast Mode (Cache Heavy)

```bash
python -m nhkprep detect-original-lang \
  --confidence 0.6 \
  --backends "tmdb" \
  --timeout 5 \
  "movie.mkv"
```

### Automation/Scripting

```bash
# Get results in JSON for processing
RESULT=$(python -m nhkprep detect-original-lang --json "movie.mkv")
LANGUAGE=$(echo "$RESULT" | jq -r '.detection.original_language')
echo "Detected language: $LANGUAGE"
```

## Troubleshooting

### Common Issues

**"No module named nhkprep"**
```bash
# Make sure you're in the right directory and environment
cd /path/to/nhkprep_skeleton
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
```

**"No TMDb API key"**
```bash
# Set API key via environment variable
export TMDB_API_KEY="your_api_key_here"
# Or pass directly to command
python -m nhkprep detect-original-lang --tmdb-key "your_key" "movie.mkv"
```

**"Permission denied" (cache directory)**
```bash
# Use a custom cache directory
python -m nhkprep detect-original-lang \
  --cache-dir ~/nhkprep_cache \
  "movie.mkv"
```

**"Timeout errors"**
```bash
# Increase timeout
python -m nhkprep detect-original-lang --timeout 30 "movie.mkv"
```

### Debug Mode

```bash
# Enable debug logging
export PYTHONPATH=src
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from nhkprep.cli import app
app(['detect-original-lang', 'movie.mkv'])
"
```

### Performance Tips

1. **Use caching** - Massive performance improvement for repeated detections
2. **Set TMDb API key** - More reliable than web scraping
3. **Adjust confidence threshold** - Higher = faster but may miss results
4. **Use batch processing** - More efficient for multiple files
5. **Monitor cache size** - Clean up regularly for best performance