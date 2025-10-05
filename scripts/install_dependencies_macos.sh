#!/bin/bash
# GiljoAI MCP - macOS Dependency Installer
# Automated installation of PostgreSQL, Python, and Node.js on macOS
# Requires Homebrew

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==========================================================${NC}"
echo -e "${CYAN}  GiljoAI MCP - macOS Dependency Installer${NC}"
echo -e "${CYAN}==========================================================${NC}"
echo ""

# Check if Homebrew is installed
check_homebrew() {
    if ! command -v brew >/dev/null 2>&1; then
        echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for current session
        if [ -f "/opt/homebrew/bin/brew" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo -e "${GREEN}Homebrew is installed${NC}"
        brew --version
    fi
    echo ""
}

# Install PostgreSQL
install_postgresql() {
    echo -e "${GREEN}Installing PostgreSQL 18...${NC}"
    
    if command -v psql >/dev/null 2>&1; then
        echo -e "${YELLOW}PostgreSQL already installed, skipping${NC}"
    else
        brew install postgresql@18
        brew services start postgresql@18
        
        # Add PostgreSQL to PATH
        echo -e "${CYAN}Adding PostgreSQL to PATH...${NC}"
        echo 'export PATH="/usr/local/opt/postgresql@18/bin:$PATH"' >> ~/.zshrc || true
        echo 'export PATH="/usr/local/opt/postgresql@18/bin:$PATH"' >> ~/.bashrc || true
    fi
    
    echo ""
}

# Install Python
install_python() {
    echo -e "${GREEN}Installing Python 3.13...${NC}"
    
    if command -v python3 >/dev/null 2>&1; then
        PY_VERSION=$(python3 --version | awk '{print $2}')
        MAJOR=$(echo $PY_VERSION | cut -d. -f1)
        MINOR=$(echo $PY_VERSION | cut -d. -f2)
        
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            echo -e "${YELLOW}Python $PY_VERSION already installed (>=3.11)${NC}"
        else
            echo -e "${YELLOW}Python $PY_VERSION found, but 3.11+ required. Installing Python 3.13...${NC}"
            brew install python@3.13
        fi
    else
        brew install python@3.13
        
        # Add Python to PATH
        echo -e "${CYAN}Adding Python to PATH...${NC}"
        echo 'export PATH="/usr/local/opt/python@3.13/bin:$PATH"' >> ~/.zshrc || true
        echo 'export PATH="/usr/local/opt/python@3.13/bin:$PATH"' >> ~/.bashrc || true
    fi
    
    echo ""
}

# Install Node.js
install_nodejs() {
    echo -e "${GREEN}Installing Node.js 18...${NC}"
    
    if command -v node >/dev/null 2>&1; then
        echo -e "${YELLOW}Node.js already installed, skipping${NC}"
    else
        brew install node@18
        
        # Add Node.js to PATH
        echo -e "${CYAN}Adding Node.js to PATH...${NC}"
        echo 'export PATH="/usr/local/opt/node@18/bin:$PATH"' >> ~/.zshrc || true
        echo 'export PATH="/usr/local/opt/node@18/bin:$PATH"' >> ~/.bashrc || true
    fi
    
    echo ""
}

# Verify installations
verify_installations() {
    echo -e "${CYAN}==========================================================${NC}"
    echo -e "${CYAN}  Verifying Installations${NC}"
    echo -e "${CYAN}==========================================================${NC}"
    echo ""
    
    ALL_GOOD=true
    
    # Check PostgreSQL
    if command -v psql >/dev/null 2>&1; then
        PG_VERSION=$(psql --version)
        echo -e "${GREEN}[OK] PostgreSQL: $PG_VERSION${NC}"
    else
        echo -e "${RED}[FAIL] PostgreSQL not found${NC}"
        echo -e "${YELLOW}  Try: export PATH=\"/usr/local/opt/postgresql@18/bin:\$PATH\"${NC}"
        ALL_GOOD=false
    fi
    
    # Check Python
    if command -v python3 >/dev/null 2>&1; then
        PY_VERSION=$(python3 --version)
        echo -e "${GREEN}[OK] Python: $PY_VERSION${NC}"
    else
        echo -e "${RED}[FAIL] Python not found${NC}"
        ALL_GOOD=false
    fi
    
    # Check Node.js
    if command -v node >/dev/null 2>&1; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        echo -e "${GREEN}[OK] Node.js: $NODE_VERSION${NC}"
        echo -e "${GREEN}[OK] npm: v$NPM_VERSION${NC}"
    else
        echo -e "${RED}[FAIL] Node.js not found${NC}"
        ALL_GOOD=false
    fi
    
    echo ""
    
    if [ "$ALL_GOOD" = true ]; then
        echo -e "${GREEN}All dependencies installed successfully!${NC}"
        echo ""
        echo -e "${CYAN}Next steps:${NC}"
        echo -e "  1. Restart your terminal to refresh PATH"
        echo -e "  2. Run: ${YELLOW}python3 installer/cli/install.py${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}Some dependencies failed to install${NC}"
        echo -e "${YELLOW}You may need to restart your terminal or source your shell config:${NC}"
        echo -e "  ${YELLOW}source ~/.zshrc${NC}  (if using zsh)"
        echo -e "  ${YELLOW}source ~/.bashrc${NC} (if using bash)"
        echo ""
        return 1
    fi
}

# Main installation flow
main() {
    check_homebrew
    install_postgresql
    install_python
    install_nodejs
    verify_installations
}

# Run main function
main
