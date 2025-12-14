# webReaper

**webReaper** is a lightweight web reconnaissance and endpoint-ranking tool designed to help pentesters quickly identify the most interesting parts of a web attack surface.

It collects URLs from multiple discovery sources, probes them for behavior and metadata, and ranks results using a novel **ReapScore** so you know **where to start first**.

## Why webReaper?

Web reconnaissance often produces hundreds or thousands of URLs, making it difficult to decide what deserves attention first.  
webReaper focuses on **prioritization over volume**, surfacing high-signal endpoints that are more likely to be useful during manual testing.

## How webReaper Works (High Level)

Target
│
▼
[ Harvest ]

Crawling
Historical URLs
robots.txt / sitemap.xml
Known path discovery
│
▼
[ Probe ]

HTTP status & redirects
Content type
Technology detection
│
▼
[ Rank ]

Discovery value
Input / parameter signals
Access hints (auth / forbidden)
Anomalies
│
▼
[ Report ]

Ranked endpoints (ReapScore)
Markdown + JSON output


webReaper does not exploit targets — it provides discovery, context, and prioritization to guide manual investigation.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Basic Usage

```bash
webreaper reap https://example.com -o out/
```

### Phase A Features

Phase A introduces passive harvesters, header analysis, JS endpoint extraction, and an explainable ReapScore system.

**Quick Start (Passive Mode)**
```bash
# Passive reconnaissance only (no active probing)
webreaper reap https://example.com -o out/ --verbose

# Use specific sources
webreaper reap https://example.com --sources robots,sitemap,wayback -o out/

# Resume mode (skip harvesting if raw_* files exist)
webreaper reap https://example.com -o out/ --resume
```

**Active Probing**
```bash
# Enable header analysis and JS endpoint extraction
webreaper reap https://example.com -o out/ --active --verbose

# Active mode with custom concurrency and timeout
webreaper reap https://example.com -o out/ --active \
  --concurrency 20 \
  --timeout 15 \
  --rate-limit 10
```

**Filtering and Output Control**
```bash
# Filter results by minimum ReapScore
webreaper reap https://example.com -o out/ --active \
  --min-score 0.5 \
  --top 25

# Custom user agent
webreaper reap https://example.com -o out/ \
  --user-agent "MyScanner/1.0"
```

**Dry Run Mode**
```bash
# Test configuration without making requests
webreaper reap https://example.com --dry-run --verbose
```

### CLI Flags Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--sources` | `robots,sitemap,wayback,crtsh` | Comma-separated list of harvesters |
| `--concurrency` | `10` | Maximum concurrent requests |
| `--timeout` | `10` | Request timeout in seconds |
| `--user-agent` | `webReaper/0.6.4` | Custom User-Agent string |
| `--rate-limit` | `None` | Maximum requests per second |
| `-o, --out-dir` | `out` | Output directory |
| `--resume` | `False` | Skip harvesting if raw_* files exist |
| `-v, --verbose` | `False` | Verbose output |
| `--dry-run` | `False` | Dry run mode (no requests) |
| `--active` | `False` | Enable active probing (headers, JS) |
| `--min-score` | `0.0` | Minimum ReapScore threshold (0.0-1.0) |
| `--top` | `50` | Number of top endpoints in REPORT.md |
| `--verify-ssl` | `False` | Enable SSL certificate verification |

## Output

webReaper writes structured output to the specified directory:

- **REPORT.md** — Top-ranked endpoints with explainable ReapScore rationale
- **findings.json** — Machine-readable results with per-signal scores
- **raw_*.json** — Cached raw data from each harvester (robots, sitemap, wayback, crtsh)

The ReapScore (0.0-1.0) combines multiple signals across categories:
- **Discovery** (20%): Source novelty, path depth, subdomain discovery
- **Params** (25%): Query parameters, high-value param names
- **Sensitivity** (30%): Auth keywords, status codes (401/403), header security signals
- **Tech** (10%): Technology detection, JS endpoints discovered
- **Anomalies** (10%): Server errors, slow responses, missing security headers
- **Third Party** (5%): External service detection

Start with the top-ranked endpoints in REPORT.md to guide further investigation.
