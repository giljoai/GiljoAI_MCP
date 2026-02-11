# 0745 Audit Followup Roadmap

**Date**: 2026-02-10
**Series**: 0745a-f (6 handovers)
**Parent**: 0740 Comprehensive Post-Cleanup Audit
**Branch Strategy**: Each handover creates its own branch from `master`, merged individually
**Testing Policy**: Light -- run existing test suite to verify no regressions. No new test creation required.

---

## How to Use This Document

1. Work handovers **in order** (0745a first -- it's the database foundation)
2. After 0745a, handovers b-f can run in any order or parallel
3. Each section has a **kickoff prompt** -- copy-paste it into a new Claude Code session
4. Each handover references its 0740 findings doc for detailed file paths and line numbers
5. Mark handovers complete in the status table below as you go

---

## Status Tracker

| Handover | Theme | Status | Branch | Completed |
|----------|-------|--------|--------|-----------|
| 0745a | Database Migration & P0 Fixes | COMPLETED | feature/0745-security-data-integrity | 2026-02-10 |
| 0745b | Dependency Security & Cleanup | COMPLETED | feature/0745b-dependency-security | 2026-02-10 |
| 0745c | Backend Dead Code Removal | COMPLETED | feature/0745c-backend-dead-code | 2026-02-10 |
| 0745d | Frontend Cleanup | COMPLETED | feature/0745d-frontend-cleanup | 2026-02-10 |
| 0745e | Architecture Polish | COMPLETED | feature/0745e-architecture-polish | 2026-02-10 |
| 0745f | Documentation Sync | COMPLETED | feature/0745f-documentation-sync | 2026-02-10 |

---

## Dependency Graph

```
0745a (Database Migration) ─── MUST BE FIRST
  │
  ├── 0745b (Dependencies)     ── can run after a
  ├── 0745c (Backend Dead Code) ── can run after a
  ├── 0745d (Frontend Cleanup)  ── can run after a
  ├── 0745e (Architecture)      ── can run after a
  └── 0745f (Documentation)     ── can run after a (ideally last, to document final state)
```

**Recommended order**: a → b → c → d → e → f
**Why f last**: Documentation should reflect the final state after all code changes.

---

## 0745a: Database Migration & P0 Fixes

**Agent**: `database-expert`
**Estimated**: 2-3 hours
**Risk**: LOW (orphaned table has 0 rows, all dropped columns are unused)
**Findings Source**: `handovers/0740_findings_database.md`

### Scope

1. Drop orphaned `mcp_agent_jobs` table (0 rows, 35 columns, no model)
2. Fix `tasks.job_id` FK: drop `fk_task_job` → create new FK to `agent_jobs.job_id`
3. Drop 11 duplicate indexes (keep `idx_*`, drop `ix_*`)
4. Fix `products.product_memory` server_default (remove `sequential_history`)
5. Drop 6 legacy columns: `download_tokens.is_used`, `download_tokens.downloaded_at`, `agent_templates.template_content`, `template_archives.template_content`, `configurations.user_id`, `projects.context_budget`
6. Fix 3 index name mismatches (update model files to match DB names)
7. Fix admin/admin credential contradiction in `docs/README_FIRST.md` lines 296-303

### What NOT to Do

- Do NOT add CASCADE to FK constraints (P2 item, deferred)
- Do NOT touch composite index recommendations (optimization, not cleanup)

### Kickoff Prompt

```
Read these documents in order:
1. F:\GiljoAI_MCP\handovers\handover_instructions.md (handover format)
2. F:\GiljoAI_MCP\handovers\0745_AUDIT_FOLLOWUP_ROADMAP.md (the 0745a section)
3. F:\GiljoAI_MCP\handovers\0740_findings_database.md (full findings with SQL)

You are executing Handover 0745a: Database Migration & P0 Fixes.

SCOPE (do ALL of these):
1. Write a migration in install.py that:
   - Drops FK fk_task_job from tasks table
   - Creates new FK: tasks.job_id -> agent_jobs.job_id
   - Drops table mcp_agent_jobs (0 rows, safe)
   - Drops 11 duplicate ix_* indexes (listed in findings P1-1)
   - Drops 6 legacy columns (findings P1-2, P1-3, P1-5, P2-1)
   - Updates products.product_memory server_default to '{"github": {}, "context": {}}'::jsonb
2. Update 3 model files to fix index name mismatches (findings P1-4):
   - src/giljo_mcp/models/templates.py:115 -> idx_template_org_id
   - src/giljo_mcp/models/products.py:160 -> idx_product_org_id
   - src/giljo_mcp/models/tasks.py:101 -> idx_task_org_id
3. Fix admin/admin credential contradiction in docs/README_FIRST.md lines 296-303
   - Remove the "Default Admin Account" block
   - Replace with text explaining the /welcome -> /first-login flow

TESTING: Light. Run existing test suite to verify no regressions. No new tests needed.
TESTS THAT SHOULD STILL PASS: pytest tests/ -x --timeout=60
DATABASE: PostgreSQL password is 4010, user postgres, database giljo_mcp
MIGRATION APPROACH: Add idempotent SQL to the install.py migration section (check before dropping)

When done, update the original handover file with a completion summary (max 1000 words per handover_instructions.md).
```

---

## 0745b: Dependency Security & Cleanup

**Agent**: `version-manager`
**Estimated**: 3-4 hours
**Risk**: MEDIUM (MCP SDK upgrade needs serena compatibility check)
**Findings Source**: `handovers/0740_findings_dependencies.md`

### Scope

1. **Python security**: Upgrade MCP SDK from 1.12.3 to >=1.23.0 (CVE-2025-66416)
   - Validate serena-agent compatibility after upgrade
   - Update pin comment in requirements.txt
2. **npm security**: Run `npm audit fix` in frontend/ (fixes axios, js-yaml, glob, vite)
3. **npm critical**: Upgrade or remove happy-dom (critical RCE CVE)
4. **Remove unused npm production deps** (10 packages): @vue-flow/* (4), chart.js, d3, gsap, socket.io-client, vue-chartjs, vuedraggable
5. **Remove unused npm dev deps** (3 packages): @eslint/compat, tailwindcss, autoprefixer
6. **Remove unused Python dep**: pydantic-settings from requirements.txt
7. **Uninstall python-jose** (installed but not in requirements, zero imports)
8. **Consolidate duplicates**:
   - Remove `sass` from devDependencies (keep `sass-embedded`)
   - Consolidate test DOM: keep `jsdom`, remove `happy-dom`, update `vite.config.js`
   - Remove `.eslintrc.json` (keep `eslint.config.js` flat config)

### What NOT to Do

- Do NOT change version pinning strategy (>=  vs ~= discussion is deferred)
- Do NOT replace lodash-es with native debounce (P3, out of scope)
- Do NOT apply Python patch updates (fastapi, alembic, etc. -- low priority)

### Kickoff Prompt

```
Read these documents in order:
1. F:\GiljoAI_MCP\handovers\handover_instructions.md (handover format)
2. F:\GiljoAI_MCP\handovers\0745_AUDIT_FOLLOWUP_ROADMAP.md (the 0745b section)
3. F:\GiljoAI_MCP\handovers\0740_findings_dependencies.md (full findings)

You are executing Handover 0745b: Dependency Security & Cleanup.

SCOPE (do ALL of these):
1. PYTHON SECURITY: Upgrade mcp in requirements.txt from ==1.12.3 to >=1.23.0
   - After upgrade, verify the server starts: python startup.py --dev
   - Check if serena-agent still works (import test)
   - Update the pin comment in requirements.txt
2. NPM SECURITY: cd frontend/ && npm audit fix
   - Then upgrade or remove happy-dom (critical RCE)
   - If removing happy-dom: update vite.config.js test.environment from 'happy-dom' to 'jsdom'
3. REMOVE UNUSED NPM PRODUCTION DEPS (run from frontend/):
   npm uninstall @vue-flow/background @vue-flow/controls @vue-flow/core @vue-flow/minimap chart.js d3 gsap socket.io-client vue-chartjs vuedraggable
4. REMOVE UNUSED NPM DEV DEPS:
   npm uninstall @eslint/compat tailwindcss autoprefixer
5. CONSOLIDATE: npm uninstall sass (keep sass-embedded)
6. REMOVE .eslintrc.json (keep eslint.config.js). If @vue/eslint-config-prettier is only used by .eslintrc.json, remove it too.
7. PYTHON CLEANUP: Remove pydantic-settings from requirements.txt. Run: pip uninstall python-jose pydantic-settings

TESTING: Light. After all changes:
- pip install -r requirements.txt (verify clean install)
- cd frontend/ && npm install && npm run build (verify frontend builds)
- pytest tests/ -x --timeout=60 (verify tests pass)

When done, update the original handover file with a completion summary.
```

---

## 0745c: Backend Dead Code Removal

**Agent**: `tdd-implementor`
**Estimated**: 4-6 hours
**Risk**: LOW (all targets verified as zero-caller dead code)
**Findings Source**: `handovers/0740_findings_backend.md`

### Scope

1. **Delete 5 orphan modules** (2,345 lines):
   - `src/giljo_mcp/agent_message_queue.py` (1,261 lines)
   - `src/giljo_mcp/tools/agent_coordination_external.py` (659 lines)
   - `src/giljo_mcp/utils/path_normalizer.py` (193 lines)
   - `api/websocket_service.py` (171 lines)
   - `api/endpoints/mcp_http_temp.py` (61 lines)
2. **Delete orphan tests** that only test deleted modules (find and remove)
3. **Remove 12 dead WebSocket broadcast methods** from `api/websocket.py`
4. **Remove 91 print() statements** from src/ (replace with logger calls or delete)
5. **Fix 2 lint issues** in `api/endpoints/projects/lifecycle.py` (remove unused variable assignments)
6. **Remove dead functions in high-value files** (top offenders from findings H1):
   - `src/giljo_mcp/auth_manager.py`: 5 dead functions
   - `src/giljo_mcp/config_manager.py`: 4 dead functions
   - `src/giljo_mcp/setup/state_manager.py`: 7 dead functions
   - `src/giljo_mcp/discovery.py`: 5 dead functions
   - `src/giljo_mcp/optimization/` directory: all functions dead (serena_optimizer.py, tool_interceptor.py)

### What NOT to Do

- Do NOT refactor F-rated functions (separate future handover)
- Do NOT remove dead functions from ALL 141 candidates -- focus on orphan modules and top offenders
- Do NOT write new tests -- just verify existing tests still pass after removal

### Kickoff Prompt

```
Read these documents in order:
1. F:\GiljoAI_MCP\handovers\handover_instructions.md (handover format)
2. F:\GiljoAI_MCP\handovers\0745_AUDIT_FOLLOWUP_ROADMAP.md (the 0745c section)
3. F:\GiljoAI_MCP\handovers\0740_findings_backend.md (full findings with file:line refs)

You are executing Handover 0745c: Backend Dead Code Removal.

APPROACH: Work in phases. After each phase, run pytest to verify nothing broke.

PHASE 1 - Delete orphan modules (highest impact, lowest risk):
- Delete these 5 files entirely:
  src/giljo_mcp/agent_message_queue.py
  src/giljo_mcp/tools/agent_coordination_external.py
  src/giljo_mcp/utils/path_normalizer.py
  api/websocket_service.py
  api/endpoints/mcp_http_temp.py
- Search for and delete any test files that ONLY test these deleted modules
- Search for and remove any imports of these modules in __init__.py files
- Run: pytest tests/ -x --timeout=60

PHASE 2 - Remove dead WebSocket methods from api/websocket.py:
- Remove the 12 dead broadcast methods listed in findings H1/Priority 2 item 5
- Run: pytest tests/ -x --timeout=60

PHASE 3 - Remove print() statements from src/:
- Search for all print() in src/giljo_mcp/
- Replace with logger.debug() or logger.info() where the message is useful
- Delete entirely where the print was clearly debug output
- Run: pytest tests/ -x --timeout=60

PHASE 4 - Fix 2 lint issues + remove dead functions from top offender files:
- Fix lifecycle.py: remove unused variable assignments (keep await calls)
- Remove dead functions from: auth_manager.py (5), config_manager.py (4),
  state_manager.py (7), discovery.py (5), optimization/ directory (all)
- IMPORTANT: For each function, verify zero callers with grep before deleting
- The findings doc has a 5% false positive rate -- verify before deleting
- Run: pytest tests/ -x --timeout=60

TESTING: Light. Run existing suite after each phase. No new tests.

When done, update the original handover file with a completion summary.
Count total lines removed and files deleted in the summary.
```

---

## 0745d: Frontend Cleanup

**Agent**: `frontend-tester`
**Estimated**: 3-4 hours
**Risk**: MEDIUM (Pinia store consolidation affects WebSocket data flow)
**Findings Source**: `handovers/0740_findings_frontend.md`

### Scope

1. **Delete 7 unused Vue components** (~1,100 lines):
   - `frontend/src/components/products/OrchestratorLaunchButton.vue`
   - `frontend/src/components/products/ProductVisionPanel.vue`
   - `frontend/src/components/projects/LaunchPromptIcons.vue`
   - `frontend/src/components/projects/AgentExecutionModal.vue`
   - `frontend/src/components/StatusBadge.integration-example.vue`
   - `frontend/src/views/UsersView.vue`
   - `frontend/src/views/ApiKeysView.vue`
2. **Remove 12 dead API definitions** from `frontend/src/services/api.js` (lines listed in findings P1-2)
3. **Delete orphaned utility modules**: `configTemplates.js`, `pathDetection.js`, `integrations/index.ts`, `integrations/registry.ts` + their orphan test files
4. **Remove ProjectDetailView stub**: Delete `frontend/src/views/ProjectDetailView.vue` and remove its route from `router/index.js` (line 85-93)
5. **Delete orphan test spec**: `VisionSummarizationCard.spec.js`
6. **Consolidate Pinia stores** (P1 bug fix):
   - Merge `agentJobs.js` and `agentJobsStore.js` into single store
   - `agentJobsStore.js` (map-based, used by WebSocket router) is the more complete one
   - Update all consumers: `stores/index.js`, `AgentCardGrid.vue`, `useAgentJobs.js` composable
   - Verify WebSocket events reach all components after consolidation
7. **Add DOMPurify** to `MessageItem.vue` and `BroadcastPanel.vue` v-html rendering
8. **Wire up useToast** in TemplateManager.vue (3 DONE TODOs at lines 1111, 1124, 1287)

### What NOT to Do

- Do NOT build a console.log debug utility (just delete obvious debug leftovers during cleanup)
- Do NOT convert ActionIcons.vue to `<script setup>` (P3 cosmetic)
- Do NOT standardize API import style (P3 cosmetic)
- Do NOT address ESLint warnings beyond what naturally resolves from deleted code

### Kickoff Prompt

```
Read these documents in order:
1. F:\GiljoAI_MCP\handovers\handover_instructions.md (handover format)
2. F:\GiljoAI_MCP\handovers\0745_AUDIT_FOLLOWUP_ROADMAP.md (the 0745d section)
3. F:\GiljoAI_MCP\handovers\0740_findings_frontend.md (full findings)

You are executing Handover 0745d: Frontend Cleanup.

APPROACH: Work in phases. After each phase, verify the frontend builds.

PHASE 1 - Delete dead components and files:
- Delete the 7 unused Vue components listed in findings P2-1
- Delete orphaned utilities: configTemplates.js, pathDetection.js, integrations/index.ts, integrations/registry.ts
- Delete their orphan test files (search for .spec.js/.spec.ts files that import deleted modules)
- Delete VisionSummarizationCard.spec.js
- Delete ProjectDetailView.vue and remove its route from router/index.js (lines 85-93)
- Run: cd frontend/ && npm run build

PHASE 2 - Remove dead API definitions from api.js:
- Remove the 12 dead endpoint definitions listed in findings P1-2
  (orchestrator block lines 517-524, terminate/hierarchy/metrics, context.getSection, session, settings.getProduct)
- Search for any callers of these removed methods and clean up
- Run: cd frontend/ && npm run build

PHASE 3 - Consolidate Pinia stores (BUG FIX):
- The agentJobsStore.js (Pinia ID 'agentJobsDomain') is the more complete store used by WebSocket
- Merge agentJobs.js functionality into agentJobsStore.js
- Update all imports: stores/index.js, AgentCardGrid.vue, useAgentJobs.js composable
- Delete the old agentJobs.js after all consumers are migrated
- Verify: websocketEventRouter.js still routes to the correct store
- Run: cd frontend/ && npm run build

PHASE 4 - Security and polish:
- Install DOMPurify: cd frontend/ && npm install dompurify
- Add DOMPurify sanitization to v-html in MessageItem.vue and BroadcastPanel.vue
- Wire up useToast() in TemplateManager.vue (replace console.log at lines 1111, 1124, 1287)
- Run: cd frontend/ && npm run build

TESTING: Light. Verify frontend builds after each phase. Run: cd frontend/ && npx vitest run (if tests exist). No new tests required.

When done, update the original handover file with a completion summary.
Count total lines/files removed and the Pinia store consolidation result.
```

---

## 0745e: Architecture Polish

**Agent**: `system-architect`
**Estimated**: 2-3 hours
**Risk**: LOW (mechanical replacements with clear patterns)
**Findings Source**: `handovers/0740_findings_architecture.md`

### Scope

1. **Fix HTTPException leak in ProductService** (P1-1):
   - `src/giljo_mcp/services/product_service.py` lines 1415-1448
   - Replace `HTTPException(400)` with `ValidationError`
   - Replace `HTTPException(404)` with `ResourceNotFoundError`
   - Remove `from fastapi import HTTPException` import from the service file
2. **Replace 8 bare ValueError** with `ValidationError` (P1-2):
   - `product_service.py:543`
   - `project_service.py:200`
   - `orchestration_service.py:2529, 2533, 2545, 2572`
   - `settings_service.py:52, 78`
3. **Fix logging inconsistency** (P2-4):
   - `src/giljo_mcp/services/consolidation_service.py` lines 10, 20
   - Replace `structlog` with standard `logging` (per CLAUDE.md policy)
4. **Remove redundant per-endpoint exception blocks** (Community Perception Smell #1):
   - The global exception handler in `api/exception_handlers.py` already maps domain exceptions to HTTP status codes
   - Remove the try/except blocks from endpoint functions that just re-map exceptions
   - Keep only endpoint-specific error handling where it does something unique
   - Estimated ~200 lines of redundant code across 15+ endpoint files

### What NOT to Do

- Do NOT standardize constructor patterns (architectural decision, separate discussion)
- Do NOT change OrgService return types (P3, cosmetic)
- Do NOT add _get_session() to TemplateService (P3, cosmetic)
- Do NOT address the 36 dict wrappers in endpoints (that's the 0730 branch work)

### Kickoff Prompt

```
Read these documents in order:
1. F:\GiljoAI_MCP\handovers\handover_instructions.md (handover format)
2. F:\GiljoAI_MCP\handovers\0745_AUDIT_FOLLOWUP_ROADMAP.md (the 0745e section)
3. F:\GiljoAI_MCP\handovers\0740_findings_architecture.md (full findings)
4. F:\GiljoAI_MCP\handovers\0740_findings_community_perception.md (Smell #1: redundant exception blocks)

You are executing Handover 0745e: Architecture Polish.

PHASE 1 - Fix service layer violations:
1. In src/giljo_mcp/services/product_service.py:
   - Lines 1415-1448: Replace HTTPException(400,...) with ValidationError(...)
   - Lines 1415-1448: Replace HTTPException(404,...) with ResourceNotFoundError(...)
   - Remove the "from fastapi import HTTPException" import (line 22)
   - Verify ValidationError and ResourceNotFoundError are imported from src.giljo_mcp.exceptions

2. Replace 8 bare ValueError with ValidationError:
   - product_service.py:543
   - project_service.py:200
   - orchestration_service.py:2529, 2533, 2545, 2572
   - settings_service.py:52, 78
   - Import ValidationError if not already imported in each file

3. In src/giljo_mcp/services/consolidation_service.py:
   - Line 10: Replace "import structlog" with "import logging"
   - Line 20: Replace "structlog.get_logger(__name__)" with "logging.getLogger(__name__)"

Run: pytest tests/ -x --timeout=60

PHASE 2 - Remove redundant exception handling from endpoints:
- Read api/exception_handlers.py first to understand what the global handler already maps
- Then go through each endpoint file in api/endpoints/ and remove try/except blocks
  that ONLY do this pattern:
    except ResourceNotFoundError as e: raise HTTPException(404, detail=str(e))
    except ValidationError as e: raise HTTPException(422, detail=str(e))
    except AuthorizationError as e: raise HTTPException(403, detail=str(e))
    except Exception as e: raise HTTPException(500, detail="Internal server error")
- KEEP any try/except that does something unique (logging specific context, transforming data, etc.)
- IMPORTANT: The global handler must cover all the exception types before you remove local handlers.
  Verify api/exception_handlers.py handles: ResourceNotFoundError, ValidationError, AuthorizationError,
  DuplicateResourceError, DatabaseError, and the generic Exception fallback.

Run: pytest tests/ -x --timeout=60

TESTING: Light. Run existing suite after each phase. No new tests.

When done, update the original handover file with a completion summary.
Count: lines removed, exception blocks removed, files touched.
```

---

## 0745f: Documentation Sync

**Agent**: `documentation-manager`
**Estimated**: 4-6 hours
**Risk**: NONE (documentation only, no code changes)
**Findings Source**: `handovers/0740_findings_documentation.md`

### Scope

1. **Fix README_FIRST.md** (P1-3):
   - Remove or fix 42+ broken links
   - Remove the entire "Recent Production Handovers" section (lines 658-1060) if all links are broken
   - Fix relative paths for files that exist in wrong directories (e.g., `developer_guides/` -> `guides/`)
2. **Update SERVICES.md** (P1-1, P1-2):
   - Lines 81-88: Change "DEPRECATED" to "REMOVED (Handover 0700c)", remove "will be removed in v4.0"
   - Lines 240, 248: Remove instance_number references
   - Lines 569-573: Replace MCPAgentJob code example with AgentJob/AgentExecution
3. **Update TESTING.md** (P1-5):
   - Remove dict wrapper assertions (lines 241, 389)
   - Remove instance_number assertions (lines 269, 336, 339)
   - Remove trigger_succession() references (lines 324, 328)
   - Update code examples to use exception-based patterns
4. **Update ORCHESTRATOR.md** (P1-4):
   - Replace dict wrapper code examples (lines 411, 728, 811, 1239)
   - Remove instance_number references (lines 892, 921, 1069)
   - Replace MCPAgentJob references (lines 37, 133, 258, 282, 344)
5. **Update thin_client_migration_guide.md** (P2-4):
   - Lines 31-259: Mark OrchestratorPromptGenerator as REMOVED (not deprecated)
   - Collapse the phased timeline to reflect completed removal
6. **Update context_tools.md** (P2-3):
   - Line 298: Replace sequential_history JSONB with product_memory_entries table format
7. **Update exception_mapping.md** (P2-1):
   - Lines 81, 222-230: Replace "Current Pattern (Dict Wrapper)" with "Legacy Pattern (Removed)"
8. **Create SECURITY.md** at project root (P3-5):
   - Supported versions, vulnerability reporting process, response timeline
   - Fixes broken README.md badge link
9. **Purge instance_number** from all remaining active docs (15+ files listed in findings P1-2)

### What NOT to Do

- Do NOT create CONTRIBUTING.md or CODE_OF_CONDUCT.md (community polish, deferred)
- Do NOT add screenshots to README.md (deferred)
- Do NOT create docs/manuals/ directory (deferred)
- Do NOT create a "What Changed in 0700/0730" summary doc (deferred)

### Kickoff Prompt

```
Read these documents in order:
1. F:\GiljoAI_MCP\handovers\handover_instructions.md (handover format)
2. F:\GiljoAI_MCP\handovers\0745_AUDIT_FOLLOWUP_ROADMAP.md (the 0745f section)
3. F:\GiljoAI_MCP\handovers\0740_findings_documentation.md (full findings with line numbers)

You are executing Handover 0745f: Documentation Sync.

This is a documentation-only handover. No code changes.

APPROACH: Work through the files systematically. The findings doc has exact line numbers for every issue.

PRIORITY ORDER:
1. Fix admin/admin contradiction in README_FIRST.md (P0) -- if not already done in 0745a
2. Update SERVICES.md (JSONB section + instance_number + MCPAgentJob)
3. Update TESTING.md (remove dict wrappers, instance_number, trigger_succession)
4. Update ORCHESTRATOR.md (dict wrappers, instance_number, MCPAgentJob)
5. Fix/remove broken links in README_FIRST.md (42+ broken links)
6. Update thin_client_migration_guide.md (OrchestratorPromptGenerator fully removed)
7. Update context_tools.md (sequential_history -> product_memory_entries)
8. Update exception_mapping.md (dict wrappers -> removed)
9. Purge instance_number from all remaining docs (use grep to find all)
10. Create SECURITY.md at project root

FOR BROKEN LINKS: When a link target doesn't exist:
- If the file exists elsewhere (wrong relative path), fix the path
- If the file was deleted/archived and the section adds no value, remove the section
- If the section is valuable but the link is dead, remove just the link and keep the text
- Prefer REMOVING dead sections over creating stub files

FOR INSTANCE_NUMBER: Use grep to find ALL remaining references in docs/**/*.md,
then remove or replace each one. The findings list 15+ files but there may be more.

TESTING: None needed (docs only). Just verify no markdown formatting errors.

When done, update the original handover file with a completion summary.
Count: files updated, broken links fixed/removed, stale references purged.
```

---

## Deferred Items Discussion

These items were identified in the 0740 audit but are **out of scope** for the 0745 series. This section documents why they're deferred and how they relate to future work.

### Item 1: 36 API Endpoint Dict Wrappers

**Status**: Active branch work (`feature/0730-service-response-models-v2`)
**Relationship to 0745**: The current branch is already addressing this. 0745e removes redundant exception blocks from the same endpoint files -- this is complementary, not conflicting. However, if the 0730 branch rewrites endpoints significantly, doing 0745e first avoids merge conflicts.
**Recommendation**: Complete 0745e before resuming the 0730 branch work, OR do 0730 first and skip the redundant exception removal from 0745e.

### Item 2: Refactoring F-Rated Functions (3 functions)

**What**: `MissionPlanner._build_context_with_priorities` (466 lines), `MessageService.send_message` (377 lines), `OrchestrationService.report_progress` (256 lines)
**Why deferred**: Each is a significant refactor (8-16h total). These are behavioral code, not dead code -- refactoring them requires understanding business logic and testing behavior.
**Recommendation**: Separate future handover (0750 or similar). No urgency -- they work correctly, they're just complex.
**Impact on 0745**: None. 0745 doesn't touch these functions.

### Item 3: Constructor Pattern Standardization

**What**: 4 different constructor patterns across services (direct tenant_key, TenantManager, raw session, no tenant)
**Why deferred**: This is an architectural decision, not a cleanup task. Changing constructor patterns requires updating all service instantiation points and their tests.
**Recommendation**: Discuss as part of a service layer v2 design. The current patterns work correctly -- the inconsistency is cognitive overhead, not a bug.
**Impact on 0745**: None.

### Item 4: 178 console.log Statements

**What**: 0745d removes obvious debug leftovers during cleanup, but doesn't build a proper debug utility
**Why deferred**: Building a `logger.debug()` wrapper with production OFF switch is a feature, not cleanup. The 178 console.logs are 56% of ESLint warnings -- removing them is valuable but building infrastructure to replace them is separate work.
**Recommendation**: After 0745d, assess how many console.logs remain. If still significant, create a small handover to either (a) delete them all or (b) build a lightweight debug utility.
**Impact on 0745**: 0745d will reduce the count. The remainder can be addressed later.

### Item 5: Docker / CONTRIBUTING.md / CODE_OF_CONDUCT.md

**What**: Community governance files and containerization
**Why deferred**: These are "open-source readiness" items, not audit followup. The community perception score is 3/10 partly due to these missing files.
**Recommendation**: Bundle as a "Community Readiness" handover when preparing for public release. Not urgent for internal development.
**Impact on 0745**: None. 0745f creates SECURITY.md (the only community file with a broken badge link).

### Decision Required: Dict Wrappers vs 0745e Sequencing

The only real dependency between deferred items and 0745 is the **dict wrappers** (Item 1) vs **0745e** (redundant exception removal). Both touch endpoint files. Options:

**Option A** (recommended): Do 0745e first. The exception block removal is a clean, mechanical change. Then resume 0730 branch work on dict wrappers with cleaner endpoint files.

**Option B**: Resume 0730 first, then do 0745e after. The 0730 work may rewrite endpoints enough that the redundant exception blocks disappear naturally.

**Option C**: Merge them. Add dict wrapper replacement to 0745e scope. This makes 0745e much larger but avoids touching files twice.

---

## Completion Criteria

The 0745 series is complete when:
- [ ] All 6 handovers marked COMPLETED in the status tracker above
- [ ] All changes merged to master
- [ ] `pytest tests/ -x` passes on master after all merges
- [ ] `cd frontend/ && npm run build` succeeds after all merges
- [ ] No P0 findings remain from the 0740 audit

---

**Document Owner**: User (manual execution of handovers)
**Created**: 2026-02-10
**Last Updated**: 2026-02-10
