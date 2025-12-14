"""Common utility functions for webReaper."""
import re


# Maximum length for safe filenames
MAX_SAFE_FILENAME_LENGTH = 90


def safe_name(s: str) -> str:
    """
    Convert string to safe filename.
    
    Args:
        s: Input string
        
    Returns:
        Safe filename string with special characters replaced
    """
    return re.sub(r'[^a-zA-Z0-9._-]+', '_', s)[:MAX_SAFE_FILENAME_LENGTH]
