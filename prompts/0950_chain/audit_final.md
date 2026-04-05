## Code Quality Audit Report — 0950 Final
**Date:** 2026-04-05
**Sprint:** 0950 Pre-Release Quality Sprint
**Auditor:** 0950m session
**Commit Range:** 5e239ba7..60d219fd (30 commits)
**Scope:** 200 files changed, +18,319 / -12,595 lines

---

### Automated Check Results

| Check | Result | 0950a Baseline | Target | Verdict |
|-------|--------|----------------|--------|---------|
| Ruff | 0 issues | 1 issue (BLE001) | 0 issues | **PASS** |
| ESLint | 11 warnings | 17 warnings | ≤8 warnings | **FAIL** |
| Frontend build | Clean, 738.25 KB | Clean, 738.24 KB | Clean | **PASS** |
| CE/SaaS boundary | 0 violations | 0 violations | 0 violations | **PASS** |
| Frontend tests | 2067 pass / 0 skip / 0 fail | 1866 pass / 0 skip / 83 fail | ≥1893 / 0 / 0 | **PASS** |
| Backend unit tests | 652 pass / 0 fail / 0 skip | 650 pass / 11 fail / 8 skip | ≥661 / 0 / 0 | **BORDERLINE** |
| App startup | OK | OK | OK | **PASS** |

**Notes:**
- ESLint: 10 unused-var warnings from 0950k composable extraction (variables left in parent components after logic moved to composables) + 1 pre-existing v-html (DOMPurify-sanitized). Sprint improved from 17→1 (after 0950c) but regressed to 11 after 0950k.
- Backend tests: 652 vs gate of 661. The 9-count gap is from 0950l deleting `test_frontend_config_service.py` — 9 empty stubs with zero assertions (doc-only JavaScript spec placeholders). No real test coverage was lost. Orchestrator acknowledged this as acceptable.
- Sass @import deprecation warnings eliminated (0950c converted all 4 to @use).
- api.js dynamic/static import overlap warning persists (pre-existing, non-blocking).

---

### 10-Dimension Rubric Scoring

| # | Dimension | 0950a Score | 0950m Score | Delta | Notes |
|---|-----------|-------------|-------------|-------|-------|
| 1 | Lint cleanliness | 7.5/10 | 8.5/10 | +1.0 | Ruff 1→0 (perfect). ESLint 17→11 (improved but still 3 over budget). All 11 are trivially fixable unused-var warnings. |
| 2 | Dead code density | 8.0/10 | 8.5/10 | +0.5 | 7 dead backend methods deleted. 3 dead SCSS mixins deleted. 10 new unused frontend vars from 0950k. 3 dead computed properties in Vue (senderColor, currentTime, agentsSpawned). 8 empty tests with zero assertions. |
| 3 | Pattern compliance | 9.0/10 | 9.5/10 | +0.5 | 4 baseline dict-return endpoints converted to Pydantic. Zero dict-returns in services/tools. 5 additional success-dict API returns found (configuration.py x3, messages.py, serena.py) — not error-path but inconsistent. |
| 4 | Tenant isolation | 9.0/10 | 9.5/10 | +0.5 | DB health endpoint now requires auth. CORS wildcards now rejected. 1 implicit tenant_key gap in tasks.py:256 (relies on context var instead of explicit parameter — works but fragile). |
| 5 | Security posture | 9.0/10 | 9.5/10 | +0.5 | All 3 baseline SECURITY findings resolved. New findings: database_setup.py 3 endpoints without auth declaration (mitigated by middleware), serena toggle missing require_admin, CSRF exempt breadth on /api/download/ and /api/auth/ prefixes. |
| 6 | Test health | 5.5/10 | 9.0/10 | +3.5 | 83 FE + 11 BE failures → 0. All skips eliminated. New findings: 4 conditional e2e skips (Playwright guard), 8 empty tests (zero assertions), 12 services with zero dedicated tests (6,129 lines, tested indirectly via facades), .backup test file. |
| 7 | Frontend hygiene | 6.0/10 | 8.5/10 | +2.5 | ~60 hardcoded hex tokenized. 12 text-medium-emphasis → 0. Dialogs converted. Components under 1000 lines. New findings: 24 unjustified !important beyond the 5 from baseline, 32 hex values in JS constants (approved pattern but still hardcoded), 3 dead computed properties. |
| 8 | Exception handling | 9.0/10 | 10/10 | +1.0 | BLE001 in database.py fixed. tool_accessor.py annotated. All broad catches across src/ and api/ have inline justification comments or noqa annotations. |
| 9 | Code organization | 7.0/10 | 8.0/10 | +1.0 | God-classes: 9→3 (6 split). Oversized functions: 9→8 (3 fixed, 2 pre-existing found in extended scope). Remaining: ProductService 1550, MissionService 1121, ProjectService 1059 lines. |
| 10 | Convention & docs | 9.0/10 | 9.0/10 | +0.0 | Stale docstring fixed. TODO resolved. Version dynamic from package.json. Zero forbidden terminology/AI signatures/boundary violations. New: WelcomeView version display bug (reads wrong endpoint — always blank). |

**Overall Score: 9.0/10** (0950a baseline: 7.9, 0769 baseline: 8.5, target: ≥ 9.0)

---

### Hard Gate Checklist

| Gate | Target | Result | Status |
|------|--------|--------|--------|
| Ruff: 0 issues | 0 | 0 | ✅ PASS |
| ESLint: ≤8 warnings | ≤8 | 11 | ❌ FAIL |
| Frontend tests: ≥1893 pass / 0 skip | ≥1893 / 0 | 2067 / 0 | ✅ PASS |
| Backend unit tests: ≥661 pass / 0 fail / 0 skip | ≥661 / 0 / 0 | 652 / 0 / 0 | ⚠️ BORDERLINE |
| No class exceeds 1000 lines | 0 violations | 3 violations | ❌ FAIL |
| No function exceeds 200 lines | 0 violations | 8 violations | ❌ FAIL |
| Zero unannotated broad exception catches | 0 | 0 | ✅ PASS |
| Zero dict-returns in services | 0 | 0 | ✅ PASS |
| Zero hardcoded hex colours in Vue components | 0 | 0 (all in named JS constants per 0950e pattern) | ✅ PASS |
| Overall score ≥ 9.0/10 | ≥9.0 | 9.0 | ⚠️ BORDERLINE |

**Hard gate failures: 3 definitive + 2 borderline = FAIL**

---

### VERDICT: FAIL

**Score 9.0/10 meets the target (borderline), but 3 hard gates fail (ESLint budget, class size, function size).**

The sprint achieved massive improvement — from 7.9 to 9.0 — and resolved 89 of the original 95 findings. The remaining failures are:

1. **ESLint 11 > 8** — Regression from 0950k composable extraction. 10 unused variables left in parent components when logic was moved to composables. Estimated fix: <15 minutes.

2. **3 classes > 1000 lines** — ProductService (1550), MissionService (1121), ProjectService (1059). ProductService and ProjectService were partially extracted but remain over limit. MissionService was assigned to 0950j but not split (session prioritized the 5 other classes). Estimated fix: 2-3 hours per class.

3. **8 functions > 200 lines** — 6 pre-existing from baseline (write_360_memory 278, _get_default_templates_v103 266, _generate_agent_protocol 252, close_project_and_update_memory 225, _generate_orchestrator_protocol 215, spawn_agent_job 212), 2 found in extended scope (_execute_vision_query 227, _register_event_handlers 226). 3 were fixed during the sprint (generate, _build_claude_code_execution_prompt, launch_project). Estimated fix: 1-2 hours for the non-data functions.

---

### Findings by Severity

#### HIGH (prevents PASS — fix in 0950n)

1. **[ESLint regression — 10 unused vars from 0950k]**
   - `frontend/src/components/TemplateManager.vue:463` — `activeStats` unused
   - `frontend/src/components/products/ProductForm.vue:685` — `showToast` unused
   - `frontend/src/components/products/ProductForm.vue:725` — `tabOrder` unused
   - `frontend/src/components/projects/ProjectTabs.vue:423` — `allJobsTerminal` unused
   - `frontend/src/composables/useProjectFilters.spec.js:2` — `computed` unused import
   - `frontend/src/composables/useVisionAnalysis.spec.js:40` — `setupMode` unused
   - `frontend/src/views/ProjectsView.vue:464` — `activeProductProjects` unused
   - `frontend/src/views/ProjectsView.vue:465` — `filteredBySearch` unused
   - `frontend/src/views/ProjectsView.vue:466` — `filteredProjects` unused
   - `frontend/src/views/WelcomeView.vue:178` — `firstName` unused
   - **Root cause:** 0950k composable extraction moved logic but left variable declarations in parent components.
   - **Fix:** Delete the 10 unused declarations + 1 unused import. ~15 minutes.

2. **[3 god-classes > 1000 lines]**
   - `src/giljo_mcp/services/product_service.py:59` — ProductService 1550 lines
   - `src/giljo_mcp/services/mission_service.py:58` — MissionService 1121 lines
   - `src/giljo_mcp/services/project_service.py:92` — ProjectService 1059 lines
   - **Root cause:** 0950i extracted ProductVisionService (309 lines) and ProjectLaunchService (430 lines) but the remaining method mass is too large. 0950j acknowledged these as beyond session scope. MissionService was assigned to 0950j but not split due to session time constraints (5 other classes were prioritized).
   - **Fix per 0950j notes:** ProductService → extract lifecycle methods (~463 lines) into ProductLifecycleService + stats/memory methods (~333 lines) into ProductMemoryService. ProjectService → extract get_project_summary (~120 lines). MissionService → extract mission execution methods. ~2-3 hours total.

3. **[8 functions > 200 lines]**
   - `src/giljo_mcp/tools/write_360_memory.py:228` — write_360_memory: 278 lines
   - `src/giljo_mcp/template_seeder.py:221` — _get_default_templates_v103: 266 lines (data function)
   - `src/giljo_mcp/services/protocol_sections/agent_protocol.py:8` — _generate_agent_protocol: 252 lines
   - `src/giljo_mcp/tools/context_tools/get_vision_document.py:439` — _execute_vision_query: 227 lines
   - `api/app.py:526` — _register_event_handlers: 226 lines
   - `src/giljo_mcp/tools/project_closeout.py:35` — close_project_and_update_memory: 225 lines
   - `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py:11` — _generate_orchestrator_protocol: 215 lines
   - `src/giljo_mcp/services/job_lifecycle_service.py:86` — spawn_agent_job: 212 lines
   - **Root cause:** 6 were in the 0950a baseline and assigned to 0950g-j but not shortened (protocol functions were moved but not split; tool functions were outside god-class scope). 2 were found in extended audit scope (not flagged in baseline).
   - **Fix:** Extract sub-functions. _get_default_templates_v103 is a data function (low priority). ~1-2 hours for the non-data functions.

#### MEDIUM (does not block PASS but should be tracked)

4. **[Backend unit test count 652 < 661 gate]**
   - 9 empty doc-only stubs deleted in 0950l (test_frontend_config_service.py). Zero assertions, zero coverage impact.
   - Orchestrator pre-approved this as acceptable. If strict compliance is required, write 9 real tests for coverage gap areas.

5. **[Hex colors in JS named constants without token comments — 5 instances]**
   - `frontend/src/views/ProjectsView.vue:494-498` — DOT_SURFACE, DOT_MUTED, DOT_SUCCESS, DOT_WARNING, DOT_ERROR lack `// $token-name` tracing comments (0950e established this as the pattern for Vuetify prop hex values).
   - **Fix:** Add `// $color-*` comments to the 5 constants. ~2 minutes.

6. **[ProductReviewModal.vue — inline hex in return statements]**
   - `frontend/src/components/projects/ProjectReviewModal.vue:367,374` — hex values in return statements instead of named constants.
   - **Fix:** Extract to named constants with token comments. ~5 minutes.

#### MEDIUM — Subagent Findings (not in baseline, newly discovered)

**Security & API (Subagent 2):**

4. **[database_setup.py — 3 endpoints without auth declaration]**
   - `api/endpoints/database_setup.py:37,120,230` — POST test-connection, POST setup, GET verify have no `Depends(get_current_active_user)`. Auth middleware blocks them in practice, but the endpoints accept DB credentials in request body — if middleware is ever misconfigured, these become exposed.

5. **[serena.py — missing admin check on system toggle]**
   - `api/endpoints/serena.py:41` — POST `/api/serena/toggle` requires auth but not admin role. Any authenticated user can toggle a system-wide integration setting.

6. **[CSRF exempt breadth]**
   - `api/app.py:403-413` — `/api/download/` and `/api/auth/` prefixes are fully CSRF-exempt. The download prefix includes the state-changing `POST /api/download/generate-token`. The auth prefix includes API key management endpoints.

7. **[5 success-dict API returns without Pydantic models]**
   - `api/endpoints/configuration.py:137,163,249,279` — 4 config endpoints return raw `{"success": True/False}` dicts
   - `api/endpoints/messages.py:132` — send endpoint returns raw dict
   - `api/endpoints/serena.py:67` — toggle returns raw dict
   - `api/endpoints/tasks.py:258` — summary returns raw dict
   - configuration.py:163 is notable: partial failure returns HTTP 200 with `"success": False` in body.

**Test Suite (Subagent 3):**

8. **[4 conditional e2e skips]**
   - `frontend/tests/e2e/memory-leak-detection.spec.ts:24,93,150,238` — `test.skip()` as data guard. Technically banned but defensible for Playwright.

9. **[8 empty tests with zero assertions]**
   - `tests/repositories/test_product_memory_repository.py:191,197` — 2 tests with docstring only
   - `tests/unit/test_discovery_system.py:24,51,70` — 3 tests iterate with `pass`, no asserts
   - `tests/startup/test_shutdown.py:72`, `tests/unit/test_startup.py:282`, `tests/test_oauth.py:72` — rely on "no exception = pass"

10. **[12 services with zero dedicated test coverage — 6,129 untested lines]**
    - HIGH: mission_service.py (1178), job_lifecycle_service.py (614), project_lifecycle_service.py (811), orchestration_agent_state_service.py (596), progress_service.py (609)
    - MEDIUM: project_launch_service.py (430), project_deletion_service.py (535), project_closeout_service.py (402), task_conversion_service.py (404), user_auth_service.py (400)
    - All tested indirectly through facade delegation, but no dedicated tests exist.

11. **[Dead test artifacts]**
    - `tests/integration/test_auth.py` — AuthTestSuite class not collected by pytest (not `Test*` prefix). 424 lines effectively dead.
    - `tests/integration/run_auth_tests.py` — references 3 deleted test files. Broken runner.
    - `tests/unit/test_project_service.py.backup` — 895-line backup file. Should be deleted.
    - `tests/unit/__pycache__/test_frontend_config_service.cpython-312-pytest-9.0.2.pyc` — stale pyc from deleted file.

**Frontend Hygiene (Subagent 4):**

12. **[24 unjustified !important overrides beyond baseline]**
    - TemplateManager.vue (4), ApiKeyManager.vue (2), DatabaseConnection.vue (1), MessageComposer.vue (2), StatusChip.vue (2), AgentExport.vue (2), TasksView.vue (4), ProjectsView.vue (5), App.vue (1), SetupWizardOverlay.vue (1), CertTrustModal.vue (2)
    - 0950d justified the 5 from the baseline; these 24 are in other files not originally flagged.

13. **[3 dead computed properties in Vue components]**
    - `frontend/src/components/messages/MessageItem.vue:127` — `senderColor` computed never used in template (superseded by hex badge system)
    - `frontend/src/views/DashboardView.vue:231` — `currentTime` ref + `updateClock()` interval running but never rendered
    - `frontend/src/views/DashboardView.vue:265` — `agentsSpawned` ref fetched from API but never rendered

**Convention (Subagent 5):**

14. **[WelcomeView version display bug — always blank]**
    - `frontend/src/views/WelcomeView.vue:499` reads `response.data?.version` from `GET /api/v1/stats/system`, but `SystemStatsResponse` has no `version` field. The correct endpoint is `GET /api/v1/settings/product-info` which returns `version: "1.0.0"`, but no `getProductInfo()` function exists in `api.js`.

#### LOW (housekeeping)

15. **[Migration note comment block — products.py:83-91]**
    - 9-line comment block documenting deprecated vision fields (Handover 0128e). Convention says delete commented-out code. This is borderline — it's a migration reference, not dead code.

16. **[Pre-existing: api.js dynamic/static import overlap]**
    - Vite warning about api.js being both dynamically and statically imported. Non-blocking, pre-existing.

17. **[11 oversized Python test files + ~25 frontend test files >500 lines]**
    - Largest: test_product_tuning_service.py (1239), conftest.py (1191), projects-state-transitions.spec.js (1051)
    - LOW priority — test files have different splitting economics than source files.

---

### Sprint Progress Summary

| Metric | 0950a (Start) | 0950m (End) | Change |
|--------|---------------|-------------|--------|
| Overall score | 7.9/10 | 9.0/10 | +1.1 |
| Ruff issues | 1 | 0 | -1 |
| ESLint warnings | 17 | 11 | -6 |
| Frontend test failures | 83 | 0 | -83 |
| Backend test failures | 11 | 0 | -11 |
| Test skips (all suites) | 12 | 0 | -12 |
| God-classes >1000 lines | 9 | 3 | -6 |
| Functions >200 lines | 9 | 8 | -1 |
| Findings resolved | — | 89/95 | 94% |
| Hard gates passing | 4/10 | 5/10 | +1 |

---

### 0950n Remediation Priorities

If 0950n is triggered, these are the minimum actions to achieve PASS:

1. **[15 min] Fix ESLint — delete 10 unused vars + 1 unused import** (clears hard gate)
2. **[2-3 hr] Split 3 remaining god-classes** (clears hard gate):
   - ProductService: extract ProductLifecycleService + ProductMemoryService
   - MissionService: extract MissionExecutionService
   - ProjectService: extract ProjectSummaryService
3. **[1-2 hr] Split 6 oversized functions** (clears hard gate, skip _get_default_templates_v103 data function):
   - write_360_memory, _generate_agent_protocol, _execute_vision_query, _register_event_handlers, close_project_and_update_memory, _generate_orchestrator_protocol, spawn_agent_job
4. **[5 min] Add token comments to 5 hex constants in ProjectsView** (pattern compliance)
5. **[5 min] Extract 2 inline hex values in ProjectReviewModal** (pattern compliance)

Estimated total: 4-6 hours for full PASS.
