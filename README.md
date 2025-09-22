# NHKPrep

A production-ready Python CLI to prepare Japanese TV/movies (NHK and similar) for English audiences.

## Features (MVP)
- Probe media with `ffprobe` and inventory streams (audio/subs, JA/EN focus)
- Validate playability (ffprobe parse health)
- Clean/remux: keep only JA/EN tracks and mark JA audio as default (no re-encode)
- Normalize subtitles to UTF-8 SRT; sanity-check EN language id
- Generate training pairs when both reference EN and system EN exist (BLEU/chrF/TER via sacrebleu)
- Outputs saved next to source: `*.cleaned.mkv`, `*.en.srt`, `*.train.jsonl`, `*.diff.html`
- Pluggable ASR/MT/OCR (stubs wired; ASR/MT/ocr are optional until you configure them)

## Quickstart (VS Code)
```bash
# inside the repo
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
source .venv/bin/activate

pip install -e ".[dev]"
nhkprep --help
```

### Scan a file
```bash
nhkprep scan "/path/to/video.mkv" --json
```

### Process (dry-run by default, no remux until --execute)
```bash
nhkprep process "/path/to/video.mkv" --prefer-ja-audio --max-line-chars 32 --max-lines 2 --max-cps 15
# add --execute to actually remux and write files
```

### Lint & test
```bash
ruff check .
mypy src/nhkprep
pytest -q
```

## Requirements
- `ffprobe` (from ffmpeg) on PATH. Optional: `mkvmerge`/`mkvpropedit` for robust MKV handling.
- Python 3.11+

## Notes
- Actual ASR/MT/OCR are pluggable; defaults are stubs. Wire in your preferred backends in `asr.py`, `mt/local.py`, and `ocr/paddleocr_impl.py`.
- The `process` command runs a safe dry-run, prints the plan, and only writes when `--execute` is set.
