# Usage Examples

Practical examples showing how to use the Original Language Detection system.

## Basic Examples

### Simple Language Detection

Detect the original language of a media file:

```python
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_language():
    # Create configuration (using TMDb API key if available)
    config = OriginalLanguageConfig()
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Detect language from filename
    result = await detector.detect_from_filename("Spirited Away (2001).mkv")
    
    if result:
        print(f"Language: {result.original_language}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Source: {result.source}")
        print(f"Method: {result.method}")
    else:
        print("No language detected")

# Run the async function
asyncio.run(high_performance_batch())
```
```

### Detection with Manual Parameters

```python
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_with_manual_params():
    # Create configuration
    config = OriginalLanguageConfig()
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Create query with manual parameters
    query = MediaSearchQuery(
        title="Spirited Away",
        year=2001,
        media_type="movie"
    )
    
    # Detect language from query
    result = await detector.detect_from_query(query)
    
    if result:
        print(f"Language: {result.original_language}")
        print(f"Confidence: {result.confidence:.3f}")
    else:
        print("No language detected")

asyncio.run(detect_with_manual_params())
```

### Using IMDb ID

```python
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_with_imdb_id():
    # Create configuration
    config = OriginalLanguageConfig()
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Create query with IMDb ID (most reliable)
    query = MediaSearchQuery(
        imdb_id="tt0245429"  # Spirited Away
    )
    
    # Detect language from IMDb ID
    result = await detector.detect_from_query(query)
    
    if result:
        print(f"Language: {result.original_language}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Details: {result.details}")
    else:
        print("No language detected")

asyncio.run(detect_with_imdb_id())
```

## Advanced Examples

### Batch Processing Multiple Files

```python
import asyncio
import os
from pathlib import Path
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def batch_process_directory(directory):
    # Create configuration
    config = OriginalLanguageConfig(
        cache_enabled=True,  # Enable caching for better performance
    )
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Find all media files
    media_files = []
    for ext in ['mkv', 'mp4', 'avi']:
        media_files.extend(Path(directory).glob(f"*.{ext}"))
    
    print(f"Found {len(media_files)} media files")
    
    # Track statistics
    detected = 0
    languages = {}
    
    # Process each file
    for file in media_files:
        try:
            result = await detector.detect_from_filename(file.name)
            
            if result and result.original_language:
                print(f"{file.name}: {result.original_language} ({result.confidence:.3f})")
                detected += 1
                
                # Count languages
                lang = result.original_language
                languages[lang] = languages.get(lang, 0) + 1
            else:
                print(f"{file.name}: No language detected")
        except Exception as e:
            print(f"{file.name}: Error - {e}")
    
    # Print summary
    print(f"\nDetected languages for {detected}/{len(media_files)} files")
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {count} files")
    
    # Cache stats
    stats = await detector.get_cache_stats()
    print(f"\nCache entries: {stats['total_entries']}")

# Run with a directory path
asyncio.run(batch_process_directory("/path/to/media/files"))
```

### Working with Multiple Backends

```python
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def test_multiple_backends():
    # Create config with both backends
    tmdb_config = OriginalLanguageConfig(
        backend_priorities=["tmdb"],  # TMDb only
        max_backends=1
    )
    
    imdb_config = OriginalLanguageConfig(
        backend_priorities=["imdb"],  # IMDb only
        max_backends=1
    )
    
    both_config = OriginalLanguageConfig(
        backend_priorities=["tmdb", "imdb"],  # Both in order
        max_backends=2
    )
    
    # Create three detectors
    tmdb_detector = OriginalLanguageDetector(tmdb_config)
    imdb_detector = OriginalLanguageDetector(imdb_config)
    both_detector = OriginalLanguageDetector(both_config)
    
    # Test filename
    filename = "Spirited Away (2001).mkv"
    
    # Test each detector
    print("Testing with TMDb backend:")
    tmdb_result = await tmdb_detector.detect_from_filename(filename)
    if tmdb_result:
        print(f"  Language: {tmdb_result.original_language}")
        print(f"  Confidence: {tmdb_result.confidence:.3f}")
        print(f"  Source: {tmdb_result.source}")
    else:
        print("  No language detected")
    
    print("\nTesting with IMDb backend:")
    imdb_result = await imdb_detector.detect_from_filename(filename)
    if imdb_result:
        print(f"  Language: {imdb_result.original_language}")
        print(f"  Confidence: {imdb_result.confidence:.3f}")
        print(f"  Source: {imdb_result.source}")
    else:
        print("  No language detected")
    
    print("\nTesting with both backends:")
    both_result = await both_detector.detect_from_filename(filename)
    if both_result:
        print(f"  Language: {both_result.original_language}")
        print(f"  Confidence: {both_result.confidence:.3f}")
        print(f"  Source: {both_result.source}")
    else:
        print("  No language detected")

asyncio.run(test_multiple_backends())
```

### Caching Controls

```python
import asyncio
import time
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def demonstrate_caching():
    # Create detector with caching enabled
    config = OriginalLanguageConfig(
        cache_enabled=True,
        cache_ttl=3600  # 1 hour cache TTL
    )
    
    detector = OriginalLanguageDetector(config)
    
    # Test filename
    filename = "Spirited Away (2001).mkv"
    
    # First detection (should go to backends)
    print("First detection (uncached):")
    start_time = time.time()
    result = await detector.detect_from_filename(filename)
    elapsed = time.time() - start_time
    
    if result:
        print(f"  Language: {result.original_language}")
        print(f"  Source: {result.source}")
        print(f"  Time: {elapsed:.3f} seconds")
    
    # Second detection (should use cache)
    print("\nSecond detection (cached):")
    start_time = time.time()
    result = await detector.detect_from_filename(filename)
    elapsed = time.time() - start_time
    
    if result:
        print(f"  Language: {result.original_language}")
        print(f"  Source: {result.source}")
        print(f"  Time: {elapsed:.3f} seconds")
    
    # Get cache stats
    stats = await detector.get_cache_stats()
    print(f"\nCache stats:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Active entries: {stats['active_entries']}")
    print(f"  Disk usage: {stats['disk_usage_mb']:.2f} MB")
    
    # Clear cache
    removed = await detector.clear_cache()
    print(f"\nRemoved {removed} entries from cache")

asyncio.run(demonstrate_caching())
```

### Error Handling

```python
import asyncio
import httpx
from nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from nhkprep.original_lang.config import OriginalLanguageConfig

async def error_handling_demo():
    # Create configuration
    config = OriginalLanguageConfig(
        request_timeout=5.0,  # Short timeout for demonstration
        tmdb_api_key="invalid_key"  # Intentionally invalid key
    )
    
    detector = OriginalLanguageDetector(config)
    
    # Test cases
    test_cases = [
        "Invalid Filename Without Year.mkv",  # No year info
        "Movie with Invalid IMDb ID [tt9999999].mkv",  # Non-existent IMDb ID
        MediaSearchQuery(title="This Movie Does Not Exist", year=2999),  # Future year
        MediaSearchQuery(imdb_id="tt9999999")  # Invalid IMDb ID
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test}")
        
        try:
            if isinstance(test, str):
                result = await detector.detect_from_filename(test)
            else:
                result = await detector.detect_from_query(test)
                
            if result:
                print(f"  Success: {result.original_language} (confidence: {result.confidence:.3f})")
            else:
                print("  No result: Detection below confidence threshold or not found")
                
        except httpx.HTTPError as e:
            print(f"  HTTP error: {e}")
        except asyncio.TimeoutError:
            print("  Timeout: Operation took too long")
        except ValueError as e:
            print(f"  Value error: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    print("\nAll error cases handled properly!")

asyncio.run(error_handling_demo())
```

## Integration Examples

### Integration with Web App

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from nhkprep.original_lang.config import OriginalLanguageConfig

# Create FastAPI app
app = FastAPI(title="Language Detection API")

# Create detector (reuse across requests)
config = OriginalLanguageConfig(
    cache_enabled=True,
    request_timeout=10.0
)
detector = OriginalLanguageDetector(config)

# Request models
class FilenameRequest(BaseModel):
    filename: str

class QueryRequest(BaseModel):
    title: str = None
    year: int = None
    imdb_id: str = None

# Response model
class DetectionResponse(BaseModel):
    original_language: str = None
    confidence: float = 0.0
    source: str = None
    title: str = None
    year: int = None
    detection_time_ms: float = 0.0

# Endpoints
@app.post("/detect/filename", response_model=DetectionResponse)
async def detect_from_filename(request: FilenameRequest):
    try:
        result = await detector.detect_from_filename(request.filename)
        
        if not result:
            raise HTTPException(status_code=404, detail="No language detected")
        
        return DetectionResponse(
            original_language=result.original_language,
            confidence=result.confidence,
            source=result.source,
            title=result.title,
            year=result.year,
            detection_time_ms=result.detection_time_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect/query", response_model=DetectionResponse)
async def detect_from_query(request: QueryRequest):
    try:
        query = MediaSearchQuery(
            title=request.title,
            year=request.year,
            imdb_id=request.imdb_id
        )
        
        result = await detector.detect_from_query(query)
        
        if not result:
            raise HTTPException(status_code=404, detail="No language detected")
        
        return DetectionResponse(
            original_language=result.original_language,
            confidence=result.confidence,
            source=result.source,
            title=result.title,
            year=result.year,
            detection_time_ms=result.detection_time_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats")
async def get_cache_stats():
    return await detector.get_cache_stats()

@app.post("/cache/clear")
async def clear_cache():
    removed = await detector.clear_cache()
    return {"removed": removed}

# Run with: uvicorn app:app --reload
```

### Integration with Processing Pipeline

```python
import asyncio
import json
from pathlib import Path
from datetime import datetime
from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def media_processing_pipeline():
    # Create detector
    config = OriginalLanguageConfig(cache_enabled=True)
    detector = OriginalLanguageDetector(config)
    
    # Input directory
    input_dir = Path("/path/to/input")
    output_file = Path("/path/to/output/language_metadata.json")
    
    # Find all media files
    media_files = []
    for ext in ['mkv', 'mp4', 'avi', 'mov']:
        media_files.extend(input_dir.glob(f"**/*.{ext}"))
    
    print(f"Processing {len(media_files)} files...")
    
    # Results dictionary
    results = {
        "processed_date": datetime.now().isoformat(),
        "total_files": len(media_files),
        "files": []
    }
    
    # Process each file
    for file in media_files:
        rel_path = file.relative_to(input_dir)
        print(f"Processing {rel_path}...")
        
        try:
            # Detect language
            result = await detector.detect_from_filename(file.name)
            
            # Add to results
            file_result = {
                "file": str(rel_path),
                "filename": file.name,
                "filesize_mb": file.stat().st_size / (1024 * 1024),
                "detection": None
            }
            
            if result:
                file_result["detection"] = {
                    "language": result.original_language,
                    "confidence": result.confidence,
                    "source": result.source,
                    "title": result.title,
                    "year": result.year,
                    "imdb_id": result.imdb_id
                }
            
            results["files"].append(file_result)
            
        except Exception as e:
            print(f"  Error: {e}")
            # Add error to results
            results["files"].append({
                "file": str(rel_path),
                "filename": file.name,
                "error": str(e)
            })
    
    # Calculate statistics
    languages = {}
    detected_count = 0
    
    for file_result in results["files"]:
        if file_result.get("detection") and file_result["detection"].get("language"):
            lang = file_result["detection"]["language"]
            languages[lang] = languages.get(lang, 0) + 1
            detected_count += 1
    
    # Add statistics
    results["statistics"] = {
        "detected_count": detected_count,
        "success_rate": detected_count / len(media_files) if media_files else 0,
        "language_distribution": languages
    }
    
    # Save results
    output_file.parent.mkdir(exist_ok=True, parents=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_file}")
    print(f"Detection rate: {detected_count}/{len(media_files)} ({detected_count/len(media_files)*100:.1f}%)")
    
    # Show language distribution
    print("\nLanguage distribution:")
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {count} files ({count/len(media_files)*100:.1f}%)")

# Run the pipeline
asyncio.run(media_processing_pipeline())
```

## Scripting Examples

### Command-Line Script

```python
#!/usr/bin/env python3
"""
Simple command-line script to detect original language of media files.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def detect_language(file_path, tmdb_api_key=None):
    """Detect language for a file."""
    # Create config
    config = OriginalLanguageConfig(
        tmdb_api_key=tmdb_api_key,
        cache_enabled=True
    )
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Get filename
    filename = Path(file_path).name
    
    # Detect language
    result = await detector.detect_from_filename(filename)
    
    if result:
        print(f"{filename}:")
        print(f"  Language: {result.original_language}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Source: {result.source}")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        if result.imdb_id:
            print(f"  IMDb ID: {result.imdb_id}")
        
        return True
    else:
        print(f"{filename}: No language detected")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Detect original language of media files")
    parser.add_argument("files", nargs="+", help="Media file(s) to analyze")
    parser.add_argument("--tmdb-key", help="TMDb API key")
    args = parser.parse_args()
    
    # Process files
    success = 0
    failed = 0
    
    for file in args.files:
        try:
            if asyncio.run(detect_language(file, args.tmdb_key)):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"{file}: ERROR - {e}")
            failed += 1
    
    # Print summary
    print(f"\nProcessed {len(args.files)} files:")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

### JSON Export Script

```python
#!/usr/bin/env python3
"""
Export language detection results to JSON.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from nhkprep.original_lang import OriginalLanguageDetector
from nhkprep.original_lang.config import OriginalLanguageConfig

async def export_language_data(directory, output_file):
    """Detect and export language data for files in directory."""
    # Create detector
    config = OriginalLanguageConfig(
        tmdb_api_key=os.environ.get("TMDB_API_KEY"),
        cache_enabled=True
    )
    detector = OriginalLanguageDetector(config)
    
    # Find media files
    extensions = ['.mkv', '.mp4', '.avi', '.mov', '.m4v']
    media_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                media_files.append(os.path.join(root, file))
    
    print(f"Found {len(media_files)} media files")
    
    # Process files
    results = []
    
    for file in media_files:
        rel_path = os.path.relpath(file, directory)
        filename = os.path.basename(file)
        
        try:
            result = await detector.detect_from_filename(filename)
            
            if result:
                results.append({
                    "file": rel_path,
                    "language": result.original_language,
                    "confidence": result.confidence,
                    "source": result.source,
                    "title": result.title,
                    "year": result.year,
                    "imdb_id": result.imdb_id,
                    "tmdb_id": result.tmdb_id
                })
            else:
                results.append({
                    "file": rel_path,
                    "language": None,
                    "error": "No language detected"
                })
        except Exception as e:
            results.append({
                "file": rel_path,
                "language": None,
                "error": str(e)
            })
    
    # Generate output
    output = {
        "timestamp": datetime.now().isoformat(),
        "directory": directory,
        "file_count": len(media_files),
        "results": results
    }
    
    # Save output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Results exported to {output_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: export_languages.py <directory> <output.json>")
        return 1
    
    directory = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory")
        return 1
    
    asyncio.run(export_language_data(directory, output_file))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Performance Optimized Examples

### High-Performance Batch Processing

```python
import asyncio
import time
from pathlib import Path
from nhkprep.original_lang import OriginalLanguageDetector, MediaSearchQuery
from nhkprep.original_lang.config import OriginalLanguageConfig

async def process_file(detector, file):
    """Process a single file."""
    try:
        result = await detector.detect_from_filename(file.name)
        return file, result
    except Exception as e:
        return file, None

async def high_performance_batch():
    """Process many files with optimized concurrency."""
    # Configure for performance
    config = OriginalLanguageConfig(
        cache_enabled=True,
        cache_ttl=86400,  # 24 hours
        request_timeout=15.0,
        confidence_threshold=0.7
    )
    
    # Create detector
    detector = OriginalLanguageDetector(config)
    
    # Find media files
    directory = Path("/path/to/media")
    media_files = []
    
    for ext in ['mkv', 'mp4', 'avi']:
        media_files.extend(directory.glob(f"*.{ext}"))
    
    # Limit for demo
    media_files = media_files[:100]
    print(f"Processing {len(media_files)} files")
    
    # Start timer
    start_time = time.time()
    
    # Create tasks (process up to 5 files concurrently)
    tasks = []
    semaphore = asyncio.Semaphore(5)  # Limit concurrency
    
    async def bounded_process(file):
        async with semaphore:
            return await process_file(detector, file)
    
    for file in media_files:
        tasks.append(asyncio.create_task(bounded_process(file)))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    # Process results
    success = 0
    languages = {}
    
    for file, result in results:
        if result and result.original_language:
            print(f"{file.name}: {result.original_language} ({result.confidence:.3f})")
            success += 1
            
            lang = result.original_language
            languages[lang] = languages.get(lang, 0) + 1
        else:
            print(f"{file.name}: No language detected")
    
    # End timer
    elapsed = time.time() - start_time
    
    # Print summary
    print(f"\nProcessed {len(media_files)} files in {elapsed:.2f} seconds")
    print(f"Average: {elapsed / len(media_files):.3f} seconds per file")
    print(f"Success rate: {success}/{len(media_files)} ({success/len(media_files)*100:.1f}%)")
    
    # Show language distribution
    print("\nLanguage distribution:")
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {count} files")
    
    # Cache stats
    cache_stats = await detector.get_cache_stats()
    print(f"\nCache entries: {cache_stats['total_entries']}")
    print(f"Cache size: {cache_stats['disk_usage_mb']:.2f} MB")

# Run the high-performance batch
asyncio.run(high_performance_batch())
```
