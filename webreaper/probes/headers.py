"""HTTP header analysis probe for security signals."""
from __future__ import annotations
from typing import Dict, Any, Optional
from urllib.parse import urlparse


def analyze_headers(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze HTTP response headers for security signals.
    
    Args:
        url: URL being analyzed
        headers: Response headers dictionary
        
    Returns:
        Dictionary containing security signals and metadata
    """
    signals = {
        'url': url,
        'cors': {},
        'csp': {},
        'hsts': {},
        'cookies': {},
        'security_score': 0,
        'issues': []
    }
    
    # Normalize headers to lowercase keys
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    # CORS analysis
    if 'access-control-allow-origin' in headers_lower:
        acao = headers_lower['access-control-allow-origin']
        signals['cors']['allow_origin'] = acao
        if acao == '*':
            signals['issues'].append('CORS: wildcard origin allowed')
            signals['security_score'] += 20
        elif acao:
            signals['cors']['specific_origin'] = True
            signals['security_score'] += 5
    
    if 'access-control-allow-credentials' in headers_lower:
        signals['cors']['allow_credentials'] = headers_lower['access-control-allow-credentials']
        if headers_lower['access-control-allow-credentials'].lower() == 'true':
            signals['security_score'] += 10
            if signals['cors'].get('allow_origin') == '*':
                signals['issues'].append('CORS: credentials with wildcard origin (high risk)')
                signals['security_score'] += 30
    
    # CSP analysis
    if 'content-security-policy' in headers_lower:
        csp = headers_lower['content-security-policy']
        signals['csp']['present'] = True
        signals['csp']['value'] = csp
        
        # Check for unsafe directives
        if 'unsafe-inline' in csp:
            signals['issues'].append('CSP: unsafe-inline detected')
            signals['security_score'] += 5
        if 'unsafe-eval' in csp:
            signals['issues'].append('CSP: unsafe-eval detected')
            signals['security_score'] += 5
    else:
        signals['csp']['present'] = False
        signals['issues'].append('CSP: not present')
    
    # HSTS analysis
    if 'strict-transport-security' in headers_lower:
        hsts = headers_lower['strict-transport-security']
        signals['hsts']['present'] = True
        signals['hsts']['value'] = hsts
        
        # Parse max-age
        if 'max-age=' in hsts.lower():
            try:
                max_age = int(hsts.lower().split('max-age=')[1].split(';')[0].strip())
                signals['hsts']['max_age'] = max_age
                if max_age < 31536000:  # Less than 1 year
                    signals['issues'].append('HSTS: max-age less than 1 year')
            except (ValueError, IndexError):
                pass
    else:
        signals['hsts']['present'] = False
        parsed = urlparse(url)
        if parsed.scheme == 'https':
            signals['issues'].append('HSTS: not present on HTTPS site')
    
    # Cookie analysis
    if 'set-cookie' in headers_lower:
        cookie = headers_lower['set-cookie']
        signals['cookies']['present'] = True
        signals['cookies']['value'] = cookie
        signals['security_score'] += 10
        
        # Check for security flags
        cookie_lower = cookie.lower()
        signals['cookies']['secure'] = 'secure' in cookie_lower
        signals['cookies']['httponly'] = 'httponly' in cookie_lower
        signals['cookies']['samesite'] = 'samesite' in cookie_lower
        
        if not signals['cookies']['secure']:
            signals['issues'].append('Cookie: Secure flag not set')
            signals['security_score'] += 5
        if not signals['cookies']['httponly']:
            signals['issues'].append('Cookie: HttpOnly flag not set')
            signals['security_score'] += 5
        if not signals['cookies']['samesite']:
            signals['issues'].append('Cookie: SameSite flag not set')
    
    # Other interesting headers
    if 'www-authenticate' in headers_lower:
        signals['auth_required'] = True
        signals['auth_type'] = headers_lower['www-authenticate'].split()[0] if headers_lower['www-authenticate'] else 'unknown'
        signals['security_score'] += 20
    
    if 'x-frame-options' in headers_lower:
        signals['x_frame_options'] = headers_lower['x-frame-options']
    
    if 'x-content-type-options' in headers_lower:
        signals['x_content_type_options'] = headers_lower['x-content-type-options']
    
    return signals


def probe_url(url: str, client, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch URL headers and analyze them.
    
    Args:
        url: URL to probe
        client: HTTP client (e.g., requests.Session)
        timeout: Request timeout in seconds
        
    Returns:
        Analysis results dictionary or None if request fails
    """
    try:
        response = client.head(url, timeout=timeout, allow_redirects=True)
        return analyze_headers(url, dict(response.headers))
    except Exception:
        # Try GET if HEAD fails
        try:
            response = client.get(url, timeout=timeout, stream=True)
            # Don't download body
            response.close()
            return analyze_headers(url, dict(response.headers))
        except Exception:
            return None
