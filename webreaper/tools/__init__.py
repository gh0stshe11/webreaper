"""
Tools module for webReaper.

This module provides additional data sources, parsers, and scoring helpers
that enhance the ReapScore calculation and data collection capabilities.

Tools are organized into categories:
- discovery: Additional URL/endpoint discovery tools
- analyzers: Tools that analyze response data for scoring signals
- scorers: Specialized scoring functions that extend the core ReapScore
"""

from __future__ import annotations

__all__ = [
    "ToolRegistry",
    "DiscoveryTool",
    "AnalyzerTool",
    "ScoringTool",
    "get_global_registry",
    "RobotsSitemapTool",
    "SecurityHeadersAnalyzer",
    "ContentPatternAnalyzer",
    "TechnologyScorer",
    "parse_robots_txt",
    "parse_sitemap_xml",
    "analyze_security_headers",
    "analyze_content_patterns",
    "score_technologies",
]

from .registry import (
    ToolRegistry,
    DiscoveryTool,
    AnalyzerTool,
    ScoringTool,
    get_global_registry,
)
from .robots_sitemap import RobotsSitemapTool, parse_robots_txt, parse_sitemap_xml
from .security_headers import SecurityHeadersAnalyzer, analyze_security_headers
from .content_patterns import ContentPatternAnalyzer, analyze_content_patterns
from .technology_scorer import TechnologyScorer, score_technologies


# Auto-register built-in tools on module import
def _register_builtin_tools():
    """Register all built-in tools with the global registry."""
    registry = get_global_registry()
    
    # Discovery tools
    registry.register_discovery(RobotsSitemapTool())
    
    # Analyzer tools
    registry.register_analyzer(SecurityHeadersAnalyzer())
    registry.register_analyzer(ContentPatternAnalyzer())
    
    # Scoring tools
    registry.register_scorer(TechnologyScorer())


_register_builtin_tools()
