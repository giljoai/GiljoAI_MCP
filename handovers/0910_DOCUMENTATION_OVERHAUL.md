# Handover 0910: Documentation Overhaul Series (Orchestrator Kickoff)

**Edition Scope:** CE
**Date:** 2026-04-06
**Priority:** High
**Estimated Effort:** 8-12 hours (orchestrator + 4 documentation subagents)
**Status:** Not Started

---

## Task Summary

Complete rewrite of the /docs folder for CE public release. Archive all stale documents. Produce a small set of authoritative, current documents that ship with the product. The orchestrator runs one session with multiple documentation subagents executing 0910a through 0910d in sequence.

## Context / Background

The /docs folder has 135 non-archived markdown files across 17 subdirectories. Most reference October-December 2025 features, stale handover numbers, and deprecated architecture. The README_FIRST.md hub references features from handover 0035-0107 era. None of this is suitable for a public CE release.

The product has evolved significantly: setup wizard (0855), MCP SDK migration (0846), multi-platform support (Claude/Codex/Gemini), 0950 quality sprint, and hundreds of handovers since the existing docs were written.

## Architecture Decision

**What ships:** A small set of focused documents in /docs root. No subdirectories except /docs/archive and /docs/Screen_shots.

**What gets archived:** Everything currently in /docs subdirectories (except archive and Screen_shots) moves to /docs/archive. The 176 files already in archive stay there.

**Writing style:** No em dashes. Use colons, semicolons, and periods. Clear, direct prose. No emoji in document body.

## Target Document Set (what ships in /docs root)

| Document | Purpose | Source Material |
|----------|---------|----------------|
| **README_FIRST.md** | Navigation hub: links to all other docs, nothing else | Rewrite from scratch |
| **PRODUCT_OVERVIEW.md** | What GiljoAI MCP is, what it does, who it is for. Harmonize with the How to Use learning modal (6 chapters). | Learning modal content in frontend, GILJOAI_MCP_PURPOSE.md |
| **USER_GUIDE.md** | Each page explained: Home, Dashboard, Products, Projects, Jobs, Tasks. What happens on each, how it works. User Settings tabs. Admin Settings tabs. WebSocket icon. Notification bell. | Frontend components, tooltip text, field hints |
| **INSTALLATION_GUIDE.md** | install.py to setup wizard to first project. Cross-platform (Windows, Linux). MCP connection for Claude/Codex/Gemini. | install.py, setup wizard components, giljo_setup tool |
| **MCP_TOOLS_REFERENCE.md** | Every MCP tool listed with name, description, parameters, and example usage. Organized by category (project management, agent lifecycle, messaging, context, discovery). | mcp_sdk_server.py tool registrations |
| **ARCHITECTURE.md** | Tech stack, system diagram, backend/frontend/database layers. Tenant isolation. WebSocket real-time. | SERVER_ARCHITECTURE_TECH_STACK.md, code structure |
| **EDITION_ISOLATION_GUIDE.md** | Kept as-is: CE vs SaaS directory rules (already authoritative) | No rewrite needed |
| **CHANGELOG.md** | Kept and updated for v1.0.0 | Existing + git history |

## Series Structure

### 0910a: Archive + Scaffold (Subagent 1)

Move all non-shipping docs to /docs/archive. Create empty scaffold files for each target document with section headers only. This gives subsequent agents a clean workspace.

**Scope:**
- Move all /docs subdirectories except archive/ and Screen_shots/ into /docs/archive/
- Move all /docs root .md files except EDITION_ISOLATION_GUIDE.md and CHANGELOG.md into /docs/archive/
- Create scaffold files with section headers for: README_FIRST.md, PRODUCT_OVERVIEW.md, USER_GUIDE.md, INSTALLATION_GUIDE.md, MCP_TOOLS_REFERENCE.md, ARCHITECTURE.md
- Commit: "docs(0910a): archive stale docs, create scaffold for release documentation"

**Effort:** Light (1-2 hours)
**Depends on:** Nothing

### 0910b: Product Overview + User Guide (Subagent 2)

Write PRODUCT_OVERVIEW.md and USER_GUIDE.md. These are the user-facing documents.

**Scope:**
- PRODUCT_OVERVIEW.md: what the product is, core value proposition, the 6 chapters from the How to Use modal (read frontend/src/components/learning/LearningModal.vue or similar), target audience, platform support
- USER_GUIDE.md: detailed page-by-page guide
  - Home page: quick launch cards, greeting, onboarding flow
  - Dashboard: stats, recent projects, recent memories
  - Products: product management, context fields, vision documents, tuning
  - Projects: create/edit with taxonomy, staging, implementation, closeout
  - Jobs: agent monitoring, status badges, phase tracking, auto check-in
  - Tasks: task board, categories, priorities, filtering
  - User Settings: each tab explained (Profile, Depth Config, Execution Mode, Setup Wizard)
  - Admin Settings: each tab explained (Network, Database, Certificates, Users)
  - WebSocket connection icon: what it means, click behavior
  - Notification bell: what shows up, lifecycle, clearance
- Source material: read Vue components for tooltip/hint text, read stores for data flow

**Effort:** Heavy (3-4 hours)
**Depends on:** 0910a (clean workspace)

### 0910c: Installation Guide + MCP Tools Reference (Subagent 3)

Write INSTALLATION_GUIDE.md and MCP_TOOLS_REFERENCE.md. These are the technical documents.

**Scope:**
- INSTALLATION_GUIDE.md: complete flow from git clone to first project
  - Prerequisites (Python 3.12+, Node 18+, PostgreSQL 18)
  - install.py walkthrough (what it does, prompts, config generation)
  - First launch: setup wizard steps 1-4
  - MCP connection: Claude Code, Codex CLI, Gemini CLI (each platform)
  - giljo_setup: what it installs, how to verify
  - Troubleshooting: common issues
  - Source: install.py, setup wizard components, giljo_setup tool code
- MCP_TOOLS_REFERENCE.md: every MCP tool
  - Read api/endpoints/mcp_sdk_server.py for all @mcp.tool registrations
  - For each tool: name, description, parameters with types and descriptions, example call, response shape
  - Organize by category: Discovery, Project Management, Agent Lifecycle, Messaging, Context and Memory, Vision Documents, Setup and Export
  - Include the discovery tool and its categories

**Effort:** Heavy (3-4 hours)
**Depends on:** 0910a (clean workspace)

### 0910d: Architecture + README Hub + Final Verification (Subagent 4)

Write ARCHITECTURE.md and README_FIRST.md. Verify all documents are consistent.

**Scope:**
- ARCHITECTURE.md: technical overview for developers and contributors
  - Tech stack (Python 3.12, FastAPI, SQLAlchemy 2.0, Vue 3, Vuetify 3, PostgreSQL 18)
  - System diagram (ASCII or text): client CLIs -> MCP -> FastAPI -> Services -> PostgreSQL
  - Backend layer structure: endpoints, services, repositories, models
  - Frontend layer structure: views, components, composables, stores
  - Real-time: WebSocket via PostgresNotifyBroker
  - Auth: JWT httpOnly cookies, CSRF double-submit
  - Multi-tenant: tenant_key isolation on every query
  - Agent lifecycle: staging -> implementation -> closeout
  - Source: SERVER_ARCHITECTURE_TECH_STACK.md (rewrite, do not copy stale content), code structure
- README_FIRST.md: simple navigation hub
  - One-line description of each document with link
  - No content: just links and one-liners
  - Ordered: Overview -> User Guide -> Installation -> MCP Tools -> Architecture -> Edition Isolation -> Changelog
- Final verification:
  - All links in README_FIRST.md resolve
  - No em dashes in any document
  - No stale handover references
  - No references to deprecated features
  - Consistent terminology throughout

**Effort:** Medium (2-3 hours)
**Depends on:** 0910b and 0910c (needs their content to verify consistency)

## Orchestrator Protocol

The orchestrator (this handover) runs one session. It:

1. Creates the chain log at prompts/0910_chain/chain_log.json
2. Spawns 0910a first (archive + scaffold)
3. After 0910a completes, spawns 0910b and 0910c in parallel (they write different files)
4. After both complete, spawns 0910d (hub + architecture + verification)
5. Reviews the final set and commits

**Terminal spawn:** Use gnome-terminal with claude --dangerously-skip-permissions.
**Branch:** feature/0910-documentation-overhaul
**Sleep heuristics:** 0910a: 10 min initial. 0910b/c: 15 min initial. 0910d: 10 min initial.

## Critical Rules for All Subagents

1. No em dashes anywhere. Use colons, semicolons, and periods.
2. No emoji in document body.
3. Read actual code and components for current behavior: do not copy from stale docs.
4. Every MCP tool name must match what is registered in mcp_sdk_server.py.
5. Every UI description must match what the component actually renders.
6. Do not reference handover numbers in user-facing docs: users do not know what handovers are.
7. Do not reference internal architecture decisions or history: write for users and contributors.
8. Keep documents concise: prefer tables and bullet lists over long paragraphs.
9. Active voice. Direct sentences. No filler.
10. Activate venv before any code inspection: source venv/bin/activate and export PYTHONPATH=.

## Success Criteria

- [ ] /docs root contains exactly: README_FIRST.md, PRODUCT_OVERVIEW.md, USER_GUIDE.md, INSTALLATION_GUIDE.md, MCP_TOOLS_REFERENCE.md, ARCHITECTURE.md, EDITION_ISOLATION_GUIDE.md, CHANGELOG.md
- [ ] /docs/archive contains all previously existing docs (nothing deleted, just moved)
- [ ] /docs/Screen_shots preserved as-is
- [ ] Zero em dashes in any shipping document
- [ ] Zero stale handover references in any shipping document
- [ ] All README_FIRST.md links resolve
- [ ] MCP_TOOLS_REFERENCE.md matches actual registered tools (count matches)
- [ ] No document exceeds 1000 lines

## Rollback Plan

All old docs are archived, not deleted. To rollback: move /docs/archive/* back to their original locations.
