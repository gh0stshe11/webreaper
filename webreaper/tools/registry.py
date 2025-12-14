"""
Tool registry and base classes for webReaper extensibility.

This module defines the core abstractions for adding new tools to webReaper:
- DiscoveryTool: Tools that discover URLs/endpoints
- AnalyzerTool: Tools that analyze responses for additional metadata
- ScoringTool: Tools that contribute to ReapScore calculation
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Protocol
from enum import Enum


class ToolCategory(str, Enum):
    """Categories of tools available in webReaper."""
    DISCOVERY = "discovery"
    ANALYZER = "analyzer"
    SCORER = "scorer"


@dataclass
class ToolMetadata:
    """Metadata about a tool."""
    name: str
    category: ToolCategory
    description: str
    version: str
    author: str = "webReaper"
    enabled_by_default: bool = False
    requires_external_binary: bool = False
    external_binary_name: Optional[str] = None


class DiscoveryTool(ABC):
    """
    Base class for discovery tools that find URLs/endpoints.
    
    Discovery tools harvest URLs from various sources (crawlers, archives,
    configuration files, etc.) and contribute to the HarvestIndex subscore.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return metadata about this tool."""
        pass
    
    @abstractmethod
    def discover(self, target: str, **kwargs) -> List[str]:
        """
        Discover URLs for the given target.
        
        Args:
            target: The target URL or domain
            **kwargs: Tool-specific configuration options
            
        Returns:
            List of discovered URLs
        """
        pass


class AnalyzerTool(ABC):
    """
    Base class for analyzer tools that extract metadata from responses.
    
    Analyzer tools process HTTP responses to extract additional signals
    that can be used for scoring (e.g., security headers, content patterns).
    """
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return metadata about this tool."""
        pass
    
    @abstractmethod
    def analyze(self, url: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a response and extract metadata.
        
        Args:
            url: The URL that was requested
            response_data: Response data including headers, body, status, etc.
            
        Returns:
            Dictionary of extracted metadata/signals
        """
        pass


class ScoringTool(ABC):
    """
    Base class for scoring tools that contribute to ReapScore.
    
    Scoring tools implement custom logic to compute additional score
    components based on endpoint characteristics.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return metadata about this tool."""
        pass
    
    @abstractmethod
    def score(self, context: Any, reasons: List[str]) -> int:
        """
        Compute a score contribution for an endpoint.
        
        Args:
            context: ScoringContext object with endpoint data
            reasons: List to append scoring reasons to
            
        Returns:
            Integer score (0-100) to add to the appropriate subscore
        """
        pass


class ToolRegistry:
    """
    Registry for managing webReaper tools.
    
    The registry maintains collections of discovery, analyzer, and scoring
    tools and provides methods to register, query, and execute them.
    """
    
    def __init__(self):
        self._discovery_tools: Dict[str, DiscoveryTool] = {}
        self._analyzer_tools: Dict[str, AnalyzerTool] = {}
        self._scoring_tools: Dict[str, ScoringTool] = {}
    
    def register_discovery(self, tool: DiscoveryTool) -> None:
        """Register a discovery tool."""
        self._discovery_tools[tool.metadata.name] = tool
    
    def register_analyzer(self, tool: AnalyzerTool) -> None:
        """Register an analyzer tool."""
        self._analyzer_tools[tool.metadata.name] = tool
    
    def register_scorer(self, tool: ScoringTool) -> None:
        """Register a scoring tool."""
        self._scoring_tools[tool.metadata.name] = tool
    
    def get_discovery_tool(self, name: str) -> Optional[DiscoveryTool]:
        """Get a discovery tool by name."""
        return self._discovery_tools.get(name)
    
    def get_analyzer_tool(self, name: str) -> Optional[AnalyzerTool]:
        """Get an analyzer tool by name."""
        return self._analyzer_tools.get(name)
    
    def get_scoring_tool(self, name: str) -> Optional[ScoringTool]:
        """Get a scoring tool by name."""
        return self._scoring_tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolMetadata]:
        """
        List all registered tools, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool metadata
        """
        tools = []
        
        if category is None or category == ToolCategory.DISCOVERY:
            tools.extend([t.metadata for t in self._discovery_tools.values()])
        
        if category is None or category == ToolCategory.ANALYZER:
            tools.extend([t.metadata for t in self._analyzer_tools.values()])
        
        if category is None or category == ToolCategory.SCORER:
            tools.extend([t.metadata for t in self._scoring_tools.values()])
        
        return tools
    
    def get_enabled_discovery_tools(self) -> List[DiscoveryTool]:
        """Get all discovery tools enabled by default."""
        return [t for t in self._discovery_tools.values() if t.metadata.enabled_by_default]
    
    def get_enabled_analyzer_tools(self) -> List[AnalyzerTool]:
        """Get all analyzer tools enabled by default."""
        return [t for t in self._analyzer_tools.values() if t.metadata.enabled_by_default]
    
    def get_enabled_scoring_tools(self) -> List[ScoringTool]:
        """Get all scoring tools enabled by default."""
        return [t for t in self._scoring_tools.values() if t.metadata.enabled_by_default]


# Global tool registry instance
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _global_registry
