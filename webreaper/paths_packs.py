from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

PACKS: Dict[str, List[str]] = {
    "common": [
        "robots.txt", "sitemap.xml", ".well-known/security.txt",
        "admin", "administrator", "api", "graphql",
        "swagger", "swagger.json", "openapi.json",
        "health", "status", "ping", "ready",
        "login", "signin", "logout", "auth", "sso",
        "index", "home", "dashboard", "portal",
    ],
    "auth": [
        "login","signin","logout","auth","sso","authentication",
        "oauth","oauth2","oidc","callback","authorize","token","userinfo",
        "register","signup","forgot","reset","password","account",
        "session","sessions","cookie","cookies",
        ".auth", "_auth", "auth/login", "auth/callback",
        "saml", "saml2", "ldap", "kerberos",
    ],
    "api": [
        "api","api/v1","api/v2","api/v3","api/v4",
        "rest","rest/v1","rest/v2",
        "graphql","graphiql","playground",
        "swagger","swagger.json","swagger-ui","swagger-ui.html",
        "openapi.json","openapi.yaml","openapi/v2","openapi/v3",
        "api-docs","docs","redoc","rapidoc",
        "schema","schema.json","schema.graphql",
        "wsdl","wadl","raml",
        "endpoints","routes",
    ],
    "ops": [
        "health","status","metrics","stats","statistics",
        "actuator","actuator/health","actuator/info","actuator/metrics",
        "actuator/env","actuator/beans","actuator/mappings",
        "server-status","server-info",
        "monitoring","monitor","prometheus",
        "debug","trace","profiler",
        "admin/queues","admin/jobs",
    ],
    "files": [
        "upload","uploads","download","downloads","export","exports",
        "backup","backups","archive","archives",
        "files","file","documents","docs",
        "media","images","img","assets","static",
        "tmp","temp","temporary",
        "data","dump","dumps",
    ],
    "sensitive": [
        ".env",".env.local",".env.production",".env.development",
        ".git",".git/config",".git/HEAD",
        ".svn",".hg",".bzr",
        "config","config.json","config.yaml","config.yml","config.xml",
        "configuration","settings","preferences",
        "web.config","app.config","appsettings.json",
        "database.yml","db.yml","database.json",
        "secrets","secret","credentials","creds",
        ".htaccess",".htpasswd",".npmrc",".dockerenv",
        "Dockerfile","docker-compose.yml",
        "package.json","composer.json","requirements.txt",
        "phpinfo.php","info.php","test.php",
        "readme","README","README.md","CHANGELOG","CHANGELOG.md",
        "error_log","access_log","debug.log","application.log",
    ],
    "admin": [
        "admin","administrator","administration",
        "admin/login","admin/dashboard","admin/panel",
        "panel","cpanel","controlpanel","control",
        "manage","manager","management",
        "console","webconsole","adminconsole",
        "wp-admin","wp-login","phpmyadmin",
        "administrator/index","admin/index",
        "backend","backoffice",
    ],
    "discovery": [
        ".well-known/security.txt",".well-known/openid-configuration",
        ".well-known/assetlinks.json",".well-known/apple-app-site-association",
        "sitemap.xml","sitemap_index.xml","sitemap.txt",
        "robots.txt","humans.txt","crossdomain.xml",
        "security.txt","security",
        "favicon.ico","apple-touch-icon.png",
        "manifest.json","browserconfig.xml",
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
