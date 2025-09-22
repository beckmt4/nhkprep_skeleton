from abc import ABC, abstractmethod
from typing import List

class MTProvider(ABC):
    @abstractmethod
    def translate_batch(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        ...
