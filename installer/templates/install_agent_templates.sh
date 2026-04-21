#!/bin/bash
# GiljoAI Agent Template Installer
# Cross-platform installation script for agent templates
# Supports: Claude Code, Gemini CLI, Codex CLI

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PLATFORM="claude_code"
MODEL=""
SCOPE="project"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --scope)
      SCOPE="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Usage: install_agent_templates.sh [--platform claude_code|gemini_cli|codex_cli] [--model MODEL] [--scope project|user]"
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------
case "$PLATFORM" in
  claude_code|gemini_cli|codex_cli) ;;
  *)
    echo -e "${RED}Error: Invalid platform '$PLATFORM'. Must be claude_code, gemini_cli, or codex_cli.${NC}"
    exit 1
    ;;
esac

case "$SCOPE" in
  project|user) ;;
  *)
    echo -e "${RED}Error: Invalid scope '$SCOPE'. Must be project or user.${NC}"
    exit 1
    ;;
esac

echo "GiljoAI Agent Template Installer"
echo "================================="
echo "  Platform: $PLATFORM"
echo "  Scope:    $SCOPE"
if [ -n "$MODEL" ]; then
  echo "  Model:    $MODEL"
fi
echo ""

# ---------------------------------------------------------------------------
# Check for API key
# ---------------------------------------------------------------------------
if [ -z "$GILJO_API_KEY" ]; then
  echo -e "${RED}Error: GILJO_API_KEY environment variable not set${NC}"
  echo "Configure GiljoAI MCP first: Settings -> Integrations"
  exit 1
fi

# ---------------------------------------------------------------------------
# Derive target directory from platform + scope
# ---------------------------------------------------------------------------
case "$PLATFORM" in
  claude_code)
    AGENTS_SUBDIR=".claude/agents"
    ;;
  gemini_cli)
    AGENTS_SUBDIR=".gemini/agents"
    ;;
  codex_cli)
    AGENTS_SUBDIR=".codex/agents"
    ;;
esac

if [ "$SCOPE" = "user" ]; then
  TARGET_DIR="$HOME/$AGENTS_SUBDIR"
else
  TARGET_DIR="$(pwd)/$AGENTS_SUBDIR"
fi

# ---------------------------------------------------------------------------
# Server URL (templated at export time)
# ---------------------------------------------------------------------------
SERVER_URL="{{SERVER_URL}}"
DOWNLOAD_URL="${SERVER_URL}/api/download/agent-templates.zip?platform=${PLATFORM}&active_only=true"

# ---------------------------------------------------------------------------
# Backup existing agent files
# ---------------------------------------------------------------------------
if [ -d "$TARGET_DIR" ] && [ "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_DIR="${TARGET_DIR}_backup_${TIMESTAMP}"

  echo -e "${YELLOW}Creating backup: $BACKUP_DIR${NC}"
  cp -r "$TARGET_DIR" "$BACKUP_DIR"
fi

# ---------------------------------------------------------------------------
# Download and extract
# ---------------------------------------------------------------------------
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}Downloading agent templates...${NC}"
curl -H "X-API-Key: $GILJO_API_KEY" \
  "$DOWNLOAD_URL" \
  -o "$TEMP_DIR/templates.zip" \
  --fail --silent --show-error

mkdir -p "$TARGET_DIR"

echo -e "${YELLOW}Installing to $TARGET_DIR...${NC}"
unzip -o "$TEMP_DIR/templates.zip" -d "$TARGET_DIR" > /dev/null

# Remove bundled install scripts from target (they belong in installer/, not agents/)
rm -f "$TARGET_DIR/install.sh" "$TARGET_DIR/install.ps1"

# ---------------------------------------------------------------------------
# Patch model in extracted files (if --model was provided)
# ---------------------------------------------------------------------------
if [ -n "$MODEL" ]; then
  echo -e "${YELLOW}Patching model to: $MODEL${NC}"
  # Markdown files (Claude Code, Gemini CLI): model: VALUE in YAML frontmatter
  for f in "$TARGET_DIR"/*.md; do
    [ -f "$f" ] && sed -i "s/^model: .*/model: $MODEL/" "$f"
  done
  # TOML files (Codex CLI): model = "VALUE"
  for f in "$TARGET_DIR"/*.toml; do
    [ -f "$f" ] && sed -i "s/^model = .*/model = \"$MODEL\"/" "$f"
  done
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Installed templates:"
for f in "$TARGET_DIR"/*; do
  [ -f "$f" ] && echo "  - $(basename "$f")"
done
echo ""
echo "Target: $TARGET_DIR"

# ---------------------------------------------------------------------------
# Platform-specific post-install instructions
# ---------------------------------------------------------------------------
echo ""
case "$PLATFORM" in
  claude_code)
    echo "Restart Claude Code to load agents."
    ;;
  gemini_cli)
    echo "Ensure experimental.enableAgents is true in ~/.gemini/settings.json."
    echo "Restart Gemini CLI to load agents."
    ;;
  codex_cli)
    echo "Register agents in ~/.codex/config.toml under [agents.gil-*] sections."
    echo "Enable [features] multi_agent = true."
    echo "Restart Codex CLI to load agents."
    ;;
esac
