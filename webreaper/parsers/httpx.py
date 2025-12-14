from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class HttpxEndpoint:
    url: str
    host: str
    path: str
    status: Optional[int]
    content_type: Optional[str]
    title: Optional[str]
    tech: list[str]
    location: Optional[str]
    has_set_cookie: bool
    www_authenticate: bool
    time_ms: Optional[int]
    body_size: Optional[int]

def parse_httpx_jsonlines(output: str) -> List[HttpxEndpoint]:
    res: List[HttpxEndpoint] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue

        headers = obj.get("header") or obj.get("headers") or {}
        ct = obj.get("content_type") or headers.get("content-type") or headers.get("Content-Type")
        loc = headers.get("location") or headers.get("Location")
        set_cookie = headers.get("set-cookie") or headers.get("Set-Cookie")
        www_auth = headers.get("www-authenticate") or headers.get("WWW-Authenticate")

        status = obj.get("status_code")
        t = obj.get("time")
        if isinstance(t, float):
            t = int(t * 1000)
        elif not isinstance(t, int):
            t = None

        size = obj.get("content_length")
        if not isinstance(size, int):
            size = None

        tech = obj.get("tech") or []
        if isinstance(tech, str):
            tech = [tech]

        res.append(HttpxEndpoint(
            url=obj.get("url") or obj.get("input") or "",
            host=obj.get("host") or "",
            path=obj.get("path") or "",
            status=status if isinstance(status, int) else None,
            content_type=str(ct) if ct else None,
            title=str(obj.get("title")) if obj.get("title") else None,
            tech=[str(x) for x in tech if x],
            location=str(loc) if loc else None,
            has_set_cookie=bool(set_cookie),
            www_authenticate=bool(www_auth),
            time_ms=t,
            body_size=size,
        ))
    return res
