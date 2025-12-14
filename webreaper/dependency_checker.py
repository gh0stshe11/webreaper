"""Dependency checker and auto-installer for webReaper external tools."""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional


# Tool installation commands
TOOL_INSTALL_COMMANDS = {
    "katana": "go install github.com/projectdiscovery/katana/cmd/katana@latest",
    "gau": "go install github.com/lc/gau/v2/cmd/gau@latest",
    "httpx": "go install github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "gospider": "go install github.com/jaeles-project/gospider@latest",
    "hakrawler": "go install github.com/hakluke/hakrawler@latest",
}


def check_tool(tool_name: str) -> bool:
    """Check if a tool is available in PATH.
    
    Args:
        tool_name: Name of the tool to check
        
    Returns:
        True if tool is available, False otherwise
    """
    return shutil.which(tool_name) is not None


def install_tool(tool_name: str, quiet: bool = False) -> bool:
    """Install a tool using go install.
    
    Args:
        tool_name: Name of the tool to install
        quiet: Suppress output messages
        
    Returns:
        True if installation succeeded, False otherwise
    """
    if tool_name not in TOOL_INSTALL_COMMANDS:
        if not quiet:
            print(f"[!] Unknown tool: {tool_name}", file=sys.stderr)
        return False
    
    # Check if Go is installed
    if not shutil.which("go"):
        if not quiet:
            print("[!] Go is not installed. Please install Go first.", file=sys.stderr)
            print("[!] Visit https://go.dev/doc/install for installation instructions.", file=sys.stderr)
        return False
    
    install_cmd = TOOL_INSTALL_COMMANDS[tool_name]
    
    if not quiet:
        print(f"[*] Installing {tool_name}...")
        print(f"[*] Running: {install_cmd}")
    
    try:
        result = subprocess.run(
            install_cmd.split(),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            # Verify installation
            if check_tool(tool_name):
                if not quiet:
                    print(f"[+] Successfully installed {tool_name}")
                return True
            else:
                if not quiet:
                    print(f"[!] {tool_name} installed but not found in PATH.", file=sys.stderr)
                    print("[!] You may need to add $HOME/go/bin to your PATH.", file=sys.stderr)
                    print("[!] Run: export PATH=$PATH:$HOME/go/bin", file=sys.stderr)
                return False
        else:
            if not quiet:
                print(f"[!] Failed to install {tool_name}", file=sys.stderr)
                if result.stderr:
                    print(f"[!] Error: {result.stderr}", file=sys.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        if not quiet:
            print(f"[!] Installation of {tool_name} timed out", file=sys.stderr)
        return False
    except Exception as e:
        if not quiet:
            print(f"[!] Error installing {tool_name}: {e}", file=sys.stderr)
        return False


def check_and_install_tool(
    tool_name: str,
    auto_install: bool = False,
    quiet: bool = False
) -> bool:
    """Check if a tool is available and optionally install it.
    
    Args:
        tool_name: Name of the tool to check/install
        auto_install: If True, install without prompting
        quiet: Suppress output messages
        
    Returns:
        True if tool is available (after installation if needed), False otherwise
    """
    # Check if already installed
    if check_tool(tool_name):
        return True
    
    if not quiet:
        print(f"[!] Tool '{tool_name}' not found in PATH", file=sys.stderr)
    
    # Determine if we should install
    should_install = auto_install
    
    if not auto_install and not quiet:
        # Prompt user
        try:
            response = input(f"[?] Would you like to install {tool_name} now? (y/n): ").strip().lower()
            should_install = response in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            print()
            should_install = False
    
    if should_install:
        return install_tool(tool_name, quiet=quiet)
    else:
        if not quiet:
            print(f"[!] Skipping installation of {tool_name}", file=sys.stderr)
        return False


def check_dependencies(
    required_tools: list[str],
    optional_tools: Optional[list[str]] = None,
    auto_install: bool = False,
    quiet: bool = False
) -> tuple[list[str], list[str]]:
    """Check multiple dependencies and optionally install missing ones.
    
    Args:
        required_tools: List of tool names that are required
        optional_tools: List of tool names that are optional
        auto_install: If True, install missing tools without prompting
        quiet: Suppress output messages
        
    Returns:
        Tuple of (available_tools, missing_required_tools)
    """
    optional_tools = optional_tools or []
    available = []
    missing_required = []
    
    # Check required tools
    for tool in required_tools:
        if check_and_install_tool(tool, auto_install=auto_install, quiet=quiet):
            available.append(tool)
        else:
            missing_required.append(tool)
    
    # Check optional tools (don't force install, just notify)
    for tool in optional_tools:
        if check_tool(tool):
            available.append(tool)
        elif not quiet:
            print(f"[i] Optional tool '{tool}' not found (skipping)", file=sys.stderr)
    
    return available, missing_required


def verify_go_installation() -> bool:
    """Verify that Go is properly installed.
    
    Returns:
        True if Go is available, False otherwise
    """
    if not shutil.which("go"):
        return False
    
    try:
        result = subprocess.run(
            ["go", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False
