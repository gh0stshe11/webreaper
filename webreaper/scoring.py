from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Dict, Optional
from urllib.parse import urlparse, parse_qs

DEFAULT_WEIGHTS = {"harvest_index": 0.30, "juice_score": 0.35, "access_signal": 0.20, "anomaly_signal": 0.15}

HIGH_SIGNAL_PARAM_NAMES = {
    "id","uid","user","username","token","auth","redirect","next","url","uri",
    "file","path","query","search","q","dest","destination","return","continue",
}
PATH_KEYWORDS = {
    "admin","login","signin","auth","sso","oauth","api","graphql","swagger","openapi",
    "debug","internal","upload","export","download","backup",
}
DYNAMIC_EXTS = {".php",".aspx",".asp",".jsp",".do",".action"}

@dataclass
class SubScores:
    harvest_index: int
    juice_score: int
    access_signal: int
    anomaly_signal: int

@dataclass
class ReapResult:
    score: int
    subs: SubScores
    reasons: List[str]
    confidence: float
    weights: Dict[str, float]

def clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))

def _path_depth(path: str) -> int:
    return len([p for p in (path or "").split("/") if p])

def compute_reapscore(
    *,
    url: str,
    sources: Iterable[str],
    status: Optional[int] = None,
    content_type: Optional[str] = None,
    redirect_location: Optional[str] = None,
    has_set_cookie: bool = False,
    www_authenticate: bool = False,
    response_time_ms: Optional[int] = None,
    response_size_bytes: Optional[int] = None,
    base_host: Optional[str] = None,
    unique_path: bool = True,
    weights: Optional[Dict[str, float]] = None,
) -> ReapResult:
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    p = urlparse(url)
    host = p.hostname or ""
    path = p.path or ""
    qs = parse_qs(p.query or "", keep_blank_values=True)
    param_names = {k.lower() for k in qs.keys()}
    param_count = len(param_names)

    path_lc = path.lower()
    ext = next((e for e in DYNAMIC_EXTS if path_lc.endswith(e)), "")

    reasons: List[str] = []
    src = {s.lower() for s in sources}

    H = 0
    if "katana" in src:
        H += 10; reasons.append("source:katana (+10 H)")
    if "gau" in src:
        H += 15; reasons.append("source:gau (+15 H)")
    if base_host and host and host != base_host:
        H += 25; reasons.append("new_host/vhost (+25 H)")
    if _path_depth(path) >= 3:
        H += 10; reasons.append("path_depth>=3 (+10 H)")
    if content_type and any(ct in content_type.lower() for ct in ("text/html","application/json")):
        H += 10; reasons.append("app_content_type (+10 H)")
    if unique_path:
        H += 10; reasons.append("unique_path (+10 H)")
    H = clamp(H)

    J = 0
    if param_names:
        J += 20; reasons.append("has_params (+20 J)")
    if param_count >= 3:
        J += 10; reasons.append("param_count>=3 (+10 J)")
    hi_params = sorted([p for p in param_names if p in HIGH_SIGNAL_PARAM_NAMES])
    if hi_params:
        J += 20; reasons.append(f"high_signal_params:{','.join(hi_params[:5])} (+20 J)")
    if any(kw in path_lc.split("/") or f"/{kw}" in path_lc for kw in PATH_KEYWORDS):
        J += 25; reasons.append("path_keywords (+25 J)")
    if ext:
        J += 10; reasons.append(f"dynamic_ext:{ext} (+10 J)")
    J = clamp(J)

    A = 0
    if status == 401:
        A += 40; reasons.append("status:401 (+40 A)")
    elif status == 403:
        A += 35; reasons.append("status:403 (+35 A)")
    elif status in (301,302,303,307,308):
        loc = (redirect_location or "").lower()
        if any(k in loc for k in ("login","signin","auth","sso","oauth")):
            A += 25; reasons.append("redirect_to_login (+25 A)")
    if www_authenticate:
        A += 20; reasons.append("www_authenticate (+20 A)")
    if has_set_cookie:
        A += 15; reasons.append("set_cookie_seen (+15 A)")
    A = clamp(A)

    N = 0
    if status is not None and 500 <= status <= 599:
        N += 35; reasons.append("status:5xx (+35 N)")
    if response_time_ms is not None and response_time_ms > 2000:
        N += 20; reasons.append("slow_response (+20 N)")
    if response_size_bytes is not None and response_size_bytes > 1_000_000:
        N += 15; reasons.append("large_response>1MB (+15 N)")
    N = clamp(N)

    observed = 0
    for v in (status, content_type, redirect_location, response_time_ms, response_size_bytes):
        if v is not None and v != "":
            observed += 1
    confidence = min(1.0, 0.55 + 0.08 * observed)

    score = round(w["harvest_index"]*H + w["juice_score"]*J + w["access_signal"]*A + w["anomaly_signal"]*N)
    score = clamp(score)

    return ReapResult(score, SubScores(H,J,A,N), reasons, round(confidence,2), w)
