"""Raw data storage and resume logic for webReaper."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class RawStore:
    """Manages raw data files in the output directory."""
    
    def __init__(self, out_dir: Path):
        """Initialize RawStore with output directory."""
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, name: str, data: Any) -> Path:
        """
        Save raw data to a JSON file.
        
        Args:
            name: The base name for the file (without .json extension)
            data: Data to save (must be JSON serializable)
        
        Returns:
            Path to the saved file
        """
        filepath = self.out_dir / f"raw_{name}.json"
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath
    
    def load(self, name: str) -> Optional[Any]:
        """
        Load raw data from a JSON file.
        
        Args:
            name: The base name for the file (without .json extension)
        
        Returns:
            Loaded data or None if file doesn't exist
        """
        filepath = self.out_dir / f"raw_{name}.json"
        if not filepath.exists():
            return None
        
        try:
            with filepath.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def exists(self, name: str) -> bool:
        """
        Check if a raw data file exists.
        
        Args:
            name: The base name for the file (without .json extension)
        
        Returns:
            True if file exists, False otherwise
        """
        filepath = self.out_dir / f"raw_{name}.json"
        return filepath.exists()
    
    def should_skip(self, name: str, resume: bool) -> bool:
        """
        Determine if harvesting should be skipped based on resume flag.
        
        Args:
            name: The base name for the file (without .json extension)
            resume: Whether resume mode is enabled
        
        Returns:
            True if harvesting should be skipped, False otherwise
        """
        return resume and self.exists(name)
