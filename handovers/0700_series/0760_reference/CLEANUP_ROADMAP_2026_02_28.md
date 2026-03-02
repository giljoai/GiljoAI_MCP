# Code Cleanup Roadmap

**Created:** 2026-02-28
**Source Audit:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md`
**Dependency Map:** `docs/cleanup/dependency_graph.json` (1,284 nodes, 2,530 edges)
**Baseline:** 0700 series (8/10 code quality, zero lint, ~15,800 lines removed)
**Current State:** 6.6/10 code quality, 65 findings (5 SECURITY, 25 HIGH, 27 MEDIUM, 8 LOW)
**Target:** 8/10+ code quality, green test suite, commercialization-ready codebase

---

## How to Use This Document

Each phase is scoped to 1-2 agent sessions. Execute in order — later phases depend on earlier ones. Each phase has a handover prompt you can copy directly to start an agent session.

After completing each phase, update the checkbox and note the commit hash.

### Dependency Graph as Reference Map

The file `docs/cleanup/dependency_graph.json` contains a full dependency map of the codebase. It is a **starting point for investigation, not a verdict.** The graph tells you where to look — it does not tell you what to do.

**Rules for using the graph:**
- Every file flagged by the graph (orphan, dead_code, etc.) must be **individually investigated** before any action. Open it, read it, understand its purpose.
- "Orphan" means zero import dependents — it does NOT mean safe to delete. Entry points (`install.py`, `backup.py`, CLI scripts) are correctly orphans.
- "Connected" with high dependents means high blast radius — it does NOT mean the file is good or bad, just that changes ripple far.
- The graph may be stale relative to recent commits. When in doubt, verify with `find_referencing_symbols` or `grep`.

**Graph snapshot (as of 2026-02-28):**

| Metric | Count | Meaning |
|--------|-------|---------|
| Total nodes | 1,284 | Files analyzed |
| Orphans | 948 (74%) | Zero dependents — investigation candidates, not deletion targets |
| Connected | 317 | Files with real dependency chains |
| Standalone | 19 | Self-contained utilities |
| Critical risk (50+ deps) | 11 | Touch with extreme care |
| High risk (20-49 deps) | 15 | Ripple effects on changes |
| Edges | 2,530 | Import/invocation relationships |

**Critical risk nodes (do NOT modify without full impact analysis):**

| File | Dependents | Role |
|------|-----------|------|
| `src/giljo_mcp/models/__init__.py` | 327 | Model registry hub |
| `src/giljo_mcp/database.py` | 133 | DB session factory |
| `src/giljo_mcp/tenant.py` | 119 | Tenant isolation core |
| `src/giljo_mcp/models/agent_identity.py` | 125 | Agent model |
| `tests/helpers/test_db_helper.py` | 54 | Test infrastructure |
| `api/app.py` | 78 | Application entry |
| `frontend/src/services/api.js` | 93 | Frontend API client |
| `src/giljo_mcp/auth/dependencies.py` | 61 | Auth injection |
| `src/giljo_mcp/exceptions.py` | 63 | Exception hierarchy |

**High risk nodes with known debt:**

| File | Dependents | TODOs | Notes |
|------|-----------|-------|-------|
| `services/orchestration_service.py` | 32 | 162 | Monolith split candidate (Phase 5) |
| `tools/tool_accessor.py` | 28 | 5 | Dict-return cleanup target (Phase 3) |
| `thin_prompt_generator.py` | 34 | 12 | Investigate before touching |
| `schemas/service_responses.py` | 42 | 5 | Shared contract — careful changes |

### Refreshing the Graph

After completing each phase, refresh the graph to measure progress:
```bash
python scripts/update_dependency_graph_full.py
```
Compare orphan counts and edge counts against the snapshot above. Orphan count should decrease as dead code is removed. Edge count may decrease as coupling is reduced.

---

## Phase 1: Protocol Document Patches

**Goal:** Fix the root cause — instruction gaps and contradictions that agents follow literally.
**Sessions:** 1
**Priority:** HIGHEST (multiplier effect on all future sessions)
**Audit Reference:** Section "Instruction Gap Analysis" — 45% of findings trace to missing/contradictory instructions

### 1A: Fix `handovers/Reference_docs/QUICK_LAUNCH.txt`

- [ ] **Replace service template code** (lines 745-807): The template uses `return {"success": False, "error": str(e)}`. Rewrite to use `raise ServiceError(...)` pattern. This is the single highest-impact change in the entire roadmap.
- [ ] **Replace endpoint example** (lines 148-150): Same dict-return pattern in the example code.
- [ ] **Strengthen the exception rule** (lines 313-322): Change from a note to a hard rule. "ALL layers — services, tools, orchestration, helpers — raise exceptions. Never return dict error responses."

### 1B: Fix `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`

- [ ] **Update status values** (lines 86-89): Replace 7 statuses with the canonical 6: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`. Remove `failed` and `cancelled`.
- [ ] **Remove dead file references** (lines 228-232): Verify which of `agent_job_manager.py`, `agent_communication.py`, `agent_coordination.py` still exist. Remove or update references.
- [ ] **Remove stale tool references** (line 141): `acknowledge_job` was removed. Find and remove all references to deleted tools.
- [ ] **Add "Last Verified" date** at top of document.

### 1C: Patch `handovers/handover_instructions.md`

- [ ] **Broaden dict-return rule** (line 128): Change "Services raise exceptions" to "All Python layers raise exceptions — services, tools, orchestration, helpers, and context management."
- [ ] **Add Endpoint Security section** (new, after line 134):
  - Every router must inject `Depends(get_current_active_user)`
  - Admin-only endpoints (config, database, system) must check role
  - Pattern: show the correct dependency injection example
- [ ] **Add Frontend Code Discipline section** (new):
  - Composable reuse: shared logic goes in `composables/`, not duplicated across components
  - Design tokens: use Vuetify theme variables, no `!important` overrides
  - Dead emit cleanup: if you remove a parent listener, remove the child `$emit`
  - Accessibility: ARIA labels on interactive elements
- [ ] **Add Function Size Limits** (new):
  - No function >200 lines without explicit justification in the handover
  - No class >1000 lines — split into focused modules
- [ ] **Add Cascading Cleanup Checklist** (new, after line 60):
  - When modifying a model: trace model -> repository -> service -> tool -> endpoint -> frontend -> tests
  - When removing a column: grep for the column name across ALL layers
  - When removing a tool: check MCP registration, frontend tool lists, test fixtures
- [ ] **Add No Placeholder Data rule** (new):
  - No `random.randint()` in production code paths
  - No hardcoded fake metrics
  - If data unavailable: return null or raise, never fabricate

### Acceptance Criteria
- All three docs updated with no contradictions between prose rules and code examples
- AGENT_FLOW_SUMMARY.md shows only 6 valid statuses
- QUICK_LAUNCH.txt templates demonstrate exception-based patterns
- handover_instructions.md has sections for: endpoint auth, frontend, size limits, cascading cleanup, no placeholders

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 1. Execute all items in 1A, 1B, 1C.
Read each target file before editing. Verify AGENT_FLOW_SUMMARY.md file references
against actual filesystem before updating. Do NOT change anything outside the three
protocol documents. Commit when all checkboxes are done.
```

---

## Phase 2: Test Suite Triage

**Goal:** Get from "can't even run tests" to "green suite with known coverage."
**Sessions:** 1-2
**Priority:** HIGH (blocks all future validation)
**Audit Reference:** Section "Test Suite" — 3 CRITICAL, 8 HIGH, 12 MEDIUM findings
**Depends on:** None (can run parallel with Phase 1)
**COMPLETED:** 167 test files remain (470+ stale files deleted). 1,238 passing, 522 skipped, 0 failed. This IS the correct baseline — do not attempt to restore deleted tests.
**Graph context:** 801 of 1,284 graph nodes are test layer. The graph flags many test files as orphans — this is expected (tests are leaf nodes, they import but are not imported). Do NOT use orphan status to decide test file fate. Use pytest collection and pass/fail results instead.

### 2A: Delete Known-Broken Tests (Session 1)

- [ ] **Delete `test_field_key_mismatches.py`** — collection error, blocks entire suite
- [ ] **Delete all `TODO(0127a-2)` skip-marked tests** — these reference the old MCPAgentJob model and will never pass without a rewrite. List:
  - `tests/integration/test_hierarchical_context.py`
  - `tests/integration/test_message_queue_integration.py`
  - `tests/integration/test_orchestrator_template.py`
  - `tests/integration/test_upgrade_validation.py`
  - `tests/performance/test_database_benchmarks.py`
- [ ] **Audit remaining test files for import errors**: Run `python -m pytest tests/ --co -q 2>&1 | grep ERROR` to find any other collection failures. For each one, **investigate the error** — is it a fixable import or a reference to deleted code? Fix if trivial, delete if the test targets removed functionality.
- [ ] **Run full suite, record baseline**: After deletions, run `python -m pytest tests/ -q --timeout=60` and record pass/fail/skip counts. This becomes the new baseline.

### 2B: Identify Core Tests (Session 1 continued)

- [ ] **Tag critical test files** that must always pass (create `tests/CORE_TESTS.md`):
  - `tests/unit/test_tenant_isolation*.py` (61 tests — SaaS critical)
  - `tests/unit/test_*_service.py` (service layer — business logic)
  - `tests/unit/test_*_repository.py` (data layer — query correctness)
  - Any test covering auth/security endpoints
- [ ] **Use the dependency graph to find test infrastructure files**: `tests/helpers/test_db_helper.py` has 54 test dependents (critical risk in graph). This file must NOT be deleted. Identify any other shared test helpers with high dependent counts and protect them.
- [ ] **Remove dead fixtures**: Check `tests/fixtures/` and `tests/conftest.py` for fixtures that are never imported by any surviving test file. For each candidate, **grep for its name across all test files** before deleting — the graph may not capture dynamic imports or conftest auto-loading.

### 2C: Fix Failing Core Tests (Session 2, if needed)

- [ ] **Fix any failures in CORE_TESTS.md files only** — don't touch non-core tests
- [ ] **Remove non-core tests that fail** — if a test outside the core set fails and isn't worth fixing, delete it. You'll write better tests as part of future feature work.
- [ ] **Final green run**: `python -m pytest tests/ -q --timeout=60` must exit 0

### Acceptance Criteria
- `pytest tests/ --co -q` collects with zero errors
- `pytest tests/ -q` runs green (all pass or skip, zero failures)
- `tests/CORE_TESTS.md` exists listing the critical test files
- Dead fixtures removed
- `test_db_helper.py` and other shared test infrastructure preserved

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 2. Execute 2A first, then 2B.
Only proceed to 2C if there are failures in core test files. The goal is a GREEN
test suite, not 100% coverage. Delete aggressively — any test that fails and isn't
in the core set gets removed. BUT: investigate each file before deleting. Read it,
understand what it tested, check if the feature still exists. Use the dependency
graph (docs/cleanup/dependency_graph.json) to identify shared test helpers that
must be preserved. Record pass/fail counts before and after in the commit message.
```

---

## Phase 3: Tools Layer Dict-to-Exception Migration

**Goal:** Eliminate the 50+ dict returns in `src/giljo_mcp/tools/`.
**Sessions:** 1-2
**Priority:** HIGH (largest code debt item, now that protocols are fixed)
**Audit Reference:** Section "Dict Return Regression" — 57 occurrences in tools layer
**Depends on:** Phase 1 (protocol docs must have correct patterns before agents execute this)
**Graph context:** `tool_accessor.py` is high risk (28 dependents, 5 TODOs). Changes here ripple into both production code and 26 test files. Work function-by-function, not file-wide. `tenant.py` is critical risk (119 dependents) — the single dict return there needs surgical precision.

### 3A: tool_accessor.py (19 occurrences — largest single file)

- [ ] **Read the file first**, understand the pattern of each dict return and what callers expect
- [ ] **Check the graph**: This file has 28 dependents. Before changing any function signature, use `find_referencing_symbols` to map every caller. Some callers may destructure the dict (`result["success"]`) — these all need updating.
- [ ] **For each `return {"success": False, ...}`**: Replace with `raise ToolError(...)` or `raise ValueError(...)` as appropriate. Investigate each one — some may be MCP tool returns that the protocol expects as dicts (these should be left alone or wrapped differently).
- [ ] **Run tests** after each function migration to catch regressions

### 3B: Remaining tools files

- [ ] `tools/agent.py` (9 occurrences)
- [ ] `tools/project_closeout.py` (8 occurrences)
- [ ] `tools/write_360_memory.py` (8 occurrences)
- [ ] `tools/context.py` (7 occurrences)
- [ ] `tools/claude_export.py` (6 occurrences)

### 3C: Context management layer

- [ ] `context_management/chunker.py` (5 occurrences)
- [ ] `context_management/manager.py` (1 occurrence)

### 3D: Remaining outliers

- [ ] `repositories/vision_document_repository.py` (1 occurrence)
- [ ] `tenant.py` (1 occurrence) — **CAUTION: 119 dependents in graph (critical risk).** Read the function, understand who calls it, and verify the dict return isn't part of a broader contract before changing.
- [ ] `tools/context_tools/fetch_context.py` (1 occurrence)

### Acceptance Criteria
- `grep -r 'return {"success": False' src/` returns zero matches
- `grep -r 'return {"error":' src/` returns zero matches
- All modified functions raise exceptions instead
- All callers updated to use try/except
- Test suite still green

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 3. Migrate all dict-return
patterns to exceptions in the tools and context_management layers. Start with
tool_accessor.py (19 occurrences), then work through each file in order.
For EACH function changed: use find_referencing_symbols to find all callers and
update them. Run tests after each file. Reference handover_instructions.md for the
correct exception pattern.
```

---

## Phase 4: API Endpoint Hardening

**Goal:** Add auth to unprotected endpoints, fix dict returns in API layer.
**Sessions:** 1
**Priority:** HIGH (SECURITY findings)
**Audit Reference:** Section "Security Findings" — config endpoints lack auth
**Depends on:** Phase 1 (auth pattern must be documented first)
**Graph context:** `api/app.py` is critical risk (78 dependents) — it registers all routers. `auth/dependencies.py` (61 dependents) provides the auth injection pattern. Read `dependencies.py` first to understand the existing auth pattern before applying it to configuration.py.

### 4A: Configuration endpoints auth

- [ ] **Read `auth/dependencies.py`** to understand the existing `get_current_active_user` pattern and any role-checking helpers
- [ ] **Read another endpoint file that already has auth** (e.g., one of the connected endpoint files in the graph) to see the exact injection pattern in practice
- [ ] **Add `Depends(get_current_active_user)` to all routes** in `api/endpoints/configuration.py`
- [ ] **Add admin role check** to sensitive endpoints: `set_configuration`, `update_configurations`, `reload_configuration`, `update_database_password`, `delete_tenant_configuration`
- [ ] **Check other endpoint files** for missing auth: use the graph to list all files in `api/endpoints/`, then grep each for `Depends`. Any endpoint file without auth injection needs investigation — is it intentionally public (health check, login) or accidentally unprotected?

### 4B: API dict returns

- [ ] **Fix 3 dict returns in `configuration.py`** (lines 493, 504, 507 — the health check endpoint)
- [ ] **Audit all endpoint files** for remaining dict-return patterns

### Acceptance Criteria
- Every endpoint requires authentication (except explicitly public ones like login, health)
- Admin-only endpoints check role
- Zero dict returns in `api/` directory
- Existing auth tests still pass

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 4. Add authentication to
api/endpoints/configuration.py following the pattern used in other endpoint files.
Read auth/dependencies.py first to understand the auth pattern. Use the dependency
graph (docs/cleanup/dependency_graph.json) to identify all endpoint files, then
check each for missing auth. Investigate each unprotected endpoint — some may be
intentionally public. Admin-only endpoints need role verification. Also fix the
3 dict returns in the health check endpoint.
```

---

## Phase 5: Monolith Splits

**Goal:** Break oversized files into focused modules.
**Sessions:** 2-3
**Priority:** MEDIUM (architecture improvement, not blocking)
**Audit Reference:** Section "Oversized Functions" — 4 functions >250 lines
**Depends on:** Phases 1-4 (don't refactor dirty code)
**Graph context:** The dependency graph shows exactly which files import each monolith. Use the graph to understand blast radius before splitting, but verify each import chain is current — the graph may not reflect Phase 3/4 changes.

### 5A: Research (Session 1)

- [ ] **Refresh the dependency graph first**: Run `python scripts/update_dependency_graph_full.py` so you're working with post-Phase-3/4 data.
- [ ] **Map OrchestrationService** (3,427 lines, 162 TODOs, 32 dependents in graph): Read it, identify natural split boundaries. Likely candidates: spawn management, retirement management, status/heartbeat management, event handling. For each proposed new module, list which current dependents would import it.
- [ ] **Map tool_accessor.py** (28 dependents in graph): Group functions by domain (agent tools, project tools, context tools, etc.). Trace each dependent to understand which domain they actually use — this determines the split.
- [ ] **Check the graph for other monolith candidates**: Filter for nodes with >500 lines or >20 dependents. Investigate each one — high dependents alone doesn't mean it needs splitting (e.g., `models/__init__.py` is a registry, not a monolith).
- [ ] **Identify any other files >500 lines**: `wc -l src/giljo_mcp/**/*.py | sort -rn | head -20`
- [ ] **Write split plan** as a sub-document: `handovers/MONOLITH_SPLIT_PLAN.md`. Include for each proposed split: current file, proposed new files, function groupings, affected dependents (from graph), and estimated session effort.

### 5B: OrchestrationService split (Session 2)

- [ ] Execute the split plan for OrchestrationService
- [ ] Maintain backward compatibility via re-exports if needed
- [ ] Update all imports across the codebase — use the graph's dependent list as a checklist but verify each file
- [ ] Run full test suite

### 5C: Other splits (Session 3, if needed)

- [ ] Execute remaining splits from the plan
- [ ] Update imports, run tests

### Acceptance Criteria
- No file >1000 lines in `src/giljo_mcp/services/`
- No function >200 lines
- All imports updated (verified against graph dependents)
- Test suite green
- Dependency graph refreshed and orphan count has not increased (splits should not create orphans)

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 5A. This is RESEARCH ONLY —
do not write code. First refresh the dependency graph:
  python scripts/update_dependency_graph_full.py
Then use the graph (docs/cleanup/dependency_graph.json) to understand dependents
for each monolith candidate. Map OrchestrationService and tool_accessor.py, identify
split boundaries, and write the plan to handovers/MONOLITH_SPLIT_PLAN.md. Include
specific line ranges, proposed new file names, function groupings, and the list of
files that import each monolith (from the graph). Investigate each file — the graph
is a map, not a verdict.
```

---

## Phase 6: Dead Code Removal

**Goal:** Remove zombie code identified in the audit.
**Sessions:** 1
**Priority:** MEDIUM (housekeeping, reduces confusion)
**Audit Reference:** Section "Dead Code" — 7 items in backend, dead emits/config in frontend
**Depends on:** Phase 2 (test suite must be green first so you can validate removals)
**Graph context:** The graph flags 948 files as orphans. Most are NOT dead code — they are entry points, scripts, CLI tools, standalone utilities, or test files. The graph is a starting point for investigation, not a deletion list.

### 6A: Backend dead code

**Investigation protocol for each candidate:**
1. Check the graph: is it flagged as orphan/standalone?
2. Open the file and read it — understand what it does
3. Is it an entry point? (`if __name__ == "__main__"`, CLI script, startup file) — if yes, it's correctly an orphan, do NOT delete
4. Is it a utility invoked dynamically? (string-based imports, plugin systems, MCP tool registration) — grep for the filename as a string
5. Use `find_referencing_symbols` for symbol-level verification
6. Only delete if steps 2-5 all confirm it's dead

- [ ] **Audit-confirmed items** (these have already been investigated by the audit subagents):
  - `AgentJobRepository` stale column references (`started_by`, `completed_by`) — re-verify these columns are actually gone from the model
  - Any service methods with zero callers — re-verify with `find_referencing_symbols`
  - Stale status string references (`active`, `pending`, `preparing`, etc.)
- [ ] **Graph orphan sampling**: Pick 20 orphan files from the graph that are NOT in `tests/`, NOT obvious entry points, and NOT in `scripts/`. Investigate each one using the protocol above. This builds a picture of how much orphan debt exists for future cleanup.
- [ ] **Run tests after each deletion batch**

### 6B: Frontend dead code

- [ ] Dead `$emit` calls with no parent listener — investigate each: is the parent conditionally rendered? Check all possible parent components, not just the obvious one.
- [ ] Unused composable imports
- [ ] Dead config fields (properties set but never read)
- [ ] `copyToClipboard` duplication — extract to shared composable. Check graph for `frontend/src/services/api.js` dependents (93 in graph) to understand the frontend dependency structure first.

### 6C: Stale pycache and artifacts

- [ ] Remove `.pyc` files for deleted `.py` modules (from Phase 2 test deletions)
- [ ] Remove any leftover fixture files for deleted tests
- [ ] Check `docs/cleanup/dependency_graph.json` itself — after all prior phases, the graph data is stale. Refresh it: `python scripts/update_dependency_graph_full.py`

### Acceptance Criteria
- Every deleted item has documented investigation (not just graph status)
- `find_referencing_symbols` confirms zero refs for each deleted item
- Test suite still green
- No stale status strings in codebase
- Dependency graph refreshed post-cleanup

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 6. Remove dead code identified
in the audit report. The dependency graph (docs/cleanup/dependency_graph.json) is
a MAP for investigation, not a deletion list. For EVERY candidate:
1. Read the file and understand what it does
2. Check if it's an entry point or dynamically loaded
3. Use find_referencing_symbols to verify zero references
4. Only delete after all checks confirm it's dead
Do NOT bulk-delete graph orphans. Run tests after each deletion batch.
Refresh the dependency graph when done.
```

---

## Phase 7: Frontend Cleanup

**Goal:** Apply the frontend standards added in Phase 1.
**Sessions:** 1-2
**Priority:** LOW (cosmetic/maintainability, not blocking)
**Audit Reference:** Section "Frontend Findings" — 3 CRITICAL, 8 HIGH, 10 MEDIUM
**Depends on:** Phase 1 (frontend rules must exist in protocol docs first)
**Graph context:** 162 frontend nodes in graph. `frontend/src/services/api.js` is critical risk (93 dependents) — do not restructure without full impact analysis. `frontend/src/stores/user.js` (28 deps) and `frontend/src/stores/products.js` (20 deps) are high risk. Investigate each frontend file before modifying — the graph shows which components depend on which stores and services.

### 7A: Critical fixes

- [ ] Remove `!important` overrides where Vuetify classes suffice — investigate each one: is it compensating for a Vuetify bug or a specificity war? Some may be intentional.
- [ ] Extract duplicated `copyToClipboard` to `composables/useClipboard.ts` — use the graph to find all components that implement their own version
- [ ] Fix stale backend references (removed features still referenced in frontend) — for each, check if the backend endpoint still exists before removing the frontend call

### 7B: Accessibility and standards

- [ ] Add ARIA labels to interactive elements missing them
- [ ] Replace hardcoded colors with Vuetify theme tokens
- [ ] Clean up dead store state (Pinia properties set but never read) — investigate: is the state used in a template `v-if` or watcher that wouldn't show up in a simple grep?

### Acceptance Criteria
- `grep -r '!important' frontend/src/ | wc -l` reduced by >50%
- No duplicated utility functions across components
- `npm run build` succeeds with zero warnings

### Handover Prompt
```
Read handovers/CLEANUP_ROADMAP_2026_02_28.md Phase 7. Apply frontend cleanup
per the standards in handover_instructions.md (Frontend Code Discipline section).
Start with critical fixes (7A), then standards (7B). Run npm run build after
each batch of changes.
```

---

## Progress Tracker

| Phase | Description | Sessions | Status | Commit | Graph Orphans After |
|-------|-------------|----------|--------|--------|---------------------|
| — | Baseline (2026-02-28) | — | Complete | — | 948 |
| 1 | Protocol doc patches | 1 | [ ] Pending | | N/A (docs only) |
| 2 | Test suite triage | 1-2 | [ ] Pending | | |
| 3 | Tools dict-to-exception | 1-2 | [ ] Pending | | |
| 4 | API endpoint hardening | 1 | [ ] Pending | | |
| — | **Mid-point re-audit** | 1 | [ ] Pending | | |
| 5 | Monolith splits | 2-3 | [ ] Pending | | |
| 6 | Dead code removal | 1 | [ ] Pending | | |
| 7 | Frontend cleanup | 1-2 | [ ] Pending | | |
| — | **Final re-audit** | 1 | [ ] Pending | | |

**Total estimated sessions:** 10-14 (including 2 re-audits)
**Target quality score after completion:** 8.5/10+

After each phase that modifies code (Phases 2-7), refresh the graph and record the orphan count:
```bash
python scripts/update_dependency_graph_full.py
python -c "import json; d=json.load(open('docs/cleanup/dependency_graph.json')); print(f'Orphans: {sum(1 for n in d[\"nodes\"] if n[\"status\"]==\"orphan\")}/{len(d[\"nodes\"])}')"
```

---

## What This Roadmap Does NOT Cover

- **New features** — this is cleanup only. Features come after.
- **Billing/payments** — intentionally deferred per product decision.
- **Docker/deployment** — infrastructure work, separate planning needed.
- **Performance optimization** — no load testing or query tuning included.
- **Full SaaS readiness** — this gets code quality to 8/10+. SaaS features (billing, onboarding, usage metering) are a separate roadmap.

---

## Re-Audit Triggers

**Mid-point (after Phases 1-4):**
```
Read handovers/Code_quality_prompt.md and execute the audit.
```
Expected: 6.6/10 -> 7.5/10+. If below 7.0, stop and reassess before continuing to Phase 5.

**Final (after all 7 phases):**
```
Read handovers/Code_quality_prompt.md and execute the audit.
```
Expected: 8.5/10+ (exceeding 0700 baseline).

**Graph comparison:** At each re-audit, compare the refreshed graph against the baseline snapshot in this document (948 orphans, 2,530 edges, 11 critical nodes). Improvements should show: fewer orphans (dead code removed), same or fewer edges (coupling reduced), same critical node count (core architecture stable).
