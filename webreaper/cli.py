"""Click-based CLI for webReaper Phase A."""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import click
import requests

# Import harvesters
from .harvesters import robots, sitemap, wayback, crtsh

# Import probes
from .probes import headers, js_extractor

# Import storage
from .storage import raw_store

# Import existing modules
from .parsers.httpx import parse_httpx_jsonlines
from .parsers.katana import parse_katana_lines
from .parsers.gau import parse_gau_lines
from .scoring import compute_reapscore
from .paths_packs import generate_path_urls, list_packs as list_path_packs
from .report.render_md import write_report, write_eli5_report


@click.group()
@click.version_option(version="0.6.4")
def cli():
    """webReaper: harvest → probe → rank → report"""
    pass


@cli.command()
def packs():
    """List built-in path packs for --paths-pack."""
    for pack in list_path_packs():
        click.echo(pack)


@cli.command()
@click.argument('target')
@click.option('--sources', default='robots,sitemap,wayback,crtsh', 
              help='Comma-separated list of passive sources (robots,sitemap,wayback,crtsh)')
@click.option('--concurrency', default=5, type=int,
              help='Concurrency level for harvesters')
@click.option('--timeout', default=30, type=int,
              help='Timeout in seconds for HTTP requests')
@click.option('--user-agent', default='webReaper/0.6.4',
              help='User-Agent string for requests')
@click.option('--rate-limit', default=50, type=int,
              help='Rate limit in requests per second')
@click.option('--out-dir', '-o', default='out', type=click.Path(),
              help='Output directory')
@click.option('--resume', is_flag=True,
              help='Resume from cached data if available')
@click.option('--verbose', '-v', is_flag=True,
              help='Verbose output')
@click.option('--dry-run', is_flag=True,
              help='Dry run - show what would be done without executing')
@click.option('--active', is_flag=True,
              help='Enable active probing (default is passive only)')
@click.option('--min-score', default=0, type=int,
              help='Minimum ReapScore to include in report')
@click.option('--top', default=100, type=int,
              help='Limit report to top N results')
def reap(target, sources, concurrency, timeout, user_agent, rate_limit, 
         out_dir, resume, verbose, dry_run, active, min_score, top):
    """
    Harvest and analyze URLs from target using passive sources.
    
    TARGET: Domain or URL to analyze (e.g., example.com or https://example.com)
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    if verbose:
        click.secho(f"[+] webReaper Phase A", fg='cyan', bold=True)
        click.secho(f"[+] Target: {target}", fg='cyan')
        click.secho(f"[+] Output: {out_path}", fg='cyan')
        click.secho(f"[+] Sources: {sources}", fg='cyan')
        click.secho(f"[+] Mode: {'active' if active else 'passive'}", fg='cyan')
        if resume:
            click.secho(f"[+] Resume: enabled", fg='cyan')
        if dry_run:
            click.secho(f"[+] DRY RUN MODE", fg='yellow', bold=True)
    
    # Parse sources
    source_list = [s.strip() for s in sources.split(',') if s.strip()]
    
    # Create HTTP client
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})
    
    # Harvest URLs from each source
    all_urls = []
    url_sources = {}
    
    harvester_map = {
        'robots': robots,
        'sitemap': sitemap,
        'wayback': wayback,
        'crtsh': crtsh
    }
    
    for source_name in source_list:
        if source_name not in harvester_map:
            if verbose:
                click.secho(f"[!] Unknown source: {source_name}", fg='yellow')
            continue
        
        if verbose:
            click.secho(f"[+] Harvesting from {source_name}...", fg='green')
        
        # Check if we should resume
        if resume:
            cached_urls = raw_store.load_raw_data(out_path, source_name, target)
            if cached_urls is not None:
                if verbose:
                    click.secho(f"[+] Loaded {len(cached_urls)} URLs from cache", fg='green')
                for url in cached_urls:
                    if url not in url_sources:
                        url_sources[url] = set()
                    url_sources[url].add(source_name)
                all_urls.extend(cached_urls)
                continue
        
        if dry_run:
            if verbose:
                click.secho(f"[+] Would harvest from {source_name}", fg='blue')
            continue
        
        # Harvest
        try:
            start = time.time()
            harvester = harvester_map[source_name]
            urls = harvester.harvest(target, session, out_path)
            duration = time.time() - start
            
            # Save to cache
            raw_store.save_raw_data(out_path, source_name, target, urls)
            
            if verbose:
                click.secho(f"[+] {source_name}: {len(urls)} URLs ({duration:.2f}s)", fg='green')
            
            # Track sources
            for url in urls:
                if url not in url_sources:
                    url_sources[url] = set()
                url_sources[url].add(source_name)
            
            all_urls.extend(urls)
            
        except Exception as e:
            if verbose:
                click.secho(f"[!] Error harvesting from {source_name}: {e}", fg='red')
    
    # Deduplicate URLs
    unique_urls = list(dict.fromkeys(all_urls))
    
    if verbose:
        click.secho(f"[+] Total URLs harvested: {len(all_urls)} ({len(unique_urls)} unique)", fg='cyan')
    
    if dry_run:
        click.secho(f"[+] Dry run complete. Would process {len(unique_urls)} URLs.", fg='blue', bold=True)
        return
    
    # Passive enrichment - probe headers
    if verbose:
        click.secho(f"[+] Probing headers for security signals...", fg='green')
    
    enriched_data = []
    for i, url in enumerate(unique_urls[:top], 1):
        if verbose and i % 10 == 0:
            click.secho(f"[+] Probed {i}/{len(unique_urls[:top])} URLs", fg='blue')
        
        # Probe headers
        header_signals = headers.probe_url(url, session, timeout)
        
        # Analyze JS (if active mode)
        js_signals = None
        if active:
            js_signals = js_extractor.analyze_js(url, session, timeout)
        
        # Build enriched entry
        entry = {
            'url': url,
            'sources': sorted(url_sources.get(url, set())),
            'header_signals': header_signals,
            'js_signals': js_signals,
        }
        
        enriched_data.append(entry)
        
        # Rate limiting
        if rate_limit > 0:
            time.sleep(1.0 / rate_limit)
    
    # Score and rank
    if verbose:
        click.secho(f"[+] Scoring and ranking URLs...", fg='green')
    
    scored_results = []
    for entry in enriched_data:
        # Compute ReapScore
        header_sig = entry.get('header_signals') or {}
        security_score = header_sig.get('security_score', 0)
        
        # Build sources list
        sources_list = entry['sources']
        
        # Compute score (basic version for Phase A)
        reap = compute_reapscore(
            url=entry['url'],
            sources=sources_list,
            status=None,  # Not available in passive mode
            content_type=None,
            redirect_location=None,
            has_set_cookie=header_sig.get('cookies', {}).get('present', False),
            www_authenticate=header_sig.get('auth_required', False),
            response_time_ms=None,
            response_size_bytes=None,
            base_host=_base_host(target),
            unique_path=True,
        )
        
        # Boost score based on security signals
        adjusted_score = reap.score + (security_score // 5)
        adjusted_score = min(adjusted_score, 100)
        
        scored_entry = {
            'url': entry['url'],
            'sources': sources_list,
            'reap_score': adjusted_score,
            'reap_details': {
                'base_score': reap.score,
                'security_bonus': security_score // 5,
                'reasons': reap.reasons,
                'confidence': reap.confidence,
            },
            'header_signals': entry.get('header_signals'),
            'js_signals': entry.get('js_signals'),
        }
        
        if scored_entry['reap_score'] >= min_score:
            scored_results.append(scored_entry)
    
    # Sort by score descending
    scored_results.sort(key=lambda x: x['reap_score'], reverse=True)
    
    # Limit to top N
    scored_results = scored_results[:top]
    
    # Write output
    findings = {
        'target': target,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'profile': 'active' if active else 'passive',
        'sources': source_list,
        'summary': {
            'urls_total': len(all_urls),
            'urls_unique': len(unique_urls),
            'urls_scored': len(scored_results),
            'top_score': scored_results[0]['reap_score'] if scored_results else 0,
        },
        'results': scored_results,
    }
    
    findings_file = out_path / 'findings.json'
    findings_file.write_text(json.dumps(findings, indent=2), encoding='utf-8')
    
    if verbose:
        click.secho(f"[+] Wrote findings to {findings_file}", fg='green')
    
    # Write simple report
    report_file = out_path / 'REPORT.md'
    with report_file.open('w', encoding='utf-8') as f:
        f.write(f"# webReaper Report\n\n")
        f.write(f"**Target:** {target}\n\n")
        f.write(f"**Timestamp:** {findings['timestamp']}\n\n")
        f.write(f"**Profile:** {findings['profile']}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total URLs: {findings['summary']['urls_total']}\n")
        f.write(f"- Unique URLs: {findings['summary']['urls_unique']}\n")
        f.write(f"- Scored URLs: {findings['summary']['urls_scored']}\n")
        f.write(f"- Top Score: {findings['summary']['top_score']}\n\n")
        f.write(f"## Top Results\n\n")
        
        for i, result in enumerate(scored_results[:20], 1):
            f.write(f"### {i}. {result['url']}\n\n")
            f.write(f"- **ReapScore:** {result['reap_score']}\n")
            f.write(f"- **Sources:** {', '.join(result['sources'])}\n")
            f.write(f"- **Reasons:** {', '.join(result['reap_details']['reasons'][:5])}\n")
            
            if result.get('header_signals', {}).get('issues'):
                f.write(f"- **Security Issues:** {len(result['header_signals']['issues'])}\n")
            
            f.write("\n")
    
    if verbose:
        click.secho(f"[+] Wrote report to {report_file}", fg='green')
    
    click.secho(f"\n[✓] Done! Results in {out_path}/", fg='green', bold=True)
    if scored_results:
        click.secho(f"[✓] Top score: {scored_results[0]['reap_score']} - {scored_results[0]['url']}", fg='cyan')


def _base_host(target: str) -> str:
    """Extract base hostname from target."""
    if "://" not in target:
        return target.strip().strip("/")
    return urlparse(target).hostname or target


if __name__ == '__main__':
    cli()
