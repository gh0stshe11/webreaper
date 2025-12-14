"""Main controller orchestrating webReaper operations."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urlparse, parse_qs
import httpx

from ..storage.raw_store import RawStore
from ..harvesters.robots import harvest_robots
from ..harvesters.sitemap import harvest_sitemap
from ..harvesters.wayback import harvest_wayback
from ..harvesters.crtsh import harvest_crtsh
from ..probes.headers import probe_headers
from ..probes.js_extractor import extract_js_endpoints
from ..scoring.reapscore import compute_reapscore
from ..output.exporters import export_findings


class WebReaperController:
    """Main controller for webReaper operations."""
    
    def __init__(
        self,
        target: str,
        out_dir: Path,
        *,
        sources: List[str] = None,
        concurrency: int = 10,
        timeout: int = 10,
        user_agent: str = None,
        rate_limit: Optional[int] = None,
        resume: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
        active: bool = False,
        min_score: float = 0.0,
        top: int = 50,
    ):
        """Initialize controller."""
        self.target = target
        self.out_dir = Path(out_dir)
        self.sources = sources or ["robots", "sitemap", "wayback", "crtsh"]
        self.concurrency = concurrency
        self.timeout = timeout
        self.user_agent = user_agent or "webReaper/0.6.4 (https://github.com/gh0stshe11/webreaper)"
        self.rate_limit = rate_limit
        self.resume = resume
        self.verbose = verbose
        self.dry_run = dry_run
        self.active = active
        self.min_score = min_score
        self.top = top
        
        self.store = RawStore(self.out_dir)
        self.semaphore = asyncio.Semaphore(concurrency)
    
    def log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[webReaper] {message}")
    
    async def rate_limit_delay(self) -> None:
        """Apply rate limiting if configured."""
        if self.rate_limit:
            await asyncio.sleep(1.0 / self.rate_limit)
    
    async def harvest(self, client: httpx.AsyncClient) -> Dict[str, List[str]]:
        """
        Run all harvesters and collect URLs.
        
        Returns:
            Dictionary mapping source name to list of URLs
        """
        results = {}
        
        # Robots.txt
        if "robots" in self.sources:
            if self.store.should_skip("robots", self.resume):
                self.log("Skipping robots.txt (resume mode)")
                results["robots"] = self.store.load("robots") or []
            else:
                self.log("Harvesting robots.txt...")
                urls = await harvest_robots(client, self.target, self.timeout)
                self.store.save("robots", urls)
                results["robots"] = urls
                self.log(f"Found {len(urls)} URLs from robots.txt")
        
        # Sitemap.xml
        if "sitemap" in self.sources:
            if self.store.should_skip("sitemap", self.resume):
                self.log("Skipping sitemap.xml (resume mode)")
                results["sitemap"] = self.store.load("sitemap") or []
            else:
                self.log("Harvesting sitemap.xml...")
                urls = await harvest_sitemap(client, self.target, self.timeout)
                self.store.save("sitemap", urls)
                results["sitemap"] = urls
                self.log(f"Found {len(urls)} URLs from sitemap.xml")
        
        # Wayback Machine
        if "wayback" in self.sources:
            if self.store.should_skip("wayback", self.resume):
                self.log("Skipping Wayback Machine (resume mode)")
                results["wayback"] = self.store.load("wayback") or []
            else:
                self.log("Harvesting Wayback Machine...")
                urls = await harvest_wayback(client, self.target, timeout=30)
                self.store.save("wayback", urls)
                results["wayback"] = urls
                self.log(f"Found {len(urls)} URLs from Wayback Machine")
        
        # crt.sh
        if "crtsh" in self.sources:
            if self.store.should_skip("crtsh", self.resume):
                self.log("Skipping crt.sh (resume mode)")
                results["crtsh"] = self.store.load("crtsh") or []
            else:
                self.log("Harvesting crt.sh...")
                subdomains = await harvest_crtsh(client, self.target, timeout=20)
                self.store.save("crtsh", subdomains)
                results["crtsh"] = subdomains
                self.log(f"Found {len(subdomains)} subdomains from crt.sh")
        
        return results
    
    async def probe_endpoint(
        self,
        client: httpx.AsyncClient,
        url: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """
        Probe a single endpoint with headers and JS extraction.
        
        Returns:
            Dictionary with endpoint data
        """
        async with self.semaphore:
            await self.rate_limit_delay()
            
            endpoint_data = {
                "url": url,
                "sources": sources,
                "status_code": None,
                "tech_stack": [],
                "header_analysis": None,
                "js_endpoints": [],
            }
            
            try:
                # Basic request
                response = await client.get(url, timeout=self.timeout, follow_redirects=True)
                endpoint_data["status_code"] = response.status_code
                
                # Header analysis
                header_analysis = await probe_headers(client, url, self.timeout)
                endpoint_data["header_analysis"] = header_analysis.to_dict()
                
                # JS endpoint extraction (only for HTML pages)
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type.lower():
                    js_endpoints = await extract_js_endpoints(client, url, self.timeout)
                    endpoint_data["js_endpoints"] = js_endpoints
            
            except Exception as e:
                self.log(f"Error probing {url}: {e}")
            
            return endpoint_data
    
    async def run(self) -> Dict[str, Any]:
        """
        Run the complete webReaper workflow.
        
        Returns:
            Findings dictionary
        """
        if self.dry_run:
            self.log("DRY RUN MODE - No actual requests will be made")
            return {
                "target": self.target,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dry_run": True,
                "endpoints": [],
            }
        
        # Create HTTP client (SSL verification disabled for reconnaissance)
        # WARNING: SSL verification is disabled to avoid certificate issues during recon
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(headers=headers, verify=False) as client:
            # Step 1: Harvest URLs
            self.log("Starting harvest phase...")
            harvest_results = await self.harvest(client)
            
            # Collect all URLs
            all_urls: Set[str] = set()
            url_to_sources: Dict[str, List[str]] = {}
            
            # Add seed target
            all_urls.add(self.target)
            url_to_sources[self.target] = ["seed"]
            
            # Add harvested URLs
            for source, urls in harvest_results.items():
                for url in urls:
                    all_urls.add(url)
                    if url not in url_to_sources:
                        url_to_sources[url] = []
                    url_to_sources[url].append(source)
            
            # Convert crt.sh subdomains to URLs
            if "crtsh" in harvest_results:
                for subdomain in harvest_results["crtsh"]:
                    # Try both http and https
                    for scheme in ["https", "http"]:
                        url = f"{scheme}://{subdomain}"
                        all_urls.add(url)
                        if url not in url_to_sources:
                            url_to_sources[url] = []
                        if "crtsh" not in url_to_sources[url]:
                            url_to_sources[url].append("crtsh")
            
            self.log(f"Total URLs to probe: {len(all_urls)}")
            
            # Step 2: Probe endpoints
            if not self.active:
                self.log("Active probing disabled - skipping detailed probes")
                endpoints = []
            else:
                self.log("Starting probe phase...")
                probe_tasks = [
                    self.probe_endpoint(client, url, url_to_sources.get(url, []))
                    for url in all_urls
                ]
                endpoints = await asyncio.gather(*probe_tasks)
            
            # Step 3: Score endpoints
            self.log("Scoring endpoints...")
            scored_endpoints = []
            
            for endpoint in endpoints:
                url = endpoint["url"]
                sources = endpoint.get("sources", [])
                status_code = endpoint.get("status_code")
                header_analysis = endpoint.get("header_analysis", {})
                js_endpoints = endpoint.get("js_endpoints", [])
                
                # Extract URL features
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query or "", keep_blank_values=True)
                param_names = list(query_params.keys())
                
                # High-value parameter names
                high_value_params = [
                    p for p in param_names
                    if p.lower() in {"id", "user", "token", "auth", "redirect", "url", "file", "path"}
                ]
                
                # Path keywords
                path_lower = (parsed.path or "").lower()
                has_auth_keywords = any(
                    kw in path_lower
                    for kw in ["login", "signin", "auth", "admin", "oauth", "sso"]
                )
                has_api_keywords = any(
                    kw in path_lower
                    for kw in ["api", "graphql", "rest", "v1", "v2", "v3"]
                )
                
                # Compute ReapScore
                reapscore = compute_reapscore(
                    url=url,
                    sources=sources,
                    status_code=status_code,
                    has_params=bool(query_params),
                    param_count=len(param_names),
                    high_value_params=high_value_params,
                    path_depth=len([p for p in parsed.path.split("/") if p]),
                    has_auth_keywords=has_auth_keywords,
                    has_api_keywords=has_api_keywords,
                    header_signals=header_analysis.get("signals", []) if header_analysis else [],
                    js_endpoints_found=len(js_endpoints),
                )
                
                # Filter by min_score
                if reapscore.score >= self.min_score:
                    scored_endpoints.append({
                        **endpoint,
                        "reapscore": reapscore.to_dict(),
                    })
            
            self.log(f"Scored {len(scored_endpoints)} endpoints (min_score={self.min_score})")
            
            # Step 4: Build findings
            findings = {
                "target": self.target,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "config": {
                    "sources": self.sources,
                    "concurrency": self.concurrency,
                    "timeout": self.timeout,
                    "rate_limit": self.rate_limit,
                    "min_score": self.min_score,
                    "top": self.top,
                    "active": self.active,
                },
                "summary": {
                    "total_endpoints": len(scored_endpoints),
                    "unique_urls": len(set(e["url"] for e in scored_endpoints)),
                    "top_score": max((e["reapscore"]["score"] for e in scored_endpoints), default=0.0),
                },
                "endpoints": scored_endpoints,
            }
            
            # Step 5: Export findings
            self.log("Exporting findings...")
            export_findings(findings, self.out_dir, top_n=self.top)
            
            self.log("Done!")
            return findings
