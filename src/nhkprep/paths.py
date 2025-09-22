from pathlib import Path
from typing import Tuple

def output_paths_for(video_path: Path, suffix: str = ".cleaned.mkv") -> Tuple[Path, Path]:
    parent = video_path.parent
    base = video_path.stem
    out_mkv = parent / f"{base}{suffix}"
    # Important: ensure the temp path still ends with .mkv so ffmpeg infers the format
    # Example: .<base>.tmp.cleaned.mkv
    tmp_mkv = parent / f".{base}.tmp{suffix}"
    return tmp_mkv, out_mkv
