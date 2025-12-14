from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Dict, Optional, Callable
from urllib.parse import urlparse, parse_qs

DEFAULT_WEIGHTS = {"harvest_index": 0.30, "juice_score": 0.35, "access_signal": 0.20, "anomaly_signal": 0.15}

HIGH_SIGNAL_PARAM_NAMES = {
    "id","uid","user","username","token","auth","redirect","next","url","uri",
    "file","path","query","search","q","dest","destination","return","continue",
    "callback", "jsonp", "api_key", "apikey", "key", "session", "sess",
}
PATH_KEYWORDS = {
    "admin","login","signin","auth","sso","oauth","api","graphql","swagger","openapi",
    "debug","internal","upload","export","download","backup","config","console",
    "dashboard", "panel", "manage", "settings", "account", "profile",
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

@dataclass
class ScoringContext:
    """Context object containing all scoring inputs."""
    url: str
    sources: set[str]
    host: str
    path: str
    path_lc: str
    param_names: set[str]
    param_count: int
    ext: str
    status: Optional[int]
    content_type: Optional[str]
    redirect_location: Optional[str]
    has_set_cookie: bool
    www_authenticate: bool
    response_time_ms: Optional[int]
    response_size_bytes: Optional[int]
    base_host: Optional[str]
    unique_path: bool
    tech: List[str] = None  # Detected technologies from httpx

# Type for scoring extension functions
ScoringExtension = Callable[[ScoringContext, List[str]], int]

def clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))

def _path_depth(path: str) -> int:
    return len([p for p in (path or "").split("/") if p])

def _build_context(
    url: str,
    sources: Iterable[str],
    status: Optional[int],
    content_type: Optional[str],
    redirect_location: Optional[str],
    has_set_cookie: bool,
    www_authenticate: bool,
    response_time_ms: Optional[int],
    response_size_bytes: Optional[int],
    base_host: Optional[str],
    unique_path: bool,
    tech: Optional[List[str]] = None,
) -> ScoringContext:
    """Build a scoring context from raw inputs."""
    p = urlparse(url)
    host = p.hostname or ""
    path = p.path or ""
    qs = parse_qs(p.query or "", keep_blank_values=True)
    param_names = {k.lower() for k in qs.keys()}
    param_count = len(param_names)
    path_lc = path.lower()
    ext = next((e for e in DYNAMIC_EXTS if path_lc.endswith(e)), "")
    
    return ScoringContext(
        url=url,
        sources={s.lower() for s in sources},
        host=host,
        path=path,
        path_lc=path_lc,
        param_names=param_names,
        param_count=param_count,
        ext=ext,
        status=status,
        content_type=content_type,
        redirect_location=redirect_location,
        has_set_cookie=has_set_cookie,
        www_authenticate=www_authenticate,
        response_time_ms=response_time_ms,
        response_size_bytes=response_size_bytes,
        base_host=base_host,
        unique_path=unique_path,
        tech=tech or [],
    )

def compute_harvest_index(ctx: ScoringContext, reasons: List[str]) -> int:
    """Compute HarvestIndex subscore (discovery & surface expansion)."""
    H = 0
    if "katana" in ctx.sources:
        H += 10; reasons.append("source:katana (+10 H)")
    if "gau" in ctx.sources:
        H += 15; reasons.append("source:gau (+15 H)")
    if "gospider" in ctx.sources:
        H += 12; reasons.append("source:gospider (+12 H)")
    if "hakrawler" in ctx.sources:
        H += 12; reasons.append("source:hakrawler (+12 H)")
    if "robots" in ctx.sources:
        H += 20; reasons.append("source:robots (+20 H)")
    if "sitemap" in ctx.sources:
        H += 18; reasons.append("source:sitemap (+18 H)")
    if ctx.base_host and ctx.host and ctx.host != ctx.base_host:
        H += 25; reasons.append("new_host/vhost (+25 H)")
    if _path_depth(ctx.path) >= 3:
        H += 10; reasons.append("path_depth>=3 (+10 H)")
    if ctx.content_type and any(ct in ctx.content_type.lower() for ct in ("text/html","application/json","application/xml")):
        H += 10; reasons.append("app_content_type (+10 H)")
    if ctx.unique_path:
        H += 10; reasons.append("unique_path (+10 H)")
    return clamp(H)

def compute_juice_score(ctx: ScoringContext, reasons: List[str]) -> int:
    """Compute JuiceScore subscore (input & sensitivity potential)."""
    J = 0
    if ctx.param_names:
        J += 20; reasons.append("has_params (+20 J)")
    if ctx.param_count >= 3:
        J += 10; reasons.append("param_count>=3 (+10 J)")
    hi_params = sorted([p for p in ctx.param_names if p in HIGH_SIGNAL_PARAM_NAMES])
    if hi_params:
        J += 20; reasons.append(f"high_signal_params:{','.join(hi_params[:5])} (+20 J)")
    if any(kw in ctx.path_lc.split("/") or f"/{kw}" in ctx.path_lc for kw in PATH_KEYWORDS):
        J += 25; reasons.append("path_keywords (+25 J)")
    if ctx.ext:
        J += 10; reasons.append(f"dynamic_ext:{ctx.ext} (+10 J)")
    # API path detection - check for versioned API paths
    if "/api/" in ctx.path_lc and any(f"/v{i}/" in ctx.path_lc for i in range(1, 5)):
        J += 15; reasons.append("api_versioned_path (+15 J)")
    return clamp(J)

def compute_access_signal(ctx: ScoringContext, reasons: List[str]) -> int:
    """Compute AccessSignal subscore (authentication hints)."""
    A = 0
    if ctx.status == 401:
        A += 40; reasons.append("status:401 (+40 A)")
    elif ctx.status == 403:
        A += 35; reasons.append("status:403 (+35 A)")
    elif ctx.status in (301,302,303,307,308):
        loc = (ctx.redirect_location or "").lower()
        if any(k in loc for k in ("login","signin","auth","sso","oauth")):
            A += 25; reasons.append("redirect_to_login (+25 A)")
    if ctx.www_authenticate:
        A += 20; reasons.append("www_authenticate (+20 A)")
    if ctx.has_set_cookie:
        A += 15; reasons.append("set_cookie_seen (+15 A)")
    return clamp(A)

def compute_anomaly_signal(ctx: ScoringContext, reasons: List[str]) -> int:
    """Compute AnomalySignal subscore (errors & unusual responses)."""
    N = 0
    if ctx.status is not None and 500 <= ctx.status <= 599:
        N += 35; reasons.append("status:5xx (+35 N)")
    if ctx.response_time_ms is not None and ctx.response_time_ms > 2000:
        N += 20; reasons.append("slow_response (+20 N)")
    if ctx.response_size_bytes is not None and ctx.response_size_bytes > 1_000_000:
        N += 15; reasons.append("large_response>1MB (+15 N)")
    return clamp(N)

def compute_confidence(ctx: ScoringContext) -> float:
    """Compute confidence score based on available metadata."""
    observed = 0
    for v in (ctx.status, ctx.content_type, ctx.redirect_location, ctx.response_time_ms, ctx.response_size_bytes):
        if v is not None and v != "":
            observed += 1
    return min(1.0, 0.55 + 0.08 * observed)

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
    tech: Optional[List[str]] = None,
    weights: Optional[Dict[str, float]] = None,
    extensions: Optional[List[ScoringExtension]] = None,
) -> ReapResult:
    """
    Compute ReapScore for an endpoint.
    
    Args:
        url: Full URL of the endpoint
        sources: Discovery sources (katana, gau, gospider, hakrawler, robots, sitemap, etc.)
        status: HTTP status code
        content_type: Content-Type header
        redirect_location: Location header for redirects
        has_set_cookie: Whether Set-Cookie header was present
        www_authenticate: Whether WWW-Authenticate header was present
        response_time_ms: Response time in milliseconds
        response_size_bytes: Response size in bytes
        base_host: Base target host for vhost detection
        unique_path: Whether this is a unique path on the host
        tech: List of detected technologies (from httpx tech-detect)
        weights: Custom subscore weights (default: harvest=0.30, juice=0.35, access=0.20, anomaly=0.15)
        extensions: Optional list of custom scoring functions for community extensions
        
    Returns:
        ReapResult with score, subscores, reasons, confidence, and weights
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    
    ctx = _build_context(
        url, sources, status, content_type, redirect_location,
        has_set_cookie, www_authenticate, response_time_ms, response_size_bytes,
        base_host, unique_path, tech
    )
    
    reasons: List[str] = []
    
    # Compute core subscores
    H = compute_harvest_index(ctx, reasons)
    J = compute_juice_score(ctx, reasons)
    A = compute_access_signal(ctx, reasons)
    N = compute_anomaly_signal(ctx, reasons)
    
    # Apply custom extensions if provided
    # Note: Extensions should return positive integers to add bonus points to JuiceScore
    # Negative or zero values are ignored to prevent score manipulation
    if extensions:
        for ext_func in extensions:
            try:
                bonus = ext_func(ctx, reasons)
                if bonus > 0:
                    J += bonus  # Extensions add to JuiceScore by default
                    J = clamp(J)
            except Exception:
                # Silently ignore extension errors to avoid breaking core scoring
                pass
    
    confidence = compute_confidence(ctx)
    
    score = round(w["harvest_index"]*H + w["juice_score"]*J + w["access_signal"]*A + w["anomaly_signal"]*N)
    score = clamp(score)
    
    return ReapResult(score, SubScores(H,J,A,N), reasons, round(confidence,2), w)
