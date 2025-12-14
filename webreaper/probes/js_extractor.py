"""JavaScript extraction from HTML pages."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def extract_js_urls(html: str, base_url: str) -> List[str]:
    """
    Extract JavaScript URLs from HTML.
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative URLs
        
    Returns:
        List of JavaScript URLs found in the HTML
    """
    js_urls = []
    
    if BeautifulSoup is None:
        return js_urls
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all script tags with src attribute
        for script in soup.find_all('script', src=True):
            src = script.get('src', '').strip()
            if src:
                # Resolve relative URLs
                full_url = urljoin(base_url, src)
                js_urls.append(full_url)
        
    except Exception:
        pass
    
    return js_urls


def extract_inline_js(html: str) -> List[str]:
    """
    Extract inline JavaScript code blocks from HTML.
    
    Args:
        html: HTML content
        
    Returns:
        List of inline JavaScript code blocks
    """
    inline_scripts = []
    
    if BeautifulSoup is None:
        return inline_scripts
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all script tags without src attribute (inline scripts)
        for script in soup.find_all('script'):
            if not script.get('src'):
                code = script.string
                if code and code.strip():
                    inline_scripts.append(code.strip())
        
    except Exception:
        pass
    
    return inline_scripts


def extract_api_endpoints(html: str, js_code: str = "") -> List[str]:
    """
    Extract potential API endpoints from HTML and JavaScript.
    
    Args:
        html: HTML content
        js_code: JavaScript code to analyze
        
    Returns:
        List of potential API endpoints found
    """
    endpoints = []
    content = html + "\n" + js_code
    
    # Patterns for API endpoints
    patterns = [
        r'["\']/(api|v\d+|graphql|rest|endpoint)[^"\']*["\']',
        r'https?://[^"\']+/api[^"\']*',
        r'["\']/(admin|internal|private)[^"\']*["\']',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Clean up the match
            endpoint = match.strip('"\' ')
            if endpoint and endpoint not in endpoints:
                endpoints.append(endpoint)
    
    return endpoints


def extract_sensitive_patterns(html: str, js_code: str = "") -> Dict[str, List[str]]:
    """
    Extract sensitive patterns from HTML and JavaScript.
    
    Args:
        html: HTML content
        js_code: JavaScript code to analyze
        
    Returns:
        Dictionary with categories of sensitive patterns found
    """
    sensitive = {
        'api_keys': [],
        'tokens': [],
        'secrets': [],
        'credentials': []
    }
    
    content = html + "\n" + js_code
    
    # API key patterns
    api_key_patterns = [
        r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']{20,})["\']',
        r'apikey["\']?\s*[:=]\s*["\']([^"\']{20,})["\']',
    ]
    
    for pattern in api_key_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        sensitive['api_keys'].extend(matches)
    
    # Token patterns
    token_patterns = [
        r'token["\']?\s*[:=]\s*["\']([^"\']{20,})["\']',
        r'auth["\']?\s*[:=]\s*["\']([^"\']{20,})["\']',
    ]
    
    for pattern in token_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        sensitive['tokens'].extend(matches)
    
    # AWS-style keys
    aws_pattern = r'AKIA[0-9A-Z]{16}'
    sensitive['api_keys'].extend(re.findall(aws_pattern, content))
    
    return sensitive


def analyze_js(url: str, client, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch HTML and analyze JavaScript content.
    
    Args:
        url: URL to analyze
        client: HTTP client (e.g., requests.Session)
        timeout: Request timeout in seconds
        
    Returns:
        Analysis results dictionary or None if request fails
    """
    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
        
        html = response.text
        
        # Extract JavaScript URLs
        js_urls = extract_js_urls(html, url)
        
        # Extract inline JavaScript
        inline_scripts = extract_inline_js(html)
        
        # Combine all JS code for analysis
        all_js = "\n".join(inline_scripts)
        
        # Extract API endpoints
        endpoints = extract_api_endpoints(html, all_js)
        
        # Extract sensitive patterns
        sensitive = extract_sensitive_patterns(html, all_js)
        
        return {
            'url': url,
            'js_urls': js_urls,
            'inline_script_count': len(inline_scripts),
            'api_endpoints': endpoints,
            'sensitive_patterns': sensitive,
            'js_score': _calculate_js_score(js_urls, inline_scripts, endpoints, sensitive)
        }
        
    except Exception:
        return None


def _calculate_js_score(js_urls: List[str], inline_scripts: List[str], 
                        endpoints: List[str], sensitive: Dict[str, List[str]]) -> int:
    """Calculate a score based on JavaScript findings."""
    score = 0
    
    score += min(len(js_urls) * 2, 20)  # External JS files
    score += min(len(inline_scripts) * 3, 30)  # Inline scripts
    score += min(len(endpoints) * 5, 25)  # API endpoints found
    
    # Sensitive patterns are high value
    for category, items in sensitive.items():
        if items:
            score += 25
    
    return min(score, 100)
