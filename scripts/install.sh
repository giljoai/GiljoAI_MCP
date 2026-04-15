#!/usr/bin/env bash

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

# GiljoAI MCP -- Linux/macOS One-Liner Installer
#
# Quick install:
#   curl -fsSL giljo.ai/install.sh | bash
#
# Customized install:
#   curl -fsSL giljo.ai/install.sh | bash -s -- --install-dir /opt/giljoai --yes
#
# Update existing:
#   curl -fsSL giljo.ai/install.sh | bash -s -- --update

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_REPO="giljoai/GiljoAI_MCP"
GITHUB_API_URL="https://api.github.com/repos/${GITHUB_REPO}/releases/latest"
DEFAULT_INSTALL_DIR="$HOME/giljoai-mcp"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=12
MIN_NODE_MAJOR=20
SERVER_PORT=7272

# ---------------------------------------------------------------------------
# CLI parameters
# ---------------------------------------------------------------------------

INSTALL_DIR=""
SKIP_PREREQS=false
UPDATE_MODE=false
AUTO_YES=false

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --skip-prereqs)
                SKIP_PREREQS=true
                shift
                ;;
            --update)
                UPDATE_MODE=true
                shift
                ;;
            --yes|-y)
                AUTO_YES=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                err "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

show_usage() {
    cat <<'USAGE'
Usage: install.sh [OPTIONS]

Options:
  --install-dir DIR   Installation directory (default: ~/giljoai-mcp)
  --skip-prereqs      Skip prerequisite checks and installation
  --update            Non-interactive update of existing installation
  --yes, -y           Auto-confirm all prompts
  --help, -h          Show this help message

Examples:
  curl -fsSL giljo.ai/install.sh | bash
  curl -fsSL giljo.ai/install.sh | bash -s -- --install-dir /opt/giljoai --yes
  curl -fsSL giljo.ai/install.sh | bash -s -- --update
USAGE
}

# ---------------------------------------------------------------------------
# Color and output utilities
# ---------------------------------------------------------------------------

# Detect color support
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
    BRAND='\033[1;33m'   # Bold yellow
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    MUTED='\033[0;90m'
    NC='\033[0m'
else
    BRAND=''
    GREEN=''
    RED=''
    CYAN=''
    MUTED=''
    NC=''
fi

print_banner() {
    echo -e "${BRAND}"
    cat <<'BANNER'

    ========================================================
      _____ _ _  _        _    ___   __  __  ___ ___
     / ____(_) |(_)      / \  |_ _| |  \/  |/ __| _ \
    | |  __ _| | _  ___ / _ \  | |  | |\/| | (__|  _/
    | |_| | | || |/ _ / ___  | | |  | |  | |\__ |_|
     \_____|_|_|/ \___/_/   \_|___| |_|  |_||___/
              |__/
    ========================================================
         Linux / macOS Installer
    ========================================================

BANNER
    echo -e "${NC}"
}

print_phase() {
    local number="$1" title="$2"
    echo ""
    echo -e "  ${BRAND}[$number/6] $title${NC}"
    local sep_len=$(( 6 + ${#title} ))
    echo -e "  ${MUTED}$(printf '%0.s-' $(seq 1 "$sep_len"))${NC}"
}

print_step() {
    echo -e "    ${CYAN}> $*${NC}"
}

print_ok() {
    echo -e "    ${GREEN}[OK]${NC} $*"
}

print_warn() {
    echo -e "    ${BRAND}[!]${NC} $*"
}

print_fail() {
    echo -e "    ${RED}[FAIL]${NC} $*"
}

err() {
    echo -e "${RED}[error]${NC} $*" >&2
}

exit_with_error() {
    echo ""
    print_fail "$*"
    echo ""
    exit 1
}

HAS_TTY=false
if [[ -t 0 ]]; then
    HAS_TTY=true
elif [[ -r /dev/tty ]] && echo -n '' < /dev/tty 2>/dev/null; then
    HAS_TTY=true
fi

read_input() {
    if [[ "$HAS_TTY" == true ]]; then
        if [[ -t 0 ]]; then
            read -r "$@"
        else
            read -r "$@" < /dev/tty
        fi
        return 0
    fi
    return 1
}

confirm() {
    local prompt="$1"
    if [[ "$AUTO_YES" == true ]]; then
        return 0
    fi
    if [[ "$HAS_TTY" != true ]]; then
        return 0
    fi
    echo -en "    ${CYAN}$prompt [Y/n]: ${NC}"
    local answer
    read_input answer
    case "$answer" in
        n|N|no|No|NO) return 1 ;;
        *) return 0 ;;
    esac
}

# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

OS_TYPE=""
DISTRO=""
PKG_MANAGER=""

detect_os() {
    local uname_s
    uname_s="$(uname -s)"
    case "$uname_s" in
        Linux)
            OS_TYPE="linux"
            if [[ -f /etc/os-release ]]; then
                # shellcheck source=/dev/null
                . /etc/os-release
                DISTRO="$ID"
            elif [[ -f /etc/redhat-release ]]; then
                DISTRO="rhel"
            else
                DISTRO="unknown"
            fi
            # Detect package manager
            if command -v apt-get &>/dev/null; then
                PKG_MANAGER="apt"
            elif command -v dnf &>/dev/null; then
                PKG_MANAGER="dnf"
            elif command -v yum &>/dev/null; then
                PKG_MANAGER="yum"
            fi
            ;;
        Darwin)
            OS_TYPE="macos"
            DISTRO="macos"
            if command -v brew &>/dev/null; then
                PKG_MANAGER="brew"
            fi
            ;;
        *)
            exit_with_error "Unsupported operating system: $uname_s. This installer supports Linux and macOS."
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Version parsing
# ---------------------------------------------------------------------------

parse_version() {
    # Extracts major.minor from a version string like "Python 3.12.4" or "v20.11.0"
    local version_string="$1"
    echo "$version_string" | grep -oE '[0-9]+\.[0-9]+' | head -1
}

version_major() {
    echo "$1" | cut -d. -f1
}

version_minor() {
    echo "$1" | cut -d. -f2
}

# ---------------------------------------------------------------------------
# Phase 1 -- Prerequisites
# ---------------------------------------------------------------------------

check_prerequisites() {
    print_phase "1" "Checking prerequisites"

    local missing=()

    # -- Python --
    print_step "Checking Python..."
    if command -v python3 &>/dev/null; then
        local py_raw py_ver py_major py_minor
        py_raw="$(python3 --version 2>&1)"
        py_ver="$(parse_version "$py_raw")"
        py_major="$(version_major "$py_ver")"
        py_minor="$(version_minor "$py_ver")"
        if [[ "$py_major" -gt "$MIN_PYTHON_MAJOR" ]] || \
           { [[ "$py_major" -eq "$MIN_PYTHON_MAJOR" ]] && [[ "$py_minor" -ge "$MIN_PYTHON_MINOR" ]]; }; then
            print_ok "Python ${py_major}.${py_minor} found"
        else
            print_warn "Python found but version too old: $py_raw (need ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+)"
            missing+=("python")
        fi
    else
        print_warn "Python not found"
        missing+=("python")
    fi

    # -- Node.js --
    print_step "Checking Node.js..."
    if command -v node &>/dev/null; then
        local node_raw node_ver node_major
        node_raw="$(node --version 2>&1)"
        node_ver="$(parse_version "$node_raw")"
        node_major="$(version_major "$node_ver")"
        if [[ "$node_major" -ge "$MIN_NODE_MAJOR" ]]; then
            print_ok "Node.js ${node_ver} found"
        else
            print_warn "Node.js found but version too old: $node_raw (need ${MIN_NODE_MAJOR}+)"
            missing+=("node")
        fi
    else
        print_warn "Node.js not found"
        missing+=("node")
    fi

    # -- Git --
    print_step "Checking Git..."
    if command -v git &>/dev/null; then
        local git_raw
        git_raw="$(git --version 2>&1)"
        print_ok "Git found: $git_raw"
    else
        print_warn "Git not found"
        missing+=("git")
    fi

    # -- PostgreSQL --
    print_step "Checking PostgreSQL..."
    if command -v pg_isready &>/dev/null || command -v psql &>/dev/null; then
        local pg_info=""
        if command -v psql &>/dev/null; then
            pg_info="$(psql --version 2>&1)"
        fi
        print_ok "PostgreSQL found${pg_info:+: $pg_info}"
    else
        print_warn "PostgreSQL not detected"
        missing+=("postgresql")
    fi

    if [[ ${#missing[@]} -eq 0 ]]; then
        print_ok "All prerequisites satisfied"
        return
    fi

    # -- Install missing prerequisites --
    echo ""
    print_step "Missing prerequisites: ${missing[*]}"

    if ! confirm "Install missing prerequisites?"; then
        exit_with_error "Cannot continue without: ${missing[*]}. Please install them manually and re-run."
    fi

    install_prerequisites "${missing[@]}"

    # Final verification
    local still_missing=()
    for item in "${missing[@]}"; do
        case "$item" in
            python)    command -v python3 &>/dev/null || still_missing+=("python") ;;
            node)      command -v node &>/dev/null || still_missing+=("node") ;;
            git)       command -v git &>/dev/null || still_missing+=("git") ;;
            postgresql) { command -v pg_isready &>/dev/null || command -v psql &>/dev/null; } || still_missing+=("postgresql") ;;
        esac
    done

    if [[ ${#still_missing[@]} -gt 0 ]]; then
        exit_with_error "Failed to install: ${still_missing[*]}. Please install manually and re-run."
    fi

    print_ok "All prerequisites satisfied after installation"
}

install_prerequisites() {
    local items=("$@")

    case "$OS_TYPE" in
        linux)
            install_prereqs_linux "${items[@]}"
            ;;
        macos)
            install_prereqs_macos "${items[@]}"
            ;;
    esac
}

install_prereqs_linux() {
    local items=("$@")

    case "$PKG_MANAGER" in
        apt)
            print_step "Updating package lists..."
            sudo apt-get update -qq

            for item in "${items[@]}"; do
                case "$item" in
                    python)
                        print_step "Installing Python 3.12..."
                        if apt-cache show python3.12 &>/dev/null; then
                            sudo apt-get install -y -qq python3.12 python3.12-venv python3-pip
                        else
                            print_step "Adding deadsnakes PPA for Python 3.12..."
                            sudo add-apt-repository -y ppa:deadsnakes/ppa
                            sudo apt-get update -qq
                            sudo apt-get install -y -qq python3.12 python3.12-venv python3-pip
                        fi
                        print_ok "Python installed"
                        ;;
                    node)
                        print_step "Installing Node.js 20..."
                        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                        sudo apt-get install -y -qq nodejs
                        print_ok "Node.js installed"
                        ;;
                    git)
                        print_step "Installing Git..."
                        sudo apt-get install -y -qq git
                        print_ok "Git installed"
                        ;;
                    postgresql)
                        print_step "Installing PostgreSQL..."
                        # Remove any stale pgdg repo config to avoid duplicates
                        sudo rm -f /etc/apt/sources.list.d/pgdg.list /etc/apt/sources.list.d/pgdg.sources
                        sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
                        # Refresh GPG key (overwrite if stale)
                        curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor --yes -o /etc/apt/trusted.gpg.d/pgdg.gpg
                        sudo apt-get update -qq
                        sudo apt-get install -y -qq postgresql postgresql-client
                        sudo systemctl start postgresql
                        sudo systemctl enable postgresql
                        print_ok "PostgreSQL installed and started"
                        ;;
                esac
            done
            ;;
        dnf|yum)
            for item in "${items[@]}"; do
                case "$item" in
                    python)
                        print_step "Installing Python 3.12..."
                        sudo "$PKG_MANAGER" install -y python3.12 python3-pip python3-devel 2>/dev/null || \
                            sudo "$PKG_MANAGER" install -y python3 python3-pip python3-devel
                        print_ok "Python installed"
                        ;;
                    node)
                        print_step "Installing Node.js 20..."
                        curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                        sudo "$PKG_MANAGER" install -y nodejs
                        print_ok "Node.js installed"
                        ;;
                    git)
                        print_step "Installing Git..."
                        sudo "$PKG_MANAGER" install -y git
                        print_ok "Git installed"
                        ;;
                    postgresql)
                        print_step "Installing PostgreSQL..."
                        sudo "$PKG_MANAGER" install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm 2>/dev/null || true
                        sudo "$PKG_MANAGER" install -y postgresql-server postgresql
                        sudo postgresql-setup --initdb 2>/dev/null || true
                        sudo systemctl start postgresql
                        sudo systemctl enable postgresql
                        print_ok "PostgreSQL installed and started"
                        ;;
                esac
            done
            ;;
        *)
            exit_with_error "No supported package manager found (apt/dnf/yum). Please install manually: ${items[*]}"
            ;;
    esac
}

install_prereqs_macos() {
    local items=("$@")

    # Ensure Homebrew is available
    if ! command -v brew &>/dev/null; then
        print_step "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add brew to PATH for Apple Silicon
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi

    for item in "${items[@]}"; do
        case "$item" in
            python)
                print_step "Installing Python 3.12..."
                brew install python@3.12
                print_ok "Python installed"
                ;;
            node)
                print_step "Installing Node.js..."
                brew install node
                print_ok "Node.js installed"
                ;;
            git)
                print_step "Installing Git..."
                brew install git
                print_ok "Git installed"
                ;;
            postgresql)
                print_step "Installing PostgreSQL..."
                brew install postgresql@18
                brew services start postgresql@18
                print_ok "PostgreSQL installed and started"
                ;;
        esac
    done
}

# ---------------------------------------------------------------------------
# Phase 2 -- Download and verify
# ---------------------------------------------------------------------------

RELEASE_VERSION=""
RELEASE_TARBALL=""
TEMP_DIR=""

cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

download_release() {
    print_phase "2" "Downloading latest release"

    TEMP_DIR="$(mktemp -d)"

    # Fetch release metadata
    print_step "Fetching latest release info from GitHub..."
    local release_json
    release_json="$(curl -fsSL "$GITHUB_API_URL")" || \
        exit_with_error "Failed to fetch release info from GitHub. Check your internet connection."

    # Parse version and manifest URL using python3 (avoids jq dependency)
    RELEASE_VERSION="$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print(data['tag_name'].lstrip('v'))
" <<< "$release_json")"
    print_ok "Latest version: $RELEASE_VERSION"

    # Find version-manifest.json asset URL
    local manifest_url
    manifest_url="$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
assets = data.get('assets', [])
for a in assets:
    if a['name'] == 'version-manifest.json':
        print(a['browser_download_url'])
        sys.exit(0)
print('')
" <<< "$release_json")"

    if [[ -z "$manifest_url" ]]; then
        exit_with_error "Release is missing version-manifest.json. This release may be malformed."
    fi

    # Download and parse the manifest
    print_step "Downloading version manifest..."
    local manifest_json
    manifest_json="$(curl -fsSL "$manifest_url")" || \
        exit_with_error "Failed to download version manifest."

    local tarball_url expected_sha
    tarball_url="$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['tarball_url'])" <<< "$manifest_json")"
    expected_sha="$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['sha256'])" <<< "$manifest_json")"

    if [[ -z "$tarball_url" || -z "$expected_sha" ]]; then
        exit_with_error "Version manifest is incomplete (missing tarball_url or sha256)."
    fi

    # Download tarball
    local tarball_name="giljoai-mcp-${RELEASE_VERSION}.tar.gz"
    RELEASE_TARBALL="${TEMP_DIR}/${tarball_name}"

    print_step "Downloading $tarball_name..."
    curl -fsSL -o "$RELEASE_TARBALL" "$tarball_url" || \
        exit_with_error "Failed to download tarball from $tarball_url"
    print_ok "Downloaded to $RELEASE_TARBALL"

    # Verify SHA256
    print_step "Verifying SHA256 checksum..."
    local actual_sha
    if command -v sha256sum &>/dev/null; then
        actual_sha="$(sha256sum "$RELEASE_TARBALL" | awk '{print $1}')"
    elif command -v shasum &>/dev/null; then
        actual_sha="$(shasum -a 256 "$RELEASE_TARBALL" | awk '{print $1}')"
    else
        exit_with_error "Neither sha256sum nor shasum found. Cannot verify download integrity."
    fi

    # Normalize to lowercase for comparison
    actual_sha="$(echo "$actual_sha" | tr '[:upper:]' '[:lower:]')"
    expected_sha="$(echo "$expected_sha" | tr '[:upper:]' '[:lower:]')"

    if [[ "$actual_sha" != "$expected_sha" ]]; then
        rm -f "$RELEASE_TARBALL"
        exit_with_error "SHA256 mismatch! Expected: $expected_sha, Got: $actual_sha. The download may be corrupted or tampered with."
    fi
    print_ok "SHA256 verified: $actual_sha"
}

# ---------------------------------------------------------------------------
# Install / extract
# ---------------------------------------------------------------------------

install_release() {
    local target_dir="$1"
    local is_update="$2"
    local backup_dir=""

    # Back up config files before extraction if updating
    if [[ "$is_update" == true ]]; then
        print_step "Backing up configuration files..."
        backup_dir="${TEMP_DIR}/config-backup"
        mkdir -p "$backup_dir"
        for f in .env config.yaml; do
            if [[ -f "${target_dir}/$f" ]]; then
                cp "${target_dir}/$f" "${backup_dir}/$f"
                print_ok "Backed up $f"
            fi
        done
    fi

    # Create target directory
    mkdir -p "$target_dir"

    # Extract tarball
    print_step "Extracting release to $target_dir..."
    tar -xzf "$RELEASE_TARBALL" -C "$target_dir" --strip-components=1 || \
        exit_with_error "Failed to extract tarball."
    print_ok "Extraction complete"

    # Restore backed-up config files
    if [[ "$is_update" == true && -n "$backup_dir" ]]; then
        print_step "Restoring configuration files..."
        for f in .env config.yaml; do
            if [[ -f "${backup_dir}/$f" ]]; then
                cp "${backup_dir}/$f" "${target_dir}/$f"
                print_ok "Restored $f"
            fi
        done
    fi

    # Write VERSION file
    echo -n "$RELEASE_VERSION" > "${target_dir}/VERSION"
}

# ---------------------------------------------------------------------------
# Phase 3 -- Environment setup
# ---------------------------------------------------------------------------

setup_environment() {
    local target_dir="$1"
    print_phase "3" "Setting up environment"

    local venv_dir="${target_dir}/venv"
    local venv_python="${venv_dir}/bin/python"
    local venv_pip="${venv_dir}/bin/pip"

    # Create venv if it does not exist
    if [[ ! -f "$venv_python" ]]; then
        print_step "Creating Python virtual environment..."
        python3 -m venv "$venv_dir"
        print_ok "Virtual environment created"
    else
        print_ok "Virtual environment already exists"
    fi

    # Upgrade pip
    print_step "Upgrading pip..."
    "$venv_python" -m pip install --upgrade pip --quiet 2>/dev/null
    print_ok "pip upgraded"

    # Install Python dependencies
    local requirements="${target_dir}/requirements.txt"
    if [[ -f "$requirements" ]]; then
        print_step "Installing Python dependencies (this may take a few minutes)..."
        "$venv_pip" install -r "$requirements" --quiet 2>/dev/null
        print_ok "Python dependencies installed"
    else
        print_warn "requirements.txt not found -- skipping pip install"
    fi

    # Build frontend
    local frontend_dir="${target_dir}/frontend"
    if [[ -f "${frontend_dir}/package.json" ]]; then
        print_step "Installing frontend dependencies..."
        (cd "$frontend_dir" && npm install --silent > /dev/null 2>&1)
        print_ok "Frontend dependencies installed"

        print_step "Building frontend (this may take a minute)..."
        (cd "$frontend_dir" && npm run build > /dev/null 2>&1)
        print_ok "Frontend built"
    else
        print_warn "Frontend package.json not found -- skipping frontend build"
    fi
}

# ---------------------------------------------------------------------------
# Phase 4 -- Database and configuration via install.py
# ---------------------------------------------------------------------------

run_install_py() {
    local target_dir="$1"
    print_phase "4" "Database and configuration setup"

    local venv_python="${target_dir}/venv/bin/python"
    local install_py="${target_dir}/install.py"

    if [[ ! -f "$install_py" ]]; then
        exit_with_error "install.py not found in $target_dir. The release may be incomplete."
    fi

    print_step "Running install.py for database setup, config generation, and template seeding..."
    echo ""

    (cd "$target_dir" && "$venv_python" "$install_py" --setup-only) || \
        exit_with_error "install.py failed. Check the output above for details."

    print_ok "Database and configuration setup complete"
}

# ---------------------------------------------------------------------------
# Phase 5 -- Service setup
# ---------------------------------------------------------------------------

setup_service() {
    local target_dir="$1"
    local version="$2"
    print_phase "5" "Service setup"

    case "$OS_TYPE" in
        linux)
            setup_systemd_service "$target_dir"
            ;;
        macos)
            setup_launchd_agent "$target_dir"
            ;;
    esac
}

setup_systemd_service() {
    local target_dir="$1"
    local current_user
    current_user="$(whoami)"

    local service_file="/etc/systemd/system/giljoai-mcp.service"
    local unit_content
    unit_content="[Unit]
Description=GiljoAI MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=${current_user}
WorkingDirectory=${target_dir}
ExecStart=${target_dir}/venv/bin/python -m api.run_api
Restart=on-failure
RestartSec=5
Environment=PATH=${target_dir}/venv/bin:/usr/local/bin:/usr/bin

[Install]
WantedBy=multi-user.target"

    print_step "Generated systemd service configuration"

    if confirm "Install and enable systemd service (giljoai-mcp)?"; then
        echo "$unit_content" | sudo tee "$service_file" > /dev/null
        sudo systemctl daemon-reload
        sudo systemctl enable --now giljoai-mcp
        print_ok "systemd service installed and started"
        print_step "Manage with: sudo systemctl {start|stop|restart|status} giljoai-mcp"
    else
        # Save the unit file locally for reference
        echo "$unit_content" > "${target_dir}/giljoai-mcp.service"
        print_ok "Service file saved to ${target_dir}/giljoai-mcp.service"
        print_step "To install later: sudo cp giljoai-mcp.service /etc/systemd/system/ && sudo systemctl enable --now giljoai-mcp"
    fi
}

setup_launchd_agent() {
    local target_dir="$1"
    local plist_dir="$HOME/Library/LaunchAgents"
    local plist_file="${plist_dir}/com.giljoai.mcp.plist"
    local plist_content
    plist_content="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>Label</key>
    <string>com.giljoai.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>${target_dir}/venv/bin/python</string>
        <string>-m</string>
        <string>api.run_api</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${target_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${target_dir}/logs/server.log</string>
    <key>StandardErrorPath</key>
    <string>${target_dir}/logs/server.err</string>
</dict>
</plist>"

    print_step "Generated launchd agent configuration"

    if confirm "Install and load launchd agent (com.giljoai.mcp)?"; then
        mkdir -p "$plist_dir"
        mkdir -p "${target_dir}/logs"
        echo "$plist_content" > "$plist_file"
        launchctl load "$plist_file"
        print_ok "launchd agent installed and loaded"
        print_step "Manage with: launchctl {load|unload} ~/Library/LaunchAgents/com.giljoai.mcp.plist"
    else
        # Save plist locally for reference
        echo "$plist_content" > "${target_dir}/com.giljoai.mcp.plist"
        print_ok "Plist saved to ${target_dir}/com.giljoai.mcp.plist"
        print_step "To install later: cp com.giljoai.mcp.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.giljoai.mcp.plist"
    fi
}

# ---------------------------------------------------------------------------
# Phase 6 -- First run
# ---------------------------------------------------------------------------

first_run() {
    local target_dir="$1"
    local version="$2"
    print_phase "6" "First run"

    local venv_python="${target_dir}/venv/bin/python"
    local server_ready=false

    # Check if service is already running (started in phase 5)
    if curl -sf "http://localhost:${SERVER_PORT}/api/health" &>/dev/null; then
        print_ok "Server is already running on port ${SERVER_PORT}"
    else
        print_step "Starting GiljoAI MCP server..."
        (cd "$target_dir" && "$venv_python" -m api.run_api &) 2>/dev/null

        # Wait for server to start
        print_step "Waiting for server to start..."
        local waited=0
        local max_wait=15
        server_ready=false
        while [[ $waited -lt $max_wait ]]; do
            sleep 1
            waited=$((waited + 1))
            if curl -sf "http://localhost:${SERVER_PORT}/api/health" &>/dev/null; then
                server_ready=true
                break
            fi
        done

        if [[ "$server_ready" == true ]]; then
            print_ok "Server is running on port ${SERVER_PORT}"
        else
            print_warn "Server did not respond within ${max_wait} seconds."
            print_warn "You can start it manually: cd $target_dir && venv/bin/python -m api.run_api"
        fi
    fi

    # Open browser
    if [[ "$server_ready" == true ]] || curl -sf "http://localhost:${SERVER_PORT}/api/health" &>/dev/null; then
        print_step "Opening browser..."
        local url="http://localhost:${SERVER_PORT}"
        case "$OS_TYPE" in
            linux)  xdg-open "$url" 2>/dev/null || true ;;
            macos)  open "$url" 2>/dev/null || true ;;
        esac
    fi

    # Print completion summary
    echo ""
    echo -e "    ${BRAND}========================================================${NC}"
    echo -e "      ${GREEN}Installation complete!${NC}"
    echo -e "    ${BRAND}========================================================${NC}"
    echo ""
    echo -e "    ${CYAN}Version:    ${version}${NC}"
    echo -e "    ${CYAN}Location:   ${target_dir}${NC}"
    echo -e "    ${CYAN}URL:        http://localhost:${SERVER_PORT}${NC}"
    echo ""
    echo -e "    ${MUTED}To start the server later:${NC}"
    case "$OS_TYPE" in
        linux)
            echo -e "    ${MUTED}  sudo systemctl start giljoai-mcp${NC}"
            echo -e "    ${MUTED}  -- or: cd $target_dir && venv/bin/python -m api.run_api${NC}"
            ;;
        macos)
            echo -e "    ${MUTED}  launchctl load ~/Library/LaunchAgents/com.giljoai.mcp.plist${NC}"
            echo -e "    ${MUTED}  -- or: cd $target_dir && venv/bin/python -m api.run_api${NC}"
            ;;
    esac
    echo ""
    echo -e "    ${MUTED}To update to a newer version:${NC}"
    echo -e "    ${MUTED}  curl -fsSL giljo.ai/install.sh | bash -s -- --update${NC}"
    echo ""
}

# ---------------------------------------------------------------------------
# Update detection
# ---------------------------------------------------------------------------

check_existing_install() {
    local target_dir="$1"
    local version_file="${target_dir}/VERSION"

    if [[ -f "$version_file" ]]; then
        cat "$version_file"
        return 0
    fi
    return 1
}

stop_existing_service() {
    local target_dir="$1"
    print_step "Stopping existing service..."

    case "$OS_TYPE" in
        linux)
            if systemctl is-active giljoai-mcp &>/dev/null; then
                sudo systemctl stop giljoai-mcp
                print_ok "systemd service stopped"
            fi
            ;;
        macos)
            local plist="$HOME/Library/LaunchAgents/com.giljoai.mcp.plist"
            if [[ -f "$plist" ]]; then
                launchctl unload "$plist" 2>/dev/null || true
                print_ok "launchd agent unloaded"
            fi
            ;;
    esac
}

restart_service() {
    local target_dir="$1"
    print_step "Restarting service..."

    case "$OS_TYPE" in
        linux)
            if systemctl is-enabled giljoai-mcp &>/dev/null; then
                sudo systemctl restart giljoai-mcp
                print_ok "systemd service restarted"
            fi
            ;;
        macos)
            local plist="$HOME/Library/LaunchAgents/com.giljoai.mcp.plist"
            if [[ -f "$plist" ]]; then
                launchctl unload "$plist" 2>/dev/null || true
                launchctl load "$plist"
                print_ok "launchd agent restarted"
            fi
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

main() {
    parse_args "$@"
    print_banner
    detect_os

    print_step "Detected OS: ${OS_TYPE} (${DISTRO})"
    if [[ -n "$PKG_MANAGER" ]]; then
        print_step "Package manager: ${PKG_MANAGER}"
    fi

    # Resolve install directory
    local target_dir
    if [[ -n "$INSTALL_DIR" ]]; then
        target_dir="$INSTALL_DIR"
    else
        target_dir="$DEFAULT_INSTALL_DIR"
    fi
    # Resolve to absolute path
    target_dir="$(cd "$(dirname "$target_dir")" 2>/dev/null && pwd)/$(basename "$target_dir")" 2>/dev/null || target_dir="$target_dir"

    # Check for existing installation
    local is_update=false
    if [[ "$UPDATE_MODE" == true ]]; then
        is_update=true
    else
        local current_version=""
        if current_version="$(check_existing_install "$target_dir")"; then
            echo ""
            echo -e "    ${BRAND}Existing installation detected!${NC}"
            echo -e "    ${CYAN}Current version: ${current_version}${NC}"
            echo ""
            if [[ "$AUTO_YES" == true ]]; then
                is_update=true
            else
                echo -e "    ${CYAN}[U] Update (preserves config and data)${NC}"
                echo -e "    ${CYAN}[R] Reinstall (fresh install)${NC}"
                echo -e "    ${MUTED}[C] Cancel${NC}"
                echo ""
                echo -en "    ${BRAND}Choice [U/R/C]: ${NC}"
                if ! read_input choice; then
                    choice="U"
                fi
                case "${choice^^}" in
                    U) is_update=true ;;
                    R) is_update=false ;;
                    *)
                        echo -e "    ${MUTED}Installation cancelled.${NC}"
                        exit 0
                        ;;
                esac
            fi
        else
            # No existing install and not a custom dir -- ask for directory
            if [[ -z "$INSTALL_DIR" && "$AUTO_YES" != true ]]; then
                echo ""
                echo -en "    ${CYAN}Install directory [$target_dir]: ${NC}"
                if ! read_input user_dir; then
                    user_dir=""
                fi
                if [[ -n "$user_dir" ]]; then
                    target_dir="$user_dir"
                fi
            fi
        fi
    fi

    # Phase 1 -- Prerequisites
    if [[ "$SKIP_PREREQS" == true ]]; then
        print_phase "1" "Checking prerequisites"
        print_ok "Skipped (--skip-prereqs flag)"
    else
        check_prerequisites
    fi

    # Phase 2 -- Download and verify
    download_release

    # Stop existing service if updating
    if [[ "$is_update" == true ]]; then
        stop_existing_service "$target_dir"
    fi

    # Extract release
    install_release "$target_dir" "$is_update"

    # Phase 3 -- Environment setup
    setup_environment "$target_dir"

    # Phase 4 -- Database and config via install.py
    run_install_py "$target_dir"

    # Phase 5 -- Service setup
    if [[ "$is_update" == true ]]; then
        # For updates, run alembic migrations and restart
        print_phase "5" "Service setup"
        local venv_python="${target_dir}/venv/bin/python"
        if [[ -f "${target_dir}/alembic.ini" ]]; then
            print_step "Running database migrations..."
            (cd "$target_dir" && "$venv_python" -m alembic upgrade head 2>&1) || \
                print_warn "Alembic migration failed -- may need manual intervention"
        fi
        restart_service "$target_dir"
        print_ok "Service restarted with updated code"
    else
        setup_service "$target_dir" "$RELEASE_VERSION"
    fi

    # Phase 6 -- First run
    first_run "$target_dir" "$RELEASE_VERSION"
}

main "$@"
