#!/usr/bin/env bash
# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.
#
# export_ce.sh -- Generate the public CE repo from the private repo.
#
# Usage:
#   ./scripts/export_ce.sh              # dry-run (shows what would happen)
#   ./scripts/export_ce.sh --push       # actually push to public repo
#
# What it does:
#   1. Clones this private repo to a temp directory
#   2. Deletes SaaS-only and demo-only directories
#   3. Deletes files listed in .export-exclude
#   4. Adds license headers to any .py files missing them
#   5. Optionally force-pushes the result to the public repo
#
# The public repo (GiljoAI_MCP) becomes a byte-for-byte CE derivation
# of this private repo. Community PRs are the only external changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PUBLIC_REPO="/media/patrik/Work/GiljoAI_MCP"
TEMP_DIR=""
DRY_RUN=true

# Parse args
if [[ "${1:-}" == "--push" ]]; then
    DRY_RUN=false
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[export]${NC} $*"; }
warn() { echo -e "${YELLOW}[export]${NC} $*"; }
err()  { echo -e "${RED}[export]${NC} $*" >&2; }

cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        log "Cleaning up temp directory..."
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# ── Preflight checks ──────────────────────────────────────────

if [[ ! -d "$REPO_ROOT/.git" ]]; then
    err "Not a git repo: $REPO_ROOT"
    exit 1
fi

if [[ ! -d "$PUBLIC_REPO/.git" ]]; then
    err "Public repo not found at: $PUBLIC_REPO"
    exit 1
fi

# ── Step 1: Clone to temp ─────────────────────────────────────

TEMP_DIR="$(mktemp -d)"
log "Cloning private repo to temp: $TEMP_DIR"
git clone --single-branch --branch master "$REPO_ROOT" "$TEMP_DIR/export" --quiet

cd "$TEMP_DIR/export"

# ── Step 2: Delete SaaS, demo, and private-only directories ───

STRIP_DIRS=(
    "src/giljo_mcp/saas"
    "api/saas_endpoints"
    "api/saas_middleware"
    "frontend/src/saas"
    "demo"
    "handovers"
    "agent_comms.json"
)

log "Stripping private-only content..."
for dir in "${STRIP_DIRS[@]}"; do
    if [[ -e "$dir" ]]; then
        rm -rf "$dir"
        log "  removed: $dir"
    fi
done

# ── Step 3: Delete files from .export-exclude ──────────────────

# Read .export-exclude from the ORIGINAL repo (not the temp clone, which also has it)
EXCLUDE_FILE="$REPO_ROOT/.export-exclude"
exclude_count=0
if [[ -f "$EXCLUDE_FILE" ]]; then
    log "Applying .export-exclude..."
    while IFS= read -r pattern || [[ -n "$pattern" ]]; do
        # Skip comments and blank lines
        pattern="$(echo "$pattern" | sed 's/#.*//' | xargs)"
        [[ -z "$pattern" ]] && continue
        # Use find for directory patterns (ending with /)
        if [[ "$pattern" == */ ]]; then
            if [[ -d "${pattern%/}" ]]; then
                rm -rf "${pattern%/}"
                log "  excluded dir: ${pattern%/}"
                exclude_count=$((exclude_count + 1))
            fi
        else
            # Expand globs with nullglob
            shopt -s nullglob
            matches=($pattern)
            shopt -u nullglob
            for f in "${matches[@]}"; do
                rm -rf "$f"
                log "  excluded: $f"
                exclude_count=$((exclude_count + 1))
            done
        fi
    done < "$EXCLUDE_FILE"
    log "  Total exclusions: $exclude_count"
fi

# ── Step 4: Ensure license headers on all .py files ───────────

HEADER='# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.'

MARKER="# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved."

header_count=0
while IFS= read -r -d '' pyfile; do
    # Skip empty __init__.py
    if [[ "$(basename "$pyfile")" == "__init__.py" && ! -s "$pyfile" ]]; then
        continue
    fi
    # Skip files already containing the marker (check first 5 lines to catch shebang files)
    if head -5 "$pyfile" | grep -qF "$MARKER"; then
        continue
    fi
    # Check for shebang
    first_line="$(head -1 "$pyfile")"
    if [[ "$first_line" == "#!"* ]]; then
        rest="$(tail -n +2 "$pyfile")"
        printf '%s\n\n%s\n\n%s\n' "$first_line" "$HEADER" "$rest" > "$pyfile"
    else
        original="$(cat "$pyfile")"
        printf '%s\n\n%s\n' "$HEADER" "$original" > "$pyfile"
    fi
    header_count=$((header_count + 1))
done < <(find . -name "*.py" -type f -print0)

if [[ $header_count -gt 0 ]]; then
    log "  Added license headers to $header_count files (safety net)"
fi

# ── Step 5: Update CLAUDE.md for public repo ──────────────────

if [[ -f "CLAUDE.md" ]]; then
    # Replace the private repo CLAUDE.md with the public version
    cat > CLAUDE.md << 'CLAUDE_EOF'
# CLAUDE.md -- Project Instructions for GiljoAI MCP

## Repository Role

**This is the public Community Edition (CE) repo.** It is a read-only downstream of the private repo, generated by `scripts/export_ce.sh`.

**Rules for this repo:**
- Do NOT commit directly here (except merging community PRs).
- All development happens in the private repo (`GiljoAI_MCP_Private`).
- Community contributions: submit PRs here. Once merged, they are cherry-picked into the private repo.
- Contents are overwritten on each CE release export.

## Project Overview

GiljoAI MCP is an AI agent orchestration platform (the "Coding Orchestrator"). This is the Community Edition -- free for single-user use under the GiljoAI Community License v1.1.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 18
- **Frontend:** Vue 3 (Composition API), Pinia, Vuetify 3, Vite
- **Real-time:** WebSocket via PostgresNotifyBroker
- **Auth:** JWT httpOnly cookies, CSRF double-submit
- **Network:** Localhost binds 127.0.0.1 (HTTP). LAN/WAN binds 0.0.0.0 with mandatory HTTPS (mkcert). Bind address derived from install-time network choice.

## Code Conventions

- Every database query MUST filter by `tenant_key` -- no exceptions
- No AI signatures in code or commits
- License is GiljoAI Community License v1.1 -- never use terms "MIT", "open source", or "open core"
- All Python layers raise exceptions on error -- never `return {"success": False, ...}`
- No function exceeds 200 lines, no class exceeds 1000 lines without justification
- No commented-out code -- delete it, git has the history
- All Python source files must have the 4-line license header
- See `docs/CODE_STANDARDS.md` for full code discipline requirements

## Key Documents

- `docs/INSTALLATION_GUIDE.md` -- setup instructions
- `docs/GETTING_STARTED.md` -- first steps after install
- `docs/USER_GUIDE.md` -- full feature walkthrough
- `docs/PRODUCT_OVERVIEW.md` -- what GiljoAI MCP is and why
- `docs/MCP_TOOLS_REFERENCE.md` -- all 29 MCP tools documented
- `docs/ARCHITECTURE.md` -- system architecture
- `docs/CODE_STANDARDS.md` -- code discipline and quality gates
- `CONTRIBUTING.md` -- how to contribute
- `SECURITY.md` -- vulnerability reporting
- `LICENSE` -- GiljoAI Community License v1.1
CLAUDE_EOF
    log "  Replaced CLAUDE.md with public version"
fi

# ── Step 6: Commit and optionally push ────────────────────────

git add -A
git commit -m "CE export from private repo" --quiet --allow-empty

# Summary
log ""
log "═══════════════════════════════════════════════"
log "  Export complete!"
log "  Temp dir: $TEMP_DIR/export"
log "  Files stripped: saas/, demo/, handovers/"
log "  License headers added: $header_count"
log "═══════════════════════════════════════════════"

if [[ "$DRY_RUN" == true ]]; then
    warn ""
    warn "DRY RUN -- nothing pushed. Review the export at:"
    warn "  $TEMP_DIR/export"
    warn ""
    warn "To push for real, run:"
    warn "  ./scripts/export_ce.sh --push"
    warn ""
    warn "Note: temp dir will be cleaned up when this script exits."
    warn "Press Enter to clean up, or Ctrl+C to keep the temp dir for inspection."
    read -r
else
    log "Pushing to public repo..."
    cd "$PUBLIC_REPO"
    # Fetch the export commit and reset local to it
    git fetch "$TEMP_DIR/export" master --quiet
    git reset --hard FETCH_HEAD --quiet
    log ""
    log "Local public repo updated at: $PUBLIC_REPO"
    log ""
    # Push to GitHub
    log "Pushing to GitHub..."
    git push origin master --force
    log "GitHub push complete."
fi
