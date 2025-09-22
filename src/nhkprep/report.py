from pathlib import Path
from typing import Iterable, Dict, Any

HTML_TEMPLATE = """
<!doctype html>
<html><head><meta charset="utf-8"><title>NHKPrep Diff Report</title></head>
<body>
<h1>NHKPrep Diff Report</h1>
<table border="1" cellspacing="0" cellpadding="6">
<tr><th>#</th><th>Reference EN</th><th>System EN</th></tr>
{rows}
</table>
</body></html>
"""

def write_diff_html(path: Path, pairs: Iterable[Dict[str, Any]]) -> None:
    rows = []
    for i, p in enumerate(pairs, start=1):
        ref = (p.get("reference_en") or "").replace("&","&amp;").replace("<","&lt;")
        sys = (p.get("system_en") or "").replace("&","&amp;").replace("<","&lt;")
        rows.append(f"<tr><td>{i}</td><td>{ref}</td><td>{sys}</td></tr>")
    html = HTML_TEMPLATE.format(rows="\n".join(rows))
    path.write_text(html, encoding="utf-8")
