"""Output exporters for webReaper findings."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


def write_findings_json(findings: Dict[str, Any], output_path: Path) -> None:
    """
    Write findings to JSON file.
    
    Args:
        findings: Dictionary containing all findings
        output_path: Path to output JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)


def write_report_md(findings: Dict[str, Any], output_path: Path, top_n: int = 50) -> None:
    """
    Write ranked findings to Markdown report.
    
    Args:
        findings: Dictionary containing all findings
        output_path: Path to output Markdown file
        top_n: Number of top endpoints to include
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    target = findings.get("target", "Unknown")
    timestamp = findings.get("timestamp", datetime.now(timezone.utc).isoformat())
    endpoints = findings.get("endpoints", [])
    summary = findings.get("summary", {})
    
    # Sort endpoints by ReapScore (descending)
    sorted_endpoints = sorted(
        endpoints,
        key=lambda e: e.get("reapscore", {}).get("score", 0.0),
        reverse=True
    )
    
    # Limit to top N
    top_endpoints = sorted_endpoints[:top_n]
    
    # Build report
    lines = [
        "# webReaper Report\n",
        f"**Target:** {target}\n",
        f"**Timestamp:** {timestamp}\n",
        "",
        "## Summary\n",
        f"- **Total Endpoints:** {summary.get('total_endpoints', len(endpoints))}",
        f"- **Unique URLs:** {summary.get('unique_urls', len(endpoints))}",
        f"- **Top ReapScore:** {summary.get('top_score', 0.0):.3f}",
        "",
        "## Top Ranked Endpoints\n",
        f"Showing top {len(top_endpoints)} endpoints ranked by ReapScore.\n",
        ""
    ]
    
    for i, endpoint in enumerate(top_endpoints, 1):
        url = endpoint.get("url", "")
        reapscore = endpoint.get("reapscore", {})
        score = reapscore.get("score", 0.0)
        rationale = reapscore.get("rationale", [])
        category_scores = reapscore.get("category_scores", {})
        
        lines.append(f"### {i}. {url}\n")
        lines.append(f"**ReapScore:** {score:.3f}\n")
        
        # Category breakdown
        if category_scores:
            lines.append("**Category Scores:**")
            for cat, cat_score in category_scores.items():
                lines.append(f"- {cat}: {cat_score:.3f}")
            lines.append("")
        
        # Rationale
        if rationale:
            lines.append("**Rationale:**")
            for reason in rationale:
                lines.append(f"- {reason}")
            lines.append("")
        
        # Additional metadata
        status = endpoint.get("status_code")
        if status:
            lines.append(f"**Status:** {status}")
        
        tech = endpoint.get("tech_stack", [])
        if tech:
            lines.append(f"**Tech:** {', '.join(tech[:5])}")
        
        sources = endpoint.get("sources", [])
        if sources:
            lines.append(f"**Sources:** {', '.join(sources)}")
        
        lines.append("")
        lines.append("---\n")
    
    # Write report
    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_findings(
    findings: Dict[str, Any],
    out_dir: Path,
    top_n: int = 50
) -> None:
    """
    Export findings to both JSON and Markdown formats.
    
    Args:
        findings: Dictionary containing all findings
        out_dir: Output directory
        top_n: Number of top endpoints to include in report
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Write findings.json
    write_findings_json(findings, out_dir / "findings.json")
    
    # Write REPORT.md
    write_report_md(findings, out_dir / "REPORT.md", top_n=top_n)
