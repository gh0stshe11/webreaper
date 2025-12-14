"""Raw data storage and resume functionality."""
from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from ..utils import safe_name


def get_raw_file_path(out_dir: Path, source: str, target: str) -> Path:
    """
    Get the path for a raw data file.
    
    Args:
        out_dir: Output directory
        source: Source name (e.g., 'robots', 'sitemap', 'wayback', 'crtsh')
        target: Target domain or URL
        
    Returns:
        Path object for the raw file
    """
    safe_target = safe_name(target)
    return out_dir / f"raw_{source}_{safe_target}.json"


def save_raw_data(out_dir: Path, source: str, target: str, data: List[str]) -> None:
    """
    Save raw harvested URLs to a JSON file.
    
    Args:
        out_dir: Output directory
        source: Source name (e.g., 'robots', 'sitemap', 'wayback', 'crtsh')
        target: Target domain or URL
        data: List of URLs to save
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_file = get_raw_file_path(out_dir, source, target)
    
    payload = {
        'source': source,
        'target': target,
        'url_count': len(data),
        'urls': data
    }
    
    raw_file.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def load_raw_data(out_dir: Path, source: str, target: str) -> Optional[List[str]]:
    """
    Load raw harvested URLs from a JSON file.
    
    Args:
        out_dir: Output directory
        source: Source name (e.g., 'robots', 'sitemap', 'wayback', 'crtsh')
        target: Target domain or URL
        
    Returns:
        List of URLs if file exists and is valid, None otherwise
    """
    raw_file = get_raw_file_path(out_dir, source, target)
    
    if not raw_file.exists():
        return None
    
    try:
        data = json.loads(raw_file.read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'urls' in data:
            return data['urls']
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def should_harvest(out_dir: Path, source: str, target: str, resume: bool) -> bool:
    """
    Determine if harvesting should be performed.
    
    Args:
        out_dir: Output directory
        source: Source name
        target: Target domain or URL
        resume: Whether resume mode is enabled
        
    Returns:
        True if harvesting should be performed, False if cached data should be used
    """
    if not resume:
        return True
    
    return load_raw_data(out_dir, source, target) is None
