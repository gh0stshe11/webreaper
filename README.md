# webReaper

**webReaper** is a lightweight web reconnaissance and endpoint-ranking tool designed to help pentesters quickly identify the most interesting parts of a web attack surface.

It collects URLs from multiple discovery sources, probes them for behavior and metadata, and ranks results using a novel **ReapScore** so you know **where to start first**.

## Why webReaper?

Web reconnaissance often produces hundreds or thousands of URLs, making it difficult to decide what deserves attention first.  
webReaper focuses on **prioritization over volume**, surfacing high-signal endpoints that are more likely to be useful during manual testing.

## How webReaper Works (High Level)

```
Target
│
▼
[ Harvest ]
  ├─ Passive Sources
  │  ├─ robots.txt disallowed paths
  │  ├─ sitemap.xml entries
  │  ├─ Wayback Machine historical URLs
  │  └─ crt.sh subdomain enumeration
  └─ Active Sources (optional)
     ├─ Crawling
     └─ Known path discovery
│
▼
[ Probe ]
  ├─ HTTP headers analysis
  │  ├─ CORS configuration
  │  ├─ CSP policies
  │  ├─ HSTS settings
  │  └─ Cookie security flags
  └─ JavaScript extraction
     ├─ External JS files
     ├─ Inline scripts
     ├─ API endpoints
     └─ Sensitive patterns
│
▼
[ Rank ]
  ├─ Discovery value
  ├─ Input / parameter signals
  ├─ Access hints (auth / forbidden)
  ├─ Security signals
  └─ Anomalies
│
▼
[ Report ]
  ├─ Ranked endpoints (ReapScore)
  ├─ Markdown + JSON output
  └─ Security findings
```

webReaper does not exploit targets — it provides discovery, context, and prioritization to guide manual investigation.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Phase A Features

Phase A focuses on **passive reconnaissance** and **header-based enrichment**:

### Passive Harvesters
- **robots.txt**: Extract disallowed paths and convert to candidate URLs
- **sitemap.xml**: Parse sitemap and nested sitemaps for URL discovery
- **Wayback Machine**: Query CDX API for historical URLs
- **crt.sh**: Enumerate subdomains via SSL certificate transparency logs

### Enrichment Probes
- **Header Analysis**: Detect CORS misconfigurations, CSP weaknesses, missing HSTS, insecure cookies
- **JavaScript Extraction**: Parse HTML for JS files, inline scripts, API endpoints, and sensitive patterns

### Resume & Caching
- Raw data is cached in `raw_*.json` files
- Use `--resume` to skip re-harvesting and load from cache

## Usage

### Basic Passive Reconnaissance

```bash
# Harvest from all passive sources
webreaper reap example.com -o out/

# Harvest with verbose output
webreaper reap example.com -o out/ --verbose

# Specify which sources to use
webreaper reap example.com -o out/ --sources robots,sitemap,wayback

# Resume from cached data
webreaper reap example.com -o out/ --resume
```

### Advanced Options

```bash
# Dry run (show what would be done)
webreaper reap example.com -o out/ --dry-run --verbose

# Enable active probing (includes JS analysis)
webreaper reap example.com -o out/ --active

# Filter results by minimum score
webreaper reap example.com -o out/ --min-score 50

# Limit to top N results
webreaper reap example.com -o out/ --top 50

# Rate limiting and timeouts
webreaper reap example.com -o out/ \
  --rate-limit 10 \
  --timeout 20 \
  --concurrency 3
```

### Available Flags

- `--sources`: Comma-separated list of passive sources (robots,sitemap,wayback,crtsh)
- `--concurrency`: Concurrency level for harvesters (default: 5)
- `--timeout`: Timeout in seconds for HTTP requests (default: 30)
- `--user-agent`: User-Agent string for requests (default: webReaper/0.6.4)
- `--rate-limit`: Rate limit in requests per second (default: 50)
- `--out-dir`, `-o`: Output directory (default: out)
- `--resume`: Resume from cached data if available
- `--verbose`, `-v`: Verbose output
- `--dry-run`: Show what would be done without executing
- `--active`: Enable active probing (default is passive only)
- `--min-score`: Minimum ReapScore to include in report (default: 0)
- `--top`: Limit report to top N results (default: 100)

## Output

webReaper writes structured output to the specified directory:

- **REPORT.md** — ranked endpoints with scoring rationale
- **findings.json** — machine-readable results with full details
- **raw_*.json** files — cached raw data from each harvester source

Start with the top-ranked endpoints in REPORT.md to guide further investigation.

## Example Workflow

```bash
# 1. Initial passive harvest
webreaper reap target.com -o recon/target --verbose

# 2. Review findings
cat recon/target/REPORT.md

# 3. Re-run with active probing on interesting domains
webreaper reap target.com -o recon/target --active --resume

# 4. Filter to high-value targets
webreaper reap target.com -o recon/target --min-score 60 --top 20
```

## Architecture

```
webreaper/
├── cli.py                 # Click-based CLI
├── harvesters/            # Passive URL harvesters
│   ├── robots.py
│   ├── sitemap.py
│   ├── wayback.py
│   └── crtsh.py
├── probes/                # Enrichment probes
│   ├── headers.py
│   └── js_extractor.py
├── storage/               # Raw data caching
│   └── raw_store.py
├── parsers/               # Output parsers
├── report/                # Report generation
└── scoring.py             # ReapScore computation
```
