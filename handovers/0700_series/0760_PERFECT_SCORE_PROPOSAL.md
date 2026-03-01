# 0760: Perfect Score (10/10) Code Quality Proposal

**Date:** 2026-03-01
**From Agent:** 0750 Sprint Orchestrator
**To Agent:** Research agent (validate estimates), then implementation agents
**Priority:** Medium
**Branch:** Create `0760-perfect-score` from `0750-cleanup-sprint`
**Baseline:** 7.8/10 (final 0750 audit, commit `59499e1a`)

---

## Purpose

This document proposes the work required to reach a 10/10 code quality score. A fresh research agent should scrub the codebase against each item below and provide realistic effort estimates before any implementation begins.

**For the research agent:** Read `handovers/0700_series/0750_FINAL_AUDIT_REPORT.md` and `prompts/0750_chain/final_audit.json` for the complete findings list. Validate each item below by checking the actual code state.

---

## Tier 1: Quick Wins (7.8 to 8.5) — Estimated 1-2 hours

These are verified deletions and trivial fixes with zero behavioral risk.

### 1A: Fix pytest-asyncio compatibility [+0.3]
- **Problem:** 68 test errors from `@pytest.fixture` on async fixtures (pytest 9 requires `@pytest_asyncio.fixture`)
- **Files:** 9 test files in `tests/services/`
- **Fix:** Either upgrade `pytest-asyncio` to >=0.23 OR add `@pytest_asyncio.fixture` decorators
- **Research task:** Check current pytest-asyncio version in requirements, determine which fix is safer

### 1B: Add missing async markers [+0.1]
- **Problem:** 8 test failures from missing `@pytest.mark.asyncio`
- **Files:** `tests/unit/test_discovery_system.py` (4), `tests/services/test_orchestration_service_websocket_emissions.py` (3, marker commented out at line 20), `tests/manual/test_config_endpoint_live.py` (1)
- **Fix:** Add decorators / uncomment marker

### 1C: Delete 19 dead ToolAccessor methods [+0.05]
- **Problem:** 19 pass-through methods with 0 MCP tool_map wiring and 0 external references
- **File:** `src/giljo_mcp/tools/tool_accessor.py`
- **Research task:** Verify each method truly has 0 references via `find_referencing_symbols`. List: `list_projects`, `get_project`, `switch_project`, `complete_project`, `cancel_project`, `restore_project`, `get_messages`, `complete_message`, `broadcast`, `log_task`, `get_context_index`, `get_vision`, `get_vision_index`, `get_product_settings`, `list_templates`, `create_template`, `update_template`, `set_product_path`, `get_product_path`

### 1D: Delete dead `activate_project` standalone function [+0.02]
- **File:** `src/giljo_mcp/tools/tool_accessor.py:43-95` (53 lines, 0 refs)

### 1E: Delete dead orchestration.js Pinia store [+0.05]
- **File:** `frontend/src/stores/orchestration.js` (117 lines, 0 imports)
- **Research task:** Confirm 0 imports across entire frontend

### 1F: Delete 5 dead JobsTab functions [+0.03]
- **File:** `frontend/src/components/projects/JobsTab.vue`
- **Functions:** `getShortId` (463), `copyId` (471), `formatCount` (645), `getMessagesSent` (688), `getMessagesRead` (703)

---

## Tier 2: Moderate Effort (8.5 to 9.0) — Estimated 4-6 hours

### 2A: Tools-layer dict-return migration [+0.15]
- **Problem:** 37 `return {"success": ...}` patterns across 6 files
- **Breakdown:** agent_coordination.py (22), agent.py (6), agent_discovery.py (5), tool_accessor.py (2), write_360_memory.py (1), context.py (1)
- **Pattern:** Same as 0750c — raise exceptions from `giljo_mcp.exceptions` instead
- **Research task:** Map each instance, identify callers, determine if any callers depend on dict structure (MCP tool handlers may need special handling since they return dicts to Claude)
- **Risk:** MCP tool handlers return dicts to the LLM by design. Need to distinguish "error dict returned to caller" (anti-pattern) from "result dict returned to LLM" (correct). The research agent must classify each instance.

### 2B: Fix statistics endpoints [+0.1]
- **H-2:** `get_project_statistics_by_id` iterates all projects, missing `current_user` arg
- **H-3:** 4 hardcoded fake metrics (avg_response_time=30.0, error_rate=0.1, active_sessions=1, avg_processing_time=45.0)
- **Research task:** Determine if these metrics CAN be computed from real data, or if the endpoints should be removed/stubbed with "not implemented"

### 2C: WebSocket bridge authentication [+0.05]
- **Problem:** `api/endpoints/websocket_bridge.py:42` POST `/emit` has zero auth
- **Fix:** Add API key or internal auth mechanism
- **Research task:** Determine who calls this endpoint (internal MCP-to-WS bridge? external clients?) and what auth mechanism is appropriate

### 2D: Delete remaining dead code [+0.05]
- Dead `acknowledgedMessages` computed in `frontend/src/stores/messages.js:29`
- Dead `BroadcastMessageRequest`/`BroadcastMessageResponse` in `api/schemas/prompt.py:53-75`
- 3 dead fixtures in `tests/conftest.py` (vision_test_files, product_service_with_session, mock_message_queue)
- Dead `test_project_with_orchestrator` fixture in `tests/integration/conftest.py:383-418`
- Dead `AgentExecution` import in `tests/services/test_successor_spawning.py:20`
- Remove 10 `[STATS DEBUG]` logger.debug lines from `statistics.py`

### 2E: Fix stale status remnants [+0.02]
- `statistics_repository.py:371` — stale "idle" status in filter
- `agent_job_repository.py:111` — docstring references "pending"/"failed"

### 2F: ActionIcons.vue Options API migration [+0.03]
- **File:** `frontend/src/components/StatusBoard/ActionIcons.vue`
- **Problem:** Uses deprecated Options API while entire codebase uses `<script setup>`
- **Research task:** Check component complexity — may be a simple rewrite

---

## Tier 3: Significant Effort (9.0 to 9.5) — Estimated 8-15 hours

### 3A: except Exception catch-all reduction [+0.1]
- **Problem:** 121 instances across 26 files
- **Major offenders:** project_service.py (21), orchestration_service.py (16), product_service.py (16), task_service.py (8), auth_service.py (8)
- **Approach:** For each catch-all, determine the specific exceptions that can occur and narrow the catch clause
- **Risk:** HIGH — overly narrow catches could surface unhandled exceptions in production
- **Research task:** Categorize the 121 instances: how many are logging-only (safe to narrow), how many are retry/fallback (need careful analysis), how many are at API boundaries (may be intentional)

### 3B: Frontend hardcoded colors to design tokens [+0.05]
- **Problem:** 108 hex colors across 20 Vue files
- **Approach:** Create/extend Vuetify theme config, replace hardcoded values with `rgb(var(--v-theme-*))`
- **Research task:** Map all 108 colors, group by semantic meaning (primary, secondary, status colors, decorative), determine how many map to existing Vuetify tokens vs needing custom tokens

### 3C: Orphan CSS cleanup [+0.03]
- 5 orphan selectors in JobsTab.vue, 2 in ProjectTabs, 1 in AgentTableView, 1 in ActionIcons
- StatusBadge invalid HTML id (`confirmDialogTitle` contains spaces)
- Static computeds that should be constants (giljoFaceIcon, actionIconColor)

### 3D: Fix 8 unhandled ProjectTabs emits [+0.03]
- **Problem:** ProjectTabs declares 11 emits, parent handles only 3
- **Research task:** Determine if these are planned features (wire up parent handlers) or dead code (remove emits + their trigger logic)

### 3E: Sort priority divergence [+0.02]
- **Problem:** agentJobsStore and useAgentData sort agents differently
- **Research task:** Determine the intended sort order (product/UX decision)

### 3F: CORS method/header restriction [+0.02]
- **Problem:** `allow_methods=["*"]`, `allow_headers=["*"]`
- **Fix:** Restrict to actual methods (GET/POST/PUT/PATCH/DELETE/OPTIONS) and headers (Content-Type, Authorization, X-API-Key, X-Tenant-Key)

### 3G: Oversized test files [+0.02]
- 14 test files over 500 lines (largest: test_orchestration_service.py at 1,161)
- **Research task:** Determine if splitting is worthwhile or just busywork

### 3H: NPM health check hardening [+0.02]
- **Problem:** `startup.py:618` and `control_panel.py:1191` use `node_modules.exists()` which passes for corrupted skeleton directories
- **Fix:** Check `.package-lock.json` or `.bin/vite.cmd` existence instead
- **Reference:** Full analysis in `handovers/NPM_VITE_corruption_report.md`
- **Note:** npm install is now healthy (0 vulnerabilities), but the detection logic still has the bug

---

## Tier 4: Architecture Changes (9.5 to 10.0) — Estimated 20-40+ hours

These require design decisions and cross-cutting changes.

### 4A: Enable CSRF middleware [+0.1]
- **Problem:** Backend middleware exists (`api/middleware/csrf.py`) but is commented out
- **Requires:** Frontend-wide change to send `X-CSRF-Token` header with every API call
- **Research task:** Audit all Axios/fetch calls in frontend, determine integration pattern (interceptor vs per-call)

### 4B: Hardcoded default tenant key removal [+0.1]
- **Problem:** `tk_cyyOVf1H...` used when tenant_key missing in 3 auth middleware locations
- **Requires:** Multi-tenant architecture decision — what happens when no tenant is provided? Reject? Default org?
- **This is a product decision, not just code quality**

### 4C: Tenant isolation pattern completion [+0.05]
- `simple_handover.py:113` — AgentJob lookup missing tenant_key filter
- `db.get(Project, id)` PK lookups bypass tenant WHERE clause (functionally safe but pattern violation)
- `launch_project` join missing tenant on AgentJob
- **Research task:** Inventory all `db.get()` calls and determine which need tenant wrapping

### 4D: Prompts endpoint encapsulation [+0.03]
- `api/endpoints/prompts.py:601,610` calls private `_build_*` methods on ThinClientPromptGenerator
- **Fix:** Make these public API methods or create a proper public interface

### 4E: update_project refactor [+0.02]
- 102 lines, bloated with mixed concerns
- **Research task:** Identify what can be extracted

### 4F: Frontend test fixtures cleanup [+0.02]
- 6 references to `mission_acknowledged_at` in spec files (field exists but may be deprecated)
- TenantManager cache mutation in smoke tests without cleanup

---

## Score Projection

| Tier | Items | Effort | Score After |
|------|-------|--------|-------------|
| Current | -- | -- | 7.8 |
| Tier 1 | 6 items | 1-2 hours | ~8.5 |
| Tier 2 | 6 items | 4-6 hours | ~9.0 |
| Tier 3 | 8 items | 8-15 hours | ~9.5 |
| Tier 4 | 6 items | 20-40 hours | ~10.0 |

**Total estimated effort: 33-63 hours**

---

## Research Agent Instructions

1. **Validate every item above** — check actual code state, confirm findings are real
2. **Provide effort estimates** for each item (hours, not days)
3. **Flag items that are WRONG** — some findings may have been fixed or may be false positives
4. **Identify dependencies** — which items must be done in order
5. **Recommend a phased execution plan** — which items to batch into sprint sessions
6. **Flag product decisions** — items where code quality can't be improved without a UX/architecture decision
7. **Check npm/vite state** — npm install is now healthy with 0 vulnerabilities. Verify the startup.py/control_panel.py detection bug still needs fixing.

Write your research report to: `handovers/0700_series/0760_RESEARCH_REPORT.md`

---

## Acceptance Criteria

- [ ] Research agent validates all items and provides estimates
- [ ] Product decisions identified and escalated
- [ ] Phased execution plan created
- [ ] Each tier achievable in a single sprint session
- [ ] Final re-audit confirms 10.0/10 (or documents why ceiling is <10)
