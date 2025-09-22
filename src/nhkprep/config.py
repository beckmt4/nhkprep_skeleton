from pydantic import BaseModel
from typing import Optional

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
