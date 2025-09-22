"""Language detection for audio and subtitle tracks."""

from __future__ import annotations
import re
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from langdetect import detect, DetectorFactory
from .shell import run, run_json, which
from .media_probe import MediaInfo, StreamInfo
from .errors import ProbeError

# Ensure deterministic results
DetectorFactory.seed = 0

@dataclass
class LanguageDetection:
    """Result of language detection for a track."""
    language: Optional[str]  # ISO 639-1 code (ja, en, etc.)
    confidence: float  # 0.0 to 1.0
    method: str  # How the language was detected
    details: str  # Additional information about detection


class LanguageDetector:
    """Detects languages for audio and subtitle tracks."""
    
    def __init__(self):
        self.confidence_threshold = 0.7
        self.filename_patterns = {
            'ja': [r'jp', r'jpn', r'jap', r'japanese', r'nihon'],
            'en': [r'en', r'eng', r'english', r'us', r'uk'],
            'zh': [r'ch', r'chi', r'chinese', r'mandarin', r'cn'],
            'ko': [r'ko', r'kor', r'korean', r'kr'],
        }
    
    def detect_subtitle_language(self, media: MediaInfo, stream: StreamInfo) -> LanguageDetection:
        """Detect language from subtitle content."""
        # First check if language is already properly tagged
        if stream.language and self._is_valid_language_code(stream.language):
            return LanguageDetection(
                language=self._normalize_language_code(stream.language),
                confidence=1.0,
                method="existing_metadata",
                details=f"Using existing language tag: {stream.language}"
            )
        
        # Try to extract subtitle text and detect language
        text_sample = self._extract_subtitle_sample(media, stream)
        if text_sample:
            try:
                detected_lang = detect(text_sample)
                # Calculate confidence based on text length and detection success
                confidence = min(0.9, len(text_sample) / 1000.0)  # More text = higher confidence
                return LanguageDetection(
                    language=detected_lang,
                    confidence=confidence,
                    method="text_analysis",
                    details=f"Analyzed {len(text_sample)} characters of subtitle text"
                )
            except Exception as e:
                # Language detection failed, try filename patterns
                pass
        
        # Fallback: check filename for language hints
        filename_lang = self._detect_from_filename(media.path, 'subtitle')
        if filename_lang:
            return LanguageDetection(
                language=filename_lang,
                confidence=0.6,
                method="filename_pattern",
                details=f"Detected from filename: {media.path.name}"
            )
        
        # No detection possible
        return LanguageDetection(
            language=None,
            confidence=0.0,
            method="no_detection",
            details="Unable to determine language"
        )
    
    def detect_audio_language(self, media: MediaInfo, stream: StreamInfo) -> LanguageDetection:
        """Detect language from audio track."""
        # First check if language is already properly tagged
        if stream.language and self._is_valid_language_code(stream.language):
            return LanguageDetection(
                language=self._normalize_language_code(stream.language),
                confidence=1.0,
                method="existing_metadata", 
                details=f"Using existing language tag: {stream.language}"
            )
        
        # For now, we'll rely on filename patterns and heuristics
        # In the future, this could be enhanced with speech recognition
        filename_lang = self._detect_from_filename(media.path, 'audio')
        if filename_lang:
            return LanguageDetection(
                language=filename_lang,
                confidence=0.6,
                method="filename_pattern",
                details=f"Detected from filename: {media.path.name}"
            )
        
        # Heuristic: if this is an anime/Japanese content, assume first audio is Japanese
        if self._looks_like_japanese_content(media.path):
            # Find the first audio track in the stream list
            audio_streams = [s for s in media.streams if s.codec_type == 'audio']
            if audio_streams and stream.index == audio_streams[0].index:
                return LanguageDetection(
                    language="ja",
                    confidence=0.5,
                    method="content_heuristic",
                    details="Assumed Japanese for first audio track in Japanese content"
                )
        
        return LanguageDetection(
            language=None,
            confidence=0.0,
            method="no_detection",
            details="Unable to determine language"
        )
    
    def detect_all_languages(self, media: MediaInfo) -> Dict[int, LanguageDetection]:
        """Detect languages for all audio and subtitle tracks."""
        results = {}
        
        for stream in media.streams:
            if stream.codec_type in ('audio', 'subtitle'):
                if stream.codec_type == 'audio':
                    detection = self.detect_audio_language(media, stream)
                else:
                    detection = self.detect_subtitle_language(media, stream)
                results[stream.index] = detection
        
        return results
    
    def _extract_subtitle_sample(self, media: MediaInfo, stream: StreamInfo) -> Optional[str]:
        """Extract a sample of subtitle text for language detection."""
        try:
            # Use ffmpeg to extract subtitle text
            which("ffmpeg")
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Extract first 2 minutes of subtitles
                run([
                    "ffmpeg", "-i", str(media.path),
                    "-map", f"0:{stream.index}",
                    "-t", "120",  # First 2 minutes
                    "-y", str(temp_path)
                ])
                
                if temp_path.exists() and temp_path.stat().st_size > 0:
                    content = temp_path.read_text(encoding='utf-8', errors='ignore')
                    # Extract just the text lines, skip timestamps and formatting
                    lines = []
                    for line in content.split('\n'):
                        line = line.strip()
                        # Skip empty lines, timestamps, and formatting
                        if line and not line.isdigit() and '-->' not in line:
                            # Clean HTML tags and formatting
                            clean_line = re.sub(r'<[^>]+>', '', line)
                            clean_line = re.sub(r'\{[^}]+\}', '', clean_line)
                            if clean_line.strip():
                                lines.append(clean_line.strip())
                    
                    return '\n'.join(lines[:20])  # First 20 lines
            finally:
                if temp_path.exists():
                    temp_path.unlink()
        
        except Exception as e:
            # Subtitle extraction failed, return None
            return None
        
        return None
    
    def _detect_from_filename(self, path: Path, track_type: str) -> Optional[str]:
        """Try to detect language from filename patterns."""
        filename = path.name.lower()
        
        # Score each language based on pattern matches
        scores = {}
        for lang, patterns in self.filename_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(rf'\b{pattern}\b', filename):
                    score += 2  # Word boundary match
                elif pattern in filename:
                    score += 1  # Partial match
            if score > 0:
                scores[lang] = score
        
        if scores:
            # Return language with highest score
            best_lang = max(scores.keys(), key=lambda x: scores[x])
            if scores[best_lang] >= 2:  # Only if we have at least one strong match
                return best_lang
        
        return None
    
    def _looks_like_japanese_content(self, path: Path) -> bool:
        """Heuristic to determine if this looks like Japanese content."""
        filename = path.name.lower()
        
        # Look for Japanese content indicators
        japanese_indicators = [
            'anime', 'jp', 'jpn', 'japanese', 'nihon',
            # Common anime/Japanese media patterns
            'episode', 'ep', 's01e', 's02e', 's03e',
            # File often contains Japanese characters or romanized names
        ]
        
        for indicator in japanese_indicators:
            if indicator in filename:
                return True
        
        # Check if filename contains what looks like romanized Japanese
        # This is a simple heuristic and could be improved
        if re.search(r'[a-z]+ no [a-z]+', filename):  # "X no Y" pattern common in Japanese
            return True
        
        return False
    
    def _is_valid_language_code(self, lang: Optional[str]) -> bool:
        """Check if language code looks valid."""
        if not lang:
            return False
        
        # Check common language codes and invalid values
        invalid_codes = {'und', 'unknown', 'null', ''}
        normalized = lang.lower().strip()
        
        if normalized in invalid_codes:
            return False
        
        # Valid if 2-3 letter code that's not obviously invalid
        return len(normalized) in (2, 3) and normalized.isalpha()
    
    def _normalize_language_code(self, lang: str) -> str:
        """Normalize language code to standard 2-letter ISO 639-1 format."""
        lang_map = {
            'jpn': 'ja', 'jap': 'ja', 'japanese': 'ja',
            'eng': 'en', 'english': 'en',
            'chi': 'zh', 'chinese': 'zh', 'zho': 'zh', 'cmn': 'zh',
            'kor': 'ko', 'korean': 'ko',
            'spa': 'es', 'spanish': 'es',
            'fra': 'fr', 'fre': 'fr', 'french': 'fr',
            'ger': 'de', 'deu': 'de', 'german': 'de',
        }
        
        normalized = lang.lower().strip()
        return lang_map.get(normalized, normalized)


def apply_language_tags(media_path: Path, language_detections: Dict[int, LanguageDetection], execute: bool = False, confidence_threshold: float = 0.5) -> List[str]:
    """Apply detected language tags to tracks using mkvpropedit."""
    which("mkvpropedit")
    
    commands = []
    changes_needed = []
    
    for track_index, detection in language_detections.items():
        if detection.language and detection.confidence >= confidence_threshold:  # Only apply if confident enough
            # mkvpropedit uses 1-based track numbers
            track_number = track_index + 1
            
            command = [
                "mkvpropedit", str(media_path),
                "--edit", f"track:{track_number}",
                "--set", f"language={detection.language}"
            ]
            
            commands.append(command)
            changes_needed.append(f"Track {track_number}: {detection.language} ({detection.method}, {detection.confidence:.2f} confidence)")
    
    if execute and commands:
        for i, command in enumerate(commands):
            try:
                run(command)
            except Exception as e:
                raise ProbeError(f"Failed to apply language tag for command {i+1}: {e}")
    
    return changes_needed