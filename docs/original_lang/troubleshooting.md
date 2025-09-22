# Troubleshooting Guide

This guide helps resolve common issues with the Original Language Detection system.

## Common Issues

### No Language Detected

**Symptoms:**
- `None` returned from detection methods
- "No language detected" in CLI output
- Empty language field in results

**Possible Causes:**

1. **Low Confidence**
   
   The detection confidence was below the threshold.
   
   **Solution:**
   ```python
   # Lower confidence threshold
   config = OriginalLanguageConfig(
       confidence_threshold=0.5  # Default is 0.7
   )
   ```
   
   **CLI Solution:**
   ```bash
   python -m nhkprep detect-original-lang --confidence 0.5 "movie.mkv"
   ```

2. **Filename Parsing Failed**
   
   The system couldn't extract title/year from the filename.
   
   **Solution:**
   ```python
   # Provide query manually
   from nhkprep.original_lang import MediaSearchQuery
   
   query = MediaSearchQuery(
       title="Spirited Away",
       year=2001
   )
   result = await detector.detect_from_query(query)
   ```
   
   **CLI Solution:**
   ```bash
   python -m nhkprep detect-original-lang --title "Spirited Away" --year 2001 "movie.mkv"
   ```

3. **No Matching Media Found**
   
   No matches found in TMDb or IMDb databases.
   
   **Solution:**
   - Check spelling of the title
   - Try with IMDb ID if available
   - Check if the media is in the databases
   
   **CLI Solution:**
   ```bash
   # Try with IMDb ID
   python -m nhkprep detect-original-lang --imdb-id "tt0245429" "movie.mkv"
   ```

4. **API Access Issues**
   
   Can't access TMDb API or IMDb website.
   
   **Solution:**
   - Check network connection
   - Verify TMDb API key is valid
   - Try with different backend
   
   **CLI Solution:**
   ```bash
   # Try IMDb only
   python -m nhkprep detect-original-lang --backends "imdb" "movie.mkv"
   ```

### API Key Issues

**Symptoms:**
- "No TMDb API key provided" errors
- "Unable to authenticate" errors
- No TMDb results despite having high-quality filenames

**Solutions:**

1. **Set Environment Variable**
   ```bash
   # Linux/macOS
   export TMDB_API_KEY=your_tmdb_api_key_here
   
   # Windows PowerShell
   $env:TMDB_API_KEY = "your_tmdb_api_key_here"
   ```

2. **Set API Key in Config**
   ```python
   config = OriginalLanguageConfig(
       tmdb_api_key="your_tmdb_api_key_here"
   )
   ```

3. **Pass API Key via CLI**
   ```bash
   python -m nhkprep detect-original-lang --tmdb-key "your_api_key" "movie.mkv"
   ```

4. **Verify API Key**
   ```bash
   # Test API key validity
   curl -H "Authorization: Bearer your_tmdb_api_key_here" \
        -H "Content-Type: application/json;charset=utf-8" \
        "https://api.themoviedb.org/3/movie/550"
   ```

5. **Fall Back to IMDb**
   ```python
   config = OriginalLanguageConfig(
       backend_priorities=["imdb"]  # Use IMDb only
   )
   ```

### Rate Limiting Issues

**Symptoms:**
- "Rate limit exceeded" errors
- Sporadic failures during batch processing
- Timeouts when processing many files

**Solutions:**

1. **Reduce Processing Rate**
   ```python
   config = OriginalLanguageConfig(
       tmdb_rate_limit=30,  # Default is 40
       imdb_rate_limit=5    # Default is 10
   )
   ```

2. **Increase Wait Times**
   ```python
   config = OriginalLanguageConfig(
       tmdb_rate_window=15,  # Default is 10
       imdb_rate_window=120  # Default is 60
   )
   ```

3. **Enable Caching**
   ```python
   config = OriginalLanguageConfig(
       cache_enabled=True,
       cache_ttl=86400  # 24 hours
   )
   ```

4. **Batch Processing with Pauses**
   ```python
   # Process files in smaller batches
   import time
   
   for batch in chunked(files, 10):
       # Process batch
       for file in batch:
           result = await detector.detect_from_filename(file.name)
       
       # Wait between batches
       time.sleep(5)
   ```

### Timeout Issues

**Symptoms:**
- `asyncio.TimeoutError`
- Operations taking too long
- Incomplete batch processing results

**Solutions:**

1. **Increase Timeouts**
   ```python
   config = OriginalLanguageConfig(
       request_timeout=60.0,  # Default is 30.0
       total_timeout=240.0    # Default is 120.0
   )
   ```

2. **CLI Timeout Setting**
   ```bash
   python -m nhkprep detect-original-lang --timeout 60 "movie.mkv"
   ```

3. **Custom Timeout Handler**
   ```python
   import asyncio
   
   try:
       result = await asyncio.wait_for(
           detector.detect_from_filename("movie.mkv"),
           timeout=120.0
       )
   except asyncio.TimeoutError:
       print("Detection timed out")
   ```

4. **Check Network**
   - Test internet connection
   - Check if TMDb/IMDb sites are accessible
   - Try with a VPN if regional restrictions apply

### Incorrect Language Detection

**Symptoms:**
- Wrong language reported
- Low confidence scores
- Inconsistent results

**Solutions:**

1. **Increase Confidence Threshold**
   ```python
   config = OriginalLanguageConfig(
       confidence_threshold=0.8  # Default is 0.7
   )
   ```

2. **Try Multiple Backends**
   ```python
   config = OriginalLanguageConfig(
       backend_priorities=["tmdb", "imdb"],
       max_backends=2  # Use both backends
   )
   ```

3. **Force Detection Method**
   ```python
   # Use IMDb ID for exact match
   from nhkprep.original_lang import MediaSearchQuery
   
   query = MediaSearchQuery(
       imdb_id="tt0245429"  # Most reliable
   )
   result = await detector.detect_from_query(query)
   ```

4. **Manual Override**
   ```python
   # If you know the language, create detection manually
   from nhkprep.original_lang import OriginalLanguageDetection
   
   detection = OriginalLanguageDetection(
       original_language="ja",
       confidence=1.0,
       source="manual",
       title="Spirited Away",
       year=2001
   )
   ```

### Cache Issues

**Symptoms:**
- "Permission denied" when writing to cache
- High disk usage
- Old/stale results

**Solutions:**

1. **Cache Directory Permissions**
   ```python
   import tempfile
   from pathlib import Path
   
   # Use user temp directory
   config = OriginalLanguageConfig(
       cache_dir=Path(tempfile.gettempdir()) / "nhkprep_cache"
   )
   ```

2. **Clear Cache**
   ```python
   # Programmatic clearing
   await detector.clear_cache()
   
   # CLI clearing
   python -m nhkprep manage-original-lang-cache clear
   ```

3. **Cleanup Expired Entries**
   ```python
   # Programmatic cleanup
   await detector.cleanup_cache()
   
   # CLI cleanup
   python -m nhkprep manage-original-lang-cache cleanup
   ```

4. **Limit Cache Size**
   ```python
   config = OriginalLanguageConfig(
       cache_max_size=500  # Default is 1000
   )
   ```

5. **Disable Cache**
   ```python
   # For testing/debugging
   config = OriginalLanguageConfig(
       cache_enabled=False
   )
   ```

### Import and Dependency Issues

**Symptoms:**
- `ModuleNotFoundError`
- `ImportError`
- Missing functionality

**Solutions:**

1. **Install Dependencies**
   ```bash
   pip install -e '.[dev]'  # Install package with dev dependencies
   ```

2. **Check Python Version**
   ```bash
   python --version  # Should be 3.10+ for best compatibility
   ```

3. **Verify Installation**
   ```bash
   python -c "import nhkprep.original_lang; print('OK')"
   ```

4. **Update Dependencies**
   ```bash
   pip install -U httpx beautifulsoup4 typer rich
   ```

5. **Fix PYTHONPATH**
   ```bash
   # Linux/macOS
   export PYTHONPATH=src:$PYTHONPATH
   
   # Windows PowerShell
   $env:PYTHONPATH = "src;$env:PYTHONPATH"
   ```

## Advanced Diagnostics

### Enable Debug Logging

```python
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("nhkprep.original_lang")
logger.setLevel(logging.DEBUG)

# For file logging
handler = logging.FileHandler("language_detection_debug.log")
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
```

### CLI Debug Mode

```bash
# Enable debug logging for CLI
PYTHONPATH=src python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from nhkprep.cli import app
app(['detect-original-lang', 'movie.mkv'])
"
```

### Inspect Cache Contents

```python
import json
from pathlib import Path

# Find cache directory
cache_dir = Path("/tmp/nhkprep/orig_lang_cache")  # Adjust as needed

# List cache files
cache_files = list(cache_dir.glob("*.json"))
print(f"Found {len(cache_files)} cache files")

# Read a sample
if cache_files:
    with open(cache_files[0], "r") as f:
        cache_data = json.load(f)
    print(json.dumps(cache_data, indent=2))
```

### Test Network Connectivity

```python
import asyncio
import httpx

async def test_apis():
    """Test API connectivity."""
    apis = [
        "https://api.themoviedb.org/3/configuration",
        "https://www.imdb.com/title/tt0245429/"
    ]
    
    async with httpx.AsyncClient() as client:
        for url in apis:
            try:
                start = asyncio.get_event_loop().time()
                response = await client.get(url, follow_redirects=True, timeout=10.0)
                elapsed = asyncio.get_event_loop().time() - start
                
                print(f"{url}: {response.status_code} ({elapsed:.2f}s)")
            except Exception as e:
                print(f"{url}: ERROR - {e}")

asyncio.run(test_apis())
```

### Performance Profiling

```python
import cProfile
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_language():
    config = OriginalLanguageConfig()
    detector = OriginalLanguageDetector(config)
    await detector.detect_from_filename("Spirited Away (2001).mkv")

# Profile function
cProfile.run("asyncio.run(detect_language())", "detection_profile")

# Analyze results
import pstats
stats = pstats.Stats("detection_profile")
stats.sort_stats("cumulative").print_stats(20)
```

## How To Get Help

If you're still having issues:

1. **Check this documentation** - Many common issues are covered here.
2. **Examine logs** - Enable debug logging for detailed information.
3. **Check unit tests** - Tests may provide examples of correct usage.
4. **File an issue** - If you've found a bug, file an issue on the repository.
5. **Community forums** - Ask in NHKPrep community forums if available.

## Reporting Bugs

When reporting bugs, please include:

1. **Error message and stack trace**
2. **Minimal reproducer code**
3. **Version information:**
   - Python version
   - NHKPrep version
   - OS name and version
4. **Configuration used**
5. **Filename example** (if relevant)
6. **Logs** (with debug logging enabled)