"""Robots.txt harvester for webReaper."""
from __future__ import annotations
import re
from typing import List, Set
from urllib.parse import urljoin, urlparse


def parse_robots_txt(content: str, base_url: str) -> List[str]:
    """
    Parse robots.txt and extract disallowed paths as candidate URLs.
    
    Args:
        content: The content of robots.txt
        base_url: The base URL of the target
    
    Returns:
        List of candidate URLs derived from disallowed paths
    """
    urls: Set[str] = set()
    
    if not content:
        return []
    
    # Parse base URL
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return []
    
    base = f"{parsed.scheme}://{parsed.netloc}"
    
    # Extract Disallow and Allow directives
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        
        # Look for Disallow or Allow directives
        if line.lower().startswith("disallow:") or line.lower().startswith("allow:"):
            # Extract the path
            _, _, path = line.partition(":")
            path = path.strip()
            
            # Skip wildcards and empty paths
            if not path or path == "/" or "*" in path:
                continue
            
            # Remove fragment and clean up
            path = path.split("#")[0].strip()
            
            # Build full URL
            if path.startswith("/"):
                full_url = base + path
                urls.add(full_url)
    
    return sorted(urls)


async def harvest_robots(client, base_url: str, timeout: int = 10) -> List[str]:
    """
    Fetch and parse robots.txt from a target.
    
    Args:
        client: httpx.AsyncClient instance
        base_url: The base URL of the target
        timeout: Request timeout in seconds
    
    Returns:
        List of discovered URLs from robots.txt
    """
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return []
    
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    try:
        response = await client.get(robots_url, timeout=timeout, follow_redirects=True)
        if response.status_code == 200:
            content = response.text
            return parse_robots_txt(content, base_url)
    except Exception:
        pass
    
    return []
