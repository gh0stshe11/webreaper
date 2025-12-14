"""Harvest URLs from sitemap.xml."""
from __future__ import annotations
from typing import List
from urllib.parse import urljoin, urlparse
import re
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def harvest(target: str, client, out_dir) -> List[str]:
    """
    Parse sitemap.xml and yield URLs.
    
    Args:
        target: Target URL or domain
        client: HTTP client (e.g., requests.Session)
        out_dir: Output directory path for saving raw data
        
    Returns:
        List of URLs from sitemap.xml
    """
    urls = []
    
    if BeautifulSoup is None:
        return urls
    
    # Normalize target to get base URL
    if not target.startswith(('http://', 'https://')):
        target = 'https://' + target
    
    parsed = urlparse(target)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    sitemap_url = urljoin(base_url, '/sitemap.xml')
    
    try:
        response = client.get(sitemap_url, timeout=10)
        response.raise_for_status()
        
        # Save raw sitemap.xml
        if out_dir:
            raw_file = out_dir / f"raw_sitemap_{_safe_name(parsed.netloc)}.xml"
            raw_file.write_text(response.text, encoding='utf-8')
        
        # Parse sitemap XML
        soup = BeautifulSoup(response.text, 'lxml-xml')
        
        # Extract URLs from <loc> tags
        for loc in soup.find_all('loc'):
            url = loc.get_text().strip()
            if url:
                urls.append(url)
        
        # Handle sitemap index files
        for sitemap in soup.find_all('sitemap'):
            loc = sitemap.find('loc')
            if loc:
                sitemap_url = loc.get_text().strip()
                if sitemap_url:
                    # Recursively fetch nested sitemaps
                    try:
                        nested = client.get(sitemap_url, timeout=10)
                        nested.raise_for_status()
                        nested_soup = BeautifulSoup(nested.text, 'lxml-xml')
                        for nested_loc in nested_soup.find_all('loc'):
                            url = nested_loc.get_text().strip()
                            if url:
                                urls.append(url)
                    except Exception:
                        pass
                        
    except Exception as e:
        # Silently fail - sitemap.xml may not exist
        pass
    
    return urls


def _safe_name(s: str) -> str:
    """Convert string to safe filename."""
    return re.sub(r'[^a-zA-Z0-9._-]+', '_', s)[:90]
