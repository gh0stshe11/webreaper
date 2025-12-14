from __future__ import annotations
from typing import List
from urllib.parse import urlparse

def parse_hakrawler_lines(output: str) -> List[str]:
    """Parse hakrawler output and return valid URLs.
    
    hakrawler outputs URLs in plain text format, one per line.
    It may include some metadata lines that should be filtered out.
    
    Args:
        output: Raw text output from hakrawler
        
    Returns:
        List of validated URLs
    """
    urls: List[str] = []
    for line in output.splitlines():
        u = line.strip()
        
        # Skip empty lines
        if not u:
            continue
        
        # Skip lines that don't look like URLs
        if "://" not in u:
            continue
        
        # hakrawler sometimes outputs debugging info or metadata
        # Skip lines that start with common metadata patterns
        if u.startswith(("[", "Starting", "Finished", "Error", "Warning")):
            continue
        
        try:
            p = urlparse(u)
        except Exception:
            continue
            
        if p.scheme and p.netloc:
            urls.append(p.geturl())
    
    return urls
