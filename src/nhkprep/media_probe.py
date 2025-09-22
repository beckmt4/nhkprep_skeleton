from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel
from pathlib import Path
from .shell import run_json, which
from .errors import ProbeError

LANG_ALIASES = {
    "ja": "ja", "jpn": "ja",
    "en": "en", "eng": "en",
}

class StreamInfo(BaseModel):
    index: int
    codec_type: Literal["audio","subtitle","video","data","attachment"]
    codec_name: Optional[str] = None
    language: Optional[str] = None
    forced: bool = False
    default: bool = False
    title: Optional[str] = None
    tags: dict = {}

class MediaInfo(BaseModel):
    path: Path
    duration: Optional[float] = None
    streams: List[StreamInfo] = []

    def ja_en_only_plan(self) -> dict:
        keep = []
        for s in self.streams:
            if s.codec_type not in {"audio","subtitle","video"}:
                continue
            if s.codec_type == "video":
                keep.append(s.index); continue
            lang = (s.language or "").lower()
            if LANG_ALIASES.get(lang) in {"ja","en"}:
                keep.append(s.index)
        return {"keep_indices": keep}

def _normalize_lang(s: dict) -> Optional[str]:
    lang = (s.get("tags") or {}).get("language") or s.get("tags", {}).get("LANGUAGE")
    if lang:
        lang = lang.lower()
        return LANG_ALIASES.get(lang, lang)
    return None

def ffprobe(path: Path) -> MediaInfo:
    which("ffprobe")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]
    data = run_json(cmd)
    if not data.get("streams"):
        raise ProbeError("No streams found in file (unplayable or corrupt?)")
    streams: List[StreamInfo] = []
    for s in data["streams"]:
        disposition = s.get("disposition") or {}
        tags = s.get("tags") or {}
        streams.append(StreamInfo(
            index=s.get("index", -1),
            codec_type=s.get("codec_type", "data"),
            codec_name=s.get("codec_name"),
            language=_normalize_lang(s) or tags.get("language"),
            forced=bool(disposition.get("forced", 0)),
            default=bool(disposition.get("default", 0)),
            title=tags.get("title"),
            tags=tags
        ))
    duration = None
    try:
        duration = float((data.get("format") or {}).get("duration"))
    except Exception:
        pass
    return MediaInfo(path=path, duration=duration, streams=streams)
