from pathlib import Path

def transcribe_japanese_to_srt(audio_video_path: Path, out_srt: Path, device: str = "auto", model: str = "large-v3") -> None:
    # Placeholder stub: integrate Faster-Whisper here.
    out_srt.write_text("""1
00:00:00,000 --> 00:00:02,000
[ASR placeholder: JA transcript]
""")
