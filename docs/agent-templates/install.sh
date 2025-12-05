#!/bin/bash
# GiljoAI Agent Template Installer
# Cross-platform installation script for agent templates

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "GiljoAI Agent Template Installer"
echo "================================="
echo ""

# Check for API key
if [ -z "$GILJO_API_KEY" ]; then
  echo -e "${RED}Error: GILJO_API_KEY environment variable not set${NC}"
  echo "Configure GiljoAI MCP first: Settings â†’ Integrations"
  exit 1
fi

# Installation type (product or personal)
INSTALL_TYPE="${1:-product}"

# Determine target directory
if [ "$INSTALL_TYPE" = "personal" ]; then
  TARGET_DIR="$HOME/.claude/agents"
else
  TARGET_DIR="$(pwd)/.claude/agents"
fi

# Server URL (templated)
SERVER_URL="http://10.1.0.164:7272"
DOWNLOAD_URL="${SERVER_URL}/api/download/agent-templates.zip?active_only=true"

# Create backup if directory exists
if [ -d "$TARGET_DIR" ] && [ "$(ls -A $TARGET_DIR 2>/dev/null)" ]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_DIR="${TARGET_DIR}_backup_${TIMESTAMP}"

  echo -e "${YELLOW}Creating backup: $BACKUP_DIR${NC}"
  cp -r "$TARGET_DIR" "$BACKUP_DIR"
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}Downloading agent templates...${NC}"
curl -H "X-API-Key: $GILJO_API_KEY" \
  "$DOWNLOAD_URL" \
  -o "$TEMP_DIR/templates.zip" \
  --fail --silent --show-error

# Create target directory
mkdir -p "$TARGET_DIR"

echo -e "${YELLOW}Installing to $TARGET_DIR...${NC}"
unzip -o "$TEMP_DIR/templates.zip" -d "$TARGET_DIR" > /dev/null

echo ""
echo -e "${GREEN}âœ… Installation complete!${NC}"
echo ""
echo "Installed templates:"
ls -1 "$TARGET_DIR"/*.md | sed 's/.*\//  - /'
echo ""
echo "Target: $TARGET_DIR"
