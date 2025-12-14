"""crt.sh certificate transparency log harvester for webReaper."""
from __future__ import annotations
import json
from typing import List, Set
from urllib.parse import quote, urlparse


async def harvest_crtsh(client, domain: str, timeout: int = 20) -> List[str]:
    """
    Query crt.sh for certificate entries and discover subdomains.
    
    Args:
        client: httpx.AsyncClient instance
        domain: The target domain
        timeout: Request timeout in seconds
    
    Returns:
        List of discovered subdomains
    """
    subdomains: Set[str] = set()
    
    # Clean domain - extract from URL if needed
    if "://" in domain:
        parsed = urlparse(domain)
        domain = parsed.netloc or domain
    
    domain = domain.strip()
    
    # Build crt.sh API URL
    # Format: https://crt.sh/?q=%25.{domain}&output=json
    crtsh_url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
    
    try:
        response = await client.get(crtsh_url, timeout=timeout, follow_redirects=True)
        if response.status_code == 200:
            try:
                data = response.json()
            except json.JSONDecodeError:
                return []
            
            if not isinstance(data, list):
                return []
            
            # Extract common_name and name_value fields
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                
                # Get common_name
                common_name = entry.get("common_name", "")
                if common_name:
                    subdomains.add(common_name.strip())
                
                # Get name_value (can be multi-line with multiple domains)
                name_value = entry.get("name_value", "")
                if name_value:
                    for line in name_value.split("\n"):
                        line = line.strip()
                        if line:
                            subdomains.add(line)
            
            # Clean up wildcards and duplicates
            cleaned = set()
            for subdomain in subdomains:
                # Remove wildcards
                subdomain = subdomain.replace("*.", "")
                subdomain = subdomain.strip()
                
                # Basic validation
                if subdomain and "." in subdomain and " " not in subdomain:
                    cleaned.add(subdomain)
            
            return sorted(cleaned)
    
    except Exception:
        pass
    
    return []
