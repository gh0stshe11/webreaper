from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

PACKS: Dict[str, List[str]] = {
    "common": [
        "robots.txt", "sitemap.xml", ".well-known/security.txt",
        "admin", "administrator", "api", "graphql",
        "swagger", "swagger.json", "openapi.json",
        "health", "status",
        "login", "signin", "logout", "auth", "sso",
    ],
    "auth": [
        "login","signin","logout","auth","sso",
        "oauth","oauth2","oidc","callback","authorize","token","userinfo",
    ],
    "api": [
        "api","api/v1","api/v2","api/v3",
        "graphql","graphiql",
        "swagger","swagger.json","swagger-ui",
        "openapi.json","openapi.yaml",
        "api-docs","docs","redoc",
    ],
    "ops": [
        "health","status","metrics",
        "actuator","actuator/health","actuator/info","actuator/metrics",
        "server-status",
    ],
    "files": [
        "upload","uploads","download","export","backup",
    ],
}

def list_packs() -> List[str]:
    return sorted(PACKS.keys()) + ["all"]

def _base_url(target: str) -> str:
    # normalize to scheme://host
    if "://" not in target:
        target = "https://" + target
    p = urlparse(target)
    scheme = p.scheme or "https"
    netloc = p.netloc or p.path  # if user gave host only
    return urlunparse((scheme, netloc, "", "", "", ""))

def _pack_paths(packs: List[str]) -> List[str]:
    if not packs:
        packs = ["common"]
    packs = [p.strip().lower() for p in packs if p.strip()]
    if "all" in packs:
        out: List[str] = []
        for v in PACKS.values():
            out.extend(v)
        return out
    out: List[str] = []
    for p in packs:
        if p in PACKS:
            out.extend(PACKS[p])
    return out

def generate_path_urls(target: str, *, packs: Optional[List[str]] = None, extra_paths: Optional[List[str]] = None, top: int = 120) -> List[str]:
    base = _base_url(target).rstrip("/")
    paths: List[str] = []
    paths.extend(_pack_paths(list(packs or [])))
    if extra_paths:
        paths.extend([x.strip().lstrip("/") for x in extra_paths if x.strip()])
    # de-dupe preserving order
    seen=set()
    norm=[]
    for p in paths:
        p=p.strip().lstrip("/")
        if not p:
            continue
        if p in seen:
            continue
        seen.add(p)
        norm.append(p)
    norm = norm[: max(0, int(top))]
    return [f"{base}/{p}" for p in norm]
