from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

def _short(url: str, n: int = 90) -> str:
    return url if len(url) <= n else url[:n-3] + "..."

def _score_badge(score: int) -> str:
    if score >= 70:
        return "🔴"
    if score >= 40:
        return "🟠"
    if score >= 20:
        return "🟢"
    return "⚪"

def _fmt_subs(subs: dict) -> str:
    return f"🌱H:{subs.get('harvest_index',0)} 🧪J:{subs.get('juice_score',0)} 🚪A:{subs.get('access_signal',0)} ⚠️N:{subs.get('anomaly_signal',0)}"

def render_report_md(findings: Dict[str, Any]) -> str:
    eps: List[Dict[str, Any]] = findings.get("endpoints", [])
    eps = sorted(eps, key=lambda e: int(e.get("reap", {}).get("score", 0)), reverse=True)

    lines: List[str] = []

    # Markdown-safe banner
    lines.append("```")
    lines.append("  w e b R e a p e r")
    lines.append("        ╱╲")
    lines.append("       ╱  ╲")
    lines.append("  probe → harvest → rank → report")
    lines.append("          ╲")
    lines.append("```")
    lines.append("")

    lines.append("# webReaper Report")
    lines.append("")
    lines.append(f"**Target:** `{findings.get('target','')}`  ")
    lines.append(f"**Timestamp:** `{findings.get('timestamp','')}`  ")
    lines.append(f"**Profile:** `{findings.get('profile','')}`")
    lines.append("")

    lines.append("## ReapScore Signals")
    lines.append("")
    lines.append("- 🔴 **High** (70–100)")
    lines.append("- 🟠 **Medium** (40–69)")
    lines.append("- 🟢 **Low** (20–39)")
    lines.append("- ⚪ **Noise** (<20)")
    lines.append("")
    lines.append("### Subscores")
    lines.append("")
    lines.append("- 🌱 HarvestIndex (discovery / surface expansion)")
    lines.append("- 🧪 JuiceScore (input / sensitivity potential)")
    lines.append("- 🚪 AccessSignal (auth / forbidden / redirects)")
    lines.append("- ⚠️ AnomalySignal (errors / slow / odd responses)")
    lines.append("")

    lines.append("## Summary")
    s = findings.get("summary", {})
    lines.append("")
    lines.append(f"- Hosts: **{s.get('hosts',0)}**")
    lines.append(f"- URLs (total / unique): **{s.get('urls_total',0)} / {s.get('urls_unique',0)}**")
    lines.append(f"- Top ReapScore: **{s.get('top_reapscore',0)}**")
    lines.append("")
    lines.append("## Top Endpoints (by ReapScore)")
    lines.append("")
    lines.append("| Pri | ReapScore | Status | Sources | URL | Why | Subscores |")
    lines.append("|---:|---:|---:|---|---|---|---|")
    for e in eps[:25]:
        reap = e.get("reap", {})
        subs = reap.get("subs", {})
        why = "; ".join((reap.get("reasons") or [])[:3])
        score = int(reap.get("score", 0))
        lines.append(
            f"| {_score_badge(score)} | {score} | {e.get('status','')} | `{','.join(e.get('sources',[]))}` | "
            f"`{_short(e.get('url',''))}` | {why} | {_fmt_subs(subs)} |"
        )
    lines.append("")
    return "\n".join(lines)

def write_report(findings_path: Path, out_path: Path) -> None:
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    out_path.write_text(render_report_md(data), encoding="utf-8")


def write_eli5_report(findings_json: Path, out_md: Path) -> None:
    """Write a short ELI5 summary of what happened and what was found."""
    data = json.loads(findings_json.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    endpoints = data.get("endpoints", []) or []
    target = data.get("target", "")

    hosts = summary.get("hosts", 0)
    urls_total = summary.get("urls_total", 0)
    urls_unique = summary.get("urls_unique", 0)
    top_score = summary.get("top_reapscore", 0)
    
    # Use heapq for efficient top-k selection with large endpoint lists
    if len(endpoints) > 100:
        import heapq
        top = heapq.nlargest(5, endpoints, key=lambda e: e.get("reap", {}).get("score", 0))
    else:
        top = sorted(endpoints, key=lambda e: e.get("reap", {}).get("score", 0), reverse=True)[:5]

    lines: list[str] = []
    lines.append("# webReaper ELI5 Report\n")
    lines.append(f"**Target:** `{target}`\n")
    lines.append("## What webReaper did\n")
    lines.append("- It **collected URLs** from your enabled sources (crawl/history/known paths).\n")
    lines.append("- It **probed** those URLs to see which ones respond and captured light metadata (status/title/tech).\n")
    lines.append("- It **ranked** endpoints so you can start with the highest-signal targets first.\n")
    lines.append("## What it found\n")
    lines.append(f"- Hosts: **{hosts}**\n")
    lines.append(f"- URLs (total / unique): **{urls_total} / {urls_unique}**\n")
    lines.append(f"- Top ReapScore: **{top_score}**\n")
    if top:
        lines.append("\n## Top 5 endpoints to look at first\n")
        for e in top:
            reap = e.get("reap", {}) or {}
            score = reap.get("score", 0)
            url = e.get("url", "")
            why = "; ".join(reap.get("reasons", [])[:3])
            lines.append(f"- **{score}** — {url}\n  - {why}\n")
    lines.append("\n## What to do next\n")
    lines.append("- Open the top endpoints and look for **login pages**, **parameters**, **API docs**, and **odd errors**.\n")
    lines.append("- Use those observations to guide your manual testing (auth, input handling, access control).\n")

    out_md.write_text("\n".join(lines), encoding="utf-8")
