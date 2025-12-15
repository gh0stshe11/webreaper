# webReaper Architecture

## Overview

webReaper is a lightweight web reconnaissance and endpoint-ranking tool designed to help security professionals quickly identify high-value targets in a web attack surface. The tool follows a four-phase pipeline: **Harvest → Probe → Rank → Report**.

## Design Philosophy

1. **Prioritization over Volume**: Rather than dumping thousands of URLs, webReaper focuses on surfacing the most interesting endpoints first.
2. **Modular Tool Integration**: Support for multiple discovery tools (crawlers, historical URL databases, path guessing) with a unified interface.
3. **Intelligent Scoring**: Multi-factor ranking algorithm (ReapScore) that considers discovery value, input potential, access signals, and anomalies.
4. **Actionable Output**: Both technical (JSON) and human-friendly (Markdown + ELI5) reports to guide manual testing.

## Architecture Components

### 1. Harvest Phase

The harvest phase collects URLs from multiple sources to build a comprehensive view of the target's attack surface.

#### Integrated Tools

- **katana** (ProjectDiscovery)
  - Web crawler for discovering endpoints via spidering
  - Supports JavaScript execution (`-jc` flag in active mode)
  - Configurable depth, rate limiting, and concurrency
  - Parser: `webreaper/parsers/katana.py`

- **gau** (GetAllURLs)
  - Historical URL aggregator from web archives (Wayback, Common Crawl, etc.)
  - Provides URLs that may no longer be linked but still exist
  - Configurable limit to prevent overwhelming results
  - Parser: `webreaper/parsers/gau.py`

- **Path Packs** (Built-in)
  - Intelligent path guessing based on curated wordlists
  - Multiple packs: `common`, `auth`, `api`, `ops`, `files`
  - Generates URLs by appending paths to target base URL
  - Module: `webreaper/paths_packs.py`

- **robots.txt / sitemap.xml** (Planned)
  - Automatic fetching and parsing of standard discovery files
  - Status: Documented in roadmap, implementation pending

#### URL Filtering

All harvested URLs pass through a comprehensive filtering system:
- **Scope control**: Host-based scoping with optional subdomain inclusion
- **Path filtering**: Include/exclude patterns for path matching
- **Extension filtering**: Drop static assets (images, CSS, JS)
- **Parameter limits**: Control query parameter complexity
- **Deduplication**: Remove duplicate URLs before probing

### 2. Probe Phase

The probe phase actively requests each URL to gather behavioral metadata.

#### Integrated Tools

- **httpx** (ProjectDiscovery) - Primary HTTP client
  - JSON output format for structured data
  - Captures: status codes, content types, titles, technologies, redirects, cookies
  - Configurable threading and rate limiting
  - Automatic redirect following
  - Parser: `webreaper/parsers/httpx.py`

#### Collected Metadata

Each probed endpoint provides:
- HTTP status code and redirect location
- Content-Type header
- Page title
- Technology fingerprints (via httpx tech detection)
- Response time (milliseconds)
- Response size (bytes)
- Security headers (Set-Cookie, WWW-Authenticate)

### 3. Rank Phase

The rank phase assigns a **ReapScore** to each endpoint based on multiple signals.

#### ReapScore Algorithm

ReapScore is a weighted composite of four subscores (0-100 each):

**HarvestIndex (🌱)** — Discovery & Surface Expansion (weight: 30%)
- Source diversity (katana, gau, path packs)
- New hosts/vhosts discovery
- Path depth and uniqueness
- Application content types (HTML, JSON)

**JuiceScore (🧪)** — Input & Sensitivity Potential (weight: 35%)
- Presence of query parameters
- High-signal parameter names (id, token, redirect, file, etc.)
- Path keywords (admin, login, api, graphql, etc.)
- Dynamic extensions (.php, .aspx, .jsp)

**AccessSignal (🚪)** — Authentication & Authorization Hints (weight: 20%)
- HTTP 401 (Unauthorized) and 403 (Forbidden) responses
- Redirects to login/auth pages
- WWW-Authenticate headers
- Set-Cookie headers

**AnomalySignal (⚠️)** — Errors & Unusual Responses (weight: 15%)
- 5xx server errors
- Slow responses (>2 seconds)
- Large responses (>1MB)

Module: `webreaper/scoring.py`

#### Scoring Confidence

Each ReapScore includes a confidence metric (0.0-1.0) based on the completeness of metadata available. More observed signals = higher confidence.

### 4. Report Phase

The report phase generates actionable output in multiple formats.

#### Output Files

- **findings.json** — Complete structured data with all endpoints and scoring details
- **REPORT.md** — Technical report with top 25 endpoints, ranked by ReapScore
- **ELI5-REPORT.md** — Plain-language summary for non-technical stakeholders
- **urls.txt** — Simple list of all discovered URLs
- **hosts.txt** — List of all discovered hosts
- **raw_*.txt** — Raw output from each discovery tool (katana, gau, httpx)
- **run.log** — Timestamped execution log

Module: `webreaper/report/render_md.py`

## Data Flow

```
Target URL
    │
    ▼
┌─────────────────┐
│  HARVEST PHASE  │
├─────────────────┤
│ • katana crawl  │
│ • gau history   │
│ • path packs    │
└────────┬────────┘
         │ URLs
         ▼
┌─────────────────┐
│ URL FILTERING   │
├─────────────────┤
│ • scope check   │
│ • path filter   │
│ • dedup         │
└────────┬────────┘
         │ Filtered URLs
         ▼
┌─────────────────┐
│  PROBE PHASE    │
├─────────────────┤
│ • httpx probe   │
│ • metadata      │
└────────┬────────┘
         │ Endpoints + Metadata
         ▼
┌─────────────────┐
│  RANK PHASE     │
├─────────────────┤
│ • ReapScore     │
│ • subscores     │
│ • confidence    │
└────────┬────────┘
         │ Scored Endpoints
         ▼
┌─────────────────┐
│  REPORT PHASE   │
├─────────────────┤
│ • JSON export   │
│ • MD reports    │
│ • ELI5 summary  │
└─────────────────┘
```

## Module Structure

```
webreaper/
├── __init__.py           # Package initialization
├── __main__.py           # Entry point for python -m webreaper
├── cli.py                # CLI interface (Typer), main orchestration
├── scoring.py            # ReapScore algorithm and weights
├── paths_packs.py        # Path wordlists and URL generation
├── dependency_checker.py # Tool dependency checking and installation
├── parsers/              # Tool output parsers
│   ├── httpx.py          # httpx JSON parser
│   ├── katana.py         # katana line parser
│   ├── gau.py            # gau line parser
│   ├── gospider.py       # gospider line parser
│   └── hakrawler.py      # hakrawler line parser
├── report/               # Report generation
│   └── render_md.py      # Markdown report rendering
└── tools/                # Extensible tools system
    ├── __init__.py       # Tools module initialization
    ├── registry.py       # Tool registry and base classes
    ├── robots_sitemap.py # robots.txt/sitemap.xml discovery
    ├── security_headers.py # Security header analysis
    ├── content_patterns.py # Content pattern detection
    └── technology_scorer.py # Technology-based scoring
```

## Tools System

webReaper includes a modular tools system for extending discovery, analysis, and scoring capabilities.

### Tool Categories

1. **Discovery Tools** (`DiscoveryTool`)
   - Find URLs and endpoints from various sources
   - Examples: robots/sitemap parser, DNS enumeration, CT log parser
   - Contribute to HarvestIndex subscore

2. **Analyzer Tools** (`AnalyzerTool`)
   - Extract metadata and signals from HTTP responses
   - Examples: security headers, content patterns, form analysis
   - Provide data for scoring calculations

3. **Scoring Tools** (`ScoringTool`)
   - Contribute bonus scores based on specific conditions
   - Examples: technology scorer, input vector scorer
   - Enhance JuiceScore and other subscores

### Tool Registry

The global tool registry manages all available tools:

```python
from webreaper.tools import get_global_registry

registry = get_global_registry()

# List all registered tools
for tool in registry.list_tools():
    print(f"{tool.name}: {tool.description}")

# Register custom tools
registry.register_discovery(MyCustomDiscoveryTool())
registry.register_analyzer(MyAnalyzerTool())
registry.register_scorer(MyScoringTool())
```

### Built-in Tools

**Discovery Tools:**
- `robots_sitemap` - Parses robots.txt and sitemap.xml files (enabled by default)
  - Fetches /robots.txt and extracts Disallow/Allow paths
  - Follows Sitemap directives and parses XML
  - Tags URLs with "robots" or "sitemap" source

**Analyzer Tools:**
- `security_headers` - Analyzes HTTP security headers
  - Detects missing security headers (CSP, HSTS, X-Frame-Options, etc.)
  - Identifies CORS misconfigurations
  - Analyzes cookie security flags
  
- `content_patterns` - Detects sensitive data patterns in response bodies
  - API keys, tokens, credentials
  - Error messages and stack traces
  - Debug/development information
  - API documentation patterns

**Scoring Tools:**
- `technology_scorer` - Provides bonus scores for detected technologies
  - Admin panels (phpMyAdmin, Adminer): +25
  - Debug tools (XDebug, phpinfo): +30
  - Legacy frameworks (Struts): +25
  - Database interfaces: +20
  - SSO/auth systems: +20

See [TOOLS.md](TOOLS.md) for complete documentation.

## Configuration & Extensibility

### CLI Configuration

All major behaviors are configurable via CLI flags:
- Discovery tool toggles (`--katana/--no-katana`, `--gau/--no-gau`, `--robots/--no-robots`, `--gospider/--no-gospider`, `--hakrawler/--no-hakrawler`)
- Rate limiting and threading (`--httpx-threads`, `--katana-rate`)
- Filtering rules (`--scope`, `--exclude-ext`, `--max-params`)
- Path pack selection (`--paths-pack`, `--paths-extra`)
- Safety modes (`--safe/--active`)

### Scoring Weight Customization

The default scoring weights can be overridden programmatically:

```python
from webreaper.scoring import compute_reapscore

custom_weights = {
    "harvest_index": 0.20,
    "juice_score": 0.40,
    "access_signal": 0.30,
    "anomaly_signal": 0.10,
}

result = compute_reapscore(
    url="https://example.com/api/user?id=123",
    sources=["katana"],
    status=200,
    weights=custom_weights
)
```

### Adding New Discovery Tools

There are two approaches to adding discovery tools:

**Approach 1: Using the Tools System (Recommended)**

Create a class implementing the `DiscoveryTool` interface:

```python
from webreaper.tools import DiscoveryTool, ToolMetadata, ToolCategory, get_global_registry

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
        urls = []
        # Your discovery logic here
        return urls

# Register the tool
registry = get_global_registry()
registry.register_discovery(MyDiscoveryTool())
```

**Approach 2: Direct Parser Integration (Legacy)**

To integrate a new external tool directly:

1. Create a parser in `webreaper/parsers/<tool>.py`
2. Implement a function that returns `List[str]` of URLs
3. Add CLI options in `cli.py` (`--<tool>/--no-<tool>`)
4. Invoke the tool in `_reap_impl()` and tag URLs with the source
5. Update documentation

Example parser interface:
```python
def parse_<tool>_lines(output: str) -> List[str]:
    """Parse tool output and return valid URLs."""
    urls = []
    for line in output.splitlines():
        # Parse and validate URL
        urls.append(validated_url)
    return urls
```

## Performance Considerations

- **Rate Limiting**: All tools support rate limiting to avoid overwhelming targets
- **Threading**: httpx uses configurable threading for parallel probing
- **Capping**: Hard limits on URLs processed (`--max-urls`) prevent resource exhaustion
- **Timeouts**: Per-tool timeouts prevent hanging on unresponsive targets
- **Incremental Processing**: URLs are filtered before probing, not after

## Safety & Ethics

webReaper includes safety controls to minimize risk during reconnaissance:

- **Safe Mode (default)**: Disables JavaScript execution in katana
- **Active Mode**: Enables JavaScript (`-jc` flag) for deeper crawling
- **Rate Limiting**: Default limits prevent accidental DoS
- **Scope Controls**: Prevent unintended scanning of out-of-scope targets
- **No Exploitation**: webReaper is discovery-only, no active exploitation

## Recent Enhancements

Version 0.6.5+ includes:

1. **Modular Tools System**
   - Extensible framework for discovery, analyzer, and scoring tools
   - Tool registry for managing custom extensions
   - Base classes for creating new tools

2. **robots.txt/sitemap.xml Discovery**
   - Automatic fetching and parsing of robots.txt
   - Sitemap XML parsing with support for sitemap indexes
   - Integration into HarvestIndex scoring (+20 for robots, +18 for sitemap)

3. **Advanced Analysis Tools**
   - Security headers analyzer for detecting missing protections
   - Content pattern detector for sensitive data and errors
   - Technology scorer for high-value tech stacks

4. **gospider/hakrawler Integration**
   - Additional crawler options for comprehensive URL discovery
   - Noise control and filtering options

5. **Enhanced Documentation**
   - TOOLS.md with complete tools documentation
   - Updated ARCHITECTURE.md with tools system details
   - SIEM_INTEGRATION.md for enterprise workflows

## Future Enhancements

Planned features documented in the roadmap:
1. **Advanced Content Analysis** - JavaScript API extraction and form analysis
2. **DNS Enumeration Tool** - Subdomain discovery via DNS queries
3. **Certificate Transparency** - CT log parsing for subdomain discovery
4. **Wayback Machine Integration** - Additional historical URL source beyond gau
5. **Common Crawl Parser** - Parse Common Crawl data for URLs
6. **Form Analyzer** - Detect and analyze HTML forms for input vectors
7. **JavaScript Analyzer** - Extract API endpoints from JavaScript files
8. **Enhanced Noise Filtering** - ML-based false positive reduction
9. **Custom Report Templates** - User-defined report formats
10. **Distributed Scanning** - Multi-node scanning for large targets

## Dependencies

- **typer** — CLI framework
- **External Tools** (must be installed separately):
  - httpx (required)
  - katana (optional)
  - gau (optional)
  - gospider (planned)
  - hakrawler (planned)

## Version History

- **0.6.4** — Current release with katana, gau, httpx, and path packs
- Future versions will add gospider, hakrawler, and enhanced reporting
