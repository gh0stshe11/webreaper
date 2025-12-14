"""Click-based CLI for webReaper Phase A."""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
import click

from .core.controller import WebReaperController


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.6.4")
def cli(ctx):
    """webReaper: harvest → probe → rank → report
    
    Phase A: Passive reconnaissance with explainable ReapScore.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("target")
@click.option(
    "--sources",
    default="robots,sitemap,wayback,crtsh",
    help="Comma-separated list of sources (robots,sitemap,wayback,crtsh)",
)
@click.option(
    "--concurrency",
    default=10,
    type=int,
    help="Maximum concurrent requests",
)
@click.option(
    "--timeout",
    default=10,
    type=int,
    help="Request timeout in seconds",
)
@click.option(
    "--user-agent",
    default=None,
    help="Custom User-Agent string",
)
@click.option(
    "--rate-limit",
    default=None,
    type=int,
    help="Maximum requests per second (optional rate limiting)",
)
@click.option(
    "--out-dir",
    "-o",
    default="out",
    type=click.Path(),
    help="Output directory for findings and raw files",
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume mode: skip harvesting if raw_* files exist",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry run mode (no actual requests)",
)
@click.option(
    "--active",
    is_flag=True,
    default=False,
    help="Enable active probing (header analysis, JS extraction)",
)
@click.option(
    "--min-score",
    default=0.0,
    type=float,
    help="Minimum ReapScore threshold (0.0-1.0)",
)
@click.option(
    "--top",
    default=50,
    type=int,
    help="Number of top endpoints to include in REPORT.md",
)
@click.option(
    "--verify-ssl",
    is_flag=True,
    default=False,
    help="Enable SSL certificate verification (disabled by default for recon)",
)
def reap(
    target: str,
    sources: str,
    concurrency: int,
    timeout: int,
    user_agent: str,
    rate_limit: int,
    out_dir: str,
    resume: bool,
    verbose: bool,
    dry_run: bool,
    active: bool,
    min_score: float,
    top: int,
    verify_ssl: bool,
):
    """Run webReaper reconnaissance on TARGET."""
    
    # Parse sources
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    
    # Create controller
    controller = WebReaperController(
        target=target,
        out_dir=Path(out_dir),
        sources=source_list,
        concurrency=concurrency,
        timeout=timeout,
        user_agent=user_agent,
        rate_limit=rate_limit,
        resume=resume,
        verbose=verbose,
        dry_run=dry_run,
        active=active,
        min_score=min_score,
        top=top,
        verify_ssl=verify_ssl,
    )
    
    # Run async controller
    try:
        asyncio.run(controller.run())
        click.secho(f"\n✓ Results written to {out_dir}/", fg="green", bold=True)
        click.secho(f"  - findings.json (structured results)", fg="green")
        click.secho(f"  - REPORT.md (top {top} ranked endpoints)", fg="green")
        click.secho(f"  - raw_* files (cached harvester data)", fg="green")
    except KeyboardInterrupt:
        click.secho("\n✗ Interrupted by user", fg="yellow")
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n✗ Error: {e}", fg="red", bold=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
