# webReaper

**webReaper** is a lightweight web reconnaissance and endpoint-ranking tool designed to help security professionals quickly identify the most interesting parts of a web attack surface.

It collects URLs from multiple discovery sources, probes them for behavior and metadata, and ranks results using a novel **ReapScore** so you know **where to start first**.

## Why webReaper?

Web reconnaissance often produces hundreds or thousands of URLs, making it difficult to decide what deserves attention first.  
webReaper focuses on **prioritization over volume**, surfacing high-signal endpoints that are more likely to be useful during manual testing.

## How webReaper Works

```
Target
  │
  ▼
┌─────────────────┐
│  HARVEST PHASE  │  Crawling (katana)
├─────────────────┤  Historical URLs (gau)
│  URL Discovery  │  Known paths (path packs)
└────────┬────────┘  robots.txt / sitemap.xml (planned)
         │
         ▼
┌─────────────────┐
│   PROBE PHASE   │  HTTP status & redirects
├─────────────────┤  Content type & title
│  HTTP Metadata  │  Technology detection (httpx)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RANK PHASE    │  Discovery value
├─────────────────┤  Input/parameter signals
│   ReapScore     │  Access hints (auth/forbidden)
└────────┬────────┘  Anomalies (errors/timing)
         │
         ▼
┌─────────────────┐
│  REPORT PHASE   │  Ranked endpoints (ReapScore)
├─────────────────┤  Markdown + JSON output
│   Structured    │  Technical + ELI5 formats
└─────────────────┘
```

webReaper does not exploit targets — it provides discovery, context, and prioritization to guide manual investigation.

## Key Features

- 🎯 **Smart Prioritization**: ReapScore algorithm ranks endpoints by testing value
- 🕷️ **Multi-Source Discovery**: Integrates katana, gau, and intelligent path guessing
- ⚡ **Fast Probing**: Configurable threading and rate limiting with httpx
- 📊 **Dual Reports**: Technical (JSON/MD) and beginner-friendly (ELI5) formats
- 🔧 **Highly Configurable**: Fine-tune filtering, scoping, and tool behavior
- 🛡️ **Safety First**: Safe mode enabled by default, with ethical controls

## Quick Start

### Prerequisites

**Required:**
- Python 3.10 or higher
- [httpx](https://github.com/projectdiscovery/httpx) (ProjectDiscovery)

**Optional (for full functionality):**
- [katana](https://github.com/projectdiscovery/katana) (ProjectDiscovery) — web crawler
- [gau](https://github.com/lc/gau) — historical URL aggregator
- [gospider](https://github.com/jaeles-project/gospider) — fast web spider (optional)
- [hakrawler](https://github.com/hakluke/hakrawler) — fast web crawler (optional)

### Installation

#### Option 1: Automated Setup (Recommended for Kali Linux)

The setup script automatically installs all dependencies including Go and required tools:

```bash
# Clone the repository
git clone https://github.com/gh0stshe11/webreaper.git
cd webreaper

# Run the automated setup script
./setup.sh

# Create virtual environment and install webReaper
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The `setup.sh` script will:
- Check and install Go if not present
- Install required tools (`httpx`, `katana`, `gau`)
- Install optional tools (`gospider`, `hakrawler`)
- Configure your PATH environment variables
- Provide helpful error messages and next steps

#### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/gh0stshe11/webreaper.git
cd webreaper

# Install Go (if not already installed)
# Visit https://go.dev/doc/install

# Install required tools
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/katana/cmd/katana@latest
go install github.com/lc/gau/v2/cmd/gau@latest

# Install optional tools
go install github.com/jaeles-project/gospider@latest
go install github.com/hakluke/hakrawler@latest

# Ensure Go binaries are in PATH
export PATH=$PATH:$HOME/go/bin

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install webReaper
pip install -e .
```

#### Automatic Dependency Installation

webReaper can automatically check and install missing tools at runtime:

```bash
# Enable automatic installation without prompting (useful for automation)
export WEBREAPER_AUTO_INSTALL=true
webreaper reap https://example.com -o out/

# Or install interactively when prompted
webreaper reap https://example.com -o out/
# You'll be prompted to install any missing tools
```

### Troubleshooting

**Tools not found after installation:**

If you get errors about missing tools even after installation, ensure Go binaries are in your PATH:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$HOME/go/bin

# Reload your shell configuration
source ~/.bashrc  # or source ~/.zshrc
```

**Go not installed:**

If you don't have Go installed, either:
1. Run `./setup.sh` which will install it automatically
2. Visit https://go.dev/doc/install for manual installation

**Permission issues:**

If you encounter permission issues during setup:
```bash
# Make sure setup.sh is executable
chmod +x setup.sh

# Some operations may require sudo
sudo ./setup.sh
```

### Basic Usage

```bash
# Simple scan with default settings
webreaper reap https://example.com -o out/

# Advanced scan with custom filters
webreaper reap https://example.com -o out/ \
  --exclude-ext png,jpg,jpeg,gif,css,js,svg,ico,woff,woff2 \
  --exclude-path logout,signout \
  --max-params 8

# Scan with specific tools
webreaper reap https://example.com -o out/ \
  --katana --no-gau \
  --paths-pack api,auth

# List available path packs
webreaper packs
```

## CLI Options

### Commands

- `webreaper reap <target>` — Run full reconnaissance pipeline
- `webreaper scan <target>` — Alias for `reap` command
- `webreaper packs` — List available path packs

### Core Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --out` | `out/` | Output directory for results |
| `-q, --quiet` | `false` | Disable banner and progress output |
| `-v, --verbose` | `false` | Show detailed timing and stage info |
| `--safe/--active` | `--safe` | Safe mode (disables JS execution) |
| `--timeout` | `600` | Timeout in seconds per tool |

### Discovery Tools

| Option | Default | Description |
|--------|---------|-------------|
| `--katana/--no-katana` | `--katana` | Enable/disable katana web crawler |
| `--gau/--no-gau` | `--gau` | Enable/disable gau historical URLs |
| `--gospider/--no-gospider` | `--no-gospider` | Enable/disable gospider web crawler (optional) |
| `--hakrawler/--no-hakrawler` | `--no-hakrawler` | Enable/disable hakrawler web crawler (optional) |
| `--katana-depth` | `2` | Maximum crawl depth for katana |
| `--katana-rate` | `50` | Rate limit (requests/sec) for katana |
| `--katana-concurrency` | `5` | Concurrent connections for katana |
| `--gospider-depth` | `2` | Maximum crawl depth for gospider |
| `--gospider-concurrency` | `5` | Concurrent connections for gospider |
| `--hakrawler-depth` | `2` | Maximum crawl depth for hakrawler |
| `--gau-limit` | `1500` | Maximum URLs to fetch from gau |

### Path Discovery

| Option | Default | Description |
|--------|---------|-------------|
| `--paths/--no-paths` | `--paths` | Enable/disable path pack probing |
| `--paths-pack` | `common` | Comma-separated pack names (see `webreaper packs`) |
| `--paths-top` | `120` | Number of paths to include from packs |
| `--paths-extra` | `` | Comma-separated custom paths to add |

**Available packs:** `common`, `auth`, `api`, `ops`, `files`, `sensitive`, `admin`, `discovery`, `all`

### HTTP Probing

| Option | Default | Description |
|--------|---------|-------------|
| `--httpx-threads` | `25` | Number of concurrent httpx threads |
| `--httpx-rate` | `50` | Rate limit (requests/sec) for httpx |
| `--max-urls` | `1500` | Hard cap on total URLs to probe |

### Filtering & Scope

| Option | Default | Description |
|--------|---------|-------------|
| `--scope` | _(none)_ | Comma-separated hosts in scope (e.g., `example.com,api.example.com`) |
| `--no-subdomains` | `false` | Require exact host match (disable subdomain inclusion) |
| `--exclude-host` | _(none)_ | Comma-separated hosts to exclude |
| `--include-path` | _(none)_ | Only keep URLs with these path tokens (substring match) |
| `--exclude-path` | _(none)_ | Drop URLs with these path tokens (substring match) |
| `--exclude-ext` | _(none)_ | Drop URLs with these file extensions (e.g., `png,jpg,css,js`) |
| `--max-params` | `10` | Drop URLs with more than N query parameters |
| `--require-param` | `false` | Keep only URLs that have query parameters |

## Output

webReaper writes structured output to the specified directory:

| File | Description |
|------|-------------|
| `REPORT.md` | Ranked endpoints with ReapScore details (top 25) |
| `ELI5-REPORT.md` | Plain-language summary for non-technical stakeholders |
| `findings.json` | Complete machine-readable results with all metadata |
| `urls.txt` | Simple list of all discovered URLs |
| `hosts.txt` | List of all discovered hosts |
| `raw_katana_*.txt` | Raw output from katana crawler |
| `raw_gau_*.txt` | Raw output from gau historical URLs |
| `raw_httpx.jsonl` | Raw JSON-lines output from httpx |
| `run.log` | Timestamped execution log with timing info |

Start with the top-ranked endpoints in `REPORT.md` to guide further investigation.

### Understanding ReapScore

ReapScore is a 0-100 composite score made up of four weighted subscores:

#### 🌱 HarvestIndex (30%) — Discovery & Surface Expansion
- Source diversity (katana, gau, path packs)
- New hosts/vhosts discovery
- Path depth and uniqueness
- Application content types

#### 🧪 JuiceScore (35%) — Input & Sensitivity Potential
- Query parameters present
- High-signal parameter names (`id`, `token`, `redirect`, `file`, etc.)
- Path keywords (`admin`, `login`, `api`, `graphql`, etc.)
- Dynamic extensions (`.php`, `.aspx`, `.jsp`)

#### 🚪 AccessSignal (20%) — Authentication Hints
- HTTP 401 (Unauthorized) and 403 (Forbidden)
- Redirects to login/auth pages
- WWW-Authenticate and Set-Cookie headers

#### ⚠️ AnomalySignal (15%) — Errors & Oddities
- 5xx server errors
- Slow responses (>2 seconds)
- Large responses (>1MB)

**Example output:**
```
| Pri | ReapScore | Status | Sources | URL | Why | Subscores |
|---:|---:|---:|---|---|---|---|
| 🔴 | 78 | 403 | katana,gau | example.com/admin/users?id=1 | status:403; high_signal_params:id; path_keywords | 🌱H:45 🧪J:75 🚪A:35 ⚠️N:0 |
```

## Examples

### Basic Reconnaissance

```bash
# Scan a target with default settings
webreaper reap https://example.com -o results/
```

### API-Focused Scan

```bash
# Focus on API endpoints with relevant path packs
webreaper reap https://api.example.com -o api-results/ \
  --paths-pack api,ops \
  --include-path api,graphql,swagger \
  --exclude-ext html,css,js
```

### Subdomain-Aware Scope

```bash
# Scan with subdomain inclusion
webreaper reap https://example.com -o wide-scan/ \
  --scope example.com
  
# Scan with exact host matching (no subdomains)
webreaper reap https://example.com -o narrow-scan/ \
  --scope example.com \
  --no-subdomains
```

### Aggressive Scan (Active Mode)

```bash
# Enable JavaScript execution and increase limits
webreaper reap https://example.com -o aggressive/ \
  --active \
  --katana-depth 3 \
  --max-urls 3000 \
  --gau-limit 2000
```

### Quiet Mode for Automation

```bash
# Minimal console output, suitable for scripts
webreaper reap https://example.com -o automated/ --quiet

# Parse results programmatically
jq '.endpoints[] | select(.reap.score > 50)' automated/findings.json
```

## Architecture & Development

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

For SIEM integration patterns, see [SIEM_INTEGRATION.md](SIEM_INTEGRATION.md).

### Key Design Principles

1. **Prioritization over volume** — Surface high-signal endpoints first
2. **Modular tool integration** — Easy to add new crawlers and parsers
3. **Transparent scoring** — ReapScore reasons included in output
4. **Safety by default** — Conservative settings to avoid harm
5. **Community extensibility** — Plugin support for custom scoring functions

### Extending webReaper

- **Add new crawlers**: Create parser in `webreaper/parsers/`, integrate in CLI (see: gospider, hakrawler)
- **Customize scoring**: Modify weights and signals in `webreaper/scoring.py` or use extensions
- **Add path packs**: Extend wordlists in `webreaper/paths_packs.py`
- **New report formats**: Add renderers in `webreaper/report/`
- **SIEM integration**: Follow patterns in `SIEM_INTEGRATION.md`

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions.

## Roadmap

Recent enhancements (v0.6.4+):

- ✅ **gospider/hakrawler integration** — Additional crawler options with noise controls
- ✅ **Enhanced path packs** — More specialized wordlists (auth, sensitive files, APIs, admin, discovery)
- ✅ **Modular scoring system** — Community-contributed scoring extensions support
- ✅ **SIEM integration patterns** — Export formats for enterprise workflows
- ✅ **Comprehensive documentation** — ARCHITECTURE.md, CONTRIBUTING.md, SIEM_INTEGRATION.md

Planned future enhancements:

- [ ] **robots.txt/sitemap.xml fetching** — Automatic discovery file parsing
- [ ] **Improved noise filtering** — ML-based false positive reduction
- [ ] **Custom report templates** — User-defined report formats
- [ ] **Distributed scanning** — Multi-node scanning for large targets

## License

This project is open source. See LICENSE file for details.

## Credits

webReaper integrates the following excellent open-source tools:
- [httpx](https://github.com/projectdiscovery/httpx) by ProjectDiscovery
- [katana](https://github.com/projectdiscovery/katana) by ProjectDiscovery
- [gau](https://github.com/lc/gau) by lc

## Disclaimer

webReaper is intended for authorized security testing only. Users are responsible for obtaining proper authorization before scanning any target. The authors are not responsible for misuse or damage caused by this tool.

Always follow responsible disclosure practices and respect scope limitations.
