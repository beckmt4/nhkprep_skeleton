from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from pathlib import Path

class RuntimeConfig(BaseModel):
    max_line_chars: int = 32
    max_lines: int = 2
    max_cps: int = 15
    min_gap: float = 0.18
    prefer_ja_audio: bool = True
    execute: bool = False
    device: str = "auto"  # auto|cuda|cpu
    asr_model: str = "large-v3"
    mt_backend: str = "local"  # local|http
    mt_model_id: str = "nllb-200-3.3B"
    ocr_on: bool = False
    ocr_sample_rate: float = 3.0
    ocr_min_text_len: int = 3
    in_place: bool = False
    output_suffix: str = ".cleaned.mkv"

    output_dir_override: Optional[str] = None  # if None, same folder as source
    
    # Original Language Detection Settings
    orig_lang_enabled: bool = True
    orig_lang_tmdb_api_key: Optional[str] = None
    orig_lang_backend_priorities: List[str] = Field(default_factory=lambda: ["tmdb", "imdb"])
    orig_lang_confidence_threshold: float = 0.7
    orig_lang_max_backends: int = 2
    
    # Rate limiting settings
    orig_lang_tmdb_rate_limit: int = 40  # requests per 10 seconds
    orig_lang_tmdb_rate_window: int = 10  # seconds
    orig_lang_imdb_rate_limit: int = 10  # requests per 60 seconds
    orig_lang_imdb_rate_window: int = 60  # seconds
    
    # Caching settings
    orig_lang_cache_enabled: bool = True
    orig_lang_cache_dir: Optional[Path] = None  # if None, use default cache location
    orig_lang_cache_ttl: int = 86400  # 24 hours in seconds
    orig_lang_cache_max_size: int = 1000  # maximum cached entries
    
    # Search and matching settings
    orig_lang_search_max_results: int = 10
    orig_lang_year_tolerance: int = 1  # allow +/- 1 year difference
    orig_lang_title_similarity_threshold: float = 0.8
    
    # Timeout settings
    orig_lang_request_timeout: float = 30.0  # seconds
    orig_lang_total_timeout: float = 120.0  # seconds for all backends combined
