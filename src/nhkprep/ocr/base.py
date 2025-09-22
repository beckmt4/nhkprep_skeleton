from abc import ABC, abstractmethod
from typing import List, Tuple

class OCRProvider(ABC):
    @abstractmethod
    def detect_text(self, image_bytes: bytes) -> List[Tuple[str, float]]:
        """Return (text, confidence)."""
        ...
