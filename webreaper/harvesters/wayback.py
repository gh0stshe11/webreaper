"""Query Wayback Machine CDX API for historical URLs."""
from __future__ import annotations
from typing import List
from urllib.parse import urlparse, quote
import re


def harvest(target: str, client, out_dir) -> List[str]:
    """
    Query Wayback CDX API for historical URLs for the target.
    
    Args:
        target: Target URL or domain
        client: HTTP client (e.g., requests.Session)
        out_dir: Output directory path for saving raw data
        
    Returns:
        List of historical URLs from Wayback Machine
    """
    urls = []
    
    # Normalize target to get domain
    if target.startswith(('http://', 'https://')):
        parsed = urlparse(target)
        domain = parsed.netloc
    else:
        domain = target.strip('/')
    
    # Wayback CDX API endpoint
    cdx_url = f"https://web.archive.org/cdx/search/cdx"
    
    params = {
        'url': f"{domain}/*",
        'matchType': 'prefix',
        'collapse': 'urlkey',
        'output': 'text',
        'fl': 'original',
        'limit': 1000,
    }
    
    try:
        response = client.get(cdx_url, params=params, timeout=30)
        response.raise_for_status()
        
        # Save raw CDX output
        if out_dir:
            raw_file = out_dir / f"raw_wayback_{_safe_name(domain)}.txt"
            raw_file.write_text(response.text, encoding='utf-8')
        
        # Parse CDX output - each line is a URL
        for line in response.text.splitlines():
            url = line.strip()
            if url and url.startswith(('http://', 'https://')):
                urls.append(url)
                
    except Exception as e:
        # Silently fail - Wayback API may be unavailable
        pass
    
    return urls


def _safe_name(s: str) -> str:
    """Convert string to safe filename."""
    return re.sub(r'[^a-zA-Z0-9._-]+', '_', s)[:90]
