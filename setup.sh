#!/bin/bash
#
# webReaper Setup Script for Kali Linux
# Automatically installs dependencies including Go and required tools
#

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${CYAN}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Banner
echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║     webReaper Setup Script           ║"
echo "  ║     Kali Linux Dependency Installer  ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on a Debian-based system
if ! command -v apt &> /dev/null; then
    print_warning "This script is designed for Debian-based systems (like Kali Linux)"
    print_warning "You may need to manually install dependencies on other systems"
fi

# Check for root/sudo
if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    print_warning "Some operations may require sudo privileges"
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# 1. Check and install Go
print_info "Checking for Go installation..."

if command_exists go; then
    GO_VERSION=$(go version | awk '{print $3}')
    print_success "Go is already installed: $GO_VERSION"
else
    print_info "Go is not installed. Installing Go..."
    
    # Determine system architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            GO_ARCH="amd64"
            ;;
        aarch64|arm64)
            GO_ARCH="arm64"
            ;;
        armv7l)
            GO_ARCH="armv6l"
            ;;
        *)
            print_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    # Use latest stable Go version (1.21 as of late 2023)
    GO_VERSION="1.21.5"
    GO_TARBALL="go${GO_VERSION}.linux-${GO_ARCH}.tar.gz"
    GO_URL="https://go.dev/dl/${GO_TARBALL}"
    
    print_info "Downloading Go ${GO_VERSION} for ${GO_ARCH}..."
    
    # Download Go
    if command_exists wget; then
        wget -q --show-progress "$GO_URL" -O "/tmp/${GO_TARBALL}" || {
            print_error "Failed to download Go"
            exit 1
        }
    elif command_exists curl; then
        curl -L "$GO_URL" -o "/tmp/${GO_TARBALL}" || {
            print_error "Failed to download Go"
            exit 1
        }
    else
        print_error "Neither wget nor curl is available. Please install one of them."
        exit 1
    fi
    
    # Remove old Go installation if exists
    if [ -d "/usr/local/go" ]; then
        print_info "Removing old Go installation..."
        sudo rm -rf /usr/local/go
    fi
    
    # Extract Go
    print_info "Installing Go to /usr/local/go..."
    sudo tar -C /usr/local -xzf "/tmp/${GO_TARBALL}"
    
    # Clean up
    rm "/tmp/${GO_TARBALL}"
    
    # Add Go to PATH if not already there
    if ! grep -q "/usr/local/go/bin" "$HOME/.bashrc" 2>/dev/null; then
        print_info "Adding Go to PATH in ~/.bashrc..."
        echo "" >> "$HOME/.bashrc"
        echo "# Go language" >> "$HOME/.bashrc"
        echo "export PATH=\$PATH:/usr/local/go/bin" >> "$HOME/.bashrc"
    fi
    
    if ! grep -q "\$HOME/go/bin" "$HOME/.bashrc" 2>/dev/null; then
        echo "export PATH=\$PATH:\$HOME/go/bin" >> "$HOME/.bashrc"
    fi
    
    # Export for current session
    export PATH=$PATH:/usr/local/go/bin
    export PATH=$PATH:$HOME/go/bin
    
    if command_exists go; then
        print_success "Go installed successfully: $(go version)"
    else
        print_error "Go installation failed"
        exit 1
    fi
fi

# Ensure Go bin directories are in PATH for current session
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$HOME/go/bin

# 2. Install Python dependencies
print_info "Checking Python installation..."

if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python is installed: $PYTHON_VERSION"
    
    # Check Python version (require 3.10+)
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "$PYTHON_MINOR" -lt 10 ]; then
        print_warning "Python 3.10+ is recommended. You have Python 3.$PYTHON_MINOR"
    fi
else
    print_error "Python 3 is not installed"
    print_info "Installing Python 3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# 3. Install Go-based tools
print_info "Installing Go-based security tools..."

# Tools to install
declare -A TOOLS=(
    ["httpx"]="github.com/projectdiscovery/httpx/cmd/httpx@latest"
    ["katana"]="github.com/projectdiscovery/katana/cmd/katana@latest"
    ["gau"]="github.com/lc/gau/v2/cmd/gau@latest"
)

# Optional tools
declare -A OPTIONAL_TOOLS=(
    ["gospider"]="github.com/jaeles-project/gospider@latest"
    ["hakrawler"]="github.com/hakluke/hakrawler@latest"
)

# Install required tools
for tool in "${!TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_success "$tool is already installed"
    else
        print_info "Installing $tool..."
        if go install "${TOOLS[$tool]}" 2>&1; then
            # Verify installation
            if command_exists "$tool"; then
                print_success "$tool installed successfully"
            else
                print_error "$tool installation completed but not found in PATH"
                print_warning "Make sure \$HOME/go/bin is in your PATH"
            fi
        else
            print_error "Failed to install $tool"
            exit 1
        fi
    fi
done

# Install optional tools (don't fail if they don't install)
print_info "Installing optional tools..."
for tool in "${!OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_success "$tool is already installed"
    else
        print_info "Installing $tool (optional)..."
        if go install "${OPTIONAL_TOOLS[$tool]}" 2>&1; then
            if command_exists "$tool"; then
                print_success "$tool installed successfully"
            else
                print_warning "$tool installation completed but not found in PATH"
            fi
        else
            print_warning "Failed to install optional tool: $tool (continuing anyway)"
        fi
    fi
done

# 4. Verify installations
print_info "Verifying installations..."

ALL_GOOD=true

for tool in "${!TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_success "✓ $tool"
    else
        print_error "✗ $tool (REQUIRED)"
        ALL_GOOD=false
    fi
done

for tool in "${!OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_success "✓ $tool (optional)"
    else
        print_warning "✗ $tool (optional, not critical)"
    fi
done

# 5. Summary and next steps
echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          Setup Summary               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"

if [ "$ALL_GOOD" = true ]; then
    print_success "All required dependencies are installed!"
else
    print_error "Some required dependencies are missing"
    echo ""
    print_info "Please ensure that \$HOME/go/bin is in your PATH:"
    echo "  export PATH=\$PATH:\$HOME/go/bin"
    echo ""
    echo "Then reload your shell configuration:"
    echo "  source ~/.bashrc"
    echo ""
fi

echo ""
print_info "Next steps:"
echo "  1. Install webReaper Python package:"
echo "     cd $(dirname "$0")"
echo "     python3 -m venv .venv"
echo "     source .venv/bin/activate"
echo "     pip install -e ."
echo ""
echo "  2. Run webReaper:"
echo "     webreaper reap https://example.com -o out/"
echo ""

if [ "$ALL_GOOD" = false ]; then
    print_warning "Remember to reload your shell or run:"
    echo "     source ~/.bashrc"
    echo "     export PATH=\$PATH:\$HOME/go/bin"
fi

print_success "Setup script completed!"
