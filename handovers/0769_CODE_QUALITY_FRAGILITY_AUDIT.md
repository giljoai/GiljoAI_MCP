# Handover 0769: Code Quality & Fragility Audit — March 2026

**Date:** 2026-03-30
**From Agent:** Claude Opus 4.6 audit session
**To Agent:** Cleanup sprint agent(s)
**Priority:** High
**Status:** AUDIT COMPLETE — Remediation Not Started
**Edition Scope:** CE

---

## Executive Summary

Full 10-dimension code quality audit plus architectural fragility analysis. The codebase has drifted from **8.35/10** (0765 baseline, early March) to **6.3/10** after several large feature sprints (setup wizard 0855, MCP SDK 0846, orchestrator protocol 0851). Primary regressions: test rot (115 failures), frontend design-token drift (396 hardcoded colors), and god-class growth in backend services.

**Commit Range:** `474d2bb2`...`bc2286af` (30 commits, 111 files, +10,444 / -4,715 lines)

---

## Automated Check Results

| Check | Result | Baseline | Status |
|-------|--------|----------|--------|
| Ruff (backend lint) | 0 issues | 0 | PASS |
| ESLint (frontend lint) | 2 errors + 14 warnings | 8 warnings max | REGRESSED |
| Frontend build | Builds, 736KB main chunk warning | Clean build | REGRESSED |
| CE/SaaS boundary | Script missing (`check_saas_import_boundary.py`) | 0 violations | UNKNOWN |
| Test suite (vitest) | 1,792 pass / 115 fail / 6 errors | 1,390+ / 0 / 0 | REGRESSED |

---

## 10-Dimension Rubric

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | **Lint cleanliness** | 7/10 | Ruff clean; ESLint 2 errors + 14 warnings (6 over budget) |
| 2 | **Dead code density** | 8/10 | 3 dead methods; 11 duplicate `formatDate`; dead `AgentExport.generateToken` |
| 3 | **Pattern compliance** | 6/10 | `agent_coordination.py`: 9 dict-return paths, raw DB logic bypassing service layer, dangling unused query, stale `src.` import |
| 4 | **Tenant isolation** | 7/10 | WebSocket cross-tenant subscription leak; PIN recovery + MCP session lack tenant_key |
| 5 | **Security posture** | 8/10 | CSRF solid, CORS solid, no secrets in source; WebSocket tenant gap is the one issue |
| 6 | **Test health** | 4/10 | 115 failures (6% rate), 23 broken files, 28 oversized test files, duplicate `__tests__/` dir |
| 7 | **Frontend hygiene** | 4/10 | 396 hardcoded colors (baseline 0), 12 border violations, 76 `!important`, 11 formatDate dupes |
| 8 | **Exception handling** | 8/10 | 6 unannotated broad catches (correct pattern, missing comment) |
| 9 | **Code organization** | 3/10 | 8 classes >1000 lines (worst 3,333), 16 functions >200 lines (worst 417), 13-param methods |
| 10 | **Convention & docs** | 8/10 | Versions consistent (1.0.0), no forbidden terms in source, ~8 docs have stale agent job statuses |

### **Overall Score: 6.3/10** (baseline: 8.35, target: >= 8.0)

---

## SECURITY (fix immediately)

### S1. WebSocket Cross-Tenant Subscription Leak

- **File:** `api/app.py:635-649`
- **Issue:** Entity tenant_key is resolved from DB but never validated against `auth_context["tenant_key"]`. An authenticated user in Tenant A can subscribe to Tenant B's project/agent/message updates by guessing entity IDs.
- **Fix:** Add `if tenant_key != auth_context.get("tenant_key"): return` before `subscribe()`.
- **Effort:** 5 minutes

---

## HIGH (fix before next release)

### H1. agent_coordination.py — Multiple Pattern Violations

- **File:** `src/giljo_mcp/tools/agent_coordination.py`
- **Issues:**
  - 9 paths return `{"success": False, "error": ...}` instead of raising exceptions (post-0480 violation)
  - Raw SQLAlchemy DB logic duplicating `AgentJobManager.spawn_agent()` service method
  - Dangling unused query at lines 201-204 (built but never executed)
  - Stale import: `from src.giljo_mcp.database` (should be `from giljo_mcp.database`)
- **Fix:** Rewrite to delegate to AgentJobManager, raise exceptions.
- **Effort:** 30 minutes

### H2. Test Suite — 115 Failures Across 23 Files

All failures stem from component refactors not propagated to tests. Grouped by root cause:

| Category | Failures | Root Cause |
|----------|----------|------------|
| Setup wizard redesign (0855e) | 20 | Tests expect old UI text/structure |
| StatusBadge refactor | 17 | Component changed from v-menu to simple v-chip |
| CreateAdminAccount | 9 + 6 errors | Missing Vuetify form ref mocks |
| Settings card text changes | 17 | String literal mismatches |
| View/tab refactors | 17 | Tab order, state management changes |
| Project component refactors | 13 | Modal/tab behavior changes |
| Vuetify stub depth | 20 | Shallow stubs don't render content |
| Duplicate `__tests__/` directory | 2 files | Runs in parallel with canonical `tests/` |

**Effort:** ~4 hours total to stabilize all 23 files

### H3. God Classes (8 classes exceeding 1000-line limit)

| Class | Lines | Methods | Changes (2mo) |
|-------|-------|---------|---------------|
| `OrchestrationService` | 3,333 | 31 | 84 |
| `ProjectService` | 2,803 | 41 | 51 |
| `ProductService` | 1,715 | — | — |
| `ThinClientPromptGenerator` | 1,698 | — | — |
| `MessageService` | 1,622 | — | 36 |
| `StatisticsRepository` | 1,084 | — | — |
| `UserService` | 1,045 | — | — |
| `TaskService` | 1,043 | — | — |

### H4. Oversized Functions (16 functions exceeding 200-line limit)

| Function | Lines | File |
|----------|-------|------|
| `_load_legacy_templates` | 417 | `template_manager.py:142` |
| `report_progress` | 382 | `orchestration_service.py:1351` |
| `get_agent_mission` | 348 | `orchestration_service.py:920` |
| `receive_messages` | 311 | `message_service.py:1016` |
| `_build_claude_code_execution_prompt` | 305 | `thin_prompt_generator.py:1322` |
| `complete_job` | 299 | `orchestration_service.py:1785` |
| `get_orchestrator_instructions` | 283 | `orchestration_service.py:2882` |
| `send_message` | 280 | `message_service.py:119` |
| `write_360_memory` | 278 | `write_360_memory.py:228` |
| `generate` | 271 | `thin_prompt_generator.py:370` |
| `_get_default_templates_v103` | 266 | `template_seeder.py:221` (data — acceptable) |
| `_generate_agent_protocol` | 250 | `protocol_builder.py:363` |
| `_execute_vision_query` | 227 | `get_vision_document.py:439` |
| `close_project_and_update_memory` | 225 | `project_closeout.py:35` |
| `launch_project` | 220 | `project_service.py:2005` |
| `spawn_agent_job` | 210 | `orchestration_service.py:369` |

### H5. Frontend Design Token Regression — 396 Hardcoded Colors

Baseline was zero post-0765c. Top offenders:

| File | Occurrences |
|------|-------------|
| `JobsTab.vue` | 41 |
| `SetupStep3Commands.vue` | 29 |
| `SetupWizardOverlay.vue` | 28 |
| `SetupStep2Connect.vue` | 25 |
| `MessageAuditModal.vue` | 18 |
| `DashboardView.vue` | 17 |

### H6. ESLint Errors (2)

- `ProjectsView.vue:1211` — `keys` should be `const` not `let`
- `RecentProjectsList.vue:55` — string concatenation instead of template literal

---

## MEDIUM

### M1. Unannotated Broad Exception Catches (6)

All follow correct service-boundary pattern but lack required annotation comment:

- `message_service.py:1676` — `get_message_status`
- `orchestration_service.py:2306` — `reactivate_job`
- `orchestration_service.py:2416` — `dismiss_reactivation`
- `product_service.py:899` — `purge_product`
- `fetch_context.py:134` — `_is_category_enabled`
- `fetch_context.py:212` — `_load_user_depth_config`

### M2. Tenant Isolation Defense-in-Depth

- `auth_pin_recovery.py:86,173` — User lookup by username without tenant_key filter
- `mcp_session.py:52-56` — Iterates all active API keys across tenants for hash verification
- `mcp_installer.py:188` — User lookup by ID without tenant_key

### M3. Stale Agent Job Status Values in Documentation

8 docs reference `pending`/`active` instead of `waiting`/`working`:
- `docs/api/AGENT_JOBS_API_REFERENCE.md` (worst — 9 stale references)
- `docs/api/agent_jobs_endpoints.md`
- `docs/api/context_tools.md`
- `docs/guides/agent_monitoring_developer_guide.md`
- `docs/guides/staging_rollback_integration_guide.md`
- `docs/TESTING.md`
- `docs/cleanup/refactoring_roadmap.md`

### M4. CSS Border Violations on Rounded Elements (12)

Should use `smooth-border` class per project rules. Top violations:
- `StatusChip.vue:114,124`
- `DashboardView.vue:584`
- `JobsTab.vue:1126,1324,1358`
- `AgentJobModal.vue:212`
- `ProjectsView.vue:1544,1585`

### M5. Duplicate formatDate Implementations (11)

11 independent `toLocaleDateString()` implementations across components. Should be a shared `useFormatDate` composable. Two files use `date-fns` while the rest use raw browser API — inconsistent approach.

### M6. !important Overrides (76 total, ~15 suspect)

Most in `global-tabs.scss` are justified Vuetify overrides. Suspect ones with hardcoded colors:
- `DashboardView.vue:562-622` (8 instances)
- `SetupWizardOverlay.vue:682`
- `SetupStep3Commands.vue:432-433`
- `SetupStep2Connect.vue:560-561`

### M7. Duplicate Test Directory

`frontend/__tests__/` contains 2 test files that duplicate files in `frontend/tests/`. Both directories are picked up by vitest.

### M8. Oversized Test Files (28 files exceed 500 lines)

Worst: `projects-state-transitions.spec.js` at 1,051 lines (2x limit).

---

## Fragility Analysis — Architectural Risks

### F1. CRITICAL — Global APIState Singleton

- **File:** `api/app.py:127-151`
- **Impact:** 57 files import `from api.app import state`. Module-level singleton holds db_manager, websocket_manager, tool_accessor, auth, event_bus. Prevents dependency injection and proper test isolation.
- **Recommendation:** Replace with FastAPI's `app.state` or DI container. Reduce imports to a single `api/dependencies.py` facade.

### F2. CRITICAL — OrchestrationService as Change Hotspot

- **84 changes in 2 months**, 3,333 lines, methods up to 382 lines with up to 11 parameters.
- **Recommendation:** Split into `AgentJobLifecycleService`, `ProgressTrackingService`, `MissionService`.

### F3. HIGH — Dual Config Subsystem

- `ConfigManager` (typed singleton with env-var overrides) vs `_config_io.read_config()` (raw YAML dict)
- **Both used in production:** 8 files use `get_config()`, 11 use `read_config()`, 4 bypass both with inline `yaml.safe_load`
- Config set via env var is invisible to `read_config()` callers
- **Recommendation:** All production code should use `get_config()`. Reserve `read_config()/write_config()` for config CRUD endpoints only.

### F4. HIGH — Sequential Startup (All-or-Nothing)

- 8-phase linear startup. Event bus failure kills REST API even though API doesn't need it.
- **Recommendation:** Classify phases as required (database, auth) vs optional (event bus, silence detector). Allow optional failures with degraded mode.

### F5. HIGH — WebSocket Reconnection Race

- `websocket.js:319-353` — No mutex on reconnect. Rapid disconnect/reconnect can create duplicate connections.
- **Recommendation:** Add `reconnectTimer` ref, clear on each attempt. Or use state machine to prevent overlapping attempts.

### F6. HIGH — websocketEventRouter Mega-Hub

- 575 lines, imports 13 stores, routes 30 event types. Changed 18 times in 2 months.
- **Recommendation:** Split into domain-specific route files (agent events, message events, project events).

### F7. HIGH — Functions with Excessive Parameters

| Method | Params | File |
|--------|--------|------|
| `_broadcast_message_events` | 13 | `message_service.py:605` |
| `_broadcast_agent_created` | 11 | `orchestration_service.py:867` |
| `create_product` | 11 | `product_service.py:227` |
| `create_project` | 10 | `project_service.py:153` |
| `spawn_agent_job` | 10 | `orchestration_service.py:369` |

**Recommendation:** Introduce parameter dataclasses (`BroadcastContext`, `SpawnRequest`).

### F8. MEDIUM — Payload Normalization Duplication

- `websocket.js:427-438` AND `websocketEventRouter.js:466-480` both normalize payloads.
- Risk of double-normalization or inconsistent event shapes.

### F9. MEDIUM — Late State Exposure During Startup

- `api/app.py:194-197` — `app.state.db_manager` set after all init completes. No guard prevents middleware accessing it during initialization.

### F10. MEDIUM — CORS Origin Resolution Scoping Bug

- `api/app.py:288` — `config` variable used outside its `try` block. If the read failed, this would be a `NameError`.

---

## LOW (housekeeping)

- **3 dead methods:** `port_manager.py:check_all_ports_available`, `jwt_manager.py:decode_token_no_verify`, `project_service.py:purge_deleted_project`
- **4 config bypass sites:** inline `yaml.safe_load` in `thin_prompt_generator.py:73`, `discovery.py:133`, `config_service.py:80`, `port_manager.py:143`
- **Dead AgentExport.generateToken:** calls old localStorage auth pattern
- **2 dead test fixtures:** `orchestrator_simulator.py`, `mock_agent_simulator.py`
- **3 forbidden-term instances** in archived docs (`docs/archive/retired-2026-01/`)

---

## Prioritized Action List

| # | Action | Effort | Priority |
|---|--------|--------|----------|
| 1 | Fix WebSocket tenant check (`app.py:635`) | 5 min | SECURITY |
| 2 | Rewrite `agent_coordination.py` — delegate to service, raise exceptions | 30 min | HIGH |
| 3 | Fix 2 ESLint errors | 2 min | HIGH |
| 4 | Fix CreateAdminAccount tests (stops 6 unhandled errors) | 15 min | HIGH |
| 5 | Rewrite StatusBadge tests for current chip API | 30 min | HIGH |
| 6 | Update setup wizard test files (4 files) | 1 hour | HIGH |
| 7 | Update remaining 14 failing test files | 2 hours | HIGH |
| 8 | Add 6 broad-catch annotation comments | 10 min | MEDIUM |
| 9 | Add tenant_key filter to PIN recovery | 10 min | MEDIUM |
| 10 | Extract `useFormatDate` composable, replace 11 implementations | 30 min | MEDIUM |
| 11 | Update 8 docs with stale agent job statuses | 30 min | MEDIUM |
| 12 | Remove duplicate `frontend/__tests__/` directory | 5 min | MEDIUM |
| 13 | Fix 12 CSS border violations (use smooth-border) | 30 min | MEDIUM |
| 14 | Split OrchestrationService (3,333 -> 3 services) | 4+ hours | TECH DEBT |
| 15 | Split ProjectService (2,803 -> 3 services) | 3+ hours | TECH DEBT |
| 16 | Replace global state singleton with DI | 8+ hours | TECH DEBT |
| 17 | Consolidate config subsystem | 2 hours | TECH DEBT |
| 18 | Fix 396 hardcoded colors across 55 files | 4+ hours | TECH DEBT |
| 19 | Add WebSocket reconnect mutex | 30 min | TECH DEBT |
| 20 | Split websocketEventRouter into domain files | 1 hour | TECH DEBT |

---

## What This Audit Does NOT Cover

- **Feature correctness** — hygiene audit, not functional testing
- **Performance** — no load testing or query optimization
- **SaaS-specific code** — `saas/` directories audited separately
- **Mobile/responsive** — no viewport testing
