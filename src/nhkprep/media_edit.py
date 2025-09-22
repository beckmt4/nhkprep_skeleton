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
    keep_plan = media.ja_en_only_plan()
    keep = keep_plan["keep_indices"]
    if not keep:
        raise RemuxError("No streams selected to keep.")
    tmp_path, out_path = output_paths_for(media.path)
    if in_place:
        out_path = media.path.with_suffix(".inplace.tmp.mkv")
    # Build mkvmerge track selection; ensure only JA/EN audio/subs + all video are kept
    keep_ids_csv = ",".join(str(i) for i in keep)
    mkvmerge_cmd = [
        "mkvmerge",
        "-o", str(tmp_path),
        "--no-attachments",  # drop attached cover images, etc.
        "--tracks", f"0:{keep_ids_csv}",
        str(media.path),
    ]
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

        # 3) Clear/set default flags on audio tracks using mkvpropedit
        if chosen_id is not None:
            for t in audio_tracks:
                tid = t.get("id")
                is_default = 1 if tid == chosen_id else 0
                run([
                    "mkvpropedit",
                    str(tmp_path),
                    "--edit", f"track:@{tid}",
                    "--set", f"flag-default={is_default}",
                ])

        # 4) Atomic move to final destination (or in-place target)
        final_path = media.path if in_place else out_path
        Path(tmp_path).replace(final_path)
        return final_path
    else:
        # Dry run: return planned path only
        return out_path
