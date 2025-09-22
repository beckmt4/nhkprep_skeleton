# NHKPrep

A production-ready Python CLI to prepare Japanese TV/movies (NHK and similar) for English audiences.

## Features
- **Media Analysis**: Probe media with `ffprobe` and inventory streams (audio/subs, JA/EN focus)
- **Language Detection**: Automatically detect and fix missing/incorrect language tags using multiple methods:
  - Subtitle text content analysis
  - Filename pattern recognition  
  - Content heuristics for Japanese media
  - Confidence scoring and thresholds
- **Smart Cleaning**: Keep only JA/EN tracks, remux losslessly with `mkvmerge`/`mkvpropedit`
- **Default Management**: Set JA audio as default, manage subtitle defaults
- **Subtitle Processing**: Normalize subtitles to UTF-8 SRT with sanity checks
- **Quality Metrics**: Generate training pairs with BLEU/chrF/TER scoring via sacrebleu
- **Organized Output**: Files saved as `*.cleaned.mkv`, `*.en.srt`, `*.train.jsonl`, `*.diff.html`
- **Pluggable Backends**: ASR/MT/OCR stubs ready for your preferred implementations

## Installation & Setup

### VS Code Development
```bash
# Inside the repository
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Or bash/zsh
source .venv/bin/activate

pip install -e ".[dev]"
nhkprep --help
```

### System Requirements
- **Required**: `ffprobe` (from ffmpeg) on PATH
- **Recommended**: `mkvmerge`/`mkvpropedit` (from mkvtoolnix) for robust MKV handling
- **Python**: 3.11+

## Usage

### 1. Media Analysis
Scan media files to see stream information:
```bash
# Basic scan
nhkprep scan "video.mkv"

# JSON output for programmatic use
nhkprep scan "video.mkv" --json
```

### 2. Language Detection & Correction
Detect and fix language tags for audio/subtitle tracks:

```bash
# Show detection results (dry-run)
nhkprep detect-lang "video.mkv"

# Apply language corrections
nhkprep detect-lang "video.mkv" --execute

# Force detection even for already-tagged tracks
nhkprep detect-lang "video.mkv" --force --execute

# Adjust confidence threshold (0.0-1.0)
nhkprep detect-lang "video.mkv" --confidence 0.3 --execute

# JSON output
nhkprep detect-lang "video.mkv" --json
```

**Detection Methods:**
- **Text Analysis**: Extracts subtitle content and analyzes language using `langdetect`
- **Filename Patterns**: Recognizes patterns like `[EN]`, `japanese`, `jpn`, etc.
- **Content Heuristics**: Smart guessing for Japanese anime/media
- **Existing Metadata**: Validates and normalizes current language tags

### 3. Complete Media Processing
Full pipeline with optional language detection:

```bash
# Standard processing (dry-run)
nhkprep process "video.mkv"

# With language detection
nhkprep process "video.mkv" --detect-languages

# Execute the full pipeline
nhkprep process "video.mkv" --detect-languages --execute

# Advanced options
nhkprep process "video.mkv" \
    --detect-languages \
    --lang-confidence 0.4 \
    --prefer-ja-audio \
    --max-line-chars 32 \
    --max-lines 2 \
    --max-cps 15 \
    --execute
```

**Processing Steps:**
1. **Language Detection** (if `--detect-languages`): Fix missing/incorrect language tags
2. **Track Selection**: Keep only JA/EN audio and EN subtitles  
3. **Remuxing**: Lossless remux with `mkvmerge`, remove attachments
4. **Default Management**: Set appropriate default flags for audio/subtitles

### 4. Quality Assurance
```bash
# Lint code
ruff check .

# Type checking  
mypy src/nhkprep

# Run tests
pytest -q
```

## Examples

### Common Workflows

**Fix language tags on existing media:**
```bash
nhkprep detect-lang "My Anime S01E01.mkv" --execute
```

**Complete processing pipeline:**  
```bash
nhkprep process "My Anime S01E01.mkv" --detect-languages --execute
```

**Batch processing with different confidence:**
```bash
for file in *.mkv; do
    nhkprep process "$file" --detect-languages --lang-confidence 0.3 --execute
done
```

### Language Detection Examples

**Before:** Audio track has `language=und`, subtitle track missing language tag
```
- idx=1 type=audio lang=und forced=False default=True 
- idx=2 type=subtitle lang=None forced=False default=True
```

**Detection Results:**
```
Track 2 (audio): und → en (confidence: 0.60, method: filename_pattern)
Track 3 (subtitle): none → en (confidence: 0.28, method: text_analysis)
```

**After:** Proper language tags applied
```
- idx=1 type=audio lang=en forced=False default=True 
- idx=2 type=subtitle lang=en forced=False default=True
```

## Configuration

### Language Detection Settings
- **Confidence Threshold**: `--lang-confidence` (default: 0.5)
  - Lower values = more aggressive detection
  - Higher values = more conservative, only high-confidence matches
- **Force Detection**: `--force-lang-detect` 
  - Detect even for tracks that already have language tags
- **Filename Patterns**: Automatically detects common patterns:
  - `[EN]`, `[JP]`, `english`, `japanese`, `jpn`, `eng`, etc.

### Processing Options
- **`--prefer-ja-audio`**: Set Japanese audio as default (default: true)
- **`--max-line-chars`**: Maximum characters per subtitle line (default: 32)  
- **`--max-lines`**: Maximum lines per subtitle cue (default: 2)
- **`--max-cps`**: Maximum characters per second (default: 15)
- **`--in-place`**: Modify files in place instead of creating `.cleaned.mkv`

## Architecture

### Pluggable Backends
The system is designed with pluggable backends for future expansion:

- **ASR** (`asr.py`): Wire in Whisper, Azure Speech, etc.
- **Machine Translation** (`mt/`): Connect to your MT service
- **OCR** (`ocr/`): Integrate PaddleOCR or similar for image subtitles

### Language Detection Pipeline
1. **Metadata Check**: Validates existing language tags
2. **Content Analysis**: Extracts and analyzes subtitle text
3. **Pattern Recognition**: Scans filename for language indicators
4. **Heuristic Fallbacks**: Smart guessing based on content type
5. **Confidence Scoring**: Each detection gets a reliability score
6. **Application**: Uses `mkvpropedit` to apply language tags

## Output Files

- **`video.cleaned.mkv`**: Processed video with JA/EN tracks only
- **`video.en.srt`**: Extracted/processed English subtitles
- **`video.train.jsonl`**: Training pairs for quality metrics
- **`video.diff.html`**: Side-by-side comparison of subtitle changes

## Troubleshooting

### Common Issues

**"Tool not found" errors:**
```bash
# Install required tools
# Windows: choco install ffmpeg mkvtoolnix  
# macOS: brew install ffmpeg mkvtoolnix
# Linux: apt install ffmpeg mkvtoolnix
```

**Low confidence language detection:**
```bash
# Lower the confidence threshold
nhkprep detect-lang video.mkv --confidence 0.2 --execute
```

**Language detection not working:**
```bash
# Force detection and check details
nhkprep detect-lang video.mkv --force --json
```

## Development

### Adding Detection Methods
Extend `LanguageDetector` class in `language_detect.py`:
```python
def detect_audio_language(self, media: MediaInfo, stream: StreamInfo) -> LanguageDetection:
    # Add your detection logic here
    return LanguageDetection(language="ja", confidence=0.8, method="custom", details="...")
```

### Custom Processing Steps
Modify `remux_keep_ja_en_set_ja_default()` in `media_edit.py` to customize the processing pipeline.

---

**Note**: The `process` command runs a safe dry-run by default. Use `--execute` to actually modify files. Always test on copies of important media files first.
