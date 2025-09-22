from typing import List, Tuple
from .base import OCRProvider

class PaddleOCRStub(OCRProvider):
    def detect_text(self, image_bytes: bytes) -> List[Tuple[str, float]]:
        # Placeholder for future OCR
        return []
