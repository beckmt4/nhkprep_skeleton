"""Enhanced production-ready language detection system."""

from __future__ import annotations
import re
import tempfile
import statistics
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import Counter

import langcodes
from langdetect import detect, detect_langs, DetectorFactory, LangDetectException
from .shell import run, run_json, which
from .media_probe import MediaInfo, StreamInfo
from .errors import ProbeError

# Optional Whisper import - will gracefully degrade if not available
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

# Optional Google Translate import - will gracefully degrade if not available
try:
    from googletrans import Translator, LANGUAGES
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False
    Translator = None
    LANGUAGES = None

# Ensure deterministic results
DetectorFactory.seed = 0

@dataclass
class LanguageDetection:
    """Enhanced result of language detection for a track."""
    language: Optional[str]  # ISO 639-1 code (ja, en, etc.)
    confidence: float  # 0.0 to 1.0
    method: str  # How the language was detected
    details: str  # Additional information about detection
    alternative_languages: Optional[List[Tuple[str, float]]] = None  # Alternative detections with confidence
    text_sample_size: int = 0  # Size of analyzed text sample
    detection_time_ms: float = 0.0  # Time taken for detection


class EnhancedLanguageDetector:
    """Production-ready language detector with multiple methods and robust confidence scoring."""
    
    def __init__(self):
        self.confidence_threshold = 0.5
        self.min_text_length = 50  # Minimum text length for reliable detection
        self.max_text_sample = 2000  # Maximum characters to analyze
        self.whisper_model = None  # Lazy-load Whisper model
        self.whisper_model_size = "base"  # Default model size (base is good balance of speed/accuracy)
        self.whisper_sample_duration = 180  # Seconds of audio to analyze (3 minutes)
        self.google_translator = None  # Lazy-load Google Translator
        self.cloud_api_enabled = True  # Enable cloud API fallback
        
        # Enhanced filename patterns with more comprehensive coverage
        self.filename_patterns = {
            'ja': [r'jp', r'jpn', r'jap', r'japanese', r'nihon', r'日本', r'anime'],
            'en': [r'en', r'eng', r'english', r'us', r'uk', r'american', r'british'],
            'zh': [r'ch', r'chi', r'chinese', r'mandarin', r'cn', r'taiwan', r'中文'],
            'ko': [r'ko', r'kor', r'korean', r'kr', r'hangul', r'한국'],
            'es': [r'es', r'spa', r'spanish', r'espanol', r'castellano'],
            'fr': [r'fr', r'fra', r'fre', r'french', r'francais'],
            'de': [r'de', r'ger', r'deu', r'german', r'deutsch'],
            'it': [r'it', r'ita', r'italian', r'italiano'],
            'pt': [r'pt', r'por', r'portuguese', r'portugues', r'brasil'],
            'ru': [r'ru', r'rus', r'russian', r'русский'],
            'ar': [r'ar', r'ara', r'arabic', r'عربي'],
            'hi': [r'hi', r'hin', r'hindi', r'हिंदी'],
            'th': [r'th', r'tha', r'thai', r'ไทย'],
        }
        
        # Common invalid language codes
        self.invalid_codes = {
            'und', 'unknown', 'null', '', 'none', 'n/a', 'undefined',
            'misc', 'other', 'multi', 'mixed', 'default'
        }
        
        # Language code mappings for normalization
        self.language_mappings = {
            # 3-letter to 2-letter ISO codes
            'jpn': 'ja', 'jap': 'ja',
            'eng': 'en',
            'chi': 'zh', 'zho': 'zh', 'cmn': 'zh',
            'kor': 'ko',
            'spa': 'es',
            'fra': 'fr', 'fre': 'fr',
            'ger': 'de', 'deu': 'de',
            'ita': 'it',
            'por': 'pt',
            'rus': 'ru',
            'ara': 'ar',
            'hin': 'hi',
            'tha': 'th',
        }
    
    def detect_subtitle_language(self, media: MediaInfo, stream: StreamInfo, force_detection: bool = False) -> LanguageDetection:
        """Enhanced subtitle language detection with multiple methods and confidence scoring."""
        import time
        start_time = time.time()
        
        # Method 1: Check existing metadata (skip if forcing detection)
        if not force_detection and stream.language and self._is_valid_language_code(stream.language):
            normalized = self._normalize_language_code(stream.language)
            return LanguageDetection(
                language=normalized,
                confidence=1.0,
                method="existing_metadata",
                details=f"Using existing language tag: {stream.language} → {normalized}",
                alternative_languages=[],
                text_sample_size=0,
                detection_time_ms=(time.time() - start_time) * 1000
            )
        
        # Method 2: Enhanced text analysis
        text_sample = self._extract_subtitle_sample(media, stream)
        if text_sample and len(text_sample.strip()) >= self.min_text_length:
            text_detection = self._detect_language_from_text(text_sample)
            if text_detection:
                text_detection.text_sample_size = len(text_sample)
                text_detection.detection_time_ms = (time.time() - start_time) * 1000
                if text_detection.confidence >= 0.3:  # Lower threshold for text analysis
                    return text_detection
        
        # Method 3: Enhanced filename pattern detection
        filename_detection = self._detect_from_filename_enhanced(media.path, 'subtitle')
        if filename_detection and filename_detection.confidence >= 0.5:
            filename_detection.detection_time_ms = (time.time() - start_time) * 1000
            return filename_detection
        
        # Method 4: Content heuristics
        heuristic_detection = self._detect_from_content_heuristics(media.path, stream, 'subtitle')
        if heuristic_detection:
            heuristic_detection.detection_time_ms = (time.time() - start_time) * 1000
            return heuristic_detection
        
        # Method 5: Cloud API fallback (Google Translate) for difficult cases
        if (GOOGLETRANS_AVAILABLE and self.cloud_api_enabled and 
            text_sample and len(text_sample.strip()) >= self.min_text_length):
            cloud_detection = self._detect_language_from_text_cloud(text_sample)
            if cloud_detection and cloud_detection.confidence >= 0.3:
                cloud_detection.text_sample_size = len(text_sample)
                cloud_detection.detection_time_ms = (time.time() - start_time) * 1000
                return cloud_detection
        
        # No reliable detection found
        return LanguageDetection(
            language=None,
            confidence=0.0,
            method="no_detection",
            details="Unable to determine language using any method",
            alternative_languages=[],
            text_sample_size=len(text_sample) if text_sample else 0,
            detection_time_ms=(time.time() - start_time) * 1000
        )
    
    def detect_audio_language(self, media: MediaInfo, stream: StreamInfo, force_detection: bool = False) -> LanguageDetection:
        """Enhanced audio language detection."""
        import time
        start_time = time.time()
        
        # Method 1: Check existing metadata (skip if forcing detection)
        if not force_detection and stream.language and self._is_valid_language_code(stream.language):
            normalized = self._normalize_language_code(stream.language)
            return LanguageDetection(
                language=normalized,
                confidence=1.0,
                method="existing_metadata",
                details=f"Using existing language tag: {stream.language} → {normalized}",
                alternative_languages=[],
                detection_time_ms=(time.time() - start_time) * 1000
            )
        
        # Method 2: Enhanced filename pattern detection
        filename_detection = self._detect_from_filename_enhanced(media.path, 'audio')
        if filename_detection and filename_detection.confidence >= 0.6:
            filename_detection.detection_time_ms = (time.time() - start_time) * 1000
            return filename_detection
        
        # Method 2.5: Audio content analysis with Whisper (if available)
        if WHISPER_AVAILABLE:
            whisper_detection = self._detect_language_from_audio_whisper(media, stream)
            if whisper_detection and whisper_detection.confidence >= 0.4:
                whisper_detection.detection_time_ms = (time.time() - start_time) * 1000
                return whisper_detection
        
        # Method 3: Enhanced content heuristics
        heuristic_detection = self._detect_from_content_heuristics(media.path, stream, 'audio')
        if heuristic_detection:
            heuristic_detection.detection_time_ms = (time.time() - start_time) * 1000
            return heuristic_detection
        
        # TODO: Future enhancement - audio analysis with Whisper
        # This would analyze actual speech content for language detection
        
        return LanguageDetection(
            language=None,
            confidence=0.0,
            method="no_detection", 
            details="Unable to determine audio language",
            alternative_languages=[],
            detection_time_ms=(time.time() - start_time) * 1000
        )
    
    def _detect_language_from_text(self, text: str) -> Optional[LanguageDetection]:
        """Enhanced text language detection with multiple confidence methods."""
        if len(text.strip()) < self.min_text_length:
            return None
        
        # Clean and preprocess text
        cleaned_text = self._preprocess_text_for_detection(text)
        if len(cleaned_text.strip()) < self.min_text_length:
            return None
        
        try:
            # Get multiple language predictions with probabilities
            lang_probs = detect_langs(cleaned_text)
            
            if not lang_probs:
                return None
            
            # Primary detection
            primary_lang = lang_probs[0]
            primary_code = self._normalize_language_code(primary_lang.lang)
            
            # Calculate enhanced confidence based on multiple factors
            confidence = self._calculate_text_confidence(
                cleaned_text, primary_lang.prob, lang_probs
            )
            
            # Prepare alternative languages
            alternatives = []
            for lang_prob in lang_probs[1:5]:  # Top 4 alternatives
                alt_code = self._normalize_language_code(lang_prob.lang)
                if alt_code != primary_code:
                    alternatives.append((alt_code, round(lang_prob.prob, 3)))
            
            return LanguageDetection(
                language=primary_code,
                confidence=confidence,
                method="enhanced_text_analysis",
                details=f"Analyzed {len(cleaned_text)} chars, primary: {primary_lang.lang} ({primary_lang.prob:.3f})",
                alternative_languages=alternatives
            )
        
        except (LangDetectException, Exception) as e:
            return None
    
    def _calculate_text_confidence(self, text: str, primary_prob: float, all_probs: List) -> float:
        """Calculate enhanced confidence score based on multiple factors."""
        # Base confidence from langdetect probability
        base_confidence = primary_prob
        
        # Adjust based on text length (more text = higher confidence)
        length_factor = min(1.0, len(text) / 500.0)  # Max boost at 500+ chars
        length_bonus = length_factor * 0.1
        
        # Adjust based on probability gap between top predictions
        if len(all_probs) >= 2:
            prob_gap = all_probs[0].prob - all_probs[1].prob
            gap_bonus = min(0.15, prob_gap * 0.3)  # Max 0.15 bonus for clear winner
        else:
            gap_bonus = 0.1  # Bonus if only one detection
        
        # Adjust based on character diversity (more diverse = more reliable)
        unique_chars = len(set(text.lower()))
        diversity_factor = min(1.0, unique_chars / 50.0)
        diversity_bonus = diversity_factor * 0.05
        
        final_confidence = base_confidence + length_bonus + gap_bonus + diversity_bonus
        return min(0.95, final_confidence)  # Cap at 0.95 for text analysis
    
    def _preprocess_text_for_detection(self, text: str) -> str:
        """Enhanced text preprocessing for better language detection."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove subtitle formatting
        text = re.sub(r'\{[^}]+\}', '', text)  # Remove {style} tags
        text = re.sub(r'\[[^\]]+\]', '', text)  # Remove [effect] tags
        
        # Remove timing information
        text = re.sub(r'\d{2}:\d{2}:\d{2}[,.]\d{3}', '', text)
        text = re.sub(r'-->', '', text)
        
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove lines that are mostly numbers or timestamps
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.isdigit() and len(line) > 2:
                # Skip lines that are mostly punctuation or symbols
                alpha_chars = sum(1 for c in line if c.isalpha())
                if alpha_chars > len(line) * 0.3:  # At least 30% alphabetic
                    lines.append(line)
        
        return '\n'.join(lines)
    
    def _detect_from_filename_enhanced(self, path: Path, track_type: str) -> Optional[LanguageDetection]:
        """Enhanced filename pattern detection with better confidence scoring."""
        filename = path.name.lower()
        
        # Score each language based on pattern matches
        language_scores = {}
        matched_patterns = {}
        
        for lang, patterns in self.filename_patterns.items():
            score = 0
            matches = []
            
            for pattern in patterns:
                # Strong match: word boundary
                if re.search(rf'\b{re.escape(pattern)}\b', filename):
                    score += 3
                    matches.append(f"word:{pattern}")
                # Medium match: with separators
                elif re.search(rf'[._\-\s]{re.escape(pattern)}[._\-\s]', filename):
                    score += 2
                    matches.append(f"sep:{pattern}")
                # Weak match: substring
                elif pattern in filename:
                    score += 1
                    matches.append(f"sub:{pattern}")
            
            if score > 0:
                language_scores[lang] = score
                matched_patterns[lang] = matches
        
        if not language_scores:
            return None
        
        # Find the best language
        best_lang = max(language_scores.keys(), key=lambda x: language_scores[x])
        best_score = language_scores[best_lang]
        
        # Calculate confidence based on score and competition
        base_confidence = min(0.9, best_score * 0.15)  # Scale score to confidence
        
        # Reduce confidence if there's competition
        other_scores = [s for lang, s in language_scores.items() if lang != best_lang]
        if other_scores:
            max_other = max(other_scores)
            if max_other >= best_score * 0.7:  # Close competition
                base_confidence *= 0.8
        
        # Only return if confidence is reasonable
        if base_confidence < 0.3:
            return None
        
        return LanguageDetection(
            language=best_lang,
            confidence=base_confidence,
            method="enhanced_filename_pattern",
            details=f"Matched patterns: {matched_patterns[best_lang]} (score: {best_score})"
        )
    
    def _detect_from_content_heuristics(self, path: Path, stream: StreamInfo, track_type: str) -> Optional[LanguageDetection]:
        """Enhanced content-based heuristic detection."""
        filename = path.name.lower()
        
        # Japanese content indicators with confidence scoring
        japanese_score = 0
        japanese_indicators = []
        
        # Strong Japanese indicators
        strong_jp_patterns = [
            r'anime', r'アニメ', r'manga', r'マンガ',
            r'nhk', r'tokyo', r'japan', r'japanese',
            r'episode', r'ep\d+', r's\d+e\d+',
            r'blu[._-]?ray', r'bd[._-]?rip'
        ]
        
        for pattern in strong_jp_patterns:
            if re.search(pattern, filename):
                japanese_score += 2
                japanese_indicators.append(pattern)
        
        # Medium Japanese indicators
        medium_jp_patterns = [
            r'[a-z]+ no [a-z]+',  # "X no Y" pattern
            r'sensei', r'sama', r'chan', r'kun',  # Common honorifics
            r'shinobi', r'ninja', r'samurai', r'yokai'  # Cultural terms
        ]
        
        for pattern in medium_jp_patterns:
            if re.search(pattern, filename):
                japanese_score += 1
                japanese_indicators.append(pattern)
        
        # For audio tracks in Japanese content
        if track_type == 'audio' and japanese_score >= 3:
            # Assume first audio track is Japanese
            return LanguageDetection(
                language="ja",
                confidence=min(0.7, japanese_score * 0.1),
                method="enhanced_content_heuristic",
                details=f"Japanese content indicators: {japanese_indicators[:3]} (score: {japanese_score})"
            )
        
        # For subtitle tracks, be more conservative
        if track_type == 'subtitle' and japanese_score >= 2:
            return LanguageDetection(
                language="en",  # Assume English subs for Japanese content
                confidence=min(0.6, japanese_score * 0.08),
                method="enhanced_content_heuristic", 
                details=f"Assumed EN subs for JP content: {japanese_indicators[:2]}"
            )
        
        return None
    
    def _is_valid_language_code(self, lang: Optional[str]) -> bool:
        """Enhanced language code validation using langcodes."""
        if not lang:
            return False
        
        normalized = lang.lower().strip()
        
        # Check against known invalid codes (including 'und' as it means undetermined)
        if normalized in self.invalid_codes or normalized == 'und':
            return False
        
        # Use langcodes to validate, but be more permissive than strict ISO validation
        try:
            lang_obj = langcodes.Language.make(language=normalized)
            # Accept if langcodes recognizes it, even if not strictly valid
            return lang_obj.language == normalized and len(normalized) in (2, 3)
        except:
            # Fallback to basic validation for edge cases
            return len(normalized) in (2, 3) and normalized.isalpha()
    
    def _normalize_language_code(self, lang: str) -> str:
        """Enhanced language code normalization using langcodes."""
        if not lang:
            return lang
        
        # First try our custom mappings
        normalized = lang.lower().strip()
        if normalized in self.language_mappings:
            return self.language_mappings[normalized]
        
        # Then try langcodes for well-known codes
        try:
            lang_obj = langcodes.Language.make(language=normalized)
            if lang_obj.is_valid() and lang_obj.language:
                # Use the language part (should be 2-letter for valid codes)
                return lang_obj.language
        except:
            pass
        
        # For unrecognized but valid-format codes, return as-is if 2-3 letters
        if len(normalized) in (2, 3) and normalized.isalpha():
            return normalized
        
        return lang
    
    def _extract_subtitle_sample(self, media: MediaInfo, stream: StreamInfo) -> Optional[str]:
        """Enhanced subtitle text extraction with better error handling."""
        try:
            which("ffmpeg")
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Extract longer sample for better detection
                run([
                    "ffmpeg", "-i", str(media.path),
                    "-map", f"0:{stream.index}",
                    "-t", "300",  # First 5 minutes instead of 2
                    "-y", str(temp_path)
                ])
                
                if temp_path.exists() and temp_path.stat().st_size > 0:
                    content = temp_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # More sophisticated text extraction
                    text_lines = self._extract_clean_subtitle_text(content)
                    
                    # Limit to max sample size for performance
                    full_text = '\n'.join(text_lines)
                    if len(full_text) > self.max_text_sample:
                        full_text = full_text[:self.max_text_sample]
                    
                    return full_text
                    
            finally:
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            return None
        
        return None
    
    def _extract_clean_subtitle_text(self, raw_content: str) -> List[str]:
        """Extract clean text lines from subtitle content."""
        lines = []
        
        for line in raw_content.split('\n'):
            line = line.strip()
            
            # Skip empty lines, timestamps, and sequence numbers
            if not line or line.isdigit() or '-->' in line:
                continue
            
            # Clean HTML tags and formatting
            clean_line = re.sub(r'<[^>]+>', '', line)
            clean_line = re.sub(r'\{[^}]+\}', '', clean_line)
            clean_line = re.sub(r'\[[^\]]+\]', '', clean_line)
            
            # Remove excessive punctuation
            clean_line = re.sub(r'[.]{3,}', '...', clean_line)
            clean_line = re.sub(r'[-]{2,}', '--', clean_line)
            
            clean_line = clean_line.strip()
            
            # Only include lines with substantial text content
            if clean_line and len(clean_line) >= 3:
                alpha_count = sum(1 for c in clean_line if c.isalpha())
                if alpha_count >= 2:  # At least 2 alphabetic characters
                    lines.append(clean_line)
        
        return lines
    
    def _detect_language_from_audio_whisper(self, media: MediaInfo, stream: StreamInfo) -> Optional[LanguageDetection]:
        """Detect language from audio content using Whisper speech recognition."""
        if not WHISPER_AVAILABLE:
            return None
        
        try:
            # Load Whisper model (lazy loading)
            if self.whisper_model is None and whisper is not None:
                self.whisper_model = whisper.load_model(self.whisper_model_size)
            
            # Extract audio sample for analysis
            audio_sample_path = self._extract_audio_sample(media, stream)
            if not audio_sample_path:
                return None
            
            try:
                if not self.whisper_model:
                    return None
                
                # Run Whisper detection
                result = self.whisper_model.transcribe(
                    audio_sample_path, 
                    word_timestamps=False,
                    temperature=0,  # More deterministic results
                    task="transcribe"  # We want detection, not translation
                )
                
                detected_language = result.get("language", "")
                if not detected_language or not isinstance(detected_language, str):
                    return None
                
                # Calculate confidence based on Whisper's internal metrics
                confidence = self._calculate_whisper_confidence(result)
                
                # Normalize language code
                normalized_lang = self._normalize_language_code(detected_language)
                
                # Prepare details
                text_length = len(result.get("text", ""))
                details = f"Whisper detected {detected_language} from {self.whisper_sample_duration}s audio sample"
                if text_length > 0:
                    details += f" (transcribed {text_length} characters)"
                
                return LanguageDetection(
                    language=normalized_lang,
                    confidence=confidence,
                    method="whisper_audio_analysis",
                    details=details,
                    alternative_languages=[],  # Whisper doesn't provide alternatives easily
                    text_sample_size=text_length
                )
                
            finally:
                # Clean up temporary audio file
                if audio_sample_path and Path(audio_sample_path).exists():
                    Path(audio_sample_path).unlink()
            
        except Exception as e:
            # Whisper analysis failed, return None to fall back to other methods
            return None
    
    def _extract_audio_sample(self, media: MediaInfo, stream: StreamInfo) -> Optional[str]:
        """Extract a sample of audio for Whisper analysis."""
        try:
            which("ffmpeg")
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Extract audio sample - Whisper prefers WAV format
                run([
                    "ffmpeg", "-i", str(media.path),
                    "-map", f"0:{stream.index}",
                    "-t", str(self.whisper_sample_duration),  # Sample duration
                    "-ac", "1",  # Convert to mono for faster processing
                    "-ar", "16000",  # 16kHz sample rate (Whisper standard)
                    "-y", str(temp_path)
                ])
                
                if temp_path.exists() and temp_path.stat().st_size > 0:
                    return str(temp_path)
                    
            except Exception:
                # Audio extraction failed
                if temp_path.exists():
                    temp_path.unlink()
                return None
                
        except Exception:
            return None
        
        return None
    
    def _calculate_whisper_confidence(self, whisper_result: dict) -> float:
        """Calculate confidence score from Whisper results."""
        # Whisper doesn't provide direct confidence scores, so we estimate based on:
        # 1. Whether it detected speech
        # 2. Length of transcribed text
        # 3. Language detection consistency
        
        text = whisper_result.get("text", "")
        language = whisper_result.get("language", "")
        
        if not language or not text.strip():
            return 0.0
        
        # Base confidence starts at 0.5 for any detection
        base_confidence = 0.5
        
        # Bonus for longer transcription (more data = more reliable)
        text_length = len(text.strip())
        if text_length > 100:
            base_confidence += 0.2
        elif text_length > 50:
            base_confidence += 0.1
        elif text_length < 10:
            base_confidence -= 0.2
        
        # Bonus for common languages (Whisper is generally more accurate with these)
        common_languages = {'en', 'ja', 'zh', 'es', 'fr', 'de', 'ko'}
        if language in common_languages:
            base_confidence += 0.1
        
        # Cap confidence at reasonable maximum for audio analysis
        return min(0.85, max(0.1, base_confidence))
    
    def _detect_language_from_text_cloud(self, text: str) -> Optional[LanguageDetection]:
        """Detect language from text using Google Translate API as fallback."""
        if not GOOGLETRANS_AVAILABLE or not self.cloud_api_enabled:
            return None
        
        try:
            # Clean and preprocess text
            cleaned_text = self._preprocess_text_for_detection(text)
            if len(cleaned_text.strip()) < self.min_text_length:
                return None
            
            # Initialize Google Translator (lazy loading)
            if self.google_translator is None and Translator is not None:
                self.google_translator = Translator()
            
            if not self.google_translator:
                return None
            
            # Use Google Translate's language detection
            detection_result = self.google_translator.detect(cleaned_text)
            
            if not detection_result or not hasattr(detection_result, 'lang'):
                return None
            
            detected_lang = detection_result.lang
            if not detected_lang:
                return None
            
            # Get confidence (Google Translate provides this)
            confidence = getattr(detection_result, 'confidence', 0.5)
            
            # Normalize language code
            normalized_lang = self._normalize_language_code(detected_lang)
            
            # Calculate adjusted confidence based on text quality and Google's confidence
            adjusted_confidence = self._calculate_cloud_confidence(
                cleaned_text, confidence, detected_lang
            )
            
            # Get language name for details
            lang_name = LANGUAGES.get(detected_lang, detected_lang) if LANGUAGES else detected_lang
            
            return LanguageDetection(
                language=normalized_lang,
                confidence=adjusted_confidence,
                method="cloud_api_translate",
                details=f"Google Translate detected {lang_name} ({detected_lang}) with {confidence:.3f} confidence",
                alternative_languages=[]  # Google Translate doesn't provide alternatives in this API
            )
            
        except Exception as e:
            # Cloud API failed, return None to indicate no detection
            return None
    
    def _calculate_cloud_confidence(self, text: str, api_confidence: float, detected_lang: str) -> float:
        """Calculate adjusted confidence score for cloud API results."""
        # Start with API-provided confidence
        base_confidence = api_confidence if api_confidence else 0.5
        
        # Adjust based on text length (more text = more reliable)
        text_length = len(text.strip())
        if text_length > 200:
            base_confidence += 0.1
        elif text_length < 50:
            base_confidence -= 0.1
        
        # Adjust based on detected language reliability
        # Google Translate is generally more reliable with major languages
        major_languages = {'en', 'ja', 'zh', 'es', 'fr', 'de', 'ko', 'ar', 'hi', 'ru'}
        if detected_lang in major_languages:
            base_confidence += 0.05
        
        # For cloud API, we're more conservative about confidence
        # since this is a fallback method
        base_confidence *= 0.9
        
        return min(0.8, max(0.2, base_confidence))
    
    def detect_all_languages(self, media: MediaInfo, force_detection: bool = False) -> Dict[int, LanguageDetection]:
        """Detect languages for all audio and subtitle tracks with enhanced reporting."""
        results = {}
        
        for stream in media.streams:
            if stream.codec_type in ('audio', 'subtitle'):
                if stream.codec_type == 'audio':
                    detection = self.detect_audio_language(media, stream, force_detection)
                else:
                    detection = self.detect_subtitle_language(media, stream, force_detection)
                    
                results[stream.index] = detection
        
        return results


def apply_language_tags(media_path: Path, language_detections: Dict[int, LanguageDetection], 
                       execute: bool = False, confidence_threshold: float = 0.5) -> List[str]:
    """Apply detected language tags with enhanced reporting."""
    which("mkvpropedit")
    
    commands = []
    changes_needed = []
    
    for track_index, detection in language_detections.items():
        if detection.language and detection.confidence >= confidence_threshold:
            track_number = track_index + 1
            
            command = [
                "mkvpropedit", str(media_path),
                "--edit", f"track:{track_number}",
                "--set", f"language={detection.language}"
            ]
            
            commands.append(command)
            changes_needed.append(
                f"Track {track_number}: {detection.language} "
                f"({detection.method}, {detection.confidence:.3f} confidence, "
                f"{detection.detection_time_ms:.1f}ms)"
            )
    
    if execute and commands:
        for i, command in enumerate(commands):
            try:
                run(command)
            except Exception as e:
                raise ProbeError(f"Failed to apply language tag for command {i+1}: {e}")
    
    return changes_needed