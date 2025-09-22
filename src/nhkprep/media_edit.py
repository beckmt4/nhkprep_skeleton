from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from .shell import which, run
from .shell import run_json
from .paths import output_paths_for
from .media_probe import MediaInfo
from .errors import RemuxError

def remux_keep_ja_en_set_ja_default(media: MediaInfo, execute: bool, in_place: bool) -> Path:
    # Use mkvmerge for remuxing and mkvpropedit for flags
    which("mkvmerge")
    which("mkvpropedit")
    # Determine tracks to keep using mkvmerge introspection (avoids cross-tool index mismatches)
    src_info = run_json(["mkvmerge", "-J", str(media.path)])
    src_tracks = src_info.get("tracks", [])

    def _norm_lang(val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        v = val.lower()
        return {"ja": "ja", "jpn": "ja", "en": "en", "eng": "en"}.get(v, v)

    keep_ids: List[int] = []
    subtitle_ids_all: List[int] = []
    subtitle_ids_kept: List[int] = []
    for t in src_tracks:
        t_type = t.get("type") or ""
        tid = t.get("id")
        if not isinstance(tid, int):
            continue
        if t_type == "video":
            keep_ids.append(tid)
        elif t_type == "audio":
            # Keep all audio tracks (language tags are often missing or unreliable)
            keep_ids.append(tid)
        elif t_type in {"subtitles", "subtitle"}:
            lang = _norm_lang((t.get("properties") or {}).get("language"))
            subtitle_ids_all.append(tid)
            if lang in {"ja", "en"}:
                keep_ids.append(tid)
                subtitle_ids_kept.append(tid)
        # ignore other types (e.g., buttons, etc.)
    # If we didn’t keep any subtitles due to missing language tags, keep the first subtitle track as a fallback
    if not subtitle_ids_kept and subtitle_ids_all:
        keep_ids.append(subtitle_ids_all[0])

    if not keep_ids:
        raise RemuxError("No tracks selected to keep (after mkvmerge inspection).")
    tmp_path, out_path = output_paths_for(media.path)
    if in_place:
        out_path = media.path.with_suffix(".inplace.tmp.mkv")
    # Build mkvmerge track selection; ensure only JA/EN audio/subs + all video are kept
    # Separate video, audio, and subtitle IDs for mkvmerge
    video_ids = [str(s.index) for s in media.streams if s.codec_type == 'video' and s.index in keep_ids]
    audio_ids = [str(s.index) for s in media.streams if s.codec_type == 'audio' and s.index in keep_ids]  
    subtitle_ids = [str(s.index) for s in media.streams if s.codec_type == 'subtitle' and s.index in keep_ids]

    mkvmerge_cmd = [
        "mkvmerge",
        "-o", str(tmp_path),
        "--no-attachments",  # drop attached cover images, etc.
    ]
    
    # Add track selection options
    if video_ids:
        mkvmerge_cmd.extend(["-d", ",".join(video_ids)])
    else:
        mkvmerge_cmd.append("-D")  # no video tracks
        
    if audio_ids:
        mkvmerge_cmd.extend(["-a", ",".join(audio_ids)])
    else:
        mkvmerge_cmd.append("-A")  # no audio tracks
        
    if subtitle_ids:
        mkvmerge_cmd.extend(["-s", ",".join(subtitle_ids)])
    else:
        mkvmerge_cmd.append("-S")  # no subtitle tracks
        
    mkvmerge_cmd.append(str(media.path))
    if execute:
        # 1) Remux to temp with selected tracks only
        run(mkvmerge_cmd)

        # 2) Determine audio tracks in the temp file and select default = first JA audio if present else first audio
        info = run_json(["mkvmerge", "-J", str(tmp_path)])
        tracks = info.get("tracks", [])
        audio_tracks = [t for t in tracks if t.get("type") == "audio"]

        def norm_lang(val: Optional[str]) -> Optional[str]:
            if not val:
                return None
            v = val.lower()
            return {"ja": "ja", "jpn": "ja", "en": "en", "eng": "en"}.get(v, v)

        # Pick preferred audio track ID
        chosen_id: Optional[int] = None
        for t in audio_tracks:
            lang = norm_lang((t.get("properties") or {}).get("language"))
            if lang == "ja":
                chosen_id = t.get("id")
                break
        if chosen_id is None and audio_tracks:
            chosen_id = audio_tracks[0].get("id")

        # 3) Set default flag on chosen audio only (do not clear others)
        if chosen_id is not None:
            run([
                "mkvpropedit",
                str(tmp_path),
                "--edit", f"track:@{chosen_id}",
                "--set", "flag-default=1",
            ])

        # 3b) Set default subtitle: prefer EN if present, else first subtitle; do not clear others
        subtitle_tracks = [t for t in tracks if t.get("type") in ("subtitles", "subtitle")]
        sub_chosen_id: Optional[int] = None
        for t in subtitle_tracks:
            if norm_lang((t.get("properties") or {}).get("language")) == "en":
                sub_chosen_id = t.get("id")
                break
        if sub_chosen_id is None and subtitle_tracks:
            sub_chosen_id = subtitle_tracks[0].get("id")
        if sub_chosen_id is not None:
            run([
                "mkvpropedit",
                str(tmp_path),
                "--edit", f"track:@{sub_chosen_id}",
                "--set", "flag-default=1",
            ])

        # 4) Atomic move to final destination (or in-place target)
        final_path = media.path if in_place else out_path
        Path(tmp_path).replace(final_path)
        return final_path
    else:
        # Dry run: return planned path only
        return out_path
