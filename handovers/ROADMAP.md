# Post-CE Roadmap

**Purpose:** Forward-looking planning document for post-launch work, including the CE/SaaS branch split and feature development.
**Replaces:** PRIORITY_ORDER.md served as the launch checklist (now complete). This document is the active planning reference.
**Last Updated:** 2026-03-30

---

## Proposed Execution Order

Prioritized sequence for remaining handovers and quick wins. Tier 1 items are standalone with no dependencies and can each be completed in a single session.

### Tier 1: Quick Wins (1-3 hours each)

| Order | ID | Title | Effort | Rationale |
|-------|-----|-------|--------|-----------|
| 1 | 0841 | Slash Command Optimization (`/gil_add`) | 1-2 hrs | Standalone refactor, 343→40 lines, no dependencies |
| 2 | 0277 | Design Token Standardization (Radius & Shadow) | 1-2 hrs | ~15 CSS-only file edits, no backend risk |
| 3 | 0847 | Tool-Aware Orchestrator Protocol | 2-3 hrs | High priority, self-contained protocol/config changes |
| 4 | — | Housekeeping (move ref docs, archive PRIORITY_ORDER.md) | 30 min | Zero risk, declutters handovers folder |

### Tier 2: 0842 Series Closure (merge-blocking)

Complete in this order — 0842L must be last as it audits the full branch.

| Order | ID | Title | Effort | Notes |
|-------|-----|-------|--------|-------|
| 5 | 0842h | Frontend Tests (Tuning/Vision) | 2-3 hrs | 11 Vitest tests, no feature code |
| 6 | 0842g | Per-Document AI Summary Badges | 2-3 hrs | Small UI + API extension |
| 7 | 0842L | Post-Implementation Audit & Cleanup | 3-4 hrs | Final gate before 0842 branch merges to master |

### Tier 3: Pre-Launch (required before public repo)

| Order | ID | Title | Effort | Notes |
|-------|-----|-------|--------|-------|
| 8 | CE Credential Scrub | Remove hardcoded secrets from code + git history | 4-6 hrs | Blocking for public repo |
| 9 | Phase 0 | Branch cleanup, rename master→main, SaaS audit | 2-3 hrs | Prerequisite for CE/SaaS split |

### Tier 4: Medium Features (post-launch)

| Order | ID | Title | Effort | Notes |
|-------|-----|-------|--------|-------|
| 10 | 0844a→b→c | Tenant Data Export/Import | 4-8 hrs | Sequential chain with manual gates between phases |
| 11 | 1014 | Security Event Auditing | 8 hrs | Deferred to `saas` branch, enterprise/compliance |

### Quick Wins from Post-CE Wishlist

Small items that can be slotted in between larger work.

| Item | Effort | Why Easy |
|------|--------|----------|
| 0901 Dashboard Scope Simplification | Small | Remove product selector from CE dashboard, show tenant-level stats only |

---

## Current State

- All launch-blocking handovers: **COMPLETE** (330+ archived)
- All actionable tech debt: **RESOLVED** (techdebt_march_2026-C.md archived)
- Test suite: **0 failures** across 91 frontend files, 1390+ backend tests
- Code quality: **8.35/10** (Perfect Score Sprint 0765a-s)
- Active feature branch: **feature/0842-vision-doc-analysis** (45+ commits, merge-ready after remaining items)
- Active handovers: **7** (2 on 0842, 7 on 0855, plus pre-launch items below)
- Branch: **master** only (no `main` or `saas` branch yet)
- SaaS scaffold: frontend `.gitkeep` placeholders only, no backend dirs

---

## Phase 0: Branch Split Preparation (Pre-Requisites)

Do these BEFORE creating the `main`/`saas` branches. Order matters.

### 0.1 Stale Branch Cleanup

30 local branches exist from old feature/backup work (0390, 0417, 0480, 0700-series, 0745-series, etc.). Many have corresponding `remotes/origin/claude/*` auto-branches.

**Action:**
- List all branches with `git branch -a`
- Confirm each is fully merged into master or obsolete
- Delete merged/obsolete local branches: `git branch -d <name>`
- Prune remote tracking refs: `git remote prune origin`
- Delete stale remote branches if desired: `git push origin --delete <name>`

**Why first:** Avoids leaking internal branch names to the public repo and keeps the branch list clean before the split.

### 0.2 Version Tag Decision

Current tags: v0.1.1 through v0.1.9. The branch split is a milestone.

**Decision needed:**
- Tag the split point as **v0.2.0** (pre-release milestone) or **v1.0.0** (GA)?
- Recommendation: v1.0.0 signals CE is production-ready (all launch work is done)

### 0.3 Rename `master` to `main`

The Edition Isolation Guide prescribes CE on `main`. GitHub supports seamless rename.

**Action:**
```bash
git branch -m master main
git push origin -u main
# Update GitHub default branch in repo settings
# Then delete old remote: git push origin --delete master
```

**Why:** Aligns with the documented architecture before SaaS branch exists.

### 0.4 Audit for SaaS Leaks in CE

Before going public, verify no SaaS-specific code leaked into CE directories.

**Checklist:**
- [ ] No Stripe/Twilio/OAuth/LDAP imports in `src/giljo_mcp/` or `api/`
- [ ] No multi-org-only features in CE frontend components
- [ ] `frontend/src/saas/` contains only `.gitkeep` files
- [ ] `saas/`, `saas_endpoints/`, `saas_middleware/` directories do not exist
- [ ] Pre-commit edition isolation hook passes
- [ ] Deletion Test passes (delete all saas dirs, app starts, tests pass)

### 0.5 Sensitive Content Sweep

Before making the repo public, ensure no secrets or private info are committed.

**Checklist:**
- [ ] No API keys, passwords, or tokens in tracked files
- [ ] No internal hostnames or IP addresses
- [ ] `.gitignore` covers `.env`, `config.yaml` (with credentials), `*.pem`, `*.key`
- [ ] Git history doesn't contain accidentally committed secrets (use `git log -p -S "password"` or similar)
- [ ] README and docs reference only public URLs

---

## Phase 1: Branch Split Execution

Once Phase 0 is complete, execute the split.

### 1.1 Create `saas` Branch

```bash
git checkout main
git checkout -b saas
git push origin -u saas
```

### 1.2 Create Backend SaaS Scaffold (on `saas` branch)

```
saas/
  __init__.py
  services/
    __init__.py
saas_endpoints/
  __init__.py
saas_middleware/
  __init__.py
migrations/
  saas_versions/
    .gitkeep
tests/
  saas/
    __init__.py
```

### 1.3 Wire Conditional Loading (on `saas` branch)

In `app.py` / startup, add the conditional registration pattern from `docs/EDITION_ISOLATION_GUIDE.md`:
- Check if `saas/` directory exists
- If yes, import and register SaaS routers, middleware, event handlers
- If no, skip silently (CE mode)

### 1.4 Set Up Remotes

**Option A: Two GitHub repos**
- Public: `origin` -> `github.com/patrik-giljoai/GiljoAI-MCP` (push `main` only)
- Private: `private` -> private repo (push `saas` only)

**Option B: Single repo with branch protection**
- `main` branch: public, protected
- `saas` branch: private visibility (requires GitHub Enterprise or separate repo)

**Decision needed:** Which remote strategy?

### 1.5 CI/CD Gates

- **CE gate (on `main`):** Deletion Test -- remove all `saas/` dirs, verify startup + tests pass
- **SaaS gate (on `saas`):** Full test suite including SaaS-specific tests
- **Merge direction enforcement:** `main --> saas` merges only, weekly minimum

---

## Phase 2: Post-Split Workflow

Once branches exist, this is the ongoing development model.

### Feature Development

| Feature Type | Develop On | Merge Direction |
|-------------|-----------|-----------------|
| Bug fixes | `main` | `main --> saas` |
| Security patches | `main` | `main --> saas` |
| Core orchestration features | `main` | `main --> saas` |
| UI/UX improvements (core) | `main` | `main --> saas` |
| Stripe/billing integration | `saas` | Never to `main` |
| OAuth/SSO/LDAP | `saas` | Never to `main` |
| Multi-org management | `saas` | Never to `main` |
| Usage analytics/metering | `saas` | Never to `main` |

### Merge Cadence

- Merge `main --> saas` at least **weekly**
- After every significant feature or security fix on `main`
- Resolve conflicts on `saas` side (SaaS adapts to CE, not vice versa)

---

## Active Implementation Work

### 0842 Series — Vision Document Analysis (remaining)

| ID | Title | Effort | Priority | Handover |
|----|-------|--------|----------|----------|
| 0842g | Per-Document AI Summary Badges | 2-3 hrs | Low | `handovers/0842g_AI_SUMMARY_BADGES_PER_DOCUMENT.md` |
| 0842h | Vitest Frontend Tests for Tuning/Vision | 2-3 hrs | Medium | `handovers/0842h_FRONTEND_TESTS_TUNING_VISION.md` |

### 0855 Series — Setup Wizard Learning Overlay (7 handovers, not started)

| ID | Title | Handover |
|----|-------|----------|
| 0855a | Backend Schema | `handovers/0855a_SETUP_WIZARD_BACKEND_SCHEMA.md` |
| 0855b | WebSocket Events | `handovers/0855b_SETUP_WIZARD_WEBSOCKET_EVENTS.md` |
| 0855c | Overlay Step 1 | `handovers/0855c_SETUP_WIZARD_OVERLAY_STEP1.md` |
| 0855d | Step 2 Connect | `handovers/0855d_SETUP_WIZARD_STEP2_CONNECT.md` |
| 0855e | Step 3 Commands | `handovers/0855e_SETUP_WIZARD_STEP3_COMMANDS.md` |
| 0855f | Step 4 Wiring | `handovers/0855f_SETUP_WIZARD_STEP4_WIRING.md` |
| 0855g | Learning Overlay Cleanup | `handovers/0855g_SETUP_WIZARD_LEARNING_OVERLAY_CLEANUP.md` |

### 0841 — Slash Command Optimization (standalone)

| ID | Title | Effort | Priority | Handover |
|----|-------|--------|----------|----------|
| 0841 | `/gil_add` Slash Command Token Bloat Rewrite | 1-2 hrs | Low | `handovers/0841_slash_command_optimization.md` |

### Pre-Launch Items (unnumbered)

| Item | Priority | Description | Source Doc |
|------|----------|-------------|------------|
| Setup Wizard Redesign | **High** (CE launch blocker) | Remove product explainer from setup flow, replace with action-oriented checklist | `handovers/SETUP_WIZARD_REDESIGN.md` |
| Credential Scrub | **High** (pre-release) | Remove all hardcoded credentials, passwords, API keys before publishing CE on `main` | `handovers/CE_LAUNCH_CREDENTIAL_SCRUB.md` |
| Demo Server Prep | Medium | Security hardening for public demo/trial server (Ubuntu, 5-day sessions) | `handovers/Demo_server_prepp.md` |
| ~~Production Frontend Serving (0902)~~ | ~~High~~ | **COMPLETE.** Single-port serving: FastAPI StaticFiles mount, SPA fallback, middleware exemptions, frontend port fixes, startup --dev flag. | `handovers/0902_SINGLE_PORT_FRONTEND_SERVING.md` |

### Deferred Handovers

| ID | Title | Effort | Priority | Notes |
|----|-------|--------|----------|-------|
| 1014 | Security Event Auditing | 8 hrs | Medium | Enterprise compliance feature. Full spec ready (`handovers/1014_security_auditing.md`, 759 lines). Develop on `saas` when compliance requirements materialize. |
| TODO_vision | Vision Summarizer LLM Upgrade | 16-24 hrs | Low | Phase 1 partial (DB columns added). Phases 2-3 untouched. Develop on `main` (improves core). |
| 0409 | ~~Unified Client Quick Setup~~ | ~~2-3 hrs~~ | ~~Low~~ | **SUPERSEDED by 0903.** Browser-based prompt bundling replaced by CLI-first install flow. |
| 0903 | Streamlined CLI Install | 12-16 hrs | Medium | `pip install giljo-mcp` → `giljo-mcp init` → paste MCP command → done. CLI entry point, MCP bootstrap auto-provisioning. Depends on 0902. Develop on `main`. |

---

## Post-CE Feature Wishlist

From `completed/techdebt_march_2026-C.md`. None are blocking. Prioritize based on user demand.

### CE Features (develop on `main`)

| Item | Effort Est. | Notes |
|------|-------------|-------|
| ~~0902 Single-Port Frontend Serving~~ | ~~Medium~~ | **COMPLETE.** FastAPI serves built frontend on :7272. |
| 0901 Dashboard Scope Simplification | Small | Remove product selector from CE dashboard — show all-tenant stats only. Handover written. |
| 0904 Orchestrator Auto Check-in | Medium | Multi-terminal toggle + interval slider (30/60/90s). Protocol injection (CH6) for orchestrator self-polling. Handover written: `handovers/0904_ORCHESTRATOR_AUTO_CHECKIN.md` |
| ~~360 Memory Frontend UI~~ | ~~Medium~~ | **Moved to SaaS.** See "360 Memory Product Knowledge Hub" in SaaS Features below |
| MCP HTTP Tool Catalog Refactoring | Large | Registry pattern to replace 1096-line inline JSON. Planned for v4.0 |
| Developer Workflow Guide | Medium | End-to-end docs + quick start tutorial |
| Developer Panel | Aspirational | Localhost read-only panel showing architecture, APIs, dependencies |

### SaaS Features (develop on `saas`)

| Item | Effort Est. | Notes |
|------|-------------|-------|
| 360 Memory Product Knowledge Hub | Medium-Large | AI-assisted aggregation of 360 memory across projects. Haiku synthesis. See detailed definition below |
| Per-Agent Tool Selection UI | Medium | Dropdown for Claude/Codex/Gemini per agent. Only relevant when multi-tool ships |
| Codex MCP Integration | Large | OpenAI Codex as agent tool. UI stubs exist (CodexConfigModal.vue). No backend |
| Gemini MCP Integration | Large | Google Gemini as agent tool. Cross-language (Node.js) complexity |
| Local LLM Stack Recommendation | Large | LM Studio integration for privacy-preserving suggestions. 16-20h |

---

## Feature Definition: 360 Memory Product Knowledge Hub (SaaS)

**Edition Scope:** SaaS only
**Effort:** Medium-Large (16-24 hrs)
**Depends On:** Phase 1 branch split complete, 360 memory backend (0135-0139, already done)
**Branch:** `saas/`

### Problem

360 memory entries are captured per project and viewable in each project's closeout review panel. However, there is no aggregated view across projects. A user with 15 completed projects must click through each one to build a picture of how their product evolved. There is also no export capability -- knowledge is locked inside the platform.

### Architecture Decision

The GiljoAI MCP server is a **passive presentation layer** -- it stores data and exposes MCP tools, but runs no AI logic. CE context tuning works by mechanically assembling prompts that the user's subscribed agent processes externally.

For the Knowledge Hub, **server-side AI synthesis is required** (deduplication, contradiction detection, coherent summarization across projects). This makes it a SaaS feature: the service calls **Claude Haiku** to perform the synthesis pass over mechanically aggregated data. Haiku keeps per-request cost minimal while providing the intelligence the passive architecture lacks.

### What Stays Mechanical (No AI)

- Database queries: fetch all `product_memory_entries` for a product
- Timeline rendering: sort by sequence/date, paginate
- Filtering: by date range, project, section type
- Export formatting: structure data into CSV/JSON templates
- UI: panels, cards, timeline component rendering

### What Haiku Handles (SaaS AI Layer)

- **Deduplication:** Recognize when multiple projects noted the same learning (semantic, not just string match)
- **Synthesis:** Merge N projects of raw entries into a coherent product knowledge summary
- **Contradiction detection:** Flag where recent project outcomes contradict current product context
- **Structured export generation:** Produce formatted markdown summaries, executive briefs
- **Evolution narrative:** Describe how architecture/stack/patterns changed over time

### UI Components

| Component | Purpose |
|-----------|---------|
| **ProductMemoryPanel** | Aggregated view of all 360 memory for a product, grouped by section (tech_stack, architecture, decisions, etc.). Shows synthesized summary at top, raw entries expandable below |
| **LearningTimeline** | Chronological timeline of decisions/outcomes spanning full project history. Visual evolution of how the product changed. Filterable by section and date range |
| **GitHubSettingsCard** | View/edit git integration config from `product_memory.git_integration`. Simplest component -- mechanical only, no Haiku needed |
| **Export Controls** | Export aggregated knowledge as Markdown (agent-friendly), CSV (spreadsheet), or JSON (machine-complete). Haiku generates a synthesis preamble for Markdown exports |

### Data Flow

```
User opens Product Knowledge Hub
    |
    v
Server fetches all product_memory_entries (mechanical)
    |
    v
Server sends entries to Haiku for synthesis (SaaS AI layer)
    |
    v
Haiku returns: deduplicated learnings, contradictions, summary
    |
    v
UI renders: ProductMemoryPanel (synthesized + raw), LearningTimeline
    |
    v
User can export (Markdown with Haiku summary, CSV/JSON mechanical)
```

### Export Use Cases

1. **Context injection:** Paste product knowledge export into Claude Code / Cursor as a context document
2. **Stakeholder sharing:** Hand off a formatted brief without giving dashboard access
3. **Onboarding:** New team member gets full product knowledge history as a document
4. **Backup/portability:** Product knowledge is not locked in the platform

### Relationship to Context Tuning (CE)

Context tuning remains a CE feature. It mechanically assembles a comparison prompt from the last N projects and the user's agent processes it externally. The Knowledge Hub complements tuning by giving users:

- A browsable view of the raw evidence that tuning draws from
- The ability to curate which learnings matter before triggering a tune
- An export path that lets users feed richer context to their agent directly

The Knowledge Hub does NOT replace tuning -- it enriches the data layer that tuning consumes.

### API Endpoints (SaaS only, `saas_endpoints/`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/products/{id}/knowledge-hub` | Aggregated entries + Haiku synthesis |
| GET | `/products/{id}/knowledge-hub/timeline` | Paginated timeline entries |
| POST | `/products/{id}/knowledge-hub/export` | Generate export (format: md/csv/json) |
| GET | `/products/{id}/knowledge-hub/export/{export_id}` | Download generated export |

---

## Housekeeping (Minor, Do Anytime)

- [ ] Move reference docs to `Reference_docs/`: `LOG_ANALYSIS_GUIDE.md`, `Agent instructions and where they live.md`, `Code_quality_prompt.md`, `codex_menu_option.md`, `GILJOAI_MCP_PPT_REFERENCE_BRIEF.md`
- [ ] Archive `PRIORITY_ORDER.md` (replaced by this roadmap, all items complete)
- [ ] Update `handovers/README.md` priority table (stale)
- [ ] Clean up 30 stale local git branches (part of Phase 0.1)

---

## References

- [EDITION_ISOLATION_GUIDE.md](../docs/EDITION_ISOLATION_GUIDE.md) -- authoritative CE/SaaS directory rules
- [PRIORITY_ORDER.md](./PRIORITY_ORDER.md) -- completed CE launch checklist
- [techdebt_march_2026-C.md](./completed/techdebt_march_2026-C.md) -- resolved tech debt + post-CE items
- [handover_catalogue.md](./handover_catalogue.md) -- full handover history
