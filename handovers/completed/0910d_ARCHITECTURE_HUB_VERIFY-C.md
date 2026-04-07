# Handover 0910d: Write ARCHITECTURE.md and README_FIRST.md, Final Verification

**Edition Scope:** CE
**Date:** 2026-04-06
**From Agent:** Orchestrator (0910 kickoff)
**To Agent:** documentation-manager
**Priority:** High
**Estimated Effort:** 2-3 hours
**Status:** Not Started
**Series:** 0910 Documentation Overhaul (subagent 4 of 4, runs after 0910b and 0910c complete)

---

## Task Summary

Write ARCHITECTURE.md and README_FIRST.md, then run a final verification pass across all six shipping documents. ARCHITECTURE.md is for developers and contributors. README_FIRST.md is a pure navigation hub with no content of its own. The verification pass checks consistency, no em dashes, no stale references, and all links resolve.

---

## Critical Rules (read before touching anything)

1. No em dashes anywhere. Use colons, semicolons, and periods. Not "this -- that". Use "this: that".
2. No emoji in any document body.
3. Read actual code structure, not stale docs. The archived docs in /docs/archive may be stale.
4. Do not reference handover numbers in output documents. Users do not know what handovers are.
5. Active voice. Direct sentences. No filler.
6. README_FIRST.md contains only links and one-liners. No content.
7. ARCHITECTURE.md is for developers, not end users. Technical depth is appropriate.
8. No document exceeds 1000 lines.
9. Activate venv before any code inspection: `source /media/patrik/Work/GiljoAI_MCP/venv/bin/activate && export PYTHONPATH=.`
10. Use absolute paths for all bash commands. The working directory resets between bash calls.

---

## Context

This is the final subagent in the 0910 series. At this point:
- 0910a has archived stale docs and created scaffold files.
- 0910b has written PRODUCT_OVERVIEW.md and USER_GUIDE.md.
- 0910c has written INSTALLATION_GUIDE.md and MCP_TOOLS_REFERENCE.md.

This subagent adds the architecture document and navigation hub, then verifies the whole set.

---

## Dependencies

**Requires:** 0910a, 0910b, and 0910c all complete.

Read the documents from 0910b and 0910c before writing ARCHITECTURE.md, to ensure consistent terminology.

---

## Source Files to Read

| File | What to Extract |
|------|-----------------|
| `/media/patrik/Work/GiljoAI_MCP/api/endpoints/mcp_sdk_server.py` | MCP server structure, how it is mounted |
| `/media/patrik/Work/GiljoAI_MCP/api/app.py` | FastAPI app structure, router registration, middleware |
| `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/` (directory listing) | Service layer structure |
| `/media/patrik/Work/GiljoAI_MCP/api/websocket_manager.py` | WebSocket and PostgresNotifyBroker |
| `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/models.py` | Entity hierarchy (or confirm model file location) |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/` (directory listing) | Frontend structure: views, components, composables, stores |
| `/media/patrik/Work/GiljoAI_MCP/migrations/` (directory listing) | Migration baseline reference |

---

## Implementation Plan

### Phase 1: Read source structure

Establish the current directory structure by reading, not from memory.

```bash
ls /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/api/
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/frontend/src/
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/frontend/src/stores/
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/frontend/src/composables/ 2>/dev/null || echo "no composables dir"
```

```bash
grep -n "app = FastAPI\|router\|include_router\|middleware\|CORSMiddleware\|PostgresNotify" \
  /media/patrik/Work/GiljoAI_MCP/api/app.py | head -40
```

```bash
grep -n "PostgresNotifyBroker\|broadcast\|notify\|channel\|listen" \
  /media/patrik/Work/GiljoAI_MCP/api/websocket_manager.py | head -30
```

```bash
grep -n "class.*Model\|class.*Base\|tenant_key\|Organization\|User\|Product\|Project\|Job\|Task" \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/models.py | head -60
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/services/ 2>/dev/null | head -30
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/repositories/ 2>/dev/null | head -30
```

Read the existing documents written by 0910b and 0910c to align terminology:

```bash
head -60 /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md
head -60 /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md
```

### Phase 2: Write ARCHITECTURE.md

Write to `/media/patrik/Work/GiljoAI_MCP/docs/ARCHITECTURE.md`.

**Tech Stack section:**

Produce a table of the primary technologies. Use versions that are confirmed in the code or install.py:

| Layer | Technology | Version |
|-------|------------|---------|
| Backend language | Python | 3.12+ |
| Backend framework | FastAPI | ... |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | ... |
| Database | PostgreSQL | 18 |
| Frontend framework | Vue | 3 (Composition API) |
| Frontend UI library | Vuetify | 3 |
| Frontend build tool | Vite | ... |
| State management | Pinia | ... |
| Protocol | MCP (Model Context Protocol) via HTTP/SSE | ... |

Read `requirements.txt` for Python version pinning:

```bash
grep -i "fastapi\|sqlalchemy\|alembic\|uvicorn" /media/patrik/Work/GiljoAI_MCP/requirements.txt | head -10
```

Read `frontend/package.json` for frontend versions:

```bash
grep "\"vue\"\|\"vuetify\"\|\"vite\"\|\"pinia\"" /media/patrik/Work/GiljoAI_MCP/frontend/package.json | head -10
```

**System Overview section:**

Include a plain-text diagram showing the main data flows. Something like:

```
AI Coding Tool (Claude Code / Codex CLI / Gemini CLI)
        |
        | MCP over HTTP/SSE
        v
   FastAPI Server
   /api/endpoints/mcp_sdk_server.py
        |
        | Python function calls
        v
   Service Layer
   src/giljo_mcp/services/
        |
        | SQLAlchemy ORM
        v
   PostgreSQL 18
        |
        | NOTIFY/LISTEN
        v
   WebSocket Broker
   api/websocket_manager.py
        |
        | WebSocket
        v
   Vue 3 Frontend (browser)
```

Describe each layer in one or two sentences.

**Backend Layer section:**

Describe the four layers:

1. Endpoints (`api/endpoints/`): FastAPI routers handling HTTP and MCP requests. Auth is enforced via `Depends(get_current_active_user)` on all non-public endpoints.
2. Services (`src/giljo_mcp/services/`): Business logic. No direct DB queries. All errors raise exceptions (not returned as dicts).
3. Repositories (`src/giljo_mcp/repositories/`): SQLAlchemy queries. Every query filters by `tenant_key`. No raw SQL.
4. Models (`src/giljo_mcp/models.py`): SQLAlchemy ORM models. Entity hierarchy: Organization > User > Product > Project > Job | Task.

**Frontend Layer section:**

Describe the four layers:

1. Views (`frontend/src/views/`): Top-level page components bound to Vue Router routes.
2. Components (`frontend/src/components/`): Reusable UI components organized by domain (products, projects, setup, navigation, etc.).
3. Composables (if the directory exists): Shared reactive logic extracted from components.
4. Stores (`frontend/src/stores/`): Pinia stores for global state. Each domain has its own store.

**Real-Time Communication section:**

The backend uses PostgreSQL `NOTIFY/LISTEN` to push events to a WebSocket broker (`api/websocket_manager.py`). The broker maintains one WebSocket connection per authenticated browser session. The frontend shows a connection status icon that reflects the WebSocket state. When an agent updates a job status or sends a message, the change is pushed to the dashboard within seconds without polling.

**Authentication section:**

Authentication uses JWT tokens stored in httpOnly cookies. CSRF protection uses the double-submit cookie pattern. Sessions are scoped to the tenant. Admin-only endpoints additionally check the user's `is_admin` flag.

**Multi-Tenant Isolation section:**

Every database query filters by `tenant_key`. The `TenantManager` service enforces this at the service layer. No query may return rows from a different tenant. This design supports both single-user CE deployments and multi-org SaaS deployments from the same codebase.

**Agent Lifecycle section:**

Describe the three project phases and how agents move through them:

1. Staging: the project is defined but not active. No agents are running.
2. Implementation: the project is activated. The orchestrator spawns agent jobs. Each job has a status from the set: `waiting`, `working`, `blocked`, `idle`, `sleeping`, `complete`, `silent`, `decommissioned`.
3. Closeout: the orchestrator writes 360 Memory and closes the project. The memory is available to future projects.

**Edition Isolation section:**

A short paragraph pointing to EDITION_ISOLATION_GUIDE.md. CE code lives in standard directories. SaaS-only code lives in `saas/`, `saas_endpoints/`, `saas_middleware/`, and `frontend/src/saas/`. CE never imports from SaaS directories.

Document length target: 300-500 lines.

### Phase 3: Write README_FIRST.md

Write to `/media/patrik/Work/GiljoAI_MCP/docs/README_FIRST.md`.

This is a navigation hub. It contains only links and one-line descriptions. No content of its own.

Structure:

```markdown
# GiljoAI MCP Documentation

## Getting Started

- [Product Overview](PRODUCT_OVERVIEW.md): What GiljoAI MCP is, how it works, and who it is for.
- [Installation Guide](INSTALLATION_GUIDE.md): Install from source, run the setup wizard, and connect your AI tools.

## Using GiljoAI MCP

- [User Guide](USER_GUIDE.md): Every page explained: Home, Dashboard, Products, Projects, Jobs, Tasks, and Settings.

## Reference

- [MCP Tools Reference](MCP_TOOLS_REFERENCE.md): All 29 MCP tools with parameters, descriptions, and examples.
- [Architecture](ARCHITECTURE.md): Tech stack, system diagram, and developer-facing technical overview.

## Licensing and Editions

- [Edition Isolation Guide](EDITION_ISOLATION_GUIDE.md): Community Edition vs SaaS Edition: directory rules and code placement.
- [Changelog](CHANGELOG.md): Release history.
```

Adjust tool count if 0910c found a different number. Keep each line to one document with a one-sentence description. No paragraphs.

### Phase 4: Final verification pass

This is the quality gate for the entire 0910 series. Check all six shipping documents plus README_FIRST.md.

**Step 4.1: Em dash check**

```bash
grep -rn " -- \| --- " /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
  /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/ARCHITECTURE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/README_FIRST.md
```

Must return no output. If any match appears, fix it before committing.

Also check for Unicode em dash character:

```bash
grep -rPn "\xe2\x80\x94" \
  /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
  /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/ARCHITECTURE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/README_FIRST.md
```

**Step 4.2: Stale reference check**

```bash
grep -in "handover\|0910\|0855\|0846\|0908\|deprecated\|legacy\|old version\|stale" \
  /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
  /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/ARCHITECTURE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/README_FIRST.md
```

No handover numbers or internal development terms should appear in any of these.

**Step 4.3: Line count check**

```bash
wc -l \
  /media/patrik/Work/GiljoAI_MCP/docs/README_FIRST.md \
  /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
  /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/ARCHITECTURE.md
```

No document may exceed 1000 lines.

**Step 4.4: Link resolution check**

All links in README_FIRST.md are relative. Verify each target file exists:

```bash
for f in PRODUCT_OVERVIEW.md USER_GUIDE.md INSTALLATION_GUIDE.md MCP_TOOLS_REFERENCE.md ARCHITECTURE.md EDITION_ISOLATION_GUIDE.md CHANGELOG.md; do
  if [ -f "/media/patrik/Work/GiljoAI_MCP/docs/$f" ]; then
    echo "OK: $f"
  else
    echo "MISSING: $f"
  fi
done
```

All must print "OK".

**Step 4.5: Docs root contents check**

```bash
ls /media/patrik/Work/GiljoAI_MCP/docs/
```

Must contain exactly:
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

Nothing else. If any unexpected file is present, move it to archive.

**Step 4.6: Terminology consistency check**

Verify consistent terminology across documents:

```bash
grep -h "GiljoAI\|360 Memory\|tenant_key\|MCP server\|bootstrap prompt\|giljo_setup" \
  /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
  /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/ARCHITECTURE.md | sort | uniq -c | sort -rn | head -20
```

Look for variant spellings or capitalization (e.g., "giljoai" vs "GiljoAI", "360memory" vs "360 Memory"). Fix any inconsistencies.

### Phase 5: Commit

```bash
cd /media/patrik/Work/GiljoAI_MCP
git add docs/ARCHITECTURE.md docs/README_FIRST.md
git commit -m "docs(0910d): write ARCHITECTURE and README_FIRST hub, final verification complete"
```

If the verification pass required fixing files from 0910b or 0910c, include those in the same commit:

```bash
git add docs/PRODUCT_OVERVIEW.md docs/USER_GUIDE.md docs/INSTALLATION_GUIDE.md docs/MCP_TOOLS_REFERENCE.md
```

---

## Testing Requirements

**Verification gate (must all pass before committing):**

1. Zero em dashes in all six documents (both ASCII `--` and Unicode em dash).
2. Zero handover number references in any document.
3. All README_FIRST.md link targets exist on disk.
4. No document exceeds 1000 lines.
5. /docs root contains exactly the expected 8 files and 2 directories.
6. Terminology is consistent across documents.
7. MCP tool count in MCP_TOOLS_REFERENCE.md matches `grep -c "@mcp.tool"` count in mcp_sdk_server.py.

---

## Success Criteria

- [ ] /docs/ARCHITECTURE.md written with all sections (tech stack, system diagram, backend layers, frontend layers, real-time, auth, tenant isolation, agent lifecycle, edition isolation)
- [ ] /docs/README_FIRST.md written as a pure navigation hub with links and one-liners only
- [ ] All six shipping documents pass the verification checks
- [ ] All README_FIRST.md links resolve
- [ ] Zero em dashes in any shipping document
- [ ] Zero stale handover references in any shipping document
- [ ] No document exceeds 1000 lines
- [ ] Final commit created with the specified message

---

## Rollback Plan

All previous subagent commits are in git. To roll back ARCHITECTURE.md and README_FIRST.md: `git revert HEAD`. The 0910b and 0910c documents remain.

To roll back the entire 0910 series: `git revert` each 0910 commit in reverse order, or reset to the commit before 0910a.

---

## Chain Log

Update `/media/patrik/Work/GiljoAI_MCP/prompts/0910_chain/chain_log.json` when done:

```json
{
  "0910d": {
    "status": "complete",
    "commit": "<commit hash>",
    "notes": "Wrote ARCHITECTURE (~N lines) and README_FIRST (~N lines). Verification: all checks passed. Any fixes applied to: <list files or 'none'>."
  }
}
```
