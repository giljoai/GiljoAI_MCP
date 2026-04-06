# Handover 0910a: Archive Stale Docs and Create Scaffold

**Edition Scope:** CE
**Date:** 2026-04-06
**From Agent:** Orchestrator (0910 kickoff)
**To Agent:** documentation-manager
**Priority:** High
**Estimated Effort:** 1-2 hours
**Status:** Not Started
**Series:** 0910 Documentation Overhaul (subagent 1 of 4, runs first)

---

## Task Summary

Move every stale document in /docs out of the way and create clean scaffold files for the six documents that will ship with CE. This is the foundation pass. Subagents 0910b, 0910c, and 0910d cannot start until this is done.

---

## Critical Rules (read before touching anything)

1. No em dashes anywhere. Use colons, semicolons, and periods. Not "this -- that". Use "this: that".
2. No emoji in any document body.
3. Read actual files, not memory. Use absolute paths.
4. Do not reference handover numbers in any output document. Users do not know what handovers are.
5. Activate venv before any code inspection: `source /media/patrik/Work/GiljoAI_MCP/venv/bin/activate && export PYTHONPATH=.`
6. Use absolute paths for all bash commands. The working directory resets between bash calls.

---

## Context

The /docs folder has accumulated documentation across two years of development. Most of it references features, handover numbers, and architecture from early 2025 or before. None of it is suitable for CE public release.

The target is a small, accurate, authoritative set of documents in the /docs root. Everything else moves to /docs/archive (not deleted).

Two documents already in /docs root are kept as-is:
- `docs/EDITION_ISOLATION_GUIDE.md` (already authoritative, no rewrite needed)
- `docs/CHANGELOG.md` (kept and updated in a later session)

---

## What to Archive

**All subdirectories in /docs except:**
- `archive/` (leave as-is)
- `Screen_shots/` (leave as-is)

**All .md files in /docs root except:**
- `EDITION_ISOLATION_GUIDE.md`
- `CHANGELOG.md`

**Other file types in /docs root (non-.md):**
- Move anything that is not a markdown file and not a subdirectory to archive as well (e.g., `flow pan.txt`, `Project_mgmt.jpg`, `organization.md` is .md so it goes).

---

## Implementation Plan

### Phase 1: Verify branch and working state

```bash
cd /media/patrik/Work/GiljoAI_MCP
git status
git branch --show-current
```

Expected branch: `feature/0910-documentation-overhaul`. If not on that branch:

```bash
git checkout -b feature/0910-documentation-overhaul
```

### Phase 2: Archive subdirectories

The following subdirectories exist in /docs and must move to /docs/archive. For each, use `mv`. If a directory with the same name already exists in archive, move the contents inside it or rename with a prefix.

Directories to archive (all directories in /docs except `archive` and `Screen_shots`):
- agent-templates
- api
- architecture
- cleanup
- components
- deprecations
- devlog
- features
- guides
- reports
- saas
- security
- testing
- user_guides
- Vision
- website

```bash
cd /media/patrik/Work/GiljoAI_MCP/docs
for dir in agent-templates api architecture cleanup components deprecations devlog features guides reports saas security testing user_guides Vision website; do
  if [ -d "$dir" ]; then
    mv "$dir" archive/
    echo "Archived: $dir"
  fi
done
```

### Phase 3: Archive root .md files

Move all .md files from /docs root to /docs/archive, excluding the two kept files.

```bash
cd /media/patrik/Work/GiljoAI_MCP/docs
for f in *.md; do
  case "$f" in
    EDITION_ISOLATION_GUIDE.md|CHANGELOG.md) echo "Keeping: $f" ;;
    *) mv "$f" archive/ && echo "Archived: $f" ;;
  esac
done
```

### Phase 4: Archive non-.md root files

```bash
cd /media/patrik/Work/GiljoAI_MCP/docs
for f in *; do
  if [ ! -d "$f" ] && [ "${f##*.}" != "md" ]; then
    mv "$f" archive/ && echo "Archived non-md: $f"
  fi
done
```

### Phase 5: Create scaffold files

Create each of the six target documents with section headers only. No content yet. Subsequent subagents will fill these in.

**File 1: /docs/README_FIRST.md**

```markdown
# GiljoAI MCP Documentation

<!-- Navigation hub: links to all docs. No content here, only links. -->
<!-- Written by 0910d -->
```

**File 2: /docs/PRODUCT_OVERVIEW.md**

```markdown
# GiljoAI MCP: Product Overview

## What Is GiljoAI MCP

## Who It Is For

## Core Value Proposition

## How It Works

## Supported AI Tools

## How to Get Started

<!-- Written by 0910b -->
```

**File 3: /docs/USER_GUIDE.md**

```markdown
# GiljoAI MCP: User Guide

## Home Page

### Quick Launch Cards

### Onboarding Flow

## Dashboard

## Products

### Creating a Product

### Context Fields

### Vision Documents

### Tuning

## Projects

### Creating a Project

### Staging and Activation

### Phases: Implementation and Closeout

## Jobs

### Agent Monitoring

### Status Badges

### Auto Check-In

## Tasks

### Task Board

### Categories and Priorities

### Filtering

## User Settings

### Profile Tab

### Depth Config Tab

### Execution Mode Tab

### Setup Wizard Tab

## Admin Settings

### Network Tab

### Database Tab

### Certificates Tab

### Users Tab

## UI Elements

### WebSocket Connection Icon

### Notification Bell

<!-- Written by 0910b -->
```

**File 4: /docs/INSTALLATION_GUIDE.md**

```markdown
# GiljoAI MCP: Installation Guide

## Prerequisites

## Installation Steps

### 1. Clone the Repository

### 2. Run install.py

### 3. Setup Wizard

### 4. First Launch

## Connecting AI Tools

### Claude Code

### Codex CLI

### Gemini CLI

## Verifying the Connection

## Troubleshooting

<!-- Written by 0910c -->
```

**File 5: /docs/MCP_TOOLS_REFERENCE.md**

```markdown
# GiljoAI MCP: Tools Reference

## Overview

## Discovery

## Project Management

## Agent Lifecycle

## Messaging

## Context and Memory

## Vision Documents

## Setup and Export

<!-- Written by 0910c -->
```

**File 6: /docs/ARCHITECTURE.md**

```markdown
# GiljoAI MCP: Architecture

## Tech Stack

## System Overview

## Backend Layer

### Endpoints

### Services

### Repositories

### Models

## Frontend Layer

### Views

### Components

### Composables and Stores

## Real-Time Communication

## Authentication

## Multi-Tenant Isolation

## Agent Lifecycle

<!-- Written by 0910d -->
```

Write each scaffold file using the Write tool (or bash heredoc). Do not leave the comment markers in place after writing; the comments are only here to guide you. The actual scaffold files should have the headers but no comments.

### Phase 6: Verify the docs root

After creating scaffolds, the /docs root should contain exactly:
- README_FIRST.md
- PRODUCT_OVERVIEW.md
- USER_GUIDE.md
- INSTALLATION_GUIDE.md
- MCP_TOOLS_REFERENCE.md
- ARCHITECTURE.md
- EDITION_ISOLATION_GUIDE.md
- CHANGELOG.md
- archive/ (directory)
- Screen_shots/ (directory)

Nothing else.

```bash
ls /media/patrik/Work/GiljoAI_MCP/docs/
```

### Phase 7: Commit

```bash
cd /media/patrik/Work/GiljoAI_MCP
git add docs/
git commit -m "docs(0910a): archive stale docs, create scaffold for release documentation"
```

---

## Testing Requirements

**Manual verification:**

1. Run `ls /media/patrik/Work/GiljoAI_MCP/docs/` and confirm exactly the 8 items listed in Phase 6.
2. Run `ls /media/patrik/Work/GiljoAI_MCP/docs/archive/` and confirm the previously stale directories and files are present.
3. Confirm `docs/EDITION_ISOLATION_GUIDE.md` exists and was not modified.
4. Confirm `docs/CHANGELOG.md` exists and was not modified.
5. Open each scaffold file and confirm it has section headers but no content.

---

## Dependencies and Blockers

**Depends on:** Nothing. This is the first subagent.

**Enables:** 0910b and 0910c can run in parallel after this commits.

---

## Success Criteria

- [ ] /docs root contains exactly the 8 expected items plus 2 directories
- [ ] All stale subdirectories are in /docs/archive (nothing deleted)
- [ ] All stale root .md files are in /docs/archive
- [ ] Six scaffold files exist with correct section headers
- [ ] EDITION_ISOLATION_GUIDE.md unchanged
- [ ] CHANGELOG.md unchanged
- [ ] Commit created with the specified message

---

## Rollback Plan

All archived files remain on disk in /docs/archive. To roll back: move them back to their original locations.

```bash
cd /media/patrik/Work/GiljoAI_MCP/docs/archive
mv agent-templates api architecture cleanup components deprecations devlog features guides reports saas security testing user_guides Vision website ..
# Then move individual .md files back
```

---

## Chain Log

Update the chain log at `/media/patrik/Work/GiljoAI_MCP/prompts/0910_chain/chain_log.json` when done:

```json
{
  "0910a": {
    "status": "complete",
    "commit": "<commit hash>",
    "notes": "Archived N directories and N files. Created 6 scaffold files."
  }
}
```
