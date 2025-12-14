"""Sitemap.xml harvester for webReaper."""
from __future__ import annotations
import re
from typing import List, Set
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


def parse_sitemap_xml(content: str) -> List[str]:
    """
    Parse sitemap.xml and extract URLs.
    
    Args:
        content: The content of sitemap.xml
    
    Returns:
        List of URLs from sitemap
    """
    urls: Set[str] = set()
    
    if not content:
        return []
    
    try:
        # Parse XML
        root = ET.fromstring(content)
        
        # Handle namespaces
        namespaces = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'xhtml': 'http://www.w3.org/1999/xhtml'
        }
        
        # Try with namespace first
        for url_elem in root.findall('.//sm:url/sm:loc', namespaces):
            if url_elem.text:
                urls.add(url_elem.text.strip())
        
        # Fallback: try without namespace
        if not urls:
            for url_elem in root.findall('.//url/loc'):
                if url_elem.text:
                    urls.add(url_elem.text.strip())
        
        # Handle sitemap index files
        for sitemap_elem in root.findall('.//sm:sitemap/sm:loc', namespaces):
            if sitemap_elem.text:
                urls.add(sitemap_elem.text.strip())
        
        if not urls:
            for sitemap_elem in root.findall('.//sitemap/loc'):
                if sitemap_elem.text:
                    urls.add(sitemap_elem.text.strip())
    
    except (ET.ParseError, Exception):
        # If XML parsing fails, try regex fallback
        url_pattern = re.compile(r'<loc>([^<]+)</loc>')
        matches = url_pattern.findall(content)
        for match in matches:
            urls.add(match.strip())
    
    return sorted(urls)


async def harvest_sitemap(client, base_url: str, timeout: int = 10) -> List[str]:
    """
    Fetch and parse sitemap.xml from a target.
    
    Args:
        client: httpx.AsyncClient instance
        base_url: The base URL of the target
        timeout: Request timeout in seconds
    
    Returns:
        List of discovered URLs from sitemap.xml
    """
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return []
    
    sitemap_urls = [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
    ]
    
    all_urls: Set[str] = set()
    
    for sitemap_url in sitemap_urls:
        try:
            response = await client.get(sitemap_url, timeout=timeout, follow_redirects=True)
            if response.status_code == 200:
                urls = parse_sitemap_xml(response.text)
                all_urls.update(urls)
        except Exception:
            pass
    
    return sorted(all_urls)
