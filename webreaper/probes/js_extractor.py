"""JavaScript endpoint extraction probe for webReaper."""
from __future__ import annotations
import re
from typing import List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def extract_endpoints_from_js(js_content: str, base_url: str) -> List[str]:
    """
    Extract API endpoints and URLs from JavaScript content.
    
    Args:
        js_content: JavaScript source code
        base_url: Base URL for resolving relative URLs
    
    Returns:
        List of discovered endpoints
    """
    endpoints: Set[str] = set()
    
    # Pattern 1: String literals that look like URLs or paths
    # Matches strings like "/api/users", "/v1/endpoint", etc.
    path_pattern = re.compile(r'''['"](/[a-zA-Z0-9/_\-\.]+)['"]''')
    for match in path_pattern.finditer(js_content):
        path = match.group(1)
        # Filter out common non-endpoint paths
        if any(ext in path.lower() for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.svg', '.ico']):
            continue
        if len(path) > 3 and '/' in path:
            endpoints.add(path)
    
    # Pattern 2: Full URLs in strings
    url_pattern = re.compile(r'''['"]((https?://[^'"]+))['"]''')
    for match in url_pattern.finditer(js_content):
        url = match.group(1)
        endpoints.add(url)
    
    # Pattern 3: fetch() and XMLHttpRequest patterns
    # fetch('/api/endpoint')
    fetch_pattern = re.compile(r'''fetch\s*\(\s*['"](https?://[^'"]+|/[^'"]+)['"]''')
    for match in fetch_pattern.finditer(js_content):
        endpoint = match.group(1)
        endpoints.add(endpoint)
    
    # Pattern 4: jQuery AJAX patterns
    # $.ajax({url: '/api/endpoint'})
    ajax_pattern = re.compile(r'''url\s*:\s*['"](https?://[^'"]+|/[^'"]+)['"]''')
    for match in ajax_pattern.finditer(js_content):
        endpoint = match.group(1)
        endpoints.add(endpoint)
    
    # Pattern 5: axios patterns
    # axios.get('/api/endpoint')
    axios_pattern = re.compile(r'''axios\.[a-z]+\s*\(\s*['"](https?://[^'"]+|/[^'"]+)['"]''')
    for match in axios_pattern.finditer(js_content):
        endpoint = match.group(1)
        endpoints.add(endpoint)
    
    # Convert relative paths to absolute URLs
    result = []
    for endpoint in endpoints:
        if endpoint.startswith('/'):
            full_url = urljoin(base_url, endpoint)
            result.append(full_url)
        elif endpoint.startswith('http://') or endpoint.startswith('https://'):
            result.append(endpoint)
    
    return result


async def extract_js_endpoints(client, url: str, timeout: int = 10) -> List[str]:
    """
    Fetch HTML, extract script tags, fetch JS files, and extract endpoints.
    
    Args:
        client: httpx.AsyncClient instance
        url: The URL to analyze
        timeout: Request timeout in seconds
    
    Returns:
        List of discovered endpoints from JavaScript
    """
    all_endpoints: Set[str] = set()
    
    try:
        # Fetch the main page
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        if response.status_code != 200:
            return []
        
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type.lower():
            return []
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all script tags
        script_tags = soup.find_all('script')
        
        # Extract inline scripts
        for script in script_tags:
            if script.string:
                endpoints = extract_endpoints_from_js(script.string, url)
                all_endpoints.update(endpoints)
        
        # Extract external scripts
        js_urls: Set[str] = set()
        for script in script_tags:
            src = script.get('src')
            if src:
                # Resolve relative URLs
                js_url = urljoin(url, src)
                js_urls.add(js_url)
        
        # Fetch and analyze external JS files (limit to avoid DoS)
        for js_url in list(js_urls)[:20]:  # Limit to 20 JS files
            try:
                js_response = await client.get(js_url, timeout=timeout, follow_redirects=True)
                if js_response.status_code == 200:
                    endpoints = extract_endpoints_from_js(js_response.text, url)
                    all_endpoints.update(endpoints)
            except Exception:
                pass  # Skip failed JS fetches
    
    except Exception:
        pass
    
    return sorted(all_endpoints)
