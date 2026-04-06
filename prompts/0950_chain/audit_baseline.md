## Code Quality Audit — 0950 Baseline
**Date:** 2026-04-05
**Commit:** 5e239ba7263f4c00e65280cd8334f69670612dd4 docs(0950): Pre-Release Quality Sprint — 14 handovers + chain log
**Auditor:** 0950a

---

### Automated Check Results

| Check | Result | Baseline | Verdict |
|-------|--------|----------|---------|
| Ruff | 1 issue (BLE001 blind exception) | 0 issues | **FAIL** |
| ESLint | 17 warnings | 6 warnings (budget 8) | **FAIL** |
| Frontend build | Clean, main chunk 738.24 KB | Clean, ~736 KB | **PASS** |
| CE/SaaS boundary | 0 violations | 0 violations | **PASS** |
| Frontend tests | 1866 pass / 0 skip / 83 fail (20 files) | 1893+ / 0 / 0 | **FAIL** |
| Backend unit tests | 650 pass / 11 fail | 661+ / 0 | **FAIL** |
| Startup import | OK | OK | **PASS** |

**Notes:**
- Ruff 0.15.9 (freshly installed) also reports 11 EXE001/EXE002 file-permission issues that weren't flagged in the baseline ruff version. These are low-severity filesystem permission artifacts, not code quality issues. A `[tool.ruff]` section should be added to `pyproject.toml` to configure consistent rules.
- Frontend build produces 4 Sass `@import` deprecation warnings (Dart Sass 3.0 migration needed) — non-blocking.
- Frontend build: `api.js` dynamic/static import overlap warning (non-blocking, pre-existing).

---

### 10-Dimension Rubric Scores

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | Lint cleanliness | 7.5/10 | 1 ruff BLE001, 17 ESLint warnings (11 over budget), 11 EXE permission issues |
| 2 | Dead code density | 8.0/10 | 7 dead backend methods, 15 unused frontend vars/imports, 3 dead SCSS mixins |
| 3 | Pattern compliance | 9.0/10 | 0 dict-return regressions in services, 4 dict returns in API endpoints, 1 stale status CheckConstraint mismatch |
| 4 | Tenant isolation | 9.0/10 | 2 minor gaps in auth.py (refresh/user-count queries), 1 unauthenticated health endpoint |
| 5 | Security posture | 9.0/10 | CORS wildcard not hard-rejected, 1 unauthenticated DB health endpoint, 2 manual auth patterns in downloads.py |
| 6 | Test health | 5.5/10 | 83 frontend failures, 11 backend failures, 8 backend skips, 4 e2e skips, 6 oversized test files |
| 7 | Frontend hygiene | 6.0/10 | ~30 hardcoded hex colors, 12 text-medium-emphasis usages, ~12 dialog anatomy violations, ~5 !important without justification |
| 8 | Exception handling | 9.0/10 | 1 unannotated broad catch (tool_accessor.py:574), BLE001 in database.py:93 |
| 9 | Code organization | 7.0/10 | 9 god-classes >1000 lines, 9 functions >200 lines |
| 10 | Convention & docs | 9.0/10 | 1 stale docstring (orchestration_service.py:1407), 1 TODO (lifecycle.py:68), version hardcoded in AppBar |

**Overall Score: 7.9/10** (baseline: 8.5, target: 9.0)

**Score dropped from 8.5 → 7.9** primarily due to:
- Test health collapse (94 total test failures across frontend + backend)
- ESLint warning regression (6 → 17)
- Frontend hygiene debt accumulated across recent UI handovers

---

### Findings by Severity

#### SECURITY

1. **[api/endpoints/configuration.py:691]** `GET /api/v1/config/health/database` has no authentication — exposes database connectivity status to unauthenticated callers. Information disclosure risk. → **0950b**

2. **[src/giljo_mcp/models/agent_identity.py:302]** `AgentExecution` CheckConstraint lists `('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned')` but `orchestration_service.py:1253` writes `idle` and `sleeping` statuses. Either the constraint is not enforced (migration gap) or writes will fail in production. → **0950b**

3. **[api/app.py:298-301]** CORS wildcard entries in config.yaml are warned but not rejected. A misconfigured `config.yaml` with `["*"]` would be silently applied. → **0950b**

#### HIGH

4. **[Frontend tests: 83 failures across 20 files]** Root causes: (a) Integration card rewrites in 47dc1fcd broke 3 integration card test files + setup wizard tests, (b) Dialog anatomy changes broke modal/layout tests, (c) Component API changes (StatusBadge, UserManager, ProductDeleteDialog, etc.) have stale test assertions. → **0950l**

5. **[Backend tests: 11 failures in test_project_service_helpers.py]** `_build_project_data` now uses Pydantic `ProjectData` model with `auto_checkin_enabled` and `auto_checkin_interval` fields, but test mocks pass `Mock` objects that fail Pydantic type validation. → **0950l**

6. **[ESLint: 17 warnings, budget 8]** 15 unused variables/imports across 8 components, 2 console.log statements. Regression from baseline of 6. → **0950c**

7. **[src/giljo_mcp/database.py:93]** `except (ImportError, Exception):` — `Exception` subsumes `ImportError`, making the tuple redundant. Should be `except Exception:` with inline justification comment, or narrowed to specific exceptions. → **0950b**

8. **[src/giljo_mcp/tools/tool_accessor.py:574]** `except Exception:` without required `# Broad catch:` annotation. → **0950b**

#### MEDIUM

**Dead Code — Backend (7 methods):**

9. **[src/giljo_mcp/tenant.py:193]** `TenantManager.inherit_tenant_key` — zero callers. → **0950f**
10. **[src/giljo_mcp/database.py:287]** `DatabaseManager.apply_tenant_filter` — dead wrapper, only TenantManager version is called. → **0950f**
11. **[src/giljo_mcp/database.py:301]** `DatabaseManager.ensure_tenant_isolation` — dead wrapper. → **0950f**
12. **[src/giljo_mcp/models/config.py:438]** `SetupState.mark_completed` — flagged in 0740, still present. → **0950f**
13. **[src/giljo_mcp/models/config.py:466]** `SetupState.add_validation_warning` — zero callers. → **0950f**
14. **[src/giljo_mcp/models/config.py:481]** `SetupState.clear_validation_failures` — flagged in 0740, still present. → **0950f**
15. **[src/giljo_mcp/models/products.py:624]** `Product.update_content_hash` — flagged in 0740, still present. → **0950f**

**Dead Code — Frontend (additional to ESLint-flagged):**

16. **[frontend/src/styles/agent-colors.scss:99]** `@mixin agent-card-border` — never `@include`'d. → **0950e**
17. **[frontend/src/styles/agent-colors.scss:124]** `@mixin chat-head-badge` — never `@include`'d. → **0950e**
18. **[frontend/src/styles/agent-colors.scss:129]** `@mixin status-badge` — never `@include`'d. → **0950e**

**Hardcoded Hex Colors (~30 instances across ~12 files):**

19. **[frontend/src/components/dashboard/RecentProjectsList.vue:138-143]** 7 hardcoded hex values in status chip styles. → **0950e**
20. **[frontend/src/components/StatusBadge.vue:25-40]** 5 hardcoded hex values in STATUS_CONFIG. → **0950e**
21. **[frontend/src/components/common/RoleBadge.vue:27]** `#8895a8` hardcoded — should use `--text-muted`. → **0950e**
22. **[frontend/src/components/messages/MessagePanel.vue:330,345,350]** Agent palette colors hardcoded. → **0950e**
23. **[frontend/src/components/navigation/NavigationDrawer.vue:569,633,642,651,661]** 5 hardcoded nav colors. → **0950e**
24. **[frontend/src/views/WelcomeView.vue:335-442]** Agent palette hex in JS card defs. → **0950e**
25. **[frontend/src/components/setup/SetupStep2Connect.vue:717,722]** Error/success colors hardcoded. → **0950e**
26. **[frontend/src/utils/statusConfig.js:12-84]** Full status color map with bare hex literals. → **0950e**
27. **[frontend/src/views/SystemSettings.vue:352,356,362]** 3 hardcoded hex values. → **0950e**
28. **[frontend/src/views/UserSettings.vue:596,600,606]** Same 3 hex values mirrored from SystemSettings. → **0950e**
29. **[frontend/src/components/AiToolConfigWizard.vue:369]** `#ffc300` — should use brand yellow token. → **0950e**
30. **[frontend/src/components/messages/BroadcastPanel.vue:517]** `#ffc300` — should use brand yellow token. → **0950e**

**text-medium-emphasis violations (12 instances):**

31. **[frontend/src/components/dashboard/DonutChart.vue:3]** → **0950d**
32. **[frontend/src/components/projects/MessageDetailView.vue:5,45]** → **0950d**
33. **[frontend/src/components/navigation/NotificationDropdown.vue:126,147]** → **0950d**
34. **[frontend/src/views/TasksView.vue:96,232,421]** → **0950d**
35. **[frontend/src/views/ProjectsView.vue:270,321,593,628]** → **0950d**

**Dialog anatomy violations (~12 components using v-card-title/v-card-actions in dialogs):**

36. **[frontend/src/components/dashboard/RecentMemoriesList.vue:33,56]** → **0950d**
37. **[frontend/src/components/projects/ProjectTabs.vue:217,237]** → **0950d**
38. **[frontend/src/components/products/ProductForm.vue:4,678]** → **0950d**
39. **[frontend/src/components/ForgotPasswordPin.vue:12,224]** → **0950d**
40. **[frontend/src/components/TemplateManager.vue:228-417]** 3 dialogs. → **0950d**
41. **[frontend/src/components/AiToolConfigWizard.vue:11]** → **0950d**
42. **[frontend/src/components/ConnectionStatus.vue:29,185]** → **0950d**
43. **[frontend/src/components/UserManager.vue:125-306]** 4 dialogs. → **0950d**
44. **[frontend/src/views/TasksView.vue:322,384]** → **0950d**
45. **[frontend/src/views/ProjectsView.vue:283-675]** 3 dialogs. → **0950d**
46. **[frontend/src/views/ProjectLaunchView.vue:40,88]** → **0950d**
47. **[frontend/src/views/OrganizationSettings.vue:121,126]** → **0950d**

**!important without justification (5 instances):**

48. **[frontend/src/components/products/ProductDetailsDialog.vue:812,821]** → **0950d**
49. **[frontend/src/components/orchestration/AgentTableView.vue:279]** → **0950d**
50. **[frontend/src/components/navigation/NavigationDrawer.vue:483,494]** → **0950d**
51. **[frontend/src/views/ProductsView.vue:1155,1198-1199]** → **0950d**

**Oversized classes (>1000 lines, 9 total):**

52. **[src/giljo_mcp/thin_prompt_generator.py:292]** `ThinClientPromptGenerator` — 1677 lines. → **0950g**
53. **[src/giljo_mcp/services/product_service.py:63]** `ProductService` — 1744 lines. → **0950i**
54. **[src/giljo_mcp/services/message_service.py:60]** `MessageService` — 1731 lines. → **0950h**
55. **[src/giljo_mcp/services/orchestration_service.py:72]** `OrchestrationService` — 1498 lines. → **0950j**
56. **[src/giljo_mcp/services/project_service.py:92]** `ProjectService` — 1299 lines. → **0950i**
57. **[src/giljo_mcp/services/mission_service.py:58]** `MissionService` — 1121 lines. → **0950j**
58. **[src/giljo_mcp/repositories/statistics_repository.py:24]** `StatisticsRepository` — 1086 lines. → **0950j**
59. **[src/giljo_mcp/services/task_service.py:56]** `TaskService` — 1043 lines. → **0950j**
60. **[src/giljo_mcp/services/user_service.py:46]** `UserService` — 1045 lines. → **0950j**

**Oversized functions (>200 lines, 9 total):**

61. **[src/giljo_mcp/thin_prompt_generator.py:333]** `generate` — 271 lines. → **0950g**
62. **[src/giljo_mcp/thin_prompt_generator.py:1264]** `_build_claude_code_execution_prompt` — 305 lines. → **0950g**
63. **[src/giljo_mcp/services/protocol_builder.py:165]** `_generate_orchestrator_protocol` — 215 lines. → **0950j**
64. **[src/giljo_mcp/services/protocol_builder.py:382]** `_generate_agent_protocol` — 253 lines. → **0950j**
65. **[src/giljo_mcp/services/project_service.py:1069]** `launch_project` — 220 lines. → **0950i**
66. **[src/giljo_mcp/services/job_lifecycle_service.py:86]** `spawn_agent_job` — 212 lines. → **0950j**
67. **[src/giljo_mcp/tools/write_360_memory.py:228]** `write_360_memory` — 278 lines. → **0950j**
68. **[src/giljo_mcp/tools/project_closeout.py:35]** `close_project_and_update_memory` — 225 lines. → **0950j**
69. **[src/giljo_mcp/template_seeder.py:221]** `_get_default_templates_v103` — 266 lines (data function, low priority). → **0950f**

**API dict returns (4 instances):**

70. **[api/endpoints/products/lifecycle.py:185]** `purge_product` returns raw dict. → **0950b**
71. **[api/endpoints/configuration.py:175]** `reload_configuration` returns raw dict. → **0950b**
72. **[api/endpoints/configuration.py:707]** `test_database_connection` returns raw dict. → **0950b**
73. **[api/endpoints/messages.py:272]** `complete_message` returns raw dict (response_model declared but not used directly). → **0950b**

**Stale docstring:**

74. **[src/giljo_mcp/services/orchestration_service.py:1407]** Docstring lists `active`, `completed`, `failed` as valid statuses — these are stale. → **0950f**

**Test skips (8 backend, 4 e2e):**

75. **[tests/unit/test_frontend_config_service.py:148]** `@pytest.mark.skip(reason="JavaScript tests - documentation only")` — the file should be deleted or converted. → **0950l**
76. **[tests/api/test_setup_wizard_endpoints.py:106-225]** 7 tests skip with "No authenticated session available" — need proper test auth fixture. → **0950l**
77. **[tests/e2e/memory-leak-detection.spec.ts:24,93,150,238]** 4 e2e tests skip. → **0950l**

#### LOW

**Oversized test files (>500 lines):**

78. **[tests/services/test_product_tuning_service.py]** 1239 lines. → **0950l**
79. **[tests/services/conftest.py]** 1191 lines. → **0950l**
80. **[tests/services/test_message_counter_atomic_self_healing.py]** 769 lines. → **0950l**
81. **[tests/unit/test_closeout_readiness_gate.py]** 731 lines. → **0950l**
82. **[tests/services/test_0830_staging_to_implementation_harmonization.py]** 697 lines. → **0950l**
83. **[tests/unit/test_0814_template_manager_ui.py]** 659 lines. → **0950l**
84. **[frontend/tests/projects-state-transitions.spec.js]** 1051 lines. → **0950l**
85. **[frontend/tests/stores/websocket.spec.js]** 982 lines. → **0950l**

**Sass @import deprecation (4 files):**

86. **[frontend/src/components/AgentExport.vue]** `@import '../styles/intg-card'`. → **0950c**
87. **[frontend/src/components/settings/integrations/McpIntegrationCard.vue]** `@import '../../../styles/intg-card'`. → **0950c**
88. **[frontend/src/components/settings/integrations/SerenaIntegrationCard.vue]** `@import '../../../styles/intg-card'`. → **0950c**
89. **[frontend/src/components/settings/integrations/GitIntegrationCard.vue]** `@import '../../../styles/intg-card'`. → **0950c**

**File permission issues (11 EXE ruff findings):**

90. **[api/__init__.py, api/broker/in_memory.py, api/endpoints/__init__.py, api/endpoints/projects/__init__.py, api/endpoints/templates/__init__.py, api/schemas/__init__.py, src/giljo_mcp/auth/__init__.py, src/giljo_mcp/repositories/__init__.py, src/giljo_mcp/setup/__init__.py, src/giljo_mcp/template_validation.py]** Executable bit set but no shebang. → **0950b**
91. **[api/run_api.py]** Shebang present but file not executable. → **0950b**

**TODO comment:**

92. **[api/endpoints/products/lifecycle.py:68]** `# TODO: Query for deactivated projects when ProjectService integration is complete` — `deactivated_projects` hardcoded to `[]`. → **0950b**

**Version maintenance risk:**

93. **[frontend/src/components/navigation/AppBar.vue:134]** Version `Beta 1.0.0` hardcoded in template — must be manually updated on version bumps. → **0950c**

**Tombstone comments (borderline):**

94. **[src/giljo_mcp/config_manager.py:547-551]** Two tombstone comments for removed methods. Convention says delete commented-out code. → **0950f**

**Auth pattern inconsistency:**

95. **[api/endpoints/downloads.py:455-575]** `bootstrap-prompt` and `generate-token` endpoints call `get_current_user` manually instead of using `Depends(get_current_active_user)`. → **0950b**

---

### Prioritized Action List

**SECURITY (fix immediately — 0950b):**
1. [SECURITY] `api/endpoints/configuration.py:691` — Add `Depends(get_current_active_user)` to DB health endpoint — <5 min
2. [SECURITY] `src/giljo_mcp/models/agent_identity.py:302` — Add `idle` and `sleeping` to AgentExecution CheckConstraint + migration — 15 min
3. [SECURITY] `api/app.py:298-301` — Reject or strip CORS wildcard entries instead of just warning — 10 min

**Quick wins (<5 min each — 0950b, 0950c):**
4. [HIGH] `src/giljo_mcp/database.py:93` — Change `except (ImportError, Exception)` to `except Exception:  # Broad catch: psutil may be unavailable` — 2 min
5. [HIGH] `src/giljo_mcp/tools/tool_accessor.py:574` — Add `# Broad catch:` annotation — 1 min
6. [HIGH] Remove 15 unused frontend vars/imports (ESLint warnings) — 15 min total → **0950c**
7. [MEDIUM] Delete 7 dead backend methods — 10 min total → **0950f**
8. [MEDIUM] Delete 3 dead SCSS mixins — 5 min → **0950e**
9. [LOW] Fix file permissions (chmod -x on 10 files, chmod +x on run_api.py) — 5 min → **0950b**
10. [LOW] Add `[tool.ruff]` config to pyproject.toml — 5 min → **0950b**

**Medium effort (15-30 min each — 0950d, 0950e):**
11. [MEDIUM] Replace 12 `text-medium-emphasis` usages with scoped CSS `color: var(--text-muted)` — 20 min → **0950d**
12. [MEDIUM] Convert ~12 dialog components from v-card-title/v-card-actions to dlg-header/dlg-footer — 30 min → **0950d**
13. [MEDIUM] Replace ~30 hardcoded hex colors with design tokens — 45 min → **0950e**
14. [MEDIUM] Fix 4 Sass @import → @use migrations — 10 min → **0950c**
15. [MEDIUM] Add !important justification comments or remove unnecessary !important — 15 min → **0950d**

**Test repairs (0950l):**
16. [HIGH] Fix 83 frontend test failures — root cause: commit 47dc1fcd rewrote integration cards + retired ProductIntroTour without updating tests. Affected: McpIntegrationCard.spec.js (34 tests), GitIntegrationCard.spec.js (31), SerenaIntegrationCard.spec.js (24), ProductIntroTour.spec.js (2, component deleted), plus collateral in UserSettings/DefaultLayout/StatusBadge/UserManager/setup wizard specs — 60-90 min → **0950l**
17. [HIGH] Fix 11 backend test failures — root cause: Handover 0904 added `auto_checkin_enabled` (bool) + `auto_checkin_interval` (int) to Project model; `mock_project` fixture in test_project_service_helpers.py:28-55 is missing these fields, so Mock objects fail Pydantic validation. Fix: add `project.auto_checkin_enabled = False` and `project.auto_checkin_interval = 60` to fixture — 5 min → **0950l**
18. [MEDIUM] Fix or delete 8 skipped backend tests (1 documentation-only, 7 need auth fixtures) — 30 min → **0950l**
19. [MEDIUM] Coverage gaps — zero dedicated tests for: `job_lifecycle_service.py` (614 lines, critical spawn path), `progress_service.py` (609 lines), `settings_service.py` (104 lines), `mission_service.py` (1178 lines) → **0950l**
20. [LOW] Split 8 oversized test files — requires planning → **0950l**

**Technical debt (requires planning — 0950g through 0950k):**
20. [MEDIUM] Split ThinClientPromptGenerator (1677 lines, 2 methods >200 lines) → **0950g**
21. [MEDIUM] Split MessageService (1731 lines) → **0950h**
22. [MEDIUM] Split ProductService (1744 lines) + ProjectService (1299 lines) → **0950i**
23. [MEDIUM] Split OrchestrationService (1498 lines) + 4 other god-classes → **0950j**
24. [MEDIUM] Frontend god-component splits → **0950k**
25. [MEDIUM] Update stale docstring in orchestration_service.py:1407 → **0950f**
26. [LOW] Remove TODO at lifecycle.py:68 or implement deactivated project query → **0950b**
27. [LOW] Extract hardcoded version from AppBar.vue to use package.json → **0950c**

---

### Session-to-Finding Assignment Summary

| Session | Finding Count | Effort |
|---------|--------------|--------|
| 0950b — Backend security + quick wins | 13 findings (#1-5, #9-10, #70-73, #90-92, #95) | Light-medium |
| 0950c — ESLint + commented code | 6 findings (#6, #86-89, #93) | Light |
| 0950d — Dialog convention + text-medium-emphasis | 22 findings (#31-51) | Medium |
| 0950e — Hex color sweep | 15 findings (#16-30) | Medium |
| 0950f — Stale docstrings + dead code | 10 findings (#9-15, #69, #74, #94) | Light |
| 0950g — Split ThinClientPromptGenerator | 3 findings (#52, #61-62) | Heavy |
| 0950h — Split MessageService | 1 finding (#54) | Heavy |
| 0950i — Split ProductService + ProjectService | 3 findings (#53, #56, #65) | Heavy |
| 0950j — Split OrchestrationService + remaining | 8 findings (#55, #57-60, #63-64, #66-68) | Heavy |
| 0950k — Frontend component splits | TBD from 0950a analysis | Heavy |
| 0950l — Test maintenance | 13 findings (#4-5 root causes, #75-85, coverage gaps) | Medium |
