"""Tests for CLI flag parsing."""
import pytest
from click.testing import CliRunner
from webreaper.cli import cli


def test_cli_help():
    """Test CLI help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "webReaper" in result.output


def test_reap_command_help():
    """Test reap command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reap", "--help"])
    assert result.exit_code == 0
    assert "TARGET" in result.output
    assert "--sources" in result.output


def test_reap_command_dry_run():
    """Test reap command with dry-run flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--dry-run",
        "--verbose"
    ])
    # Dry run should succeed without errors
    assert result.exit_code == 0


def test_reap_sources_parsing():
    """Test sources flag parsing."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--sources", "robots,sitemap",
        "--dry-run"
    ])
    assert result.exit_code == 0


def test_reap_min_score():
    """Test min-score flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--min-score", "0.5",
        "--dry-run"
    ])
    assert result.exit_code == 0


def test_reap_concurrency():
    """Test concurrency flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--concurrency", "20",
        "--dry-run"
    ])
    assert result.exit_code == 0


def test_reap_timeout():
    """Test timeout flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--timeout", "30",
        "--dry-run"
    ])
    assert result.exit_code == 0


def test_reap_active_flag():
    """Test active flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--active",
        "--dry-run"
    ])
    assert result.exit_code == 0


def test_reap_resume_flag():
    """Test resume flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--resume",
        "--dry-run"
    ])
    assert result.exit_code == 0


def test_reap_verbose_flag():
    """Test verbose flag."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "reap",
        "https://example.com",
        "--verbose",
        "--dry-run"
    ])
    assert result.exit_code == 0
    assert "webReaper" in result.output
