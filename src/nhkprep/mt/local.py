from typing import List
from .base import MTProvider

class LocalDummyMT(MTProvider):
    def __init__(self, model_id: str = "nllb-200-3.3B") -> None:
        self.model_id = model_id

    def translate_batch(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        # Placeholder: echo with marker
        return [f"[MT:{self.model_id}] {t}" for t in texts]
