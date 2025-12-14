"""Harvest URLs from robots.txt disallowed paths."""
from __future__ import annotations
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from ..utils import safe_name


def harvest(target: str, client, out_dir) -> List[str]:
    """
    Fetch robots.txt and derive candidate URLs from disallowed paths.
    
    Args:
        target: Target URL or domain
        client: HTTP client (e.g., requests.Session)
        out_dir: Output directory path for saving raw data
        
    Returns:
        List of candidate URLs derived from robots.txt
    """
    urls = []
    
    # Normalize target to get base URL
    if not target.startswith(('http://', 'https://')):
        target = 'https://' + target
    
    parsed = urlparse(target)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base_url, '/robots.txt')
    
    try:
        response = client.get(robots_url, timeout=10)
        response.raise_for_status()
        
        # Save raw robots.txt
        if out_dir:
            raw_file = out_dir / f"raw_robots_{safe_name(parsed.netloc)}.txt"
            raw_file.write_text(response.text, encoding='utf-8')
        
        # Parse disallow directives
        for line in response.text.splitlines():
            line = line.strip()
            if line.lower().startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                if path and path != '/':
                    # Remove wildcards and convert to URL
                    path = path.replace('*', '')
                    if path.startswith('/'):
                        url = urljoin(base_url, path)
                        urls.append(url)
                        
    except Exception:
        # Silently fail - robots.txt may not exist
        pass
    
    return urls
