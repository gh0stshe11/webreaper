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

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

## Usage

webreaper reap https://example.com -o out/

webreaper reap https://example.com -o out/ \
  --exclude-ext png,jpg,jpeg,gif,css,js,svg,ico,woff,woff2 \
  --exclude-path logout,signout \
  --max-params 8

## Output

webReaper writes structured output to the specified directory:
REPORT.md — ranked endpoints with scoring rationale
ELI5-REPORT.md — plain-language summary of findings
findings.json — machine-readable results
raw_* files — raw discovery data from each source

Start with the top-ranked endpoints in REPORT.md to guide further investigation.
