"""
Content pattern analyzer tool.

This tool analyzes response body content for sensitive data patterns,
API endpoints, and other interesting signals.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set

from .registry import AnalyzerTool, ToolMetadata, ToolCategory


class ContentPatternAnalyzer(AnalyzerTool):
    """
    Analyzes response content for sensitive patterns and signals.
    
    This tool searches for:
    - Sensitive data patterns (API keys, tokens, credentials)
    - Error messages and stack traces
    - Debug/development information
    - API documentation patterns
    - Database query patterns
    
    Contribution to ReapScore:
    - Enhances JuiceScore for endpoints with API patterns
    - Enhances AnomalySignal for endpoints with error messages
    - Identifies endpoints with sensitive data exposure
    """
    
    # Patterns for sensitive data (basic examples, not exhaustive)
    SENSITIVE_PATTERNS = {
        "api_key": re.compile(r'api[_-]?key["\s:=]+([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
        "bearer_token": re.compile(r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE),
        "jwt": re.compile(r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'),
        "aws_key": re.compile(r'AKIA[0-9A-Z]{16}'),
        "private_key": re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----', re.IGNORECASE),
        "password_field": re.compile(r'password["\s:=]+["\']([^"\']{3,})', re.IGNORECASE),
    }
    
    # Error message patterns
    ERROR_PATTERNS = {
        "sql_error": re.compile(r'(SQL syntax|mysql_|postgresql|ORA-\d+|sqlite)', re.IGNORECASE),
        "stack_trace": re.compile(r'(at\s+[\w\.]+\([\w\.]+:\d+\)|Traceback|Exception in thread)', re.IGNORECASE),
        "php_error": re.compile(r'(Fatal error|Warning|Notice).*in\s+[\w/\\\.]+\s+on line', re.IGNORECASE),
        "asp_error": re.compile(r'(Server Error|Runtime Error).*\.asp', re.IGNORECASE),
        "java_error": re.compile(r'(java\.[a-z\.]+Exception|javax\.[a-z\.]+Exception)', re.IGNORECASE),
    }
    
    # Debug/development patterns
    DEBUG_PATTERNS = {
        "debug_mode": re.compile(r'debug["\s:=]+(true|1|on|enabled)', re.IGNORECASE),
        "phpinfo": re.compile(r'<title>phpinfo\(\)</title>', re.IGNORECASE),
        "swagger": re.compile(r'(swagger-ui|/api-docs|openapi\.json)', re.IGNORECASE),
        "graphql": re.compile(r'(graphql|__schema|__type)', re.IGNORECASE),
    }
    
    # API patterns
    API_PATTERNS = {
        "rest_api": re.compile(r'(/api/v\d+/|/rest/|"apiVersion")', re.IGNORECASE),
        "json_api": re.compile(r'("data":\s*\[|"type":\s*"|"attributes":\s*{)', re.IGNORECASE),
        "xml_api": re.compile(r'<\?xml|xmlns[:=]', re.IGNORECASE),
    }
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="content_patterns",
            category=ToolCategory.ANALYZER,
            description="Analyzes response content for sensitive patterns and signals",
            version="1.0.0",
            enabled_by_default=True,
            requires_external_binary=False,
        )
    
    def analyze(self, url: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze response content for patterns.
        
        Args:
            url: The requested URL
            response_data: Dict with 'body' key containing response content
            
        Returns:
            Dict with analysis results:
            {
                "sensitive_patterns": [...],
                "error_patterns": [...],
                "debug_patterns": [...],
                "api_patterns": [...],
                "has_sensitive_data": bool,
                "has_errors": bool,
                "has_debug_info": bool,
                "is_api": bool,
                "pattern_score": int (0-100),
            }
        """
        body = response_data.get("body", "")
        
        # Limit analysis to first 100KB to avoid performance issues
        if isinstance(body, bytes):
            body = body[:100_000].decode('utf-8', errors='ignore')
        elif isinstance(body, str):
            body = body[:100_000]
        
        analysis = {
            "sensitive_patterns": [],
            "error_patterns": [],
            "debug_patterns": [],
            "api_patterns": [],
            "has_sensitive_data": False,
            "has_errors": False,
            "has_debug_info": False,
            "is_api": False,
            "pattern_score": 0,
        }
        
        # Check for sensitive patterns
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            if pattern.search(body):
                analysis["sensitive_patterns"].append(pattern_name)
                analysis["has_sensitive_data"] = True
        
        # Check for error patterns
        for pattern_name, pattern in self.ERROR_PATTERNS.items():
            if pattern.search(body):
                analysis["error_patterns"].append(pattern_name)
                analysis["has_errors"] = True
        
        # Check for debug patterns
        for pattern_name, pattern in self.DEBUG_PATTERNS.items():
            if pattern.search(body):
                analysis["debug_patterns"].append(pattern_name)
                analysis["has_debug_info"] = True
        
        # Check for API patterns
        for pattern_name, pattern in self.API_PATTERNS.items():
            if pattern.search(body):
                analysis["api_patterns"].append(pattern_name)
                analysis["is_api"] = True
        
        # Compute pattern score (higher = more interesting)
        score = 0
        score += len(analysis["sensitive_patterns"]) * 30  # Sensitive data is very interesting
        score += len(analysis["error_patterns"]) * 20      # Errors reveal internals
        score += len(analysis["debug_patterns"]) * 15      # Debug info is interesting
        score += len(analysis["api_patterns"]) * 10        # APIs are interesting
        
        analysis["pattern_score"] = min(100, score)
        
        return analysis


def analyze_content_patterns(content: str) -> Dict[str, Any]:
    """
    Standalone function to analyze content patterns.
    
    Args:
        content: Response body content
        
    Returns:
        Analysis results dict
    """
    analyzer = ContentPatternAnalyzer()
    return analyzer.analyze("", {"body": content})
