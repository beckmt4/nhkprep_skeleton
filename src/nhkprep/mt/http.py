from typing import List
from .base import MTProvider

class HTTPMT(MTProvider):
    def __init__(self, url: str) -> None:
        self.url = url

    def translate_batch(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        # Placeholder: wire to your HTTP endpoint
        return [f"[HTTP:{self.url}] {t}" for t in texts]
