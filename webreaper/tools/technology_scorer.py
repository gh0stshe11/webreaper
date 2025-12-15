"""
Technology fingerprint scoring tool.

This tool provides additional scoring based on detected web technologies,
frameworks, and platforms that may indicate testing value.
"""

from __future__ import annotations
from typing import List, Any, Dict

from .registry import ScoringTool, ToolMetadata, ToolCategory


class TechnologyScorer(ScoringTool):
    """
    Scores endpoints based on detected web technologies.
    
    This tool assigns bonus scores based on technology fingerprints:
    - Known vulnerable or legacy frameworks
    - High-value targets (admin panels, databases, APIs)
    - Development/staging indicators
    
    Contribution to ReapScore:
    - Enhances JuiceScore for high-value technology stacks
    - Identifies outdated/vulnerable technologies
    - Prioritizes admin/database interfaces
    """
    
    # Technologies that indicate high testing value
    # Format: {tech_name: (score_bonus, reason)}
    HIGH_VALUE_TECH = {
        # Admin panels & management interfaces
        "phpmyadmin": (25, "database_admin_panel"),
        "adminer": (25, "database_admin_panel"),
        "wordpress": (15, "cms_with_known_vulns"),
        "drupal": (15, "cms_with_known_vulns"),
        "joomla": (15, "cms_with_known_vulns"),
        
        # API frameworks
        "graphql": (20, "api_framework"),
        "swagger": (20, "api_docs"),
        "openapi": (20, "api_docs"),
        "rest-api": (15, "rest_api"),
        
        # Development/debug tools
        "xdebug": (30, "debug_tool_exposed"),
        "phpinfo": (30, "debug_info_exposed"),
        "laravel-debugbar": (25, "debug_tool_exposed"),
        "symfony-profiler": (25, "debug_tool_exposed"),
        
        # Database interfaces
        "mysql": (20, "database_interface"),
        "postgresql": (20, "database_interface"),
        "mongodb": (20, "database_interface"),
        "redis": (20, "cache_interface"),
        
        # Application servers
        "tomcat": (15, "app_server"),
        "jboss": (15, "app_server"),
        "weblogic": (15, "app_server"),
        "websphere": (15, "app_server"),
        
        # Legacy/vulnerable frameworks
        "struts": (25, "legacy_framework"),
        "spring": (15, "java_framework"),
        "flask": (10, "python_framework"),
        "django": (10, "python_framework"),
        "rails": (10, "ruby_framework"),
        
        # Web servers (for version detection)
        "apache": (5, "web_server"),
        "nginx": (5, "web_server"),
        "iis": (10, "microsoft_server"),
        
        # SSO/Auth systems
        "oauth": (20, "auth_system"),
        "saml": (20, "auth_system"),
        "jwt": (15, "token_auth"),
        "keycloak": (20, "sso_server"),
        "okta": (20, "sso_server"),
    }
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="technology_scorer",
            category=ToolCategory.SCORER,
            description="Scores endpoints based on detected web technologies",
            version="1.0.0",
            enabled_by_default=True,
            requires_external_binary=False,
        )
    
    def score(self, context: Any, reasons: List[str]) -> int:
        """
        Compute technology-based score bonus.
        
        Args:
            context: ScoringContext object with 'tech' attribute
            reasons: List to append scoring reasons to
            
        Returns:
            Score bonus (0-100) based on detected technologies
        """
        # Access technologies from context
        # Expected: context has a 'tech' attribute with list of detected techs
        tech_list = getattr(context, 'tech', [])
        
        if not tech_list:
            return 0
        
        score = 0
        detected_categories = set()
        
        for tech in tech_list:
            tech_lower = tech.lower()
            
            # Check against high-value technologies
            for tech_pattern, (bonus, category) in self.HIGH_VALUE_TECH.items():
                if tech_pattern in tech_lower:
                    score += bonus
                    detected_categories.add(category)
                    reasons.append(f"tech:{tech} (+{bonus} T)")
        
        # Cap the total technology bonus
        return min(100, score)


def score_technologies(tech_list: List[str]) -> Dict[str, Any]:
    """
    Standalone function to score a list of technologies.
    
    Args:
        tech_list: List of detected technology names
        
    Returns:
        Dict with scoring results:
        {
            "score": int,
            "high_value_techs": [...],
            "categories": [...],
        }
    """
    scorer = TechnologyScorer()
    
    # Create a simple context object
    class SimpleContext:
        def __init__(self, techs):
            self.tech = techs
    
    reasons = []
    score = scorer.score(SimpleContext(tech_list), reasons)
    
    # Extract high-value techs from reasons
    high_value = []
    for reason in reasons:
        if reason.startswith("tech:"):
            tech_name = reason.split("(")[0].replace("tech:", "").strip()
            high_value.append(tech_name)
    
    # Extract categories
    categories = set()
    for tech in tech_list:
        tech_lower = tech.lower()
        for tech_pattern, (_, category) in scorer.HIGH_VALUE_TECH.items():
            if tech_pattern in tech_lower:
                categories.add(category)
    
    return {
        "score": score,
        "high_value_techs": high_value,
        "categories": list(categories),
    }
