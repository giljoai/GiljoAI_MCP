#!/bin/bash
# GiljoAI MCP - Linux Dependency Installer
# Automated installation of PostgreSQL, Python, and Node.js on Linux
# Supports Ubuntu, Debian, RHEL, CentOS, Fedora

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==========================================================${NC}"
echo -e "${CYAN}  GiljoAI MCP - Linux Dependency Installer${NC}"
echo -e "${CYAN}==========================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}WARNING: Running as root${NC}"
    echo -e "${YELLOW}It's recommended to run this script as a regular user${NC}"
    echo ""
fi

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    else
        echo -e "${RED}ERROR: Cannot detect Linux distribution${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Detected: $PRETTY_NAME${NC}"
    echo ""
}

# Install PostgreSQL
install_postgresql() {
    echo -e "${GREEN}Installing PostgreSQL 18...${NC}"
    
    case $DISTRO in
        ubuntu|debian)
            # Add PostgreSQL repository
            echo -e "${CYAN}Adding PostgreSQL repository...${NC}"
            sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
            wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
            
            # Install PostgreSQL
            sudo apt update
            sudo apt install -y postgresql-18 postgresql-client-18
            
            # Start service
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
            
        rhel|centos|fedora)
            # Add PostgreSQL repository
            echo -e "${CYAN}Adding PostgreSQL repository...${NC}"
            sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm || true
            
            # Install PostgreSQL
            sudo dnf install -y postgresql18-server postgresql18
            
            # Initialize and start
            sudo /usr/pgsql-18/bin/postgresql-18-setup initdb || true
            sudo systemctl start postgresql-18
            sudo systemctl enable postgresql-18
            ;;
            
        *)
            echo -e "${RED}ERROR: Unsupported distribution for auto-install${NC}"
            echo "Please install PostgreSQL manually"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}PostgreSQL installed${NC}"
    echo ""
}

# Install Python
install_python() {
    echo -e "${GREEN}Installing Python 3.11+...${NC}"
    
    case $DISTRO in
        ubuntu|debian)
            # Check if Python 3.11+ is available
            if apt-cache show python3.13 >/dev/null 2>&1; then
                sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip
            elif apt-cache show python3.12 >/dev/null 2>&1; then
                sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
            elif apt-cache show python3.11 >/dev/null 2>&1; then
                sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
            else
                # Add deadsnakes PPA for older Ubuntu
                echo -e "${CYAN}Adding deadsnakes PPA for Python 3.13...${NC}"
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt update
                sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip
            fi
            ;;
            
        rhel|centos|fedora)
            sudo dnf install -y python3.11 python3-pip python3-devel || \
            sudo dnf install -y python3 python3-pip python3-devel
            ;;
            
        *)
            echo -e "${RED}ERROR: Unsupported distribution${NC}"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}Python installed${NC}"
    echo ""
}

# Install Node.js
install_nodejs() {
    echo -e "${GREEN}Installing Node.js 18...${NC}"
    
    case $DISTRO in
        ubuntu|debian)
            # Add NodeSource repository
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt install -y nodejs
            ;;
            
        rhel|centos|fedora)
            # Add NodeSource repository
            curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
            sudo dnf install -y nodejs
            ;;
            
        *)
            echo -e "${RED}ERROR: Unsupported distribution${NC}"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}Node.js installed${NC}"
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
        echo -e "  1. Run: ${YELLOW}python3 installer/cli/install.py${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}Some dependencies failed to install${NC}"
        echo -e "${RED}Please install missing dependencies manually${NC}"
        echo ""
        return 1
    fi
}

# Main installation flow
main() {
    detect_distro
    
    # Check if dependencies already installed
    SKIP_PG=false
    SKIP_PY=false
    SKIP_NODE=false
    
    if command -v psql >/dev/null 2>&1; then
        echo -e "${YELLOW}PostgreSQL already installed, skipping${NC}"
        SKIP_PG=true
    fi
    
    if command -v python3 >/dev/null 2>&1; then
        echo -e "${YELLOW}Python already installed, skipping${NC}"
        SKIP_PY=true
    fi
    
    if command -v node >/dev/null 2>&1; then
        echo -e "${YELLOW}Node.js already installed, skipping${NC}"
        SKIP_NODE=true
    fi
    
    echo ""
    
    # Install dependencies
    [ "$SKIP_PG" = false ] && install_postgresql
    [ "$SKIP_PY" = false ] && install_python
    [ "$SKIP_NODE" = false ] && install_nodejs
    
    # Verify
    verify_installations
}

# Run main function
main
