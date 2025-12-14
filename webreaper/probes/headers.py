"""Header analysis probe for webReaper."""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class HeaderAnalysis:
    """Results from header analysis."""
    url: str
    cors_allow_origin: Optional[str] = None
    cors_allow_credentials: Optional[str] = None
    csp: Optional[str] = None
    hsts: Optional[str] = None
    server: Optional[str] = None
    cookies: List[Dict[str, Any]] = None
    signals: List[str] = None
    
    def __post_init__(self):
        if self.cookies is None:
            self.cookies = []
        if self.signals is None:
            self.signals = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


def analyze_cookie(cookie_value: str) -> Dict[str, Any]:
    """
    Analyze a Set-Cookie header value.
    
    Args:
        cookie_value: The Set-Cookie header value
    
    Returns:
        Dictionary with cookie analysis
    """
    analysis = {
        "value": cookie_value,
        "secure": False,
        "httponly": False,
        "samesite": None,
        "issues": []
    }
    
    cookie_lower = cookie_value.lower()
    
    # Check flags
    if "secure" in cookie_lower:
        analysis["secure"] = True
    else:
        analysis["issues"].append("missing_secure")
    
    if "httponly" in cookie_lower:
        analysis["httponly"] = True
    else:
        analysis["issues"].append("missing_httponly")
    
    # Check SameSite
    if "samesite=strict" in cookie_lower:
        analysis["samesite"] = "Strict"
    elif "samesite=lax" in cookie_lower:
        analysis["samesite"] = "Lax"
    elif "samesite=none" in cookie_lower:
        analysis["samesite"] = "None"
    else:
        analysis["issues"].append("missing_samesite")
    
    return analysis


async def probe_headers(client, url: str, timeout: int = 10) -> HeaderAnalysis:
    """
    Fetch and analyze HTTP headers for security signals.
    
    Args:
        client: httpx.AsyncClient instance
        url: The URL to probe
        timeout: Request timeout in seconds
    
    Returns:
        HeaderAnalysis object
    """
    analysis = HeaderAnalysis(url=url)
    
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        headers = response.headers
        
        # CORS headers
        if "access-control-allow-origin" in headers:
            analysis.cors_allow_origin = headers["access-control-allow-origin"]
            if headers["access-control-allow-origin"] == "*":
                analysis.signals.append("cors_wildcard")
        
        if "access-control-allow-credentials" in headers:
            analysis.cors_allow_credentials = headers["access-control-allow-credentials"]
            if headers["access-control-allow-credentials"].lower() == "true":
                analysis.signals.append("cors_credentials")
        
        # Check for dangerous CORS combination
        if analysis.cors_allow_origin == "*" and analysis.cors_allow_credentials:
            analysis.signals.append("cors_misconfiguration")
        
        # Content Security Policy
        if "content-security-policy" in headers:
            analysis.csp = headers["content-security-policy"]
            if "unsafe-inline" in analysis.csp.lower():
                analysis.signals.append("csp_unsafe_inline")
            if "unsafe-eval" in analysis.csp.lower():
                analysis.signals.append("csp_unsafe_eval")
        else:
            analysis.signals.append("no_csp")
        
        # HSTS
        if "strict-transport-security" in headers:
            analysis.hsts = headers["strict-transport-security"]
        else:
            if url.startswith("https://"):
                analysis.signals.append("no_hsts")
        
        # Server header
        if "server" in headers:
            analysis.server = headers["server"]
            analysis.signals.append("server_header_present")
        
        # Cookie analysis
        if "set-cookie" in headers:
            # httpx normalizes headers, but set-cookie can appear multiple times
            # Get all set-cookie headers
            cookies = []
            for key, value in response.headers.raw:
                if key.lower() == b"set-cookie":
                    cookie_analysis = analyze_cookie(value.decode("utf-8", errors="ignore"))
                    cookies.append(cookie_analysis)
            
            analysis.cookies = cookies
            
            # Add signals based on cookie issues
            for cookie in cookies:
                if "missing_secure" in cookie.get("issues", []):
                    if "cookie_no_secure" not in analysis.signals:
                        analysis.signals.append("cookie_no_secure")
                if "missing_httponly" in cookie.get("issues", []):
                    if "cookie_no_httponly" not in analysis.signals:
                        analysis.signals.append("cookie_no_httponly")
                if "missing_samesite" in cookie.get("issues", []):
                    if "cookie_no_samesite" not in analysis.signals:
                        analysis.signals.append("cookie_no_samesite")
    
    except Exception:
        pass
    
    return analysis
