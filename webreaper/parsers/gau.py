from __future__ import annotations
from typing import List
from urllib.parse import urlparse

def parse_gau_lines(output: str) -> List[str]:
    urls: List[str] = []
    for line in output.splitlines():
        u = line.strip()
        if not u or "://" not in u:
            continue
        try:
            p = urlparse(u)
        except Exception:
            continue
        if p.scheme and p.netloc:
            urls.append(p.geturl())
    return urls
