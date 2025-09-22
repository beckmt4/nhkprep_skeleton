from typing import List, Tuple

def cps_ok(text: str, duration_s: float, max_cps: int) -> bool:
    if duration_s <= 0:
        return True
    return (len(text) / duration_s) <= max_cps

def wrap_line(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + (1 if cur else 0) > max_chars:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += len(w) + (1 if cur_len>0 else 0)
    if cur:
        lines.append(" ".join(cur))
    return lines

def is_forced_heuristic(lines_per_min: float, median_chars: float, coverage_ratio: float) -> bool:
    return (coverage_ratio < 0.25) and (median_chars < 18) and (lines_per_min < 8)
