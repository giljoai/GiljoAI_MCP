#!/bin/bash

# GiljoAI MCP Coding Orchestrator - One-Liner Installation Script
# For macOS and Linux
# Usage: curl -fsSL https://install.giljo.ai/install.sh | bash

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GITHUB_REPO="giljoai/GiljoAI_MCP"
DEFAULT_INSTALL_DIR="$HOME/giljoai-mcp"
MIN_PYTHON_VERSION="3.11"
MIN_NODE_VERSION="18"
MIN_DISK_SPACE_MB=2048
LOG_FILE="$HOME/giljoai_install.log"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Display banner
show_banner() {
    echo ""
    echo "╔═════════════════════════════════════════════════════════════════════╗"
    echo "║       GiljoAI MCP Coding Orchestrator - Installation                ║"
    echo "║       Multi-Agent Orchestration Platform                            ║"
    echo "╚═════════════════════════════════════════════════════════════════════╝"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Compare version strings
version_ge() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Check Python version
check_python() {
    print_info "Checking Python installation..."
    log_message "Checking Python installation"
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        echo ""
        echo "Please install Python 3.11 or higher:"
        echo "  macOS:   brew install python@3.11"
        echo "  Ubuntu:  sudo apt install python3.11"
        echo "  Manual:  https://www.python.org/downloads/"
        echo ""
        log_message "ERROR: Python 3 not found"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    
    if ! version_ge "$PYTHON_VERSION" "$MIN_PYTHON_VERSION"; then
        print_error "Python $PYTHON_VERSION is installed, but version $MIN_PYTHON_VERSION or higher is required"
        echo ""
        echo "Please upgrade Python:"
        echo "  https://www.python.org/downloads/"
        echo ""
        log_message "ERROR: Python version $PYTHON_VERSION < $MIN_PYTHON_VERSION"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION detected"
    log_message "Python $PYTHON_VERSION detected"
}

# Check PostgreSQL
check_postgresql() {
    print_info "Checking PostgreSQL installation..."
    log_message "Checking PostgreSQL installation"
    
    if ! command_exists psql; then
        print_error "PostgreSQL is not installed"
        echo ""
        echo "Please install PostgreSQL 14 or higher:"
        echo "  macOS:   brew install postgresql@14"
        echo "  Ubuntu:  sudo apt install postgresql postgresql-contrib"
        echo "  Manual:  https://www.postgresql.org/download/"
        echo ""
        log_message "ERROR: PostgreSQL not found"
        exit 1
    fi
    
    PG_VERSION=$(psql --version | awk '{print $3}' | cut -d. -f1)
    
    if [ "$PG_VERSION" -lt 14 ]; then
        print_error "PostgreSQL $PG_VERSION is installed, but version 14 or higher is required"
        echo ""
        echo "Please upgrade PostgreSQL:"
        echo "  https://www.postgresql.org/download/"
        echo ""
        log_message "ERROR: PostgreSQL version $PG_VERSION < 14"
        exit 1
    fi
    
    print_success "PostgreSQL $PG_VERSION detected"
    log_message "PostgreSQL $PG_VERSION detected"
}

# Check Node.js
check_nodejs() {
    print_info "Checking Node.js installation..."
    log_message "Checking Node.js installation"
    
    if ! command_exists node; then
        print_error "Node.js is not installed"
        echo ""
        echo "Please install Node.js 18 or higher:"
        echo "  macOS:   brew install node@18"
        echo "  Ubuntu:  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"
        echo "  Manual:  https://nodejs.org/"
        echo ""
        log_message "ERROR: Node.js not found"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
    
    if [ "$NODE_VERSION" -lt "$MIN_NODE_VERSION" ]; then
        print_error "Node.js v$NODE_VERSION is installed, but v$MIN_NODE_VERSION or higher is required"
        echo ""
        echo "Please upgrade Node.js:"
        echo "  https://nodejs.org/"
        echo ""
        log_message "ERROR: Node.js version $NODE_VERSION < $MIN_NODE_VERSION"
        exit 1
    fi
    
    print_success "Node.js v$(node --version) detected"
    log_message "Node.js $(node --version) detected"
}

# Check disk space
check_disk_space() {
    print_info "Checking available disk space..."
    log_message "Checking disk space"
    
    # Get available space in MB
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        AVAILABLE_MB=$(df -m "$HOME" | awk 'NR==2 {print $4}')
    else
        # Linux
        AVAILABLE_MB=$(df -BM "$HOME" | awk 'NR==2 {print $4}' | sed 's/M//')
    fi
    
    if [ "$AVAILABLE_MB" -lt "$MIN_DISK_SPACE_MB" ]; then
        print_error "Insufficient disk space: ${AVAILABLE_MB}MB available, ${MIN_DISK_SPACE_MB}MB required"
        echo ""
        echo "Please free up disk space and try again"
        echo ""
        log_message "ERROR: Insufficient disk space: ${AVAILABLE_MB}MB < ${MIN_DISK_SPACE_MB}MB"
        exit 1
    fi
    
    print_success "Sufficient disk space: ${AVAILABLE_MB}MB available"
    log_message "Disk space: ${AVAILABLE_MB}MB available"
}

# Check internet connectivity
check_internet() {
    print_info "Checking internet connectivity..."
    log_message "Checking internet connectivity"
    
    if ! curl -s --head --max-time 5 https://github.com >/dev/null; then
        print_error "Cannot reach GitHub. Please check your internet connection"
        echo ""
        log_message "ERROR: No internet connectivity"
        exit 1
    fi
    
    print_success "Internet connection verified"
    log_message "Internet connection verified"
}

# Prompt for installation directory
prompt_install_directory() {
    echo ""
    print_info "Select installation directory"
    read -p "Install directory [default: $DEFAULT_INSTALL_DIR]: " INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
    
    # Expand tilde
    INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"
    
    # Create parent directory if needed
    PARENT_DIR=$(dirname "$INSTALL_DIR")
    if [ ! -d "$PARENT_DIR" ]; then
        print_error "Parent directory does not exist: $PARENT_DIR"
        exit 1
    fi
    
    # Check if directory already exists
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory already exists: $INSTALL_DIR"
        read -p "Overwrite existing installation? [y/N]: " OVERWRITE
        if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
            print_info "Installation cancelled"
            exit 0
        fi
        print_info "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    fi
    
    print_success "Installation directory: $INSTALL_DIR"
    log_message "Installation directory: $INSTALL_DIR"
}

# Download latest release
download_latest_release() {
    print_info "Downloading GiljoAI MCP Coding Orchestrator..."
    log_message "Downloading from GitHub: $GITHUB_REPO"
    
    TEMP_DIR=$(mktemp -d)
    DOWNLOAD_URL="https://github.com/$GITHUB_REPO/archive/refs/heads/master.zip"
    
    if ! curl -L -o "$TEMP_DIR/giljoai-mcp.zip" "$DOWNLOAD_URL" 2>>"$LOG_FILE"; then
        print_error "Failed to download from GitHub"
        echo ""
        echo "Manual installation:"
        echo "  git clone https://github.com/$GITHUB_REPO"
        echo "  cd GiljoAI-MCP"
        echo "  python3 install.py"
        echo ""
        log_message "ERROR: Download failed"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    print_success "Downloaded successfully"
    log_message "Download complete"
    
    # Extract archive
    print_info "Extracting files..."
    log_message "Extracting archive"
    
    if ! unzip -q "$TEMP_DIR/giljoai-mcp.zip" -d "$TEMP_DIR" 2>>"$LOG_FILE"; then
        print_error "Failed to extract archive"
        log_message "ERROR: Extraction failed"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Move to installation directory
    EXTRACTED_DIR="$TEMP_DIR/GiljoAI-MCP-master"
    mkdir -p "$INSTALL_DIR"
    mv "$EXTRACTED_DIR"/* "$INSTALL_DIR/" 2>>"$LOG_FILE"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    print_success "Files extracted to $INSTALL_DIR"
    log_message "Extraction complete"
}

# Verify installation
verify_installation() {
    print_info "Verifying installation files..."
    log_message "Verifying installation"
    
    REQUIRED_FILES=(
        "install.py"
        "startup.py"
        "requirements.txt"
        "frontend/package.json"
        "api/app.py"
        "src/giljo_mcp/__init__.py"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$INSTALL_DIR/$file" ]; then
            print_error "Missing required file: $file"
            log_message "ERROR: Missing file: $file"
            exit 1
        fi
    done
    
    print_success "All required files present"
    log_message "Verification complete"
}

# Execute install.py
execute_installer() {
    print_info "Starting interactive setup wizard..."
    echo ""
    log_message "Executing install.py"
    
    cd "$INSTALL_DIR" || exit 1
    
    # Set environment variable to indicate scripted installation
    export GILJO_SCRIPTED_INSTALL=true
    
    if ! python3 install.py; then
        print_error "Installation failed during setup wizard"
        echo ""
        echo "Check logs:"
        echo "  $LOG_FILE"
        echo "  $INSTALL_DIR/logs/install.log"
        echo ""
        log_message "ERROR: install.py failed"
        exit 1
    fi
    
    log_message "install.py completed successfully"
}

# Show success message
show_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║           Installation Complete!                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    print_success "GiljoAI MCP Coding Orchestrator installed successfully"
    echo ""
    echo "Next steps:"
    echo ""
    echo "  1. Start the server:"
    echo "     cd $INSTALL_DIR"
    echo "     python3 startup.py"
    echo ""
    echo "  2. Open your browser:"
    echo "     http://localhost:7272"
    echo ""
    echo "  3. Complete first-time setup in the web interface"
    echo ""
    echo "For help: https://github.com/$GITHUB_REPO/blob/master/docs/README_FIRST.md"
    echo ""
    log_message "Installation completed successfully"
}

# Main installation flow
main() {
    # Initialize log file
    echo "GiljoAI MCP Installation Log - $(date)" > "$LOG_FILE"
    
    # Show banner
    show_banner
    
    # Pre-flight checks
    print_info "Running pre-flight checks..."
    echo ""
    check_python
    check_postgresql
    check_nodejs
    check_disk_space
    check_internet
    echo ""
    print_success "All pre-flight checks passed"
    echo ""
    
    # User prompts
    prompt_install_directory
    
    # Download and extract
    echo ""
    download_latest_release
    
    # Verify installation
    verify_installation
    
    # Execute install.py
    echo ""
    execute_installer
    
    # Success
    show_success
}

# Run main function
main
