#!/bin/bash
# GiljoAI MCP PostgreSQL Configuration Restoration Script for Linux/macOS
# This is a template - actual scripts are generated during installation
#
# INSTRUCTIONS:
# 1. Make sure you have sudo privileges
# 2. Run: sudo bash restore_pg_config.sh
#
# This script will:
# - Stop PostgreSQL service
# - Restore postgresql.conf from backup
# - Restore pg_hba.conf from backup
# - Restart PostgreSQL service

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}   GiljoAI MCP - PostgreSQL Configuration Restoration${NC}"
echo -e "${CYAN}====================================================================${NC}"
echo ""

# Function to find backup directory
find_backup_directory() {
    local installer_backups="installer/backups/postgresql"

    if [ -d "$installer_backups" ]; then
        # Find most recent backup
        local latest_backup=$(ls -t "$installer_backups" 2>/dev/null | head -1)
        if [ -n "$latest_backup" ]; then
            echo "$installer_backups/$latest_backup"
            return 0
        fi
    fi

    return 1
}

# Function to find PostgreSQL config directory
find_postgresql_config_dir() {
    local candidate_paths=(
        "/etc/postgresql/18/main"
        "/etc/postgresql/17/main"
        "/etc/postgresql/16/main"
        "/etc/postgresql/15/main"
        "/etc/postgresql/14/main"
        "/var/lib/pgsql/18/data"
        "/var/lib/pgsql/17/data"
        "/var/lib/pgsql/16/data"
        "/var/lib/pgsql/15/data"
        "/var/lib/pgsql/14/data"
        "/var/lib/postgresql/data"
        "/usr/local/var/postgres"
        "/opt/homebrew/var/postgres"
    )

    for path in "${candidate_paths[@]}"; do
        if [ -d "$path" ] && [ -f "$path/postgresql.conf" ]; then
            echo "$path"
            return 0
        fi
    done

    return 1
}

# Function to stop PostgreSQL
stop_postgresql() {
    echo -e "${YELLOW}Stopping PostgreSQL service...${NC}"

    if systemctl list-units --type=service 2>/dev/null | grep -q postgresql; then
        sudo systemctl stop postgresql
        echo -e "  ${GREEN}Service stopped via systemctl${NC}"
        return 0
    elif command -v pg_ctl &> /dev/null && [ -n "$CONFIG_DIR" ]; then
        sudo -u postgres pg_ctl stop -D "$CONFIG_DIR" 2>/dev/null || true
        echo -e "  ${GREEN}Service stopped via pg_ctl${NC}"
        return 0
    elif command -v brew &> /dev/null; then
        brew services stop postgresql 2>/dev/null || true
        echo -e "  ${GREEN}Service stopped via homebrew${NC}"
        return 0
    else
        echo -e "  ${YELLOW}WARNING: Could not stop PostgreSQL automatically${NC}"
        echo -e "  ${YELLOW}Please stop PostgreSQL manually before continuing${NC}"
        read -p "Press Enter when PostgreSQL is stopped..."
        return 0
    fi
}

# Function to start PostgreSQL
start_postgresql() {
    echo ""
    echo -e "${YELLOW}Starting PostgreSQL service...${NC}"

    if systemctl list-units --type=service 2>/dev/null | grep -q postgresql; then
        sudo systemctl start postgresql
        echo -e "  ${GREEN}Service started via systemctl${NC}"
        return 0
    elif command -v pg_ctl &> /dev/null && [ -n "$CONFIG_DIR" ]; then
        sudo -u postgres pg_ctl start -D "$CONFIG_DIR" 2>/dev/null || true
        echo -e "  ${GREEN}Service started via pg_ctl${NC}"
        return 0
    elif command -v brew &> /dev/null; then
        brew services start postgresql 2>/dev/null || true
        echo -e "  ${GREEN}Service started via homebrew${NC}"
        return 0
    else
        echo -e "  ${YELLOW}WARNING: Could not start PostgreSQL automatically${NC}"
        echo -e "  ${YELLOW}Please start PostgreSQL manually${NC}"
        return 0
    fi
}

# Parse command line arguments
BACKUP_DIR=""
CONFIG_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--backup-dir DIR] [--config-dir DIR]"
            echo ""
            echo "Options:"
            echo "  --backup-dir DIR    Path to backup directory"
            echo "  --config-dir DIR    Path to PostgreSQL config directory"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Determine backup directory
if [ -z "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}Searching for backup directory...${NC}"
    if BACKUP_DIR=$(find_backup_directory); then
        echo -e "  ${GREEN}Found backup: $BACKUP_DIR${NC}"
    else
        echo -e "${RED}ERROR: No backup directory found!${NC}"
        echo -e "${RED}Please specify backup directory with --backup-dir${NC}"
        exit 1
    fi
fi

# Determine config directory
if [ -z "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Searching for PostgreSQL configuration directory...${NC}"
    if CONFIG_DIR=$(find_postgresql_config_dir); then
        echo -e "  ${GREEN}Found config: $CONFIG_DIR${NC}"
    else
        echo -e "${RED}ERROR: PostgreSQL configuration directory not found!${NC}"
        echo -e "${RED}Please specify config directory with --config-dir${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo -e "  ${GRAY}Backup directory: $BACKUP_DIR${NC}"
echo -e "  ${GRAY}Config directory: $CONFIG_DIR${NC}"
echo ""

# Verify backup files exist
POSTGRESQL_BACKUP="$BACKUP_DIR/postgresql.conf"
HBA_BACKUP="$BACKUP_DIR/pg_hba.conf"

if [ ! -f "$POSTGRESQL_BACKUP" ]; then
    echo -e "${RED}ERROR: postgresql.conf backup not found at $POSTGRESQL_BACKUP${NC}"
    exit 1
fi

if [ ! -f "$HBA_BACKUP" ]; then
    echo -e "${RED}ERROR: pg_hba.conf backup not found at $HBA_BACKUP${NC}"
    exit 1
fi

# Verify config directory exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo -e "${RED}ERROR: Configuration directory not found: $CONFIG_DIR${NC}"
    exit 1
fi

# Confirm restoration
echo -e "${YELLOW}WARNING: This will restore PostgreSQL configuration files to their backed-up state.${NC}"
echo -e "${YELLOW}         Current server mode settings will be lost.${NC}"
echo ""
read -p "Do you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Restoration cancelled.${NC}"
    exit 0
fi

echo ""

# Stop PostgreSQL
stop_postgresql

echo ""
echo -e "${YELLOW}Restoring configuration files...${NC}"

# Create backup of current files (before restoration)
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
PRE_RESTORE_BACKUP="$BACKUP_DIR/pre_restore_$TIMESTAMP"
sudo mkdir -p "$PRE_RESTORE_BACKUP"

CURRENT_POSTGRESQL="$CONFIG_DIR/postgresql.conf"
CURRENT_HBA="$CONFIG_DIR/pg_hba.conf"

if [ -f "$CURRENT_POSTGRESQL" ]; then
    sudo cp "$CURRENT_POSTGRESQL" "$PRE_RESTORE_BACKUP/postgresql.conf"
    echo -e "  ${GRAY}Current postgresql.conf backed up${NC}"
fi

if [ -f "$CURRENT_HBA" ]; then
    sudo cp "$CURRENT_HBA" "$PRE_RESTORE_BACKUP/pg_hba.conf"
    echo -e "  ${GRAY}Current pg_hba.conf backed up${NC}"
fi

# Restore files
sudo cp "$POSTGRESQL_BACKUP" "$CURRENT_POSTGRESQL"
echo -e "  ${GREEN}Restored postgresql.conf${NC}"

sudo cp "$HBA_BACKUP" "$CURRENT_HBA"
echo -e "  ${GREEN}Restored pg_hba.conf${NC}"

# Set proper permissions
sudo chmod 600 "$CURRENT_POSTGRESQL"
sudo chmod 600 "$CURRENT_HBA"

# Set proper ownership (try different approaches)
if id -u postgres &>/dev/null; then
    sudo chown postgres:postgres "$CURRENT_POSTGRESQL" 2>/dev/null || true
    sudo chown postgres:postgres "$CURRENT_HBA" 2>/dev/null || true
elif id -u _postgres &>/dev/null; then
    sudo chown _postgres:_postgres "$CURRENT_POSTGRESQL" 2>/dev/null || true
    sudo chown _postgres:_postgres "$CURRENT_HBA" 2>/dev/null || true
fi

# Start PostgreSQL
start_postgresql

echo ""
echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}   Configuration Restoration Complete!${NC}"
echo -e "${GREEN}====================================================================${NC}"
echo ""
echo -e "${GRAY}PostgreSQL configuration files have been restored.${NC}"
echo -e "${GRAY}Pre-restoration backup saved to: $PRE_RESTORE_BACKUP${NC}"
echo ""
