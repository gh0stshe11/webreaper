"""Explainable ReapScore calculator for webReaper."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs


# Starter weights for ReapScore calculation
DEFAULT_WEIGHTS = {
    "discovery": 0.20,
    "params": 0.25,
    "sensitivity": 0.30,
    "tech": 0.10,
    "anomalies": 0.10,
    "third_party": 0.05,
}


@dataclass
class Signal:
    """A single scoring signal with evidence."""
    name: str
    category: str
    score: float
    evidence: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "score": self.score,
            "evidence": self.evidence,
        }


@dataclass
class ReapScore:
    """Complete ReapScore with signals and rationale."""
    url: str
    score: float  # 0.0 - 1.0
    signals: List[Signal] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "score": round(self.score, 3),
            "signals": [s.to_dict() for s in self.signals],
            "category_scores": {k: round(v, 3) for k, v in self.category_scores.items()},
            "rationale": self.rationale,
            "weights": self.weights,
        }


def compute_reapscore(
    url: str,
    *,
    sources: List[str] = None,
    status_code: Optional[int] = None,
    has_params: bool = False,
    param_count: int = 0,
    high_value_params: List[str] = None,
    path_depth: int = 0,
    has_auth_keywords: bool = False,
    has_api_keywords: bool = False,
    tech_stack: List[str] = None,
    header_signals: List[str] = None,
    js_endpoints_found: int = 0,
    response_time_ms: Optional[int] = None,
    is_subdomain: bool = False,
    weights: Optional[Dict[str, float]] = None,
) -> ReapScore:
    """
    Compute explainable ReapScore for an endpoint.
    
    Args:
        url: The URL being scored
        sources: Discovery sources (robots, sitemap, wayback, etc.)
        status_code: HTTP status code
        has_params: Whether URL has query parameters
        param_count: Number of query parameters
        high_value_params: List of high-value parameter names found
        path_depth: Depth of URL path
        has_auth_keywords: Whether URL contains auth-related keywords
        has_api_keywords: Whether URL contains API-related keywords
        tech_stack: Detected technologies
        header_signals: Security signals from headers
        js_endpoints_found: Number of endpoints discovered in JS
        response_time_ms: Response time in milliseconds
        is_subdomain: Whether this is a subdomain discovery
        weights: Custom weights (uses DEFAULT_WEIGHTS if not provided)
    
    Returns:
        ReapScore object with signals and rationale
    """
    # Initialize
    sources = sources or []
    high_value_params = high_value_params or []
    tech_stack = tech_stack or []
    header_signals = header_signals or []
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    
    # Convert sources to lowercase once for efficiency
    sources_lower = [s.lower() for s in sources]
    
    signals: List[Signal] = []
    category_scores: Dict[str, float] = {
        "discovery": 0.0,
        "params": 0.0,
        "sensitivity": 0.0,
        "tech": 0.0,
        "anomalies": 0.0,
        "third_party": 0.0,
    }
    rationale: List[str] = []
    
    # === DISCOVERY CATEGORY ===
    discovery_score = 0.0
    
    if "wayback" in sources_lower:
        discovery_score += 0.3
        signals.append(Signal("wayback_source", "discovery", 0.3, "Found in Wayback Machine"))
        rationale.append("Historical URL from Wayback Machine (+0.3)")
    
    if "robots" in sources_lower:
        discovery_score += 0.4
        signals.append(Signal("robots_source", "discovery", 0.4, "Found in robots.txt"))
        rationale.append("Disallowed in robots.txt (+0.4)")
    
    if "sitemap" in sources_lower:
        discovery_score += 0.2
        signals.append(Signal("sitemap_source", "discovery", 0.2, "Found in sitemap.xml"))
        rationale.append("Listed in sitemap.xml (+0.2)")
    
    if "crtsh" in sources_lower or is_subdomain:
        discovery_score += 0.5
        signals.append(Signal("subdomain_discovery", "discovery", 0.5, "Subdomain discovered"))
        rationale.append("New subdomain discovered (+0.5)")
    
    if path_depth >= 3:
        discovery_score += 0.2
        signals.append(Signal("deep_path", "discovery", 0.2, f"Path depth: {path_depth}"))
        rationale.append(f"Deep URL path (depth={path_depth}) (+0.2)")
    
    category_scores["discovery"] = min(1.0, discovery_score)
    
    # === PARAMS CATEGORY ===
    params_score = 0.0
    
    if has_params:
        params_score += 0.3
        signals.append(Signal("has_params", "params", 0.3, f"Query params: {param_count}"))
        rationale.append(f"Has query parameters (count={param_count}) (+0.3)")
    
    if param_count >= 3:
        params_score += 0.2
        signals.append(Signal("many_params", "params", 0.2, f"Parameter count: {param_count}"))
        rationale.append(f"Multiple parameters (>= 3) (+0.2)")
    
    if high_value_params:
        params_score += 0.5
        param_list = ", ".join(high_value_params[:5])
        signals.append(Signal("high_value_params", "params", 0.5, f"Params: {param_list}"))
        rationale.append(f"High-value parameters: {param_list} (+0.5)")
    
    category_scores["params"] = min(1.0, params_score)
    
    # === SENSITIVITY CATEGORY ===
    sensitivity_score = 0.0
    
    if has_auth_keywords:
        sensitivity_score += 0.6
        signals.append(Signal("auth_keywords", "sensitivity", 0.6, "Authentication-related endpoint"))
        rationale.append("Auth-related keywords in path (+0.6)")
    
    if has_api_keywords:
        sensitivity_score += 0.4
        signals.append(Signal("api_keywords", "sensitivity", 0.4, "API endpoint"))
        rationale.append("API-related keywords in path (+0.4)")
    
    if status_code == 401:
        sensitivity_score += 0.7
        signals.append(Signal("status_401", "sensitivity", 0.7, "Requires authentication"))
        rationale.append("Status 401: Authentication required (+0.7)")
    elif status_code == 403:
        sensitivity_score += 0.6
        signals.append(Signal("status_403", "sensitivity", 0.6, "Access forbidden"))
        rationale.append("Status 403: Access forbidden (+0.6)")
    
    # Header signals
    if "cors_wildcard" in header_signals:
        sensitivity_score += 0.3
        signals.append(Signal("cors_wildcard", "sensitivity", 0.3, "CORS allows any origin"))
        rationale.append("CORS wildcard configured (+0.3)")
    
    if "cors_misconfiguration" in header_signals:
        sensitivity_score += 0.5
        signals.append(Signal("cors_misconfig", "sensitivity", 0.5, "Dangerous CORS config"))
        rationale.append("Dangerous CORS misconfiguration (+0.5)")
    
    if "cookie_no_secure" in header_signals or "cookie_no_httponly" in header_signals:
        sensitivity_score += 0.2
        signals.append(Signal("insecure_cookies", "sensitivity", 0.2, "Insecure cookie flags"))
        rationale.append("Cookies missing security flags (+0.2)")
    
    category_scores["sensitivity"] = min(1.0, sensitivity_score)
    
    # === TECH CATEGORY ===
    tech_score = 0.0
    
    if tech_stack:
        tech_score += 0.3
        tech_list = ", ".join(tech_stack[:5])
        signals.append(Signal("tech_detected", "tech", 0.3, f"Tech: {tech_list}"))
        rationale.append(f"Technologies detected: {tech_list} (+0.3)")
    
    if js_endpoints_found > 0:
        tech_score += 0.4
        signals.append(Signal("js_endpoints", "tech", 0.4, f"JS endpoints: {js_endpoints_found}"))
        rationale.append(f"JavaScript endpoints discovered: {js_endpoints_found} (+0.4)")
    
    if "server_header_present" in header_signals:
        tech_score += 0.1
        signals.append(Signal("server_header", "tech", 0.1, "Server header exposed"))
        rationale.append("Server header exposed (+0.1)")
    
    category_scores["tech"] = min(1.0, tech_score)
    
    # === ANOMALIES CATEGORY ===
    anomalies_score = 0.0
    
    if status_code and 500 <= status_code <= 599:
        anomalies_score += 0.6
        signals.append(Signal("status_5xx", "anomalies", 0.6, f"Server error: {status_code}"))
        rationale.append(f"Server error {status_code} (+0.6)")
    
    if response_time_ms and response_time_ms > 2000:
        anomalies_score += 0.3
        signals.append(Signal("slow_response", "anomalies", 0.3, f"Response time: {response_time_ms}ms"))
        rationale.append(f"Slow response ({response_time_ms}ms) (+0.3)")
    
    if "no_csp" in header_signals:
        anomalies_score += 0.2
        signals.append(Signal("no_csp", "anomalies", 0.2, "No CSP header"))
        rationale.append("Missing Content-Security-Policy (+0.2)")
    
    if "no_hsts" in header_signals:
        anomalies_score += 0.2
        signals.append(Signal("no_hsts", "anomalies", 0.2, "No HSTS header"))
        rationale.append("Missing HSTS on HTTPS endpoint (+0.2)")
    
    category_scores["anomalies"] = min(1.0, anomalies_score)
    
    # === THIRD PARTY CATEGORY ===
    third_party_score = 0.0
    
    # Parse URL to check for third-party indicators
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    
    # Check if it's a common third-party domain
    third_party_indicators = ["cdn.", "static.", "assets.", "s3.amazonaws.com", "cloudfront.net"]
    if any(indicator in hostname.lower() for indicator in third_party_indicators):
        third_party_score += 0.3
        signals.append(Signal("third_party_domain", "third_party", 0.3, "Third-party service"))
        rationale.append("Third-party service detected (+0.3)")
    
    category_scores["third_party"] = min(1.0, third_party_score)
    
    # === AGGREGATE SCORE ===
    final_score = sum(
        category_scores[cat] * w[cat]
        for cat in category_scores
    )
    
    final_score = max(0.0, min(1.0, final_score))
    
    return ReapScore(
        url=url,
        score=final_score,
        signals=signals,
        category_scores=category_scores,
        rationale=rationale,
        weights=w,
    )
