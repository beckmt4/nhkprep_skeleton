from typing import List, Dict, Any

def simple_align_by_index(ref: List[str], sys: List[str]) -> List[Dict[str, Any]]:
    pairs = []
    for i, s in enumerate(sys):
        r = ref[i] if i < len(ref) else ""
        pairs.append({"reference_en": r, "system_en": s, "start": None, "end": None})
    return pairs
