# Post-CE Roadmap

**Purpose:** Forward-looking planning document for post-launch work, including the CE/SaaS branch split and feature development.
**Replaces:** PRIORITY_ORDER.md served as the launch checklist (now complete). This document is the active planning reference.
**Last Updated:** 2026-04-05

---

## Proposed Execution Order

Prioritized sequence for remaining handovers and quick wins. Tier 1 items are standalone with no dependencies and can each be completed in a single session.

### Tier 1: Quick Wins (1-3 hours each)

| Order | ID | Title | Effort | Status |
|-------|-----|-------|--------|--------|
| 1 | ~~0841~~ | ~~Slash Command Optimization (`/gil_add`)~~ | ~~1-2 hrs~~ | **COMPLETE** |
| 2 | ~~0277~~ | ~~Design Token Standardization (Radius & Shadow)~~ | ~~1-2 hrs~~ | **COMPLETE** (absorbed into 0870a) |
| 3 | ~~0847~~ | ~~Tool-Aware Orchestrator Protocol~~ | ~~2-3 hrs~~ | **COMPLETE** |
| 4 | — | ~~Housekeeping (move ref docs, archive PRIORITY_ORDER.md)~~ | ~~30 min~~ | **COMPLETE** (2026-04-03) |

### Tier 2: 0842 Series Closure — **COMPLETE**

All 0842 handovers merged to master. Branch deleted.

| Order | ID | Title | Status |
|-------|-----|-------|--------|
| 5 | ~~0842h~~ | ~~Frontend Tests (Tuning/Vision)~~ | **COMPLETE** |
| 6 | ~~0842g~~ | ~~Per-Document AI Summary Badges~~ | **COMPLETE** |
| 7 | ~~0842L~~ | ~~Post-Implementation Audit & Cleanup~~ | **COMPLETE** |

### Tier 3: Pre-Launch (required before public repo)

| Order | ID | Title | Effort | Notes |
|-------|-----|-------|--------|-------|
| 8 | CE Credential Scrub | Remove hardcoded secrets from code + git history | 4-6 hrs | Blocking for public repo |
| 9 | Phase 0 | Branch cleanup, rename master→main, SaaS audit | 2-3 hrs | Prerequisite for CE/SaaS split |

### Tier 4: Medium Features (post-launch)

| Order | ID | Title | Effort | Notes |
|-------|-----|-------|--------|-------|
| 10 | ~~0844a→b→c~~ | ~~Tenant Data Export/Import~~ | ~~4-8 hrs~~ | **DEFERRED** post-launch |
| 11 | ~~1014~~ | ~~Security Event Auditing~~ | ~~8 hrs~~ | **DEFERRED** post-launch, `saas` branch |

### Quick Wins from Post-CE Wishlist

~~All quick wins complete.~~

---

## Current State

- All launch-blocking handovers: **COMPLETE** (530+ archived)
- All actionable tech debt: **RESOLVED** (techdebt_march_2026-C.md archived)
- Test suite: **0 failures** across 91 frontend files, 1390+ backend tests
- Code quality: **8.35/10** (Perfect Score Sprint 0765a-s)
- Feature branches: **all merged to master** (0842, 0855, 0873, 0907, 0908 series all complete)
- Active numbered handovers: **0** (0844, 0903 deferred post-launch; 1014 deferred)
- Pre-launch items: **2** (Credential Scrub, repo preparation)
- **Repo strategy:** Three separate repos (CE public, SaaS private, Demo private). No branch split.
- This repo (`GiljoAI_MCP`) becomes a frozen reference after CE repo is created
- All future development happens directly in the CE repo

---

## Phase 0: Pre-Release Preparation

> **Note (2026-04-05):** Branch split strategy replaced by three-repo strategy. Sections 0.3 (rename master) dropped. Sections 0.1, 0.2, 0.4, 0.5 still apply — they prepare this codebase for the initial CE repo push.

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

### ~~0.3 Rename `master` to `main`~~ — DROPPED

> Unnecessary. CE repo will use `master`. No branch split needed.

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

## ~~Phase 1: Branch Split Execution~~ — SUPERSEDED

> Replaced by three-repo strategy (see Phase 1 below).

## ~~Phase 2: Post-Split Workflow~~ — SUPERSEDED

> Replaced by three-repo strategy (see Phase 2 below).

---

## Phase 1: CE Repo Release

Once Phase 0 checklists pass, create the public CE repo and prepare it for launch.

### 1.1 Repository Strategy (Three Repos)

| Repo | Visibility | Purpose |
|------|-----------|---------|
| `GiljoAI_MCP` (CE) | **Public** | Community Edition. All core development happens here. Community contributions land here. |
| `GiljoAI_MCP_SaaS` | **Private** | SaaS edition. Merges from CE, adds billing/multi-org/SSO. Created later. |
| `GiljoAI_MCP_Demo` | **Private** | Demo server. Merges from CE, adds auto-provisioning/7-day teardown/email registration. Embryo for SaaS. |

**Merge flow:**
```
Community PRs --> GiljoAI_MCP (CE)
                      |
          +-----------+-----------+
          |                       |
  GiljoAI_MCP_SaaS     GiljoAI_MCP_Demo
  (merge from CE)       (merge from CE)
```

When SaaS matures, Demo becomes a deployment mode of SaaS and the Demo repo is retired.

### 1.2 Create CE Repo

1. Create `GiljoAI_MCP` on GitHub (public)
2. Push clean code from this repo, **excluding**:
   - `handovers/` (internal planning docs)
   - `product setup.docx`, `DEMO_TRIAL_TECHNICAL_ANALYSIS.md`
   - Any internal notes, session logs, chain logs
   - SaaS scaffold `.gitkeep` files (not needed in CE)
3. Ensure `.gitignore` covers local-only files:
   - `config.yaml` (DB credentials, secrets)
   - `.env`
   - `*.pem`, `*.key` (TLS certs)
   - `data/` (local database dumps)
   - `handovers/` (if kept locally for reference)

### 1.3 README Rewrite (Storefront Quality)

The README is the landing page. Design it like a product page:

- **Hero section** -- logo/banner in brand colors, one-line tagline, badge row (version, license, build status)
- **What it does** -- 2-3 sentences, not a wall of text
- **Screenshot or GIF** -- dashboard screenshot, agent workflow in action
- **Quick start** -- copy-paste install commands, running in under 2 minutes
- **Feature highlights** -- short bullet list with icons or cards
- **Architecture overview** -- optional diagram showing MCP + agents + orchestrator
- **Contributing / License** -- standard sections

### 1.4 GitHub Repo Setup

- **Description:** one-line summary for the repo header
- **Topics/tags:** `ai`, `mcp`, `orchestration`, `claude`, `agents`, `developer-tools`
- **Social preview image:** branded card (1280x640) for link sharing
- **Issue templates:** `.github/ISSUE_TEMPLATE/` — bug report + feature request
- **PR template:** `.github/PULL_REQUEST_TEMPLATE.md`
- **Funding:** `.github/FUNDING.yml` (if accepting sponsors)
- **Branch protection:** require PR reviews on `master`

### 1.5 Version Tag

Tag the first public commit as **v1.0.0** — signals CE is production-ready.

```bash
git tag -a v1.0.0 -m "GiljoAI MCP Community Edition v1.0.0"
git push origin v1.0.0
```

### 1.6 CHANGELOG

Create `CHANGELOG.md` with a v1.0.0 entry summarizing the initial release capabilities. Keep it updated with each subsequent release.

---

## Phase 2: Post-Release Workflow

### Daily Development

Work directly in the CE repo. Every commit shows up in the public history — keeps the repo looking active and maintained. Internal planning docs (handovers, notes) stay local and gitignored.

### Feature Development

| Feature Type | Develop In | Merge Direction |
|-------------|-----------|-----------------|
| Bug fixes | CE | CE --> SaaS, CE --> Demo |
| Security patches | CE | CE --> SaaS, CE --> Demo |
| Core orchestration features | CE | CE --> SaaS, CE --> Demo |
| UI/UX improvements (core) | CE | CE --> SaaS, CE --> Demo |
| Stripe/billing integration | SaaS | Never to CE |
| OAuth/SSO/LDAP | SaaS | Never to CE |
| Multi-org management | SaaS | Never to CE |
| Auto-provisioning/teardown | Demo | Never to CE |
| Email registration/password reset | Demo | Never to CE |

### Pulling CE Updates into SaaS/Demo

```bash
# In SaaS or Demo repo:
git remote add ce https://github.com/patrik-giljoai/GiljoAI_MCP.git
git fetch ce
git merge ce/master
# Resolve any conflicts, commit
```

Merge from CE at least weekly, or after every significant feature/security fix.

---

## Active Implementation Work

### Completed Series

- **0842 Series** — Vision Document Analysis: all handovers COMPLETE, merged to master
- **0855 Series** — Setup Wizard Learning Overlay (0855a-g): all COMPLETE, merged to master
- **0841** — Slash Command Optimization: COMPLETE
- **0860a-d** — Code Provenance & License Audit: CE PASS, SaaS PASS
- **0900-0902** — WebSocket simplification, dashboard scope, single-port serving: COMPLETE
- **0904** — Orchestrator Auto Check-in: COMPLETE
- **0905** — Dependency Cleanup & Lazy Imports: COMPLETE
- **0906** — install.py --dev Flag: COMPLETE
- **0907** — MCP Bootstrap Setup Tool (`giljo_setup`): COMPLETE
- **0908** — How to Use Modal Rewrite (6 chapters): COMPLETE
- **0834b** — Remote Client Certificate Trust Modal: COMPLETE

### Pre-Launch Items (unnumbered)

| Item | Priority | Description | Source Doc |
|------|----------|-------------|------------|
| ~~Setup Wizard Redesign~~ | ~~High~~ | **COMPLETE** (0855 series + 0907 + 0908). | — |
| Credential Scrub | **High** (pre-release) | Remove all hardcoded credentials, passwords, API keys before publishing CE on `main` | `handovers/CE_LAUNCH_CREDENTIAL_SCRUB.md` |
| Demo Server Prep | Medium | Security hardening for public demo/trial server (Ubuntu, 5-day sessions) | `handovers/Demo_server_prepp.md` |
| ~~Production Frontend Serving (0902)~~ | ~~High~~ | **COMPLETE.** | — |

### Deferred Handovers

| ID | Title | Effort | Priority | Notes |
|----|-------|--------|----------|-------|
| 0844 | Tenant Data Export/Import (0844a-c) | 4-8 hrs | Medium | Post-launch. Sequential chain with manual gates. Develop on `main`. |
| 0903 | Streamlined CLI Install | 12-16 hrs | Medium | Post-launch. `pip install giljo-mcp` → `giljo-mcp init` → paste MCP command → done. Depends on 0902. Develop on `main`. |
| 1014 | Security Event Auditing | 8 hrs | Medium | Enterprise compliance feature. Full spec ready (`handovers/1014_security_auditing.md`). Develop on `saas` when compliance requirements materialize. |
| TODO_vision | Vision Summarizer LLM Upgrade | 16-24 hrs | Low | Phase 1 partial (DB columns added). Phases 2-3 untouched. Develop on `main` (improves core). |

---

## Post-CE Feature Wishlist

From `completed/techdebt_march_2026-C.md`. None are blocking. Prioritize based on user demand.

### CE Features (develop on `main`)

| Item | Effort Est. | Notes |
|------|-------------|-------|
| ~~0901 Dashboard Scope Simplification~~ | ~~Small~~ | **COMPLETE.** |
| ~~0902 Single-Port Frontend Serving~~ | ~~Medium~~ | **COMPLETE.** |
| ~~0904 Orchestrator Auto Check-in~~ | ~~Medium~~ | **COMPLETE.** |
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

- [x] Move reference docs to `Reference_docs/` — **DONE**
- [x] Archive `PRIORITY_ORDER.md` — **DONE** (in `completed/PRIORITY_ORDER-C.md`)
- [ ] Update `handovers/README.md` priority table (stale)
- [ ] Clean up 30 stale local git branches (part of Phase 0.1)

---

## References

- [EDITION_ISOLATION_GUIDE.md](../docs/EDITION_ISOLATION_GUIDE.md) -- authoritative CE/SaaS directory rules
- [PRIORITY_ORDER.md](./PRIORITY_ORDER.md) -- completed CE launch checklist
- [techdebt_march_2026-C.md](./completed/techdebt_march_2026-C.md) -- resolved tech debt + post-CE items
- [handover_catalogue.md](./handover_catalogue.md) -- full handover history
