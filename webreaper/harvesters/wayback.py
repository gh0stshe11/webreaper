"""Wayback Machine CDX API harvester for webReaper."""
from __future__ import annotations
import json
from typing import List, Set
from urllib.parse import quote


async def harvest_wayback(client, target: str, timeout: int = 30) -> List[str]:
    """
    Query Wayback Machine CDX API for historical URLs.
    
    Args:
        client: httpx.AsyncClient instance
        target: The target domain or URL
        timeout: Request timeout in seconds
    
    Returns:
        List of discovered historical URLs
    """
    urls: Set[str] = set()
    
    # Clean target - extract domain if it's a URL
    if "://" in target:
        from urllib.parse import urlparse
        parsed = urlparse(target)
        domain = parsed.netloc or target
    else:
        domain = target.strip()
    
    # Build CDX API URL
    # Format: https://web.archive.org/cdx/search/cdx?url={target}&output=json&fl=original&collapse=urlkey
    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url={quote(domain)}"
        f"&output=json"
        f"&fl=original"
        f"&collapse=urlkey"
    )
    
    try:
        response = await client.get(cdx_url, timeout=timeout, follow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            
            # CDX API returns JSON array where first row is headers
            # Format: [["original"], ["url1"], ["url2"], ...]
            if isinstance(data, list) and len(data) > 1:
                for row in data[1:]:  # Skip header row
                    if isinstance(row, list) and len(row) > 0:
                        url = row[0]
                        if url and isinstance(url, str):
                            # Basic URL validation
                            if url.startswith(("http://", "https://")):
                                urls.add(url)
    
    except Exception:
        pass
    
    return sorted(urls)
