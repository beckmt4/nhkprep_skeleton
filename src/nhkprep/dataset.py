from __future__ import annotations
from pathlib import Path
from typing import Iterable, Dict, Any

def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            # Minimal escaping; avoid importing orjson to keep deps light
            import json
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
