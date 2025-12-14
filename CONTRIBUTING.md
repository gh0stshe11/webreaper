# Contributing to webReaper

Thank you for your interest in contributing to webReaper! This guide will help you get started with development, testing, and submitting contributions.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Style](#code-style)
4. [Architecture Overview](#architecture-overview)
5. [Adding New Features](#adding-new-features)
6. [Testing](#testing)
7. [Submitting Changes](#submitting-changes)
8. [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Optional external tools for full functionality:
  - httpx (ProjectDiscovery) — **required**
  - katana (ProjectDiscovery) — optional
  - gau — optional
  - gospider — optional (planned)
  - hakrawler — optional (planned)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/webreaper.git
   cd webreaper
   ```

3. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install in editable mode**:
   ```bash
   pip install -e .
   ```

5. **Verify installation**:
   ```bash
   webreaper --help
   ```

## Development Setup

### Project Structure

```
webreaper/
├── ARCHITECTURE.md       # Detailed architecture documentation
├── CONTRIBUTING.md       # This file
├── README.md             # User-facing documentation
├── pyproject.toml        # Project metadata and dependencies
├── webreaper/            # Main package
│   ├── cli.py            # CLI interface and orchestration
│   ├── scoring.py        # ReapScore algorithm
│   ├── paths_packs.py    # Path wordlists
│   ├── parsers/          # Tool output parsers
│   │   ├── httpx.py
│   │   ├── katana.py
│   │   ├── gau.py
│   │   ├── gospider.py   # Planned
│   │   └── hakrawler.py  # Planned
│   └── report/           # Report generation
│       └── render_md.py
```

### Running from Source

While developing, run webReaper directly:

```bash
# Using the installed command
webreaper reap https://example.com -o /tmp/test-output

# Or via Python module
python -m webreaper reap https://example.com -o /tmp/test-output
```

### Debugging

Use verbose mode to see detailed execution:

```bash
webreaper reap https://example.com -o /tmp/debug --verbose
```

Check the run log for detailed timing information:
```bash
cat /tmp/debug/run.log
```

## Code Style

### Python Style Guidelines

- **Formatting**: Follow PEP 8
- **Type Hints**: Use type hints for all function signatures (`from __future__ import annotations`)
- **Imports**: Group imports (standard library, third-party, local)
- **Line Length**: Keep lines under 120 characters where reasonable
- **Docstrings**: Use docstrings for public functions and modules

### Example Function Style

```python
from __future__ import annotations
from typing import List, Optional

def parse_tool_output(
    output: str,
    *,
    filter_invalid: bool = True,
    max_urls: Optional[int] = None,
) -> List[str]:
    """Parse tool output and extract valid URLs.
    
    Args:
        output: Raw tool output text
        filter_invalid: Whether to filter out invalid URLs
        max_urls: Maximum number of URLs to return
        
    Returns:
        List of validated URL strings
    """
    urls: List[str] = []
    # Implementation
    return urls
```

### Naming Conventions

- **Functions**: `snake_case` (e.g., `compute_reapscore`, `parse_httpx_jsonlines`)
- **Classes**: `PascalCase` (e.g., `HttpxEndpoint`, `ReapResult`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_WEIGHTS`, `PATH_KEYWORDS`)
- **Private functions**: Prefix with `_` (e.g., `_filter_url`, `_safe_name`)

## Architecture Overview

Please read [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed understanding of:
- The four-phase pipeline (Harvest → Probe → Rank → Report)
- How each integrated tool works
- The ReapScore algorithm and its subscores
- Data flow and module responsibilities

## Adding New Features

### Adding a New Discovery Tool

To integrate a new web crawler or URL discovery tool (e.g., gospider, hakrawler):

1. **Create a parser** in `webreaper/parsers/<tool>.py`:

```python
from __future__ import annotations
from typing import List
from urllib.parse import urlparse

def parse_<tool>_lines(output: str) -> List[str]:
    """Parse <tool> output and return valid URLs.
    
    Args:
        output: Raw text output from <tool>
        
    Returns:
        List of validated URLs
    """
    urls: List[str] = []
    for line in output.splitlines():
        u = line.strip()
        if not u or "://" not in u:
            continue
        try:
            p = urlparse(u)
            if p.scheme and p.netloc:
                urls.append(p.geturl())
        except Exception:
            continue
    return urls
```

2. **Add CLI options** in `cli.py`:

```python
# In the reap() and scan() commands, add:
<tool>: bool = typer.Option(True, "--<tool>/--no-<tool>", help="Enable <tool> discovery"),
<tool>_option: str = typer.Option("default", "--<tool>-option", help="Tool-specific option"),
```

3. **Integrate into harvest phase** in `_reap_impl()`:

```python
# Import the parser at the top
from .parsers.<tool> import parse_<tool>_lines

# In _reap_impl(), add the tool invocation:
<tool>_urls: List[str] = []
if use_<tool>:
    if not quiet:
        typer.secho(f"[+] <tool>: running...", fg=typer.colors.GREEN)
    try:
        start = time.time()
        r = _run(["<tool>", target, "<options>"], timeout=timeout)
        dur = int((time.time()-start)*1000)
        (out / f"raw_<tool>_{_safe_name(target)}.txt").write_text(r.stdout or "", encoding="utf-8")
        if (r.stderr or "").strip():
            (out / f"<tool>_{_safe_name(target)}.stderr.txt").write_text(r.stderr, encoding="utf-8")
        for u in parse_<tool>_lines(r.stdout or ""):
            <tool>_urls.append(u)
            url_sources.setdefault(u, set()).add("<tool>")
        if not quiet:
            typer.secho(f"[+] <tool> harvested {len(set(<tool>_urls))} urls ({dur} ms)", fg=typer.colors.GREEN)
    except FileNotFoundError:
        if not quiet:
            typer.secho("[!] <tool> not found (skipping).", fg=typer.colors.YELLOW)

# Add to candidates merge
candidates = [target, *katana_urls, *gau_urls, *<tool>_urls]
```

4. **Update documentation**:
   - Add tool description to README.md
   - Document in ARCHITECTURE.md
   - Update CLI help text

### Adding a New Path Pack

To add a new wordlist for path discovery:

1. **Edit `webreaper/paths_packs.py`**:

```python
PACKS: Dict[str, List[str]] = {
    "common": [...],
    "auth": [...],
    "api": [...],
    "ops": [...],
    "files": [...],
    "new_pack": [  # Your new pack
        "path1",
        "path2",
        "path3",
    ],
}
```

2. **Document the pack**:
   - Add description in README.md under CLI options
   - Update ARCHITECTURE.md with pack purpose

3. **Test the pack**:
```bash
webreaper packs  # Should list your new pack
webreaper reap https://example.com --paths-pack new_pack -o /tmp/test
```

### Modifying the ReapScore Algorithm

To adjust scoring behavior:

1. **Edit `webreaper/scoring.py`**:
   - Modify `DEFAULT_WEIGHTS` to change subscore importance
   - Add new signals within subscores (H, J, A, N)
   - Update `compute_reapscore()` function

2. **Maintain backward compatibility**:
   - Keep the same subscore structure (harvest_index, juice_score, access_signal, anomaly_signal)
   - Use the `weights` parameter for custom weights
   - Document any breaking changes

3. **Example - Adding a new signal**:

```python
# In compute_reapscore(), within the JuiceScore section:
J = 0
if param_names:
    J += 20; reasons.append("has_params (+20 J)")
if param_count >= 3:
    J += 10; reasons.append("param_count>=3 (+10 J)")
    
# NEW: Add bonus for REST API endpoints
if path_lc.startswith("/api/") or "/v1/" in path_lc or "/v2/" in path_lc:
    J += 15; reasons.append("rest_api_path (+15 J)")
    
J = clamp(J)
```

### Adding New Report Formats

To add new output formats (e.g., CSV, HTML):

1. **Create a new module** in `webreaper/report/render_<format>.py`:

```python
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

def write_<format>_report(findings_path: Path, out_path: Path) -> None:
    """Generate report in <FORMAT> format."""
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    
    # Generate your format
    output = generate_<format>(data)
    
    out_path.write_text(output, encoding="utf-8")

def generate_<format>(findings: Dict[str, Any]) -> str:
    """Convert findings to <FORMAT> format."""
    # Implementation
    return formatted_output
```

2. **Integrate into CLI**:

```python
# In cli.py, after write_report() and write_eli5_report():
from .report.render_<format> import write_<format>_report

# In _reap_impl():
write_<format>_report(out / "findings.json", out / "REPORT.<ext>")
```

## Testing

### Manual Testing

Test your changes with a safe target:

```bash
# Basic test
webreaper reap https://example.com -o /tmp/test-run

# Test with specific tools disabled
webreaper reap https://example.com -o /tmp/no-katana --no-katana

# Test with custom filters
webreaper reap https://example.com -o /tmp/filtered \
  --exclude-ext png,jpg,css,js \
  --max-params 5

# Test path packs
webreaper packs
webreaper reap https://example.com -o /tmp/paths --paths-pack api,auth
```

### Validation Checklist

Before submitting changes:

- [ ] Code follows Python style guidelines
- [ ] Type hints are present on all functions
- [ ] New CLI options have help text
- [ ] Error handling is in place (try/except for external tools)
- [ ] Tool outputs are saved to `raw_*.txt` files
- [ ] Stderr is captured to `*.stderr.txt` if present
- [ ] URL filtering is applied consistently
- [ ] Documentation is updated (README, ARCHITECTURE, CONTRIBUTING)
- [ ] Tested with `--verbose` flag for debugging
- [ ] No secrets or sensitive data in code or commits

### Performance Testing

For performance-sensitive changes:

```bash
# Test with large URL sets
webreaper reap https://example.com -o /tmp/perf --max-urls 5000 --verbose

# Check run.log for timing information
cat /tmp/perf/run.log
```

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, focused commits:
   ```bash
   git add .
   git commit -m "Add gospider parser and CLI integration"
   ```

3. **Update documentation** in the same commit or branch:
   - README.md for user-facing changes
   - ARCHITECTURE.md for design changes
   - CONTRIBUTING.md if adding new patterns

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request** with:
   - **Clear title**: "Add gospider integration" or "Fix scoring edge case"
   - **Description**: What changes were made and why
   - **Testing notes**: How you validated the changes
   - **Related issues**: Reference any GitHub issues

### Commit Message Guidelines

- Use imperative mood: "Add feature" not "Added feature"
- Keep first line under 72 characters
- Add detail in commit body if needed
- Reference issues: "Fixes #123" or "Relates to #456"

Good examples:
```
Add gospider parser and CLI integration

- Create webreaper/parsers/gospider.py
- Add --gospider/--no-gospider CLI option
- Integrate into harvest phase in cli.py
- Update ARCHITECTURE.md with gospider details
```

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn
- Keep discussions on-topic

### Getting Help

- **Documentation**: Start with README.md and ARCHITECTURE.md
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas

### Areas for Contribution

Current priorities (see GitHub Issues for details):

1. **gospider/hakrawler integration** — Add new crawler support
2. **Path pack expansion** — Curate more specialized wordlists
3. **Scoring refinements** — Improve ReapScore algorithm
4. **Report formats** — Add CSV, HTML, or SIEM integrations
5. **Documentation** — Examples, tutorials, use cases
6. **Testing** — Unit tests, integration tests, test fixtures

### Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant features
- Special thanks for documentation improvements

## Questions?

If you have questions about contributing:
- Open a GitHub Discussion
- Check existing documentation (README, ARCHITECTURE)
- Review closed PRs for examples

Thank you for contributing to webReaper! 🚀
