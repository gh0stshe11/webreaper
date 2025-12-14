from __future__ import annotations
from typing import List
from urllib.parse import urlparse

def parse_gospider_lines(output: str) -> List[str]:
    """Parse gospider output and return valid URLs.
    
    gospider outputs URLs in the format: [tag] URL
    Tags include: [url], [form], [javascript], [linkfinder], etc.
    
    Args:
        output: Raw text output from gospider
        
    Returns:
        List of validated URLs
    """
    urls: List[str] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # gospider output format: [tag] URL
        # Extract URL after the tag
        if line.startswith("["):
            # Find the closing bracket
            close_bracket = line.find("]")
            if close_bracket != -1 and close_bracket < len(line) - 1:
                # URL is after the closing bracket
                u = line[close_bracket + 1:].strip()
            else:
                continue
        else:
            u = line.strip()
        
        if not u or "://" not in u:
            continue
            
        try:
            p = urlparse(u)
        except Exception:
            continue
            
        if p.scheme and p.netloc:
            urls.append(p.geturl())
    
    return urls
