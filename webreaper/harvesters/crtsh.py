"""Query crt.sh to enumerate subdomains."""
from __future__ import annotations
from typing import List
from urllib.parse import urlparse
import json

from ..utils import safe_name


def harvest(target: str, client, out_dir) -> List[str]:
    """
    Query crt.sh to enumerate subdomains for the target domain.
    
    Args:
        target: Target URL or domain
        client: HTTP client (e.g., requests.Session)
        out_dir: Output directory path for saving raw data
        
    Returns:
        List of subdomain URLs discovered from SSL certificates
    """
    urls = []
    
    # Normalize target to get domain
    if target.startswith(('http://', 'https://')):
        parsed = urlparse(target)
        domain = parsed.netloc
        scheme = parsed.scheme
    else:
        domain = target.strip('/')
        scheme = 'https'
    
    # Remove port if present
    if ':' in domain:
        domain = domain.split(':')[0]
    
    # crt.sh JSON API endpoint
    crtsh_url = "https://crt.sh/"
    
    params = {
        'q': f"%.{domain}",
        'output': 'json'
    }
    
    try:
        response = client.get(crtsh_url, params=params, timeout=30)
        response.raise_for_status()
        
        # Save raw crt.sh output
        if out_dir:
            raw_file = out_dir / f"raw_crtsh_{safe_name(domain)}.json"
            raw_file.write_text(response.text, encoding='utf-8')
        
        # Parse JSON response
        try:
            data = json.loads(response.text)
            subdomains = set()
            
            for entry in data:
                if 'name_value' in entry:
                    # name_value can contain multiple domains separated by newlines
                    for name in entry['name_value'].split('\n'):
                        name = name.strip().lower()
                        # Skip wildcards and invalid entries
                        if name and '*' not in name and name.endswith(domain):
                            subdomains.add(name)
            
            # Convert subdomains to URLs
            for subdomain in sorted(subdomains):
                url = f"{scheme}://{subdomain}/"
                urls.append(url)
                
        except json.JSONDecodeError:
            pass
            
    except Exception:
        # Silently fail - crt.sh may be unavailable or have no data
        pass
    
    return urls
