from __future__ import annotations
from pathlib import Path
from typing import List
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # deterministic

def is_english_text(lines: List[str], threshold: float = 0.9) -> bool:
    samples = [ln for ln in lines if ln.strip()][:50]
    if not samples:
        return False
    en = 0
    total = 0
    for s in samples:
        try:
            lang = detect(s)
            total += 1
            if lang == "en":
                en += 1
        except Exception:
            continue
    if total == 0:
        return False
    return (en / total) >= threshold

def normalize_to_srt(src_path: Path, dst_path: Path) -> None:
    # Placeholder: in a full implementation, convert VTT/ASS/PGS to SRT.
    # Here we just copy if already SRT.
    if src_path.suffix.lower() == ".srt":
        dst_path.write_bytes(src_path.read_bytes())
    else:
        # TODO: implement real converters
        dst_path.write_text("""1
00:00:00,000 --> 00:00:02,000
[placeholder conversion]
""")
