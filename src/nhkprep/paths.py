from pathlib import Path
from typing import Tuple

def output_paths_for(video_path: Path, suffix: str = ".cleaned.mkv") -> Tuple[Path, Path]:
    parent = video_path.parent
    base = video_path.stem
    out_mkv = parent / f"{base}{suffix}"
    tmp_mkv = parent / f".{base}{suffix}.tmp"
    return tmp_mkv, out_mkv
