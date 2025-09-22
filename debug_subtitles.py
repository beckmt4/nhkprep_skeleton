#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

def norm_lang(val):
    if not val:
        return None
    v = val.lower()
    return {"ja": "ja", "jpn": "ja", "en": "en", "eng": "en"}.get(v, v)

# Test the logic
file_path = r"C:\Users\Tom Beck\Videos\Test Files\Kiki's Delivery Service (1989) {imdb-tt0097814} [Bluray-1080p Proper][EAC3 2.0][x265].cleaned.mkv"

result = subprocess.run(["mkvmerge", "-J", file_path], capture_output=True, text=True)
info = json.loads(result.stdout)
tracks = info.get("tracks", [])

subtitle_tracks = [t for t in tracks if t.get("type") in ("subtitles", "subtitle")]
print(f"Found {len(subtitle_tracks)} subtitle tracks:")

for i, t in enumerate(subtitle_tracks):
    track_id = t.get("id")
    props = t.get("properties", {})
    lang = props.get("language")
    normalized = norm_lang(lang)
    default = props.get("default_track")
    print(f"  Track {i+1}: ID={track_id}, Lang='{lang}' -> '{normalized}', Default={default}")

print("\nLooking for English track:")
sub_chosen_id = None
for t in subtitle_tracks:
    props = t.get("properties", {})
    lang = props.get("language")
    normalized = norm_lang(lang)
    print(f"  Checking track {t.get('id')}: '{lang}' -> '{normalized}' == 'en'? {normalized == 'en'}")
    if normalized == "en":
        sub_chosen_id = t.get("id")
        print(f"    ✓ Found English subtitle track: ID {sub_chosen_id}")
        break

if sub_chosen_id is None:
    print("  ✗ No English track found")
    if subtitle_tracks:
        sub_chosen_id = subtitle_tracks[0].get("id")
        print(f"  Using first track: ID {sub_chosen_id}")