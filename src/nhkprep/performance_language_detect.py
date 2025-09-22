"""Performance-optimized language detection with caching and parallel processing."""

from __future__ import annotations
import asyncio
import hashlib
import concurrent.futures
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import tempfile

try:
    import diskcache as dc
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    dc = None

from .enhanced_language_detect import (
    EnhancedLanguageDetector, 
    LanguageDetection,
    WHISPER_AVAILABLE,
    GOOGLETRANS_AVAILABLE
)
from .media_probe import MediaInfo, StreamInfo


@dataclass
class PerformanceMetrics:
    """Performance metrics for language detection operations."""
    total_time_ms: float
    cache_hits: int
    cache_misses: int
    parallel_workers: int
    detection_method_counts: Dict[str, int]
    whisper_model_load_time_ms: float
    audio_extraction_time_ms: float
    text_analysis_time_ms: float
    cloud_api_calls: int
    error_count: int


class PerformanceOptimizedDetector(EnhancedLanguageDetector):
    """Production-ready language detector with caching, parallel processing, and performance metrics."""
    
    def __init__(self, cache_dir: Optional[Path] = None, enable_parallel: bool = True, 
                 max_workers: int = 4, cache_ttl: int = 7 * 24 * 3600):  # 7 days default TTL
        super().__init__()
        
        # Performance optimization settings
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.cache_ttl = cache_ttl  # Cache time-to-live in seconds
        
        # Initialize cache
        self.cache = None
        if CACHE_AVAILABLE and cache_dir:
            self.cache = dc.Cache(str(cache_dir))
        elif CACHE_AVAILABLE:
            # Use temporary directory for cache
            cache_path = Path(tempfile.gettempdir()) / "nhkprep_lang_cache"
            cache_path.mkdir(exist_ok=True)
            self.cache = dc.Cache(str(cache_path))
        
        # Performance metrics
        self.metrics = PerformanceMetrics(
            total_time_ms=0.0,
            cache_hits=0,
            cache_misses=0,
            parallel_workers=0,
            detection_method_counts={},
            whisper_model_load_time_ms=0.0,
            audio_extraction_time_ms=0.0,
            text_analysis_time_ms=0.0,
            cloud_api_calls=0,
            error_count=0
        )
        
        # Cache keys for different operations
        self._cache_prefix = "nhkprep_v2"
    
    def detect_all_languages_optimized(self, media: MediaInfo, force_detection: bool = False) -> Dict[int, LanguageDetection]:
        """Optimized language detection with caching and optional parallel processing."""
        start_time = time.time()
        self.metrics = PerformanceMetrics(  # Reset metrics
            total_time_ms=0.0,
            cache_hits=0,
            cache_misses=0,
            parallel_workers=0,
            detection_method_counts={},
            whisper_model_load_time_ms=0.0,
            audio_extraction_time_ms=0.0,
            text_analysis_time_ms=0.0,
            cloud_api_calls=0,
            error_count=0
        )
        
        # Get relevant streams
        streams_to_detect = [s for s in media.streams if s.codec_type in ('audio', 'subtitle')]
        
        if not streams_to_detect:
            self.metrics.total_time_ms = (time.time() - start_time) * 1000
            return {}
        
        # Check cache first if available
        cached_results = {}
        streams_needing_detection = []
        
        for stream in streams_to_detect:
            cache_key = self._generate_cache_key(media, stream, force_detection)
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                cached_results[stream.index] = cached_result
                self.metrics.cache_hits += 1
            else:
                streams_needing_detection.append(stream)
                self.metrics.cache_misses += 1
        
        # Process streams that need detection
        new_results = {}
        if streams_needing_detection:
            if self.enable_parallel and len(streams_needing_detection) > 1:
                new_results = self._detect_streams_parallel(media, streams_needing_detection, force_detection)
                self.metrics.parallel_workers = min(self.max_workers, len(streams_needing_detection))
            else:
                new_results = self._detect_streams_sequential(media, streams_needing_detection, force_detection)
                self.metrics.parallel_workers = 1
            
            # Cache new results
            for stream_index, detection in new_results.items():
                stream = next(s for s in streams_needing_detection if s.index == stream_index)
                cache_key = self._generate_cache_key(media, stream, force_detection)
                self._cache_result(cache_key, detection)
        
        # Combine cached and new results
        all_results = {**cached_results, **new_results}
        
        # Update metrics
        self.metrics.total_time_ms = (time.time() - start_time) * 1000
        return all_results
    
    def _detect_streams_parallel(self, media: MediaInfo, streams: List[StreamInfo], 
                               force_detection: bool) -> Dict[int, LanguageDetection]:
        """Detect languages for multiple streams in parallel."""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit detection tasks
            future_to_stream = {}
            for stream in streams:
                future = executor.submit(self._detect_single_stream_safe, media, stream, force_detection)
                future_to_stream[future] = stream
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_stream):
                stream = future_to_stream[future]
                try:
                    detection = future.result()
                    if detection:
                        results[stream.index] = detection
                        self._update_method_count(detection.method)
                except Exception as e:
                    self.metrics.error_count += 1
                    # Create error detection result
                    results[stream.index] = LanguageDetection(
                        language=None,
                        confidence=0.0,
                        method="error",
                        details=f"Detection failed: {str(e)}",
                        alternative_languages=[],
                        detection_time_ms=0.0
                    )
        
        return results
    
    def _detect_streams_sequential(self, media: MediaInfo, streams: List[StreamInfo], 
                                 force_detection: bool) -> Dict[int, LanguageDetection]:
        """Detect languages for streams sequentially."""
        results = {}
        
        for stream in streams:
            try:
                detection = self._detect_single_stream_safe(media, stream, force_detection)
                if detection:
                    results[stream.index] = detection
                    self._update_method_count(detection.method)
            except Exception as e:
                self.metrics.error_count += 1
                results[stream.index] = LanguageDetection(
                    language=None,
                    confidence=0.0,
                    method="error",
                    details=f"Detection failed: {str(e)}",
                    alternative_languages=[],
                    detection_time_ms=0.0
                )
        
        return results
    
    def _detect_single_stream_safe(self, media: MediaInfo, stream: StreamInfo, 
                                 force_detection: bool) -> Optional[LanguageDetection]:
        """Safely detect language for a single stream with error handling."""
        try:
            if stream.codec_type == 'audio':
                return self.detect_audio_language(media, stream, force_detection)
            else:
                return self.detect_subtitle_language(media, stream, force_detection)
        except Exception:
            return None
    
    def _generate_cache_key(self, media: MediaInfo, stream: StreamInfo, force_detection: bool) -> str:
        """Generate a unique cache key for a media stream."""
        # Create hash from media file path, size, and stream properties
        key_data = f"{media.path}_{media.path.stat().st_size}_{media.path.stat().st_mtime}"
        key_data += f"_{stream.index}_{stream.codec_type}_{stream.language}_{force_detection}"
        key_data += f"_{self.whisper_model_size}_{self.confidence_threshold}"
        
        # Hash the key data to create a manageable cache key
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{self._cache_prefix}_{key_hash}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[LanguageDetection]:
        """Retrieve a cached detection result."""
        if not self.cache:
            return None
        
        try:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                # Reconstruct LanguageDetection from cached data
                return LanguageDetection(**cached_data)
        except Exception:
            pass
        
        return None
    
    def _cache_result(self, cache_key: str, detection: LanguageDetection) -> None:
        """Cache a detection result."""
        if not self.cache:
            return
        
        try:
            # Convert to dict for caching
            cache_data = asdict(detection)
            self.cache.set(cache_key, cache_data, expire=self.cache_ttl)
        except Exception:
            pass
    
    def _update_method_count(self, method: str) -> None:
        """Update the count of detection methods used."""
        if method not in self.metrics.detection_method_counts:
            self.metrics.detection_method_counts[method] = 0
        self.metrics.detection_method_counts[method] += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        total_detections = sum(self.metrics.detection_method_counts.values())
        cache_hit_rate = (
            self.metrics.cache_hits / (self.metrics.cache_hits + self.metrics.cache_misses)
            if (self.metrics.cache_hits + self.metrics.cache_misses) > 0 else 0.0
        )
        
        report = {
            "performance_summary": {
                "total_time_ms": round(self.metrics.total_time_ms, 2),
                "total_detections": total_detections,
                "average_time_per_detection_ms": (
                    round(self.metrics.total_time_ms / total_detections, 2)
                    if total_detections > 0 else 0.0
                ),
                "parallel_processing": {
                    "enabled": self.enable_parallel,
                    "workers_used": self.metrics.parallel_workers,
                    "max_workers": self.max_workers
                }
            },
            "cache_performance": {
                "enabled": self.cache is not None,
                "hits": self.metrics.cache_hits,
                "misses": self.metrics.cache_misses,
                "hit_rate_percent": round(cache_hit_rate * 100, 1),
                "ttl_hours": self.cache_ttl / 3600
            },
            "detection_methods": {
                "method_usage": self.metrics.detection_method_counts,
                "most_used_method": (
                    max(self.metrics.detection_method_counts.items(), key=lambda x: x[1])[0]
                    if self.metrics.detection_method_counts else "none"
                )
            },
            "component_performance": {
                "whisper_model_load_ms": round(self.metrics.whisper_model_load_time_ms, 2),
                "audio_extraction_ms": round(self.metrics.audio_extraction_time_ms, 2), 
                "text_analysis_ms": round(self.metrics.text_analysis_time_ms, 2),
                "cloud_api_calls": self.metrics.cloud_api_calls
            },
            "reliability": {
                "error_count": self.metrics.error_count,
                "success_rate_percent": round(
                    ((total_detections - self.metrics.error_count) / total_detections * 100)
                    if total_detections > 0 else 0.0, 1
                )
            },
            "system_capabilities": {
                "whisper_available": WHISPER_AVAILABLE,
                "google_translate_available": GOOGLETRANS_AVAILABLE,
                "cache_available": CACHE_AVAILABLE,
                "parallel_processing_available": True
            }
        }
        
        return report
    
    def clear_cache(self) -> int:
        """Clear the detection cache and return number of cleared entries."""
        if not self.cache:
            return 0
        
        try:
            # Count entries with our prefix
            count = len([key for key in self.cache if key.startswith(self._cache_prefix)])
            
            # Clear entries with our prefix
            keys_to_delete = [key for key in self.cache if key.startswith(self._cache_prefix)]
            for key in keys_to_delete:
                del self.cache[key]
            
            return count
        except Exception:
            return 0
    
    def benchmark_detection_methods(self, media: MediaInfo, iterations: int = 3) -> Dict[str, Any]:
        """Benchmark different detection methods on a media file."""
        streams_to_test = [s for s in media.streams if s.codec_type in ('audio', 'subtitle')]
        
        if not streams_to_test:
            return {"error": "No audio or subtitle streams found for benchmarking"}
        
        results = {
            "media_file": str(media.path),
            "stream_count": len(streams_to_test),
            "iterations": iterations,
            "benchmarks": {}
        }
        
        # Test different configurations
        configs = [
            ("sequential_no_cache", {"enable_parallel": False, "use_cache": False}),
            ("sequential_with_cache", {"enable_parallel": False, "use_cache": True}),
            ("parallel_no_cache", {"enable_parallel": True, "use_cache": False}),
            ("parallel_with_cache", {"enable_parallel": True, "use_cache": True}),
        ]
        
        for config_name, config in configs:
            times = []
            
            for i in range(iterations):
                # Clear cache if not using it
                if not config["use_cache"]:
                    self.clear_cache()
                
                # Configure detector
                original_parallel = self.enable_parallel
                self.enable_parallel = config["enable_parallel"]
                
                # Run detection
                start_time = time.time()
                detections = self.detect_all_languages_optimized(media, force_detection=True)
                end_time = time.time()
                
                times.append((end_time - start_time) * 1000)  # Convert to milliseconds
                
                # Restore original setting
                self.enable_parallel = original_parallel
            
            results["benchmarks"][config_name] = {
                "average_time_ms": round(sum(times) / len(times), 2),
                "min_time_ms": round(min(times), 2),
                "max_time_ms": round(max(times), 2),
                "times_ms": [round(t, 2) for t in times]
            }
        
        return results


def apply_language_tags_optimized(media_path: Path, language_detections: Dict[int, LanguageDetection], 
                                execute: bool = False, confidence_threshold: float = 0.5) -> List[str]:
    """Optimized version of apply_language_tags with batch processing."""
    from .shell import run, which
    from .errors import ProbeError
    
    which("mkvpropedit")
    
    # Group changes by track to minimize mkvpropedit calls
    changes_needed = []
    batch_commands = []
    
    for track_index, detection in language_detections.items():
        if detection.language and detection.confidence >= confidence_threshold:
            track_number = track_index + 1
            batch_commands.extend([
                "--edit", f"track:{track_number}",
                "--set", f"language={detection.language}"
            ])
            
            changes_needed.append(
                f"Track {track_number}: {detection.language} "
                f"({detection.method}, {detection.confidence:.3f} confidence)"
            )
    
    # Execute all changes in a single mkvpropedit call for better performance
    if execute and batch_commands:
        try:
            command = ["mkvpropedit", str(media_path)] + batch_commands
            run(command)
        except Exception as e:
            raise ProbeError(f"Failed to apply language tags in batch: {e}")
    
    return changes_needed