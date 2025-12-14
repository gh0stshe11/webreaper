"""
Robots.txt and Sitemap.xml discovery tool.

This tool fetches and parses robots.txt and sitemap.xml files to discover
additional endpoints that may not be linked from the main site.
"""

from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

from .registry import DiscoveryTool, ToolMetadata, ToolCategory


class RobotsSitemapTool(DiscoveryTool):
    """
    Discovers URLs from robots.txt and sitemap.xml files.
    
    This tool:
    1. Fetches /robots.txt and extracts Sitemap directives and Disallow paths
    2. Recursively parses sitemap.xml files (including sitemap indexes)
    3. Returns discovered URLs that can be probed
    
    Contribution to ReapScore:
    - Adds "robots" and "sitemap" as sources for HarvestIndex
    - Disallowed paths often indicate sensitive/interesting endpoints
    """
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="robots_sitemap",
            category=ToolCategory.DISCOVERY,
            description="Discovers URLs from robots.txt and sitemap.xml files",
            version="1.0.0",
            enabled_by_default=True,
            requires_external_binary=False,
        )
    
    def discover(self, target: str, **kwargs) -> List[str]:
        """
        Discover URLs from robots.txt and sitemaps.
        
        Args:
            target: Base URL to scan
            **kwargs: Optional parameters:
                - robots_content: Pre-fetched robots.txt content
                - sitemap_contents: Dict of sitemap URL -> content
                - max_sitemaps: Maximum number of sitemaps to parse (default: 10)
                
        Returns:
            List of discovered URLs
        """
        # Note: This is a parser-only implementation
        # Actual HTTP fetching should be done by the caller (httpx)
        # to maintain consistency with webReaper's architecture
        
        discovered: Set[str] = set()
        base_url = self._normalize_url(target)
        
        # Parse robots.txt if provided
        robots_content = kwargs.get("robots_content", "")
        if robots_content:
            discovered.update(self._parse_robots(base_url, robots_content))
        
        # Parse sitemaps if provided
        sitemap_contents = kwargs.get("sitemap_contents", {})
        max_sitemaps = kwargs.get("max_sitemaps", 10)
        
        sitemap_urls = self._extract_sitemap_urls_from_robots(robots_content)
        if not sitemap_urls:
            # Try default sitemap.xml location
            sitemap_urls.add(urljoin(base_url, "/sitemap.xml"))
        
        parsed_count = 0
        for sitemap_url in sitemap_urls:
            if parsed_count >= max_sitemaps:
                break
            
            sitemap_content = sitemap_contents.get(sitemap_url, "")
            if sitemap_content:
                urls = self._parse_sitemap(sitemap_content)
                discovered.update(urls)
                parsed_count += 1
        
        return list(discovered)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize target URL to base URL with scheme."""
        if "://" not in url:
            url = "http://" + url
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _parse_robots(self, base_url: str, content: str) -> Set[str]:
        """
        Parse robots.txt and extract URLs from Disallow and Allow directives.
        
        Args:
            base_url: Base URL of the target
            content: robots.txt content
            
        Returns:
            Set of discovered URLs
        """
        urls: Set[str] = set()
        
        for line in content.splitlines():
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Extract Disallow and Allow paths
            # Format: "Disallow: /path" or "Allow: /path"
            if line.lower().startswith(("disallow:", "allow:")):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    path = parts[1].strip()
                    
                    # Skip wildcards and empty disallows
                    if not path or path == "/" or "*" in path:
                        continue
                    
                    # Remove end-of-line comments
                    if "#" in path:
                        path = path.split("#")[0].strip()
                    
                    # Build full URL
                    if path.startswith("/"):
                        full_url = urljoin(base_url, path)
                        urls.add(full_url)
        
        return urls
    
    def _extract_sitemap_urls_from_robots(self, content: str) -> Set[str]:
        """
        Extract Sitemap URLs from robots.txt.
        
        Args:
            content: robots.txt content
            
        Returns:
            Set of sitemap URLs
        """
        sitemap_urls: Set[str] = set()
        
        for line in content.splitlines():
            line = line.strip()
            
            # Extract Sitemap directives
            # Format: "Sitemap: http://example.com/sitemap.xml"
            if line.lower().startswith("sitemap:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    sitemap_url = parts[1].strip()
                    
                    # Handle URLs without scheme
                    if sitemap_url and "://" in sitemap_url:
                        sitemap_urls.add(sitemap_url)
        
        return sitemap_urls
    
    def _parse_sitemap(self, content: str) -> Set[str]:
        """
        Parse sitemap XML and extract URLs.
        
        Handles both regular sitemaps and sitemap indexes.
        
        Args:
            content: XML content of the sitemap
            
        Returns:
            Set of discovered URLs
        """
        urls: Set[str] = set()
        
        try:
            root = ET.fromstring(content)
            
            # Handle both namespaced and non-namespaced XML
            # Common namespaces: http://www.sitemaps.org/schemas/sitemap/0.9
            
            # Try to find <loc> tags which contain URLs
            # Works for both <url><loc> and <sitemap><loc> structures
            for loc in root.iter():
                if loc.tag.endswith("}loc") or loc.tag == "loc":
                    url = (loc.text or "").strip()
                    if url and "://" in url:
                        urls.add(url)
        
        except ET.ParseError:
            # If XML parsing fails, try regex fallback
            # This handles malformed XML or plain text sitemaps
            url_pattern = r'<loc>([^<]+)</loc>'
            matches = re.findall(url_pattern, content, re.IGNORECASE)
            for url in matches:
                url = url.strip()
                if url and "://" in url:
                    urls.add(url)
        
        return urls


def parse_robots_txt(base_url: str, content: str) -> List[str]:
    """
    Standalone function to parse robots.txt content.
    
    Args:
        base_url: Base URL of the target
        content: robots.txt file content
        
    Returns:
        List of discovered URLs from Disallow/Allow directives
    """
    tool = RobotsSitemapTool()
    return tool.discover(base_url, robots_content=content)


def parse_sitemap_xml(content: str) -> List[str]:
    """
    Standalone function to parse sitemap.xml content.
    
    Args:
        content: Sitemap XML content
        
    Returns:
        List of discovered URLs
    """
    tool = RobotsSitemapTool()
    return list(tool._parse_sitemap(content))
