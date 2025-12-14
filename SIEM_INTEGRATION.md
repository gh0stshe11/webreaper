# SIEM Integration Guide

This document describes how to integrate webReaper output with Security Information and Event Management (SIEM) systems and other security tools.

## Output Formats

webReaper generates multiple output formats suitable for automation and integration:

### JSON Format (findings.json)

The primary machine-readable output. Contains complete endpoint data with scoring details.

**Structure:**
```json
{
  "target": "https://example.com",
  "timestamp": "2025-12-14T15:23:16Z",
  "profile": "safe",
  "limits": {
    "max_urls": 1500,
    "gau_limit": 1500,
    "httpx_threads": 25,
    "httpx_rate": 50,
    "katana_depth": 2,
    "katana_rate": 50,
    "katana_concurrency": 5,
    "use_katana": true,
    "use_gau": true
  },
  "filters": {
    "scope": ["example.com"],
    "allow_subdomains": true,
    "exclude_host": [],
    "include_path": [],
    "exclude_path": [],
    "exclude_ext": [".png", ".jpg"],
    "max_params": 10,
    "require_param": false
  },
  "summary": {
    "hosts": 3,
    "urls_total": 245,
    "urls_unique": 198,
    "top_reapscore": 78
  },
  "endpoints": [
    {
      "url": "https://example.com/admin/users?id=1",
      "host": "example.com",
      "path": "/admin/users",
      "status": 403,
      "content_type": "text/html",
      "title": "Forbidden",
      "tech": ["nginx"],
      "sources": ["katana", "httpx"],
      "reap": {
        "score": 78,
        "subs": {
          "harvest_index": 45,
          "juice_score": 75,
          "access_signal": 35,
          "anomaly_signal": 0
        },
        "reasons": [
          "source:katana (+10 H)",
          "high_signal_params:id (+20 J)",
          "status:403 (+35 A)"
        ],
        "confidence": 0.87,
        "weights": {
          "harvest_index": 0.30,
          "juice_score": 0.35,
          "access_signal": 0.20,
          "anomaly_signal": 0.15
        }
      }
    }
  ]
}
```

### Text Formats

- **urls.txt** — Newline-separated list of all discovered URLs
- **hosts.txt** — Newline-separated list of all discovered hosts

## SIEM Integration Patterns

### Splunk

#### Method 1: File Monitor Input

1. Configure webReaper to write to a monitored directory:
   ```bash
   webreaper reap https://example.com -o /var/log/webreaper/$(date +%Y%m%d_%H%M%S)/
   ```

2. Configure Splunk inputs.conf:
   ```ini
   [monitor:///var/log/webreaper/*/findings.json]
   sourcetype = webreaper:json
   index = security
   disabled = false
   ```

3. Create field extractions in props.conf:
   ```ini
   [webreaper:json]
   INDEXED_EXTRACTIONS = json
   KV_MODE = json
   TIMESTAMP_FIELDS = timestamp
   TIME_FORMAT = %Y-%m-%dT%H:%M:%SZ
   ```

4. Example Splunk queries:
   ```spl
   # High-risk endpoints
   index=security sourcetype=webreaper:json endpoints{}.reap.score>70
   | table endpoints{}.url endpoints{}.reap.score endpoints{}.status
   
   # Authentication-related findings
   index=security sourcetype=webreaper:json endpoints{}.reap.subs.access_signal>30
   | table endpoints{}.url endpoints{}.path endpoints{}.status
   
   # New vhosts/subdomains discovered
   index=security sourcetype=webreaper:json endpoints{}.reap.reasons="*new_host/vhost*"
   | stats count by endpoints{}.host
   ```

#### Method 2: HTTP Event Collector (HEC)

Convert findings.json to HEC-compatible events:

```python
#!/usr/bin/env python3
import json
import requests

def send_to_splunk_hec(findings_file, hec_url, hec_token):
    with open(findings_file) as f:
        data = json.load(f)
    
    headers = {
        "Authorization": f"Splunk {hec_token}",
        "Content-Type": "application/json"
    }
    
    for endpoint in data.get("endpoints", []):
        event = {
            "time": data["timestamp"],
            "sourcetype": "webreaper:endpoint",
            "event": {
                "target": data["target"],
                "url": endpoint["url"],
                "host": endpoint["host"],
                "path": endpoint["path"],
                "status": endpoint["status"],
                "reapscore": endpoint["reap"]["score"],
                "harvest_index": endpoint["reap"]["subs"]["harvest_index"],
                "juice_score": endpoint["reap"]["subs"]["juice_score"],
                "access_signal": endpoint["reap"]["subs"]["access_signal"],
                "anomaly_signal": endpoint["reap"]["subs"]["anomaly_signal"],
                "sources": endpoint["sources"],
                "reasons": endpoint["reap"]["reasons"],
            }
        }
        requests.post(hec_url, headers=headers, json=event)

# Usage
send_to_splunk_hec(
    "out/findings.json",
    "https://splunk.example.com:8088/services/collector",
    "your-hec-token-here"
)
```

### Elastic Stack (ELK)

#### Filebeat Configuration

1. Configure webReaper output location:
   ```bash
   webreaper reap https://example.com -o /var/log/webreaper/latest/
   ```

2. Configure filebeat.yml:
   ```yaml
   filebeat.inputs:
   - type: log
     enabled: true
     paths:
       - /var/log/webreaper/*/findings.json
     json.keys_under_root: true
     json.add_error_key: true
     fields:
       log_type: webreaper
   
   output.elasticsearch:
     hosts: ["https://elasticsearch.example.com:9200"]
     index: "webreaper-%{+yyyy.MM.dd}"
   
   setup.ilm.enabled: false
   setup.template.name: "webreaper"
   setup.template.pattern: "webreaper-*"
   ```

3. Create Elasticsearch index template:
   ```json
   {
     "index_patterns": ["webreaper-*"],
     "mappings": {
       "properties": {
         "timestamp": { "type": "date" },
         "target": { "type": "keyword" },
         "endpoints": {
           "type": "nested",
           "properties": {
             "url": { "type": "keyword" },
             "host": { "type": "keyword" },
             "path": { "type": "keyword" },
             "status": { "type": "integer" },
             "reap": {
               "properties": {
                 "score": { "type": "integer" },
                 "confidence": { "type": "float" }
               }
             }
           }
         }
       }
     }
   }
   ```

4. Example Kibana queries:
   ```
   # High-risk endpoints
   endpoints.reap.score: [70 TO *]
   
   # Authentication issues
   endpoints.reap.subs.access_signal: [30 TO *]
   
   # 5xx errors
   endpoints.status: [500 TO 599]
   ```

### QRadar

#### Custom Log Source

1. Configure webReaper for syslog output (wrapper script):
   ```bash
   #!/bin/bash
   OUTPUT_DIR="/tmp/webreaper/$(date +%s)"
   webreaper reap "$1" -o "$OUTPUT_DIR" --quiet
   
   # Send high-priority findings to syslog
   jq -r '.endpoints[] | select(.reap.score > 50) | 
     "webreaper[" + (.reap.score|tostring) + "]: " + .url + 
     " (status=" + (.status|tostring) + ", reasons=" + (.reap.reasons|join(", ")) + ")"' \
     "$OUTPUT_DIR/findings.json" | logger -t webreaper -p local0.info
   ```

2. Configure QRadar log source:
   - Log Source Type: Syslog
   - Log Source Identifier: webreaper
   - Parse using custom DSM

### Microsoft Sentinel

#### Azure Log Analytics Ingestion

```python
import json
import datetime
import hashlib
import hmac
import base64
import requests

def post_data_to_sentinel(customer_id, shared_key, body, log_type):
    method = 'POST'
    content_type = 'application/json'
    resource = '/api/logs'
    rfc1123date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    content_length = len(body)
    signature = build_signature(customer_id, shared_key, rfc1123date, content_length, method, content_type, resource)
    uri = f'https://{customer_id}.ods.opinsights.azure.com{resource}?api-version=2016-04-01'
    
    headers = {
        'content-type': content_type,
        'Authorization': signature,
        'Log-Type': log_type,
        'x-ms-date': rfc1123date
    }
    
    response = requests.post(uri, data=body, headers=headers)
    return response.status_code

def build_signature(customer_id, shared_key, date, content_length, method, content_type, resource):
    x_headers = f'x-ms-date:{date}'
    string_to_hash = f'{method}\n{content_length}\n{content_type}\n{x_headers}\n{resource}'
    bytes_to_hash = bytes(string_to_hash, encoding="utf-8")  
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()).decode()
    authorization = f"SharedKey {customer_id}:{encoded_hash}"
    return authorization

# Usage
with open('out/findings.json') as f:
    data = json.load(f)

# Send each endpoint as separate event
for endpoint in data.get('endpoints', []):
    event = {
        'TimeGenerated': data['timestamp'],
        'Target': data['target'],
        'URL': endpoint['url'],
        'Host': endpoint['host'],
        'Path': endpoint['path'],
        'Status': endpoint['status'],
        'ReapScore': endpoint['reap']['score'],
        'HarvestIndex': endpoint['reap']['subs']['harvest_index'],
        'JuiceScore': endpoint['reap']['subs']['juice_score'],
        'AccessSignal': endpoint['reap']['subs']['access_signal'],
        'AnomalySignal': endpoint['reap']['subs']['anomaly_signal'],
        'Sources': ','.join(endpoint['sources']),
        'Reasons': '; '.join(endpoint['reap']['reasons'])
    }
    
    body = json.dumps([event])
    post_data_to_sentinel('YOUR_WORKSPACE_ID', 'YOUR_SHARED_KEY', body, 'WebReaper')
```

## Automation Workflows

### CI/CD Integration

#### GitLab CI Example

```yaml
webreaper_scan:
  stage: security
  image: python:3.10
  before_script:
    - pip install -e .
    - apt-get update && apt-get install -y httpx katana gau
  script:
    - webreaper reap https://$CI_ENVIRONMENT_URL -o scan-results/ --quiet
    - jq '.summary' scan-results/findings.json
  artifacts:
    when: always
    paths:
      - scan-results/
    reports:
      junit: scan-results/findings.json
  allow_failure: true
```

#### GitHub Actions Example

```yaml
name: WebReaper Scan

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install webReaper
        run: |
          pip install -e .
          
      - name: Install tools
        run: |
          go install github.com/projectdiscovery/httpx/cmd/httpx@latest
          go install github.com/projectdiscovery/katana/cmd/katana@latest
          
      - name: Run scan
        run: |
          webreaper reap ${{ secrets.TARGET_URL }} -o results/ --quiet
          
      - name: Upload to security platform
        env:
          SIEM_API_KEY: ${{ secrets.SIEM_API_KEY }}
        run: |
          python scripts/upload_to_siem.py results/findings.json
          
      - name: Archive results
        uses: actions/upload-artifact@v3
        with:
          name: webreaper-scan
          path: results/
```

### Alert Rules

#### Splunk Alert Examples

High-risk endpoint discovered:
```spl
index=security sourcetype=webreaper:json endpoints{}.reap.score>70
| dedup endpoints{}.url
| table _time target endpoints{}.url endpoints{}.status endpoints{}.reap.score
| outputlookup webreaper_high_risk.csv
```

New admin panel found:
```spl
index=security sourcetype=webreaper:json endpoints{}.path="*/admin*" OR endpoints{}.path="*/administrator*"
| dedup endpoints{}.url
| eval alert_message="New admin panel discovered: " . endpoints{}.url
| sendemail to="security@example.com" subject="WebReaper Alert"
```

#### Elasticsearch Watcher Example

```json
{
  "trigger": {
    "schedule": {
      "interval": "1h"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["webreaper-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                { "range": { "timestamp": { "gte": "now-1h" } } },
                { "range": { "endpoints.reap.score": { "gte": 70 } } }
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total": {
        "gt": 0
      }
    }
  },
  "actions": {
    "send_email": {
      "email": {
        "to": "security@example.com",
        "subject": "WebReaper: High-risk endpoints found",
        "body": "{{ctx.payload.hits.total}} high-risk endpoints discovered"
      }
    }
  }
}
```

## Best Practices

1. **Scheduled Scanning**: Run webReaper on a schedule (daily/weekly) for continuous monitoring
2. **Baseline Establishment**: Create baseline of expected endpoints and alert on deviations
3. **Score Thresholds**: Tune ReapScore thresholds based on your environment (e.g., >70 = critical, >40 = medium)
4. **Trend Analysis**: Track changes in endpoint counts, new hosts, and score distributions over time
5. **Correlation**: Correlate webReaper findings with vulnerability scanner results and WAF logs
6. **Retention**: Keep historical findings.json for trend analysis (suggest 90+ days)
7. **Privacy**: Sanitize sensitive data (tokens, session IDs) before sending to SIEM

## Data Retention

Recommended retention periods:
- **findings.json**: 90 days (for trend analysis)
- **REPORT.md**: 30 days (for manual review)
- **raw_* files**: 7 days (for debugging)

## Compliance Considerations

When integrating with SIEM:
- Ensure findings.json doesn't contain sensitive data (passwords, tokens)
- Apply data classification tags based on ReapScore
- Implement access controls for high-score findings
- Consider data residency requirements for cloud SIEM platforms

## Support & Community Extensions

For community-contributed SIEM integrations and automation scripts, see:
- GitHub Issues with `siem-integration` label
- Community discussions on integrations

To contribute your own integration pattern, submit a PR with documentation and example scripts.
