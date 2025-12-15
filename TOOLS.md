# webReaper Tools System

## Overview

The webReaper tools system provides a modular, extensible framework for adding new data sources, analyzers, and scoring enhancements. This document describes the available tools, how to use them, and how to create custom tools.

## Architecture

Tools are organized into three categories:

1. **Discovery Tools** - Find URLs and endpoints from various sources
2. **Analyzer Tools** - Extract metadata and signals from responses
3. **Scoring Tools** - Contribute additional scoring logic to ReapScore

### Tool Registry

All tools are registered in a global registry that manages their lifecycle and makes them available to the webReaper CLI. The registry supports:

- Tool discovery and listing
- Runtime tool selection
- Extension by custom/community tools

## Built-in Tools

### Discovery Tools

#### Robots/Sitemap Discovery (`robots_sitemap`)

**Status:** ✅ Enabled by default

**Description:** Discovers URLs from robots.txt and sitemap.xml files

**Contribution to ReapScore:**
- Adds "robots" and "sitemap" as discovery sources for HarvestIndex (+20 and +18 respectively)
- robots.txt Disallow paths often indicate sensitive/interesting endpoints
- Sitemap URLs provide comprehensive site structure

**CLI Usage:**
```bash
# Enabled by default
webreaper reap https://example.com -o out/

# Disable if needed
webreaper reap https://example.com -o out/ --no-robots
```

**How it works:**
1. Fetches `/robots.txt` from the target
2. Parses Disallow and Allow directives to extract paths
3. Extracts Sitemap directives to find sitemap locations
4. Fetches and parses sitemap XML files (up to 3 sitemaps)
5. Returns discovered URLs with "robots" or "sitemap" source tags

**Output files:**
- `raw_robots.txt` - Raw robots.txt content
- `raw_sitemap_*.xml` - Raw sitemap XML content

**Example robots.txt parsing:**
```
User-agent: *
Disallow: /admin/          → Discovers: https://example.com/admin/
Disallow: /api/internal/   → Discovers: https://example.com/api/internal/
Sitemap: https://example.com/sitemap.xml
```

### Analyzer Tools

#### Security Headers Analyzer (`security_headers`)

**Status:** ✅ Enabled by default (analysis only, not yet integrated into scoring)

**Description:** Analyzes HTTP security headers for scoring signals

**Analyzed Headers:**

**Security Headers:**
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy` (CSP)
- `X-Frame-Options`
- `X-Content-Type-Options`
- `X-XSS-Protection`
- `Referrer-Policy`
- `Permissions-Policy`
- `Cross-Origin-Embedder-Policy`
- `Cross-Origin-Opener-Policy`
- `Cross-Origin-Resource-Policy`

**Authentication Headers:**
- `WWW-Authenticate`
- `Authorization`
- `Proxy-Authenticate`
- `Proxy-Authorization`

**CORS Headers:**
- `Access-Control-Allow-Origin`
- `Access-Control-Allow-Credentials`
- `Access-Control-Allow-Methods`
- And other CORS headers

**Analysis Output:**
```python
{
    "missing_security_headers": [...],   # List of missing headers
    "present_security_headers": [...],   # List of present headers
    "auth_headers": [...],               # Authentication headers found
    "cors_enabled": bool,                # CORS is enabled
    "cors_misconfigured": bool,          # CORS allows * with credentials
    "has_hsts": bool,                    # HSTS is enabled
    "has_csp": bool,                     # CSP is enabled
    "cookie_flags": {                    # Cookie security analysis
        "has_secure": bool,
        "has_httponly": bool,
        "has_samesite": bool,
    },
    "security_score": int,               # 0-100 (higher = less secure = more interesting)
}
```

**Contribution to ReapScore:**
- **Current:** Headers already analyzed by httpx contribute to AccessSignal
- **Future:** Missing security headers can boost JuiceScore (indicates potential vulnerabilities)

**Programmatic Usage:**
```python
from webreaper.tools.security_headers import analyze_security_headers

headers = {
    "Content-Type": "text/html",
    "Set-Cookie": "session=abc; Secure; HttpOnly",
}

analysis = analyze_security_headers(headers)
print(f"Missing: {analysis['missing_security_headers']}")
```

#### Content Pattern Analyzer (`content_patterns`)

**Status:** ✅ Implemented (not yet integrated into CLI workflow)

**Description:** Analyzes response body content for sensitive patterns and signals

**Detected Patterns:**

**Sensitive Data:**
- API keys (`api_key`, `apikey`)
- Bearer tokens
- JWT tokens
- AWS access keys
- Private keys (PEM format)
- Password fields

**Error Messages:**
- SQL errors (MySQL, PostgreSQL, Oracle, SQLite)
- Stack traces (Java, Python, etc.)
- PHP errors
- ASP.NET errors
- Java exceptions

**Debug/Development:**
- Debug mode indicators
- phpinfo() pages
- Swagger/OpenAPI documentation
- GraphQL introspection

**API Patterns:**
- REST API endpoints (`/api/v1/`, `/rest/`)
- JSON API structures
- XML API responses

**Analysis Output:**
```python
{
    "sensitive_patterns": [...],     # List of sensitive pattern types found
    "error_patterns": [...],         # List of error pattern types found
    "debug_patterns": [...],         # List of debug pattern types found
    "api_patterns": [...],           # List of API pattern types found
    "has_sensitive_data": bool,      # Sensitive data detected
    "has_errors": bool,              # Errors detected
    "has_debug_info": bool,          # Debug info detected
    "is_api": bool,                  # API patterns detected
    "pattern_score": int,            # 0-100 based on findings
}
```

**Contribution to ReapScore:**
- **Future:** Pattern score can enhance JuiceScore and AnomalySignal
  - Sensitive data patterns → +30 per pattern to JuiceScore
  - Error patterns → +20 per pattern to AnomalySignal
  - Debug patterns → +15 per pattern to JuiceScore
  - API patterns → +10 per pattern to JuiceScore

**Programmatic Usage:**
```python
from webreaper.tools.content_patterns import analyze_content_patterns

content = """
<html>
  <script>
    const apiKey = "sk_live_abc123def456...";
  </script>
</html>
"""

analysis = analyze_content_patterns(content)
print(f"Patterns found: {analysis['sensitive_patterns']}")
```

### Scoring Tools

#### Technology Scorer (`technology_scorer`)

**Status:** ✅ Implemented (not yet integrated into CLI workflow)

**Description:** Provides additional scoring based on detected web technologies

**High-Value Technologies:**

**Admin Panels & Management Interfaces:**
- phpMyAdmin (+25)
- Adminer (+25)
- WordPress (+15)
- Drupal (+15)
- Joomla (+15)

**API Frameworks:**
- GraphQL (+20)
- Swagger/OpenAPI (+20)
- REST API (+15)

**Development/Debug Tools:**
- XDebug (+30)
- phpinfo (+30)
- Laravel Debugbar (+25)
- Symfony Profiler (+25)

**Database Interfaces:**
- MySQL (+20)
- PostgreSQL (+20)
- MongoDB (+20)
- Redis (+20)

**Application Servers:**
- Tomcat (+15)
- JBoss (+15)
- WebLogic (+15)
- WebSphere (+15)

**Legacy/Vulnerable Frameworks:**
- Struts (+25)
- Spring (+15)
- Flask (+10)
- Django (+10)
- Rails (+10)

**SSO/Auth Systems:**
- OAuth (+20)
- SAML (+20)
- Keycloak (+20)
- Okta (+20)
- JWT (+15)

**Contribution to ReapScore:**
- **Future:** Technology score bonuses enhance JuiceScore
- Identifies admin panels, debug tools, and legacy frameworks
- Prioritizes endpoints running high-value technology stacks

**Programmatic Usage:**
```python
from webreaper.tools.technology_scorer import score_technologies

techs = ["WordPress", "phpMyAdmin", "MySQL"]
result = score_technologies(techs)
print(f"Score: {result['score']}")           # 60 (15+25+20)
print(f"High-value: {result['high_value_techs']}")
print(f"Categories: {result['categories']}")
```

## Future Tools (Roadmap)

### Planned Discovery Tools

1. **DNS Enumeration Tool** - Discover subdomains via DNS
2. **Certificate Transparency Log Parser** - Find subdomains from CT logs
3. **Wayback Machine API** - Additional historical URL source
4. **Common Crawl Parser** - Parse Common Crawl data for URLs

### Planned Analyzer Tools

1. **Form Analyzer** - Detect and analyze HTML forms for input vectors
2. **JavaScript Analyzer** - Extract API endpoints from JavaScript files
3. **Header Fingerprinter** - Advanced server/framework fingerprinting
4. **Response Time Analyzer** - Detect timing-based vulnerabilities

### Planned Scoring Tools

1. **Input Vector Scorer** - Score based on form complexity and input types
2. **Authentication Complexity Scorer** - Score auth mechanisms
3. **Rate Limit Detector** - Identify and score rate-limited endpoints
4. **Session Management Scorer** - Score session handling quality

## Creating Custom Tools

### Discovery Tool Example

```python
from webreaper.tools import DiscoveryTool, ToolMetadata, ToolCategory

class MyDiscoveryTool(DiscoveryTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            category=ToolCategory.DISCOVERY,
            description="My custom discovery tool",
            version="1.0.0",
            enabled_by_default=False,
        )
    
    def discover(self, target: str, **kwargs) -> List[str]:
        # Your discovery logic here
        urls = []
        # ... discover URLs ...
        return urls
```

### Analyzer Tool Example

```python
from webreaper.tools import AnalyzerTool, ToolMetadata, ToolCategory

class MyAnalyzer(AnalyzerTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_analyzer",
            category=ToolCategory.ANALYZER,
            description="My custom analyzer",
            version="1.0.0",
        )
    
    def analyze(self, url: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your analysis logic here
        return {
            "my_metric": 42,
            "my_flag": True,
        }
```

### Scoring Tool Example

```python
from webreaper.tools import ScoringTool, ToolMetadata, ToolCategory

class MyScorer(ScoringTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_scorer",
            category=ToolCategory.SCORER,
            description="My custom scorer",
            version="1.0.0",
        )
    
    def score(self, context: Any, reasons: List[str]) -> int:
        # Your scoring logic here
        bonus = 0
        if some_condition:
            bonus += 20
            reasons.append("my_condition (+20)")
        return bonus
```

### Registering Custom Tools

```python
from webreaper.tools import get_global_registry

# Create and register your tool
registry = get_global_registry()
registry.register_discovery(MyDiscoveryTool())
registry.register_analyzer(MyAnalyzer())
registry.register_scorer(MyScorer())

# List all registered tools
for tool in registry.list_tools():
    print(f"{tool.name}: {tool.description}")
```

## Integration with ReapScore

### Current Integration

The tools system is designed to enhance the ReapScore algorithm at multiple points:

1. **HarvestIndex (30%)** - Discovery tools contribute source diversity
   - robots: +20 points
   - sitemap: +18 points
   - (existing: katana +10, gau +15, gospider +12, hakrawler +12)

2. **JuiceScore (35%)** - Technology and pattern analysis can add bonuses
   - High-value technologies detected by httpx tech-detect
   - Future: Content patterns, API detection

3. **AccessSignal (20%)** - Security header analysis provides auth signals
   - Already integrated via httpx headers
   - Future: Enhanced CORS and auth detection

4. **AnomalySignal (15%)** - Error patterns and unusual responses
   - Future: Content pattern errors, timing anomalies

### Future Integration

The scoring system supports extensions through the `extensions` parameter:

```python
from webreaper.tools.technology_scorer import TechnologyScorer

scorer = TechnologyScorer()

reap = compute_reapscore(
    url="https://example.com/admin",
    sources=["katana", "robots"],
    tech=["phpMyAdmin", "MySQL"],
    extensions=[scorer.score],  # Add custom scoring
)
```

## CLI Integration

### Current Flags

```bash
# Discovery tools
--robots / --no-robots        # robots.txt and sitemap.xml (enabled by default)
--katana / --no-katana        # katana crawler (enabled by default)
--gau / --no-gau              # gau historical URLs (enabled by default)
--gospider / --no-gospider    # gospider crawler (disabled by default)
--hakrawler / --no-hakrawler  # hakrawler crawler (disabled by default)
--paths / --no-paths          # path pack probing (enabled by default)
```

### Future Flags

Additional tools will be added with similar flag patterns:

```bash
--analyze-content / --no-analyze-content    # Content pattern analysis
--score-technology / --no-score-technology  # Technology-based scoring
--security-headers / --no-security-headers  # Security header analysis
```

## API Reference

See inline documentation in:
- `webreaper/tools/registry.py` - Core abstractions and registry
- `webreaper/tools/robots_sitemap.py` - Robots/sitemap tool
- `webreaper/tools/security_headers.py` - Security headers analyzer
- `webreaper/tools/content_patterns.py` - Content pattern analyzer
- `webreaper/tools/technology_scorer.py` - Technology scorer

## Contributing

To contribute a new tool:

1. Create a new file in `webreaper/tools/` implementing one of the base classes
2. Register your tool in `webreaper/tools/__init__.py`
3. Add CLI integration in `webreaper/cli.py` if needed
4. Update this documentation
5. Add tests demonstrating the tool's functionality
6. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
