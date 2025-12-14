from __future__ import annotations
import json
import subprocess
import time
import re
import sys
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime

import typer

from .parsers.httpx import parse_httpx_jsonlines
from .parsers.katana import parse_katana_lines
from .parsers.gau import parse_gau_lines
from .parsers.gospider import parse_gospider_lines
from .parsers.hakrawler import parse_hakrawler_lines
from .scoring import compute_reapscore
from .paths_packs import generate_path_urls, list_packs as list_path_packs
from .report.render_md import write_report, write_eli5_report
from .dependency_checker import check_dependencies, check_tool
from .tools.robots_sitemap import parse_robots_txt, parse_sitemap_xml

app = typer.Typer(add_completion=False, help="webReaper: harvest → probe → rank → report")

def _log(outdir: Path, msg: str) -> None:
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / "run.log"
        ts = datetime.utcnow().isoformat() + "Z"
        with p.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg.rstrip()}\n")
    except Exception:
        pass

def _stage(outdir: Path, label: str, *, quiet: bool, verbose: bool) -> None:
    line = f"→ {label}"
    _log(outdir, line)
    if (not quiet) and verbose:
        typer.secho(line, fg=typer.colors.CYAN, bold=True)

def banner(*, quiet: bool) -> None:
    if quiet or not sys.stdout.isatty():
        return

    typer.secho("  w e b R e a p e r", fg=typer.colors.WHITE, bold=True)
    typer.secho("        ╱╲", fg=typer.colors.BRIGHT_BLACK)
    typer.secho("       ╱  ╲", fg=typer.colors.BRIGHT_BLACK)

    typer.secho("  probe ", fg=typer.colors.WHITE, nl=False)
    typer.secho("→", fg=typer.colors.RED, nl=False, bold=True)
    typer.secho(" harvest ", fg=typer.colors.WHITE, nl=False)
    typer.secho("→", fg=typer.colors.RED, nl=False, bold=True)
    typer.secho(" rank ", fg=typer.colors.WHITE, nl=False)
    typer.secho("→", fg=typer.colors.BLUE, nl=False, bold=True)
    typer.secho(" report", fg=typer.colors.WHITE)

    typer.secho("          ╲", fg=typer.colors.RED, bold=True)
    typer.echo("")

def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:90]

def _run(cmd: List[str], *, input_text: Optional[str] = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, timeout=timeout)

def _base_host(target: str) -> str:
    if "://" not in target:
        return target.strip().strip("/")
    return urlparse(target).hostname or target

def _normalize_target_for_katana(t: str) -> str:
    return t if "://" in t else "http://" + t.strip("/")

def _csv_set(val: Optional[str]) -> Set[str]:
    if not val:
        return set()
    return {c.strip() for c in val.split(",") if c.strip()}

def _csv_list(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [c.strip() for c in val.split(",") if c.strip()]

def _host_in_scope(host: str, scope_hosts: Set[str], allow_subdomains: bool) -> bool:
    if not scope_hosts:
        return True
    h = (host or "").lower()
    for s in scope_hosts:
        s = s.lower()
        if h == s:
            return True
        if allow_subdomains and h.endswith("." + s):
            return True
    return False

def _filter_url(
    url: str,
    *,
    scope_hosts: Set[str],
    allow_subdomains: bool,
    exclude_hosts: Set[str],
    include_path_tokens: List[str],
    exclude_path_tokens: List[str],
    exclude_exts: Set[str],
    max_params: int,
    require_param: bool,
) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if not p.scheme or not p.netloc:
        return False

    host = (p.hostname or "").lower()
    if host in {h.lower() for h in exclude_hosts}:
        return False
    if not _host_in_scope(host, scope_hosts, allow_subdomains):
        return False

    path_lc = (p.path or "").lower()

    if include_path_tokens:
        if not any(tok.lower() in path_lc for tok in include_path_tokens if tok):
            return False

    for tok in exclude_path_tokens:
        t = tok.lower()
        if t and t in path_lc:
            return False

    if exclude_exts:
        last = path_lc.rsplit("/", 1)[-1]
        if "." in last:
            ext = "." + last.rsplit(".", 1)[-1]
            if ext in exclude_exts:
                return False

    qs = parse_qs(p.query or "", keep_blank_values=True)
    if require_param and not qs:
        return False
    if max_params >= 0 and len(qs.keys()) > max_params:
        return False

    return True

def _reap_impl(
    *,
    target: str,
    out: Path,
    quiet: bool,
    verbose: bool,
    safe: bool,
    timeout: int,
    use_katana: bool,
    use_gau: bool,
    use_gospider: bool,
    use_hakrawler: bool,
    use_robots: bool,
    max_urls: int,
    katana_depth: int,
    katana_rate: int,
    katana_concurrency: int,
    gau_limit: int,
    gospider_depth: int,
    gospider_concurrency: int,
    hakrawler_depth: int,
    httpx_threads: int,
    httpx_rate: int,
    scope: Set[str],
    allow_subdomains: bool,
    paths: bool,
    paths_pack: str,
    paths_top: int,
    paths_extra: str,
    exclude_host: Set[str],
    include_path: List[str],
    exclude_path: List[str],
    exclude_ext: Set[str],
    max_params: int,
    require_param: bool,
):
    out.mkdir(parents=True, exist_ok=True)
    base = _base_host(target)

    banner(quiet=quiet)
    
    # Check dependencies
    if not quiet:
        typer.secho("[*] Checking tool dependencies...", fg=typer.colors.CYAN)
    
    # Determine which tools are needed
    required_tools = ["httpx"]  # httpx is always required
    optional_tools = []
    
    if use_katana:
        required_tools.append("katana")
    if use_gau:
        optional_tools.append("gau")
    if use_gospider:
        optional_tools.append("gospider")
    if use_hakrawler:
        optional_tools.append("hakrawler")
    
    # Check and optionally install missing tools
    # Only auto-install in non-interactive mode or if explicitly enabled via env var
    import os
    auto_install = os.getenv("WEBREAPER_AUTO_INSTALL", "").lower() in ("1", "true", "yes")
    
    available, missing_required = check_dependencies(
        required_tools=required_tools,
        optional_tools=optional_tools,
        auto_install=auto_install,
        quiet=quiet
    )
    
    # Handle missing required tools
    if missing_required:
        typer.secho(f"[!] Missing required tools: {', '.join(missing_required)}", fg=typer.colors.RED)
        typer.secho("[!] Please install missing tools and try again.", fg=typer.colors.RED)
        typer.secho("[!] Run './setup.sh' or manually install with 'go install'", fg=typer.colors.YELLOW)
        raise typer.Exit(code=2)
    
    if not quiet:
        typer.secho("[+] All required dependencies are available", fg=typer.colors.GREEN)

    url_sources: dict[str, set[str]] = {target: {"seed"}}

    if not quiet:
        typer.secho(f"[+] Target: {target}", fg=typer.colors.CYAN)
        typer.secho(f"[+] Output: {out}", fg=typer.colors.CYAN)
        typer.secho(f"[+] Caps: max_urls={max_urls}, gau_limit={gau_limit}", fg=typer.colors.CYAN)
        typer.secho(f"[+] Throttle: httpx_threads={httpx_threads}, httpx_rate={httpx_rate}, katana_rate={katana_rate}", fg=typer.colors.CYAN)

    exclude_ext_norm = set()
    for e in exclude_ext:
        e = e.strip().lower()
        if not e:
            continue
        exclude_ext_norm.add(e if e.startswith(".") else "." + e)

    katana_urls: List[str] = []
    if use_katana:
        kt = _normalize_target_for_katana(target)
        katana_cmd = ["katana","-u",kt,"-silent","-d",str(katana_depth),"-rl",str(katana_rate),"-c",str(katana_concurrency)]
        if not safe:
            katana_cmd += ["-jc"]
        if not quiet:
            typer.secho(f"[+] katana: {' '.join(katana_cmd)}", fg=typer.colors.GREEN)
        try:
            start = time.time()
            r = _run(katana_cmd, timeout=timeout)
            dur = int((time.time()-start)*1000)
            (out / f"raw_katana_{_safe_name(kt)}.txt").write_text(r.stdout or "", encoding="utf-8")
            if (r.stderr or "").strip():
                (out / f"katana_{_safe_name(kt)}.stderr.txt").write_text(r.stderr, encoding="utf-8")
            for u in parse_katana_lines(r.stdout or ""):
                katana_urls.append(u)
                url_sources.setdefault(u, set()).add("katana")
            if not quiet:
                typer.secho(f"[+] katana harvested {len(set(katana_urls))} urls ({dur} ms)", fg=typer.colors.GREEN)
        except FileNotFoundError:
            if not quiet:
                typer.secho("[!] katana not found (skipping).", fg=typer.colors.YELLOW)

    gau_urls: List[str] = []
    if use_gau:
        if not quiet:
            typer.secho(f"[+] gau: gau {base} (keeping first {gau_limit})", fg=typer.colors.GREEN)
        try:
            start = time.time()
            r = _run(["gau", base], timeout=timeout)
            dur = int((time.time()-start)*1000)
            lines = (r.stdout or "").splitlines()[:gau_limit]
            gau_out = "\n".join(lines) + ("\n" if lines else "")
            (out / f"raw_gau_{_safe_name(base)}.txt").write_text(gau_out, encoding="utf-8")
            if (r.stderr or "").strip():
                (out / f"gau_{_safe_name(base)}.stderr.txt").write_text(r.stderr, encoding="utf-8")
            for u in parse_gau_lines(gau_out):
                gau_urls.append(u)
                url_sources.setdefault(u, set()).add("gau")
            if not quiet:
                typer.secho(f"[+] gau harvested {len(set(gau_urls))} urls ({dur} ms)", fg=typer.colors.GREEN)
        except FileNotFoundError:
            if not quiet:
                typer.secho("[!] gau not found (skipping).", fg=typer.colors.YELLOW)

    gospider_urls: List[str] = []
    if use_gospider:
        gs_target = _normalize_target_for_katana(target)
        gospider_cmd = ["gospider", "-s", gs_target, "-d", str(gospider_depth), "-c", str(gospider_concurrency), "--no-redirect"]
        if not quiet:
            typer.secho(f"[+] gospider: {' '.join(gospider_cmd)}", fg=typer.colors.GREEN)
        try:
            start = time.time()
            r = _run(gospider_cmd, timeout=timeout)
            dur = int((time.time()-start)*1000)
            (out / f"raw_gospider_{_safe_name(gs_target)}.txt").write_text(r.stdout or "", encoding="utf-8")
            if (r.stderr or "").strip():
                (out / f"gospider_{_safe_name(gs_target)}.stderr.txt").write_text(r.stderr, encoding="utf-8")
            for u in parse_gospider_lines(r.stdout or ""):
                gospider_urls.append(u)
                url_sources.setdefault(u, set()).add("gospider")
            if not quiet:
                typer.secho(f"[+] gospider harvested {len(set(gospider_urls))} urls ({dur} ms)", fg=typer.colors.GREEN)
        except FileNotFoundError:
            if not quiet:
                typer.secho("[!] gospider not found (skipping).", fg=typer.colors.YELLOW)

    hakrawler_urls: List[str] = []
    if use_hakrawler:
        hk_target = _normalize_target_for_katana(target)
        hakrawler_cmd = ["hakrawler", "-url", hk_target, "-depth", str(hakrawler_depth), "-plain"]
        if not quiet:
            typer.secho(f"[+] hakrawler: {' '.join(hakrawler_cmd)}", fg=typer.colors.GREEN)
        try:
            start = time.time()
            r = _run(hakrawler_cmd, timeout=timeout)
            dur = int((time.time()-start)*1000)
            (out / f"raw_hakrawler_{_safe_name(hk_target)}.txt").write_text(r.stdout or "", encoding="utf-8")
            if (r.stderr or "").strip():
                (out / f"hakrawler_{_safe_name(hk_target)}.stderr.txt").write_text(r.stderr, encoding="utf-8")
            for u in parse_hakrawler_lines(r.stdout or ""):
                hakrawler_urls.append(u)
                url_sources.setdefault(u, set()).add("hakrawler")
            if not quiet:
                typer.secho(f"[+] hakrawler harvested {len(set(hakrawler_urls))} urls ({dur} ms)", fg=typer.colors.GREEN)
        except FileNotFoundError:
            if not quiet:
                typer.secho("[!] hakrawler not found (skipping).", fg=typer.colors.YELLOW)

    # Robots.txt and sitemap.xml discovery
    robots_urls: List[str] = []
    sitemap_urls: List[str] = []
    if use_robots:
        base_url = _normalize_target_for_katana(target)
        
        # Fetch robots.txt
        robots_url = urljoin(base_url, "/robots.txt")
        if not quiet:
            typer.secho(f"[+] Fetching robots.txt from {robots_url}", fg=typer.colors.GREEN)
        
        try:
            start = time.time()
            r = _run(["httpx", "-silent", "-u", robots_url], timeout=30)
            dur = int((time.time()-start)*1000)
            
            if r.stdout:
                (out / "raw_robots.txt").write_text(r.stdout, encoding="utf-8")
                # Parse robots.txt for paths
                for u in parse_robots_txt(base_url, r.stdout):
                    robots_urls.append(u)
                    url_sources.setdefault(u, set()).add("robots")
                
                # Extract sitemap URLs from robots.txt and fetch them
                sitemap_locations = []
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if line.lower().startswith("sitemap:"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            sitemap_loc = parts[1].strip()
                            if sitemap_loc and "://" in sitemap_loc:
                                sitemap_locations.append(sitemap_loc)
                
                # If no sitemap in robots.txt, try default location
                if not sitemap_locations:
                    sitemap_locations.append(urljoin(base_url, "/sitemap.xml"))
                
                # Fetch and parse sitemaps (limit to first 3 to avoid recursion)
                for sitemap_loc in sitemap_locations[:3]:
                    try:
                        sitemap_r = _run(["httpx", "-silent", "-u", sitemap_loc], timeout=30)
                        if sitemap_r.stdout:
                            sitemap_name = _safe_name(sitemap_loc)
                            (out / f"raw_sitemap_{sitemap_name}.xml").write_text(sitemap_r.stdout, encoding="utf-8")
                            
                            for u in parse_sitemap_xml(sitemap_r.stdout):
                                sitemap_urls.append(u)
                                url_sources.setdefault(u, set()).add("sitemap")
                    except Exception:
                        pass  # Silently skip failed sitemap fetches
                
                if not quiet:
                    total_disc = len(set(robots_urls)) + len(set(sitemap_urls))
                    typer.secho(f"[+] robots/sitemap discovered {total_disc} urls (robots:{len(set(robots_urls))}, sitemap:{len(set(sitemap_urls))}) ({dur} ms)", fg=typer.colors.GREEN)
        
        except Exception as e:
            if not quiet:
                typer.secho(f"[!] robots/sitemap discovery failed: {e}", fg=typer.colors.YELLOW)

    candidates = [target, *katana_urls, *gau_urls, *gospider_urls, *hakrawler_urls, *robots_urls, *sitemap_urls]
    merged: List[str] = []
    filtered_out = 0
    for u in candidates:
        if u in merged:
            continue
        if not _filter_url(
            u,
            scope_hosts=scope,
            allow_subdomains=allow_subdomains,
            exclude_hosts=exclude_host,
            include_path_tokens=include_path,
            exclude_path_tokens=exclude_path,
            exclude_exts=exclude_ext_norm,
            max_params=max_params,
            require_param=require_param,
        ):
            filtered_out += 1
            continue
        merged.append(u)
        if len(merged) >= max_urls:
            break

    if not quiet:
        typer.secho(f"[+] Filtered in {len(merged)} urls (filtered_out={filtered_out}, capped at {max_urls})", fg=typer.colors.GREEN)

    httpx_cmd = ["httpx","-silent","-json","-title","-tech-detect","-status-code","-content-type","-location","-follow-redirects"]
    if httpx_threads > 0:
        httpx_cmd += ["-threads", str(httpx_threads)]
    if httpx_rate > 0:
        httpx_cmd += ["-rl", str(httpx_rate)]
    input_blob = "\n".join(merged) + "\n"

    if not quiet:
        typer.secho(f"[+] httpx probing {len(merged)} urls", fg=typer.colors.GREEN)

    try:
        start = time.time()
        r = _run(httpx_cmd, input_text=input_blob, timeout=timeout)
        dur = int((time.time()-start)*1000)
    except FileNotFoundError:
        typer.secho("[!] Missing required tool: httpx (ProjectDiscovery).", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    (out / "raw_httpx.jsonl").write_text(r.stdout or "", encoding="utf-8")
    if (r.stderr or "").strip():
        (out / "httpx.stderr.txt").write_text(r.stderr, encoding="utf-8")

    if r.returncode != 0 and not (r.stdout or "").strip():
        typer.secho("[!] httpx failed. See out/httpx.stderr.txt", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not quiet:
        typer.secho(f"[+] httpx done ({dur} ms). Scoring…", fg=typer.colors.GREEN)

    eps = parse_httpx_jsonlines(r.stdout or "")
    seen_paths = set()
    endpoint_dicts = []
    urls = []
    hosts = set()

    for ep in eps:
        if ep.url and not _filter_url(
            ep.url,
            scope_hosts=scope,
            allow_subdomains=allow_subdomains,
            exclude_hosts=exclude_host,
            include_path_tokens=include_path,
            exclude_path_tokens=exclude_path,
            exclude_exts=exclude_ext_norm,
            max_params=max_params,
            require_param=require_param,
        ):
            continue

        urls.append(ep.url)
        if ep.host:
            hosts.add(ep.host)

        key = (ep.host, ep.path)
        unique_path = key not in seen_paths
        seen_paths.add(key)

        sources = sorted(url_sources.get(ep.url, set()) | {"httpx"})
        reap = compute_reapscore(
            url=ep.url,
            sources=sources,
            status=ep.status,
            content_type=ep.content_type,
            redirect_location=ep.location,
            has_set_cookie=ep.has_set_cookie,
            www_authenticate=ep.www_authenticate,
            response_time_ms=ep.time_ms,
            response_size_bytes=ep.body_size,
            base_host=base,
            unique_path=unique_path,
            tech=ep.tech,
        )

        endpoint_dicts.append({
            "url": ep.url,
            "host": ep.host,
            "path": ep.path,
            "status": ep.status,
            "content_type": ep.content_type,
            "title": ep.title,
            "tech": ep.tech,
            "sources": sources,
            "reap": {
                "score": reap.score,
                "subs": {
                    "harvest_index": reap.subs.harvest_index,
                    "juice_score": reap.subs.juice_score,
                    "access_signal": reap.subs.access_signal,
                    "anomaly_signal": reap.subs.anomaly_signal,
                },
                "reasons": reap.reasons,
                "confidence": reap.confidence,
                "weights": reap.weights,
            },
        })

    top_score = max((int(e["reap"]["score"]) for e in endpoint_dicts), default=0)

    findings = {
        "target": target,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "profile": "safe" if safe else "active",
        "limits": {
            "max_urls": max_urls,
            "gau_limit": gau_limit,
            "httpx_threads": httpx_threads,
            "httpx_rate": httpx_rate,
            "katana_depth": katana_depth,
            "katana_rate": katana_rate,
            "katana_concurrency": katana_concurrency,
            "use_katana": use_katana,
            "use_gau": use_gau,
        },
        "filters": {
            "scope": sorted(scope),
            "allow_subdomains": allow_subdomains,
            "exclude_host": sorted(exclude_host),
            "include_path": include_path,
            "exclude_path": exclude_path,
            "exclude_ext": sorted(exclude_ext_norm),
            "max_params": max_params,
            "require_param": require_param,
        },
        "summary": {
            "hosts": len(hosts),
            "urls_total": len(urls),
            "urls_unique": len(set(urls)),
            "top_reapscore": top_score,
        },
        "endpoints": endpoint_dicts,
    }

    (out / "findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    (out / "urls.txt").write_text("\n".join(sorted(set(urls))) + ("\n" if urls else ""), encoding="utf-8")
    (out / "hosts.txt").write_text("\n".join(sorted(hosts)) + ("\n" if hosts else ""), encoding="utf-8")
    _stage(out, "report", quiet=quiet, verbose=verbose)
    write_report(out / "findings.json", out / "REPORT.md")
    write_eli5_report(out / "findings.json", out / "ELI5-REPORT.md")

    if not quiet:
        typer.secho(f"[+] Done. Wrote {out/'REPORT.md'}", fg=typer.colors.GREEN)


@app.command(name="packs")
def packs():
    """List built-in path packs for --paths-pack."""
    typer.echo("\n".join(list_path_packs()))

@app.command(name="reap")
def reap(
    target: str = typer.Argument(..., help="Target URL or host"),
    out: Path = typer.Option(Path("out"), "-o", "--out", help="Output directory"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable banner + progress output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="More runtime output (stage output + tool timing)"),
    safe: bool = typer.Option(True, "--safe/--active", help="Safe mode (default)"),
    timeout: int = typer.Option(600, "--timeout", help="Timeout in seconds per tool"),
    katana: bool = typer.Option(True, "--katana/--no-katana", help="Enable katana crawling"),
    gau: bool = typer.Option(True, "--gau/--no-gau", help="Enable gau historical URLs"),
    gospider: bool = typer.Option(False, "--gospider/--no-gospider", help="Enable gospider web crawler"),
    hakrawler: bool = typer.Option(False, "--hakrawler/--no-hakrawler", help="Enable hakrawler web crawler"),
    max_urls: int = typer.Option(1500, "--max-urls", help="Hard cap on total URLs probed (prevents CPU melt)"),
    gau_limit: int = typer.Option(1500, "--gau-limit", help="Max gau URLs to keep (first N lines)"),
    katana_depth: int = typer.Option(2, "--katana-depth", help="Katana depth"),
    katana_rate: int = typer.Option(50, "--katana-rate", help="Katana rate limit (req/sec)"),
    katana_concurrency: int = typer.Option(5, "--katana-concurrency", help="Katana concurrency"),
    gospider_depth: int = typer.Option(2, "--gospider-depth", help="gospider crawl depth"),
    gospider_concurrency: int = typer.Option(5, "--gospider-concurrency", help="gospider concurrency"),
    hakrawler_depth: int = typer.Option(2, "--hakrawler-depth", help="hakrawler crawl depth"),
    paths: bool = typer.Option(True, "--paths/--no-paths", help="Enable known-path probing (pack-based)"),
    paths_pack: str = typer.Option("common", "--paths-pack", help="Comma-separated pack names (common,auth,api,ops,files,all). See: webreaper packs"),
    paths_top: int = typer.Option(120, "--paths-top", help="How many known paths to add from packs"),
    paths_extra: str = typer.Option("", "--paths-extra", help="Comma-separated extra paths to include (e.g. admin,api,graphql)"),
    httpx_threads: int = typer.Option(25, "--httpx-threads", help="httpx threads"),
    httpx_rate: int = typer.Option(50, "--httpx-rate", help="httpx rate limit (req/sec)"),

    scope: Optional[str] = typer.Option(None, "--scope", help="Comma-separated hosts in scope (e.g. example.com,api.example.com)"),
    no_subdomains: bool = typer.Option(False, "--no-subdomains", help="With --scope, require exact host match (no subdomains)"),
    exclude_host: Optional[str] = typer.Option(None, "--exclude-host", help="Comma-separated hosts to exclude"),
    include_path: Optional[str] = typer.Option(None, "--include-path", help="Comma-separated path tokens to require (substring match)"),
    exclude_path: Optional[str] = typer.Option(None, "--exclude-path", help="Comma-separated path tokens to drop (substring match)"),
    exclude_ext: Optional[str] = typer.Option(None, "--exclude-ext", help="Comma-separated file extensions to drop (e.g. png,jpg,css,js)"),
    max_params: int = typer.Option(10, "--max-params", help="Drop URLs with more than this many query params"),
    require_param: bool = typer.Option(False, "--require-param", help="Keep only URLs that have query params"),
):
    _reap_impl(
        target=target, out=out, quiet=quiet, safe=safe, timeout=timeout,
        verbose=verbose,
        use_katana=katana, use_gau=gau, use_gospider=gospider, use_hakrawler=hakrawler,
        use_robots=robots,
        max_urls=max_urls, katana_depth=katana_depth, katana_rate=katana_rate, katana_concurrency=katana_concurrency,
        gau_limit=gau_limit, 
        gospider_depth=gospider_depth, gospider_concurrency=gospider_concurrency,
        hakrawler_depth=hakrawler_depth,
        httpx_threads=httpx_threads, httpx_rate=httpx_rate,
        scope=_csv_set(scope),
        allow_subdomains=not no_subdomains,
        exclude_host=_csv_set(exclude_host),
        include_path=_csv_list(include_path),
        exclude_path=_csv_list(exclude_path),
        exclude_ext=_csv_set(exclude_ext),
        max_params=max_params,
        require_param=require_param,
        paths=paths,
        paths_pack=paths_pack,
        paths_top=paths_top,
        paths_extra=paths_extra,
    )

@app.command(name="scan")
def scan(
    target: str = typer.Argument(..., help="Target URL or host"),
    out: Path = typer.Option(Path("out"), "-o", "--out", help="Output directory"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable banner + progress output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="More runtime output (stage output + tool timing)"),
    safe: bool = typer.Option(True, "--safe/--active", help="Safe mode (default)"),
    timeout: int = typer.Option(600, "--timeout", help="Timeout in seconds per tool"),
    katana: bool = typer.Option(True, "--katana/--no-katana", help="Enable katana crawling"),
    gau: bool = typer.Option(True, "--gau/--no-gau", help="Enable gau historical URLs"),
    gospider: bool = typer.Option(False, "--gospider/--no-gospider", help="Enable gospider web crawler"),
    hakrawler: bool = typer.Option(False, "--hakrawler/--no-hakrawler", help="Enable hakrawler web crawler"),
    robots: bool = typer.Option(True, "--robots/--no-robots", help="Enable robots.txt and sitemap.xml discovery"),
    max_urls: int = typer.Option(1500, "--max-urls", help="Hard cap on total URLs probed (prevents CPU melt)"),
    gau_limit: int = typer.Option(1500, "--gau-limit", help="Max gau URLs to keep (first N lines)"),
    katana_depth: int = typer.Option(2, "--katana-depth", help="Katana depth"),
    katana_rate: int = typer.Option(50, "--katana-rate", help="Katana rate limit (req/sec)"),
    katana_concurrency: int = typer.Option(5, "--katana-concurrency", help="Katana concurrency"),
    gospider_depth: int = typer.Option(2, "--gospider-depth", help="gospider crawl depth"),
    gospider_concurrency: int = typer.Option(5, "--gospider-concurrency", help="gospider concurrency"),
    hakrawler_depth: int = typer.Option(2, "--hakrawler-depth", help="hakrawler crawl depth"),
    paths: bool = typer.Option(True, "--paths/--no-paths", help="Enable known-path probing (pack-based)"),
    paths_pack: str = typer.Option("common", "--paths-pack", help="Comma-separated pack names (common,auth,api,ops,files,all). See: webreaper packs"),
    paths_top: int = typer.Option(120, "--paths-top", help="How many known paths to add from packs"),
    paths_extra: str = typer.Option("", "--paths-extra", help="Comma-separated extra paths to include (e.g. admin,api,graphql)"),
    httpx_threads: int = typer.Option(25, "--httpx-threads", help="httpx threads"),
    httpx_rate: int = typer.Option(50, "--httpx-rate", help="httpx rate limit (req/sec)"),

    scope: Optional[str] = typer.Option(None, "--scope", help="Comma-separated hosts in scope (e.g. example.com,api.example.com)"),
    no_subdomains: bool = typer.Option(False, "--no-subdomains", help="With --scope, require exact host match (no subdomains)"),
    exclude_host: Optional[str] = typer.Option(None, "--exclude-host", help="Comma-separated hosts to exclude"),
    include_path: Optional[str] = typer.Option(None, "--include-path", help="Comma-separated path tokens to require (substring match)"),
    exclude_path: Optional[str] = typer.Option(None, "--exclude-path", help="Comma-separated path tokens to drop (substring match)"),
    exclude_ext: Optional[str] = typer.Option(None, "--exclude-ext", help="Comma-separated file extensions to drop (e.g. png,jpg,css,js)"),
    max_params: int = typer.Option(10, "--max-params", help="Drop URLs with more than this many query params"),
    require_param: bool = typer.Option(False, "--require-param", help="Keep only URLs that have query params"),
):
    _reap_impl(
        target=target, out=out, quiet=quiet, safe=safe, timeout=timeout,
        verbose=verbose,
        use_katana=katana, use_gau=gau, use_gospider=gospider, use_hakrawler=hakrawler,
        use_robots=robots,
        max_urls=max_urls, katana_depth=katana_depth, katana_rate=katana_rate, katana_concurrency=katana_concurrency,
        gau_limit=gau_limit,
        gospider_depth=gospider_depth, gospider_concurrency=gospider_concurrency,
        hakrawler_depth=hakrawler_depth,
        httpx_threads=httpx_threads, httpx_rate=httpx_rate,
        scope=_csv_set(scope),
        allow_subdomains=not no_subdomains,
        exclude_host=_csv_set(exclude_host),
        include_path=_csv_list(include_path),
        exclude_path=_csv_list(exclude_path),
        exclude_ext=_csv_set(exclude_ext),
        max_params=max_params,
        require_param=require_param,
        paths=paths,
        paths_pack=paths_pack,
        paths_top=paths_top,
        paths_extra=paths_extra,
    )
