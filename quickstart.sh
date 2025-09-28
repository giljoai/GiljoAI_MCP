#!/bin/bash

# ============================================================
# GiljoAI MCP Intelligent Quick Start for Mac/Linux
# ============================================================
# This script will:
#   1. Check for Python 3.8+
#   2. Install Python if missing
#   3. Launch bootstrap.py for full installation
# ============================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print header
echo "============================================================"
echo "  GiljoAI MCP Orchestrator - Intelligent Quick Start"
echo "============================================================"
echo

# Detect OS
OS="unknown"
DISTRO=""
PKG_MANAGER=""

if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo -e "${GREEN}[OK]${NC} Detected macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    # Detect Linux distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        echo -e "${GREEN}[OK]${NC} Detected Linux ($NAME)"
        
        # Determine package manager
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
        elif command -v pacman &> /dev/null; then
            PKG_MANAGER="pacman"
        elif command -v zypper &> /dev/null; then
            PKG_MANAGER="zypper"
        fi
    fi
else
    echo -e "${YELLOW}[!]${NC} Unknown operating system: $OSTYPE"
fi

# ============================================================
# STEP 1: Check for Python
# ============================================================
echo
echo "[1/4] Checking for Python installation..."

PYTHON_CMD=""
PYTHON_VERSION=""
PYTHON_OK=false

# Check python3 command
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_CMD="python3"
    echo -e "${GREEN}[OK]${NC} Found Python $PYTHON_VERSION"
    
    # Check version is 3.8+
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
        PYTHON_OK=true
    else
        echo -e "${YELLOW}[!]${NC} Python version too old. Need 3.8+, found $PYTHON_VERSION"
    fi
# Check python command
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
    PYTHON_CMD="python"
    echo -e "${GREEN}[OK]${NC} Found Python $PYTHON_VERSION"
    
    # Check version
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
        PYTHON_OK=true
    else
        echo -e "${YELLOW}[!]${NC} Python version too old. Need 3.8+, found $PYTHON_VERSION"
    fi
else
    echo -e "${RED}[X]${NC} Python not found on this system"
fi

# ============================================================
# STEP 2: Install Python if needed
# ============================================================
if [ "$PYTHON_OK" = false ]; then
    echo
    echo "Python 3.8+ is required but not found or too old."
    echo
    echo "Installation options:"
    echo "  1. Automatically install Python (recommended)"
    echo "  2. Open Python download page in browser"
    echo "  3. Exit and install manually"
    echo
    read -p "Select option [1-3]: " choice
    
    case $choice in
        1)
            echo
            echo "[2/4] Installing Python..."
            
            if [ "$OS" = "macos" ]; then
                # Check for Homebrew
                if command -v brew &> /dev/null; then
                    echo "Using Homebrew to install Python..."
                    brew install python3
                    
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}[OK]${NC} Python installed successfully"
                        PYTHON_CMD="python3"
                        PYTHON_OK=true
                    else
                        echo -e "${RED}[X]${NC} Installation failed"
                        exit 1
                    fi
                else
                    echo "Homebrew not found. Installing Homebrew first..."
                    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                    
                    if [ $? -eq 0 ]; then
                        brew install python3
                        PYTHON_CMD="python3"
                        PYTHON_OK=true
                    else
                        echo -e "${RED}[X]${NC} Failed to install Homebrew"
                        echo "Please install Python manually from: https://www.python.org/downloads/"
                        exit 1
                    fi
                fi
                
            elif [ "$OS" = "linux" ]; then
                case $PKG_MANAGER in
                    apt)
                        echo "Using apt to install Python..."
                        sudo apt update
                        sudo apt install -y python3 python3-pip python3-venv
                        ;;
                    yum)
                        echo "Using yum to install Python..."
                        sudo yum install -y python3 python3-pip
                        ;;
                    dnf)
                        echo "Using dnf to install Python..."
                        sudo dnf install -y python3 python3-pip
                        ;;
                    pacman)
                        echo "Using pacman to install Python..."
                        sudo pacman -S --noconfirm python python-pip
                        ;;
                    zypper)
                        echo "Using zypper to install Python..."
                        sudo zypper install -y python3 python3-pip
                        ;;
                    *)
                        echo -e "${RED}[X]${NC} Unknown package manager"
                        echo "Please install Python manually:"
                        echo "  sudo $PKG_MANAGER install python3 python3-pip python3-venv"
                        exit 1
                        ;;
                esac
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}[OK]${NC} Python installed successfully"
                    PYTHON_CMD="python3"
                    PYTHON_OK=true
                else
                    echo -e "${RED}[X]${NC} Installation failed"
                    exit 1
                fi
            else
                echo -e "${RED}[X]${NC} Automatic installation not supported for this OS"
                echo "Please install Python manually from: https://www.python.org/downloads/"
                exit 1
            fi
            ;;
            
        2)
            echo
            echo "Opening Python download page..."
            
            # Try to open browser
            if [ "$OS" = "macos" ]; then
                open https://www.python.org/downloads/
            elif [ "$OS" = "linux" ]; then
                if command -v xdg-open &> /dev/null; then
                    xdg-open https://www.python.org/downloads/
                elif command -v gnome-open &> /dev/null; then
                    gnome-open https://www.python.org/downloads/
                else
                    echo "Could not open browser. Please visit: https://www.python.org/downloads/"
                fi
            fi
            
            echo
            echo "After installing Python 3.8+, please run this script again."
            exit 0
            ;;
            
        3)
            echo
            echo "Please install Python 3.8+ manually from:"
            echo "https://www.python.org/downloads/"
            echo
            echo "Installation commands for common systems:"
            echo "  macOS:        brew install python3"
            echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
            echo "  RHEL/CentOS:  sudo yum install python3 python3-pip"
            echo "  Arch:         sudo pacman -S python python-pip"
            exit 0
            ;;
            
        *)
            echo -e "${RED}[X]${NC} Invalid option"
            exit 1
            ;;
    esac
fi

# ============================================================
# STEP 3: Verify Python components
# ============================================================
echo
echo "[2/4] Verifying Python components..."

# Check for pip
$PYTHON_CMD -m pip --version &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[!]${NC} pip not found, installing..."
    
    # Try to install pip
    if [ "$OS" = "macos" ]; then
        $PYTHON_CMD -m ensurepip --default-pip
    elif [ "$OS" = "linux" ]; then
        # Try ensurepip first
        $PYTHON_CMD -m ensurepip --default-pip 2>/dev/null
        
        if [ $? -ne 0 ]; then
            # Fallback to package manager
            case $PKG_MANAGER in
                apt)
                    sudo apt install -y python3-pip
                    ;;
                yum|dnf)
                    sudo $PKG_MANAGER install -y python3-pip
                    ;;
                pacman)
                    sudo pacman -S --noconfirm python-pip
                    ;;
                *)
                    echo -e "${RED}[X]${NC} Failed to install pip"
                    echo "Please install pip manually"
                    exit 1
                    ;;
            esac
        fi
    fi
    
    # Verify pip is now available
    $PYTHON_CMD -m pip --version &> /dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}[X]${NC} Failed to install pip"
        exit 1
    fi
fi
echo -e "${GREEN}[OK]${NC} pip is available"

# Check for venv
$PYTHON_CMD -m venv --help &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[!]${NC} venv module not found"
    
    if [ "$OS" = "linux" ] && [ "$PKG_MANAGER" = "apt" ]; then
        echo "Installing python3-venv..."
        sudo apt install -y python3-venv
    else
        echo "Installing virtualenv as fallback..."
        $PYTHON_CMD -m pip install virtualenv
    fi
fi
echo -e "${GREEN}[OK]${NC} venv is available"

# ============================================================
# STEP 4: Launch bootstrap.py
# ============================================================
echo
echo "[3/4] Checking for bootstrap.py..."

if [ ! -f "bootstrap.py" ]; then
    echo -e "${RED}[X]${NC} bootstrap.py not found in current directory"
    echo "    Please make sure you're in the GiljoAI MCP directory"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} bootstrap.py found"
echo
echo "[4/4] Launching GiljoAI MCP installer..."
echo
echo "============================================================"
echo
echo "Starting GiljoAI MCP installer..."
echo

# Launch bootstrap with Python
$PYTHON_CMD bootstrap.py

if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[X]${NC} Installation encountered an error"
    echo "    Please check the error messages above"
    exit $?
fi

echo
echo "============================================================"
echo "  Installation completed successfully!"
echo "============================================================"
echo
echo "To start GiljoAI MCP, use the launcher created on your desktop"
echo "or run: $PYTHON_CMD -m src.giljo_mcp.mcp_server"
echo