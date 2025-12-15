"""
Security headers analyzer tool.

This tool analyzes HTTP security headers to provide additional scoring signals
and identify potentially vulnerable or well-secured endpoints.
"""

from __future__ import annotations
from typing import Dict, Any, List, Set

from .registry import AnalyzerTool, ToolMetadata, ToolCategory


class SecurityHeadersAnalyzer(AnalyzerTool):
    """
    Analyzes security-related HTTP headers.
    
    This tool examines response headers for security indicators:
    - Missing security headers (CSP, HSTS, X-Frame-Options, etc.)
    - Authentication headers (WWW-Authenticate, Authorization)
    - Session management (Set-Cookie attributes)
    - Security misconfigurations
    
    Contribution to ReapScore:
    - Enhances AccessSignal for endpoints with authentication headers
    - Adds signals for endpoints with missing security headers (potential targets)
    - Identifies secure vs insecure endpoints
    """
    
    # Security headers to check for
    SECURITY_HEADERS = {
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "x-xss-protection",
        "referrer-policy",
        "permissions-policy",
        "cross-origin-embedder-policy",
        "cross-origin-opener-policy",
        "cross-origin-resource-policy",
    }
    
    # Authentication/access control headers
    AUTH_HEADERS = {
        "www-authenticate",
        "authorization",
        "proxy-authenticate",
        "proxy-authorization",
    }
    
    # CORS headers
    CORS_HEADERS = {
        "access-control-allow-origin",
        "access-control-allow-credentials",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "access-control-expose-headers",
        "access-control-max-age",
    }
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="security_headers",
            category=ToolCategory.ANALYZER,
            description="Analyzes HTTP security headers for scoring signals",
            version="1.0.0",
            enabled_by_default=True,
            requires_external_binary=False,
        )
    
    def analyze(self, url: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze response headers for security signals.
        
        Args:
            url: The requested URL
            response_data: Dict with keys like 'headers', 'status', etc.
            
        Returns:
            Dict with analysis results:
            {
                "missing_security_headers": [...],
                "present_security_headers": [...],
                "auth_headers": [...],
                "cors_enabled": bool,
                "cors_misconfigured": bool,
                "has_hsts": bool,
                "has_csp": bool,
                "cookie_flags": {...},
                "security_score": int (0-100),
            }
        """
        headers = response_data.get("headers", {})
        
        # Normalize header names to lowercase
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        analysis = {
            "missing_security_headers": [],
            "present_security_headers": [],
            "auth_headers": [],
            "cors_enabled": False,
            "cors_misconfigured": False,
            "has_hsts": False,
            "has_csp": False,
            "cookie_flags": {},
            "security_score": 0,
        }
        
        # Check security headers
        for header in self.SECURITY_HEADERS:
            if header in headers_lower:
                analysis["present_security_headers"].append(header)
                if header == "strict-transport-security":
                    analysis["has_hsts"] = True
                elif header == "content-security-policy":
                    analysis["has_csp"] = True
            else:
                analysis["missing_security_headers"].append(header)
        
        # Check auth headers
        for header in self.AUTH_HEADERS:
            if header in headers_lower:
                analysis["auth_headers"].append(header)
        
        # Check CORS configuration
        cors_headers_present = [h for h in self.CORS_HEADERS if h in headers_lower]
        if cors_headers_present:
            analysis["cors_enabled"] = True
            
            # Check for CORS misconfiguration (overly permissive)
            acao = headers_lower.get("access-control-allow-origin", "")
            acac = headers_lower.get("access-control-allow-credentials", "")
            
            if acao == "*" and acac.lower() == "true":
                analysis["cors_misconfigured"] = True
        
        # Analyze Set-Cookie headers for security flags
        set_cookie = headers_lower.get("set-cookie", "")
        if set_cookie:
            analysis["cookie_flags"] = self._analyze_cookie_flags(set_cookie)
        
        # Compute a simple security score (0-100)
        # More missing headers = lower score = more interesting for testing
        # This is inversely correlated with security posture
        total_security_headers = len(self.SECURITY_HEADERS)
        missing_count = len(analysis["missing_security_headers"])
        
        # Score: 0 = all headers present (well secured)
        #        100 = no headers present (potentially vulnerable)
        analysis["security_score"] = int((missing_count / total_security_headers) * 100)
        
        return analysis
    
    def _analyze_cookie_flags(self, set_cookie_value: str) -> Dict[str, Any]:
        """
        Analyze Set-Cookie header for security flags.
        
        Args:
            set_cookie_value: Value of Set-Cookie header
            
        Returns:
            Dict with flags: {
                "has_secure": bool,
                "has_httponly": bool,
                "has_samesite": bool,
                "samesite_value": str or None,
            }
        """
        value_lower = set_cookie_value.lower()
        
        return {
            "has_secure": "secure" in value_lower,
            "has_httponly": "httponly" in value_lower,
            "has_samesite": "samesite" in value_lower,
            "samesite_value": self._extract_samesite_value(set_cookie_value),
        }
    
    def _extract_samesite_value(self, set_cookie_value: str) -> Optional[str]:
        """Extract SameSite attribute value from Set-Cookie header."""
        import re
        
        match = re.search(r'samesite=(\w+)', set_cookie_value, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None


def analyze_security_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Standalone function to analyze security headers.
    
    Args:
        headers: Dict of HTTP response headers
        
    Returns:
        Analysis results dict
    """
    analyzer = SecurityHeadersAnalyzer()
    return analyzer.analyze("", {"headers": headers})
