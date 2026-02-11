# 0740 Findings: Frontend Code Health

## Executive Summary

The GiljoAI MCP frontend (Vue 3 + Vuetify) is in moderate health. ESLint maintains 0 errors from the 0720 cleanup, but the same 316 warnings persist -- 178 of which are `console.log` statements. The audit identified 7 completely unused Vue components, 6 dead/orphaned API endpoint definitions in `api.js`, 2 orphaned utility modules, a duplicate Pinia store pair (`agentJobs.js` vs `agentJobsStore.js`), and a stub view registered in the router. No deprecated Vue 2 patterns or event bus anti-patterns were found; the codebase consistently uses Vue 3 Composition API with `<script setup>`.

## Methodology

- **Unused Components**: Cross-referenced every `.vue` file against `router/index.js` dynamic imports, all production `import` statements in `.vue`/`.js` files, and `App.vue`/layout entry points. Excluded test files (`.spec.js`) from positive-import evidence.
- **Dead Code**: Analyzed ESLint `no-unused-vars` warnings for declared-but-unused variables, functions, and imports. Checked for methods not called in templates.
- **Console.log**: Full `ripgrep` across `frontend/src/**/*.{vue,js}` for `console.log`, `console.warn`, and `console.error`. Categorized by tagged-logging (e.g., `[ROUTER]`) vs untagged debug leftovers.
- **Deprecated Patterns**: Searched for `this.$`, `$refs`, `$on`/`$off` event bus patterns, Options API `data()`, and Vuetify 2 component names.
- **ESLint**: Ran `npx eslint src/` with current config; parsed warning categories.
- **API Health**: Compared every `api.js` endpoint URL path against backend `@router` decorators in `api/endpoints/`.
- **Prop Validation**: Searched for `defineProps([` (array syntax, no types) and verified all `defineProps({` have type definitions.

---

## Findings (by priority)

### P0 Critical

**No P0 critical issues found.**

---

### P1 High

#### P1-1: Duplicate Pinia Store -- `agentJobs.js` vs `agentJobsStore.js`

Two separate stores export `useAgentJobsStore` with different Pinia IDs:

| File | Pinia ID | Consumers |
|------|----------|-----------|
| `frontend/src/stores/agentJobs.js` (line 23) | `'agentJobs'` | `stores/index.js` re-export, `AgentCardGrid.vue`, composable `useAgentJobs.js` |
| `frontend/src/stores/agentJobsStore.js` (line 36) | `'agentJobsDomain'` | `websocketEventRouter.js`, `LaunchTab.vue` |

**Impact**: Two separate Pinia store instances are created at runtime. WebSocket events routed through `websocketEventRouter.js` update `agentJobsDomain`, but components reading from the `agentJobs` store (via `stores/index.js`) see stale data. This is a **data synchronization bug** -- WebSocket-driven real-time updates may not reach all components.

**Files**:
- `F:\GiljoAI_MCP\frontend\src\stores\agentJobs.js` (line 23)
- `F:\GiljoAI_MCP\frontend\src\stores\agentJobsStore.js` (line 36)
- `F:\GiljoAI_MCP\frontend\src\stores\index.js` (line 12)
- `F:\GiljoAI_MCP\frontend\src\stores\websocketEventRouter.js` (line 3)

#### P1-2: Dead API Endpoints in `api.js` -- No Backend Routes

The following frontend API definitions reference URLs with no corresponding backend routes:

| Frontend API Method | URL Path | Evidence |
|-------------------|----------|----------|
| `api.orchestrator.launch()` | `/api/v1/orchestration/launch` | No `/api/v1/orchestration/` prefix registered in `api/app.py` |
| `api.orchestrator.getWorkflowStatus()` | `/api/v1/orchestration/workflow-status/{id}` | Same -- no orchestration prefix |
| `api.orchestrator.getMetrics()` | `/api/v1/orchestration/metrics/{id}` | Same |
| `api.orchestrator.createMissions()` | `/api/v1/orchestration/create-missions` | Same |
| `api.orchestrator.spawnTeam()` | `/api/v1/orchestration/spawn-team` | Same |
| `api.agentJobs.terminate()` | `/api/agent-jobs/{id}/terminate` | No `terminate` endpoint in backend `agent_jobs/` module |
| `api.agentJobs.hierarchy()` | `/api/agent-jobs/hierarchy` | No `hierarchy` endpoint in backend |
| `api.agentJobs.metrics()` | `/api/agent-jobs/metrics` | No `metrics` endpoint in backend |
| `api.context.getSection()` | `/api/v1/context/section/` | No `/section` route in `api/endpoints/context.py` |
| `api.session.info()` | `/api/v1/stats/session/` | No `/session` route in `api/endpoints/statistics.py` |
| `api.session.stats()` | `/api/v1/stats/` | No root `/` route in statistics (only `/system`, `/call-counts`, etc.) |
| `api.settings.getProduct()` | `/api/v1/config/product/` | No `/product` route in configuration endpoints |

**File**: `F:\GiljoAI_MCP\frontend\src\services\api.js`
- Lines 517-524 (orchestrator block)
- Lines 457-461 (terminate, hierarchy, metrics)
- Lines 331-334 (context.getSection)
- Lines 366-369 (session)
- Line 343 (settings.getProduct)

**Note**: `api.orchestrator.launchProject()` at line 518 is valid -- it maps to `/api/agent-jobs/launch-project` which exists.

**Active Callers**: `api.session.info()` is called from `stores/settings.js:112`. The others appear uncalled in production code but represent dead weight in the service layer.

---

### P2 Medium

#### P2-1: Unused Vue Components (7 components)

| Component | File Path | Evidence |
|-----------|-----------|----------|
| `OrchestratorLaunchButton.vue` | `F:\GiljoAI_MCP\frontend\src\components\products\OrchestratorLaunchButton.vue` | Zero imports outside its own file. Also uses dead API `api.orchestrator.launch()`. |
| `ProductVisionPanel.vue` | `F:\GiljoAI_MCP\frontend\src\components\products\ProductVisionPanel.vue` | Zero imports -- not referenced by any `.vue` or `.js` file. |
| `LaunchPromptIcons.vue` | `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchPromptIcons.vue` | Zero production imports. Only referenced in `DELIVERY_SUMMARY.md` and `README.md` documentation. |
| `AgentExecutionModal.vue` | `F:\GiljoAI_MCP\frontend\src\components\projects\AgentExecutionModal.vue` | Zero imports -- self-referential only. |
| `StatusBadge.integration-example.vue` | `F:\GiljoAI_MCP\frontend\src\components\StatusBadge.integration-example.vue` | Zero imports. Example/demo file, not a production component. |
| `UsersView.vue` | `F:\GiljoAI_MCP\frontend\src\views\UsersView.vue` | Not in router. `Users.vue` is the registered route component for `/admin/users`. |
| `ApiKeysView.vue` | `F:\GiljoAI_MCP\frontend\src\views\ApiKeysView.vue` | Not in router, not imported anywhere. API key management is embedded in `UserSettings.vue` via `ApiKeyManager` component. |

**Total lines of dead component code**: ~1,100 lines

#### P2-2: Orphaned Utility Modules (2 files)

| File | Path | Evidence |
|------|------|----------|
| `configTemplates.js` | `F:\GiljoAI_MCP\frontend\src\utils\configTemplates.js` | Zero production imports. Only referenced in test file `tests/unit/utils/configTemplates.spec.js`. |
| `pathDetection.js` | `F:\GiljoAI_MCP\frontend\src\utils\pathDetection.js` | Zero production imports. Only referenced in test file `tests/unit/utils/pathDetection.spec.js`. |

#### P2-3: Orphaned TypeScript Integration Module

| File | Path | Evidence |
|------|------|----------|
| `integrations/index.ts` | `F:\GiljoAI_MCP\frontend\src\integrations\index.ts` | Zero production imports. |
| `integrations/registry.ts` | `F:\GiljoAI_MCP\frontend\src\integrations\registry.ts` | Zero production imports. Only test file `tests/unit/integrations/registry.spec.ts` references it. |

#### P2-4: Stub View Registered in Router

`ProjectDetailView.vue` is registered at `/products/:id` in the router (line 87) but is an empty placeholder:

```vue
<template>
  <v-container>
    <h1 class="text-h4 mb-4">ProjectDetail</h1>
    <v-alert type="info" variant="tonal">
      ProjectDetailView - Awaiting implementation after analyzer results
    </v-alert>
  </v-container>
</template>
```

**File**: `F:\GiljoAI_MCP\frontend\src\views\ProjectDetailView.vue` (12 lines)
**Router**: `F:\GiljoAI_MCP\frontend\src\router\index.js` (line 85-93)

This route is accessible to users. The `ProductDetailView.vue` (separate file, full implementation) handles the actual product detail at a different route.

#### P2-5: Orphan Test Spec -- `VisionSummarizationCard.spec.js`

Test file `F:\GiljoAI_MCP\frontend\src\components\settings\integrations\VisionSummarizationCard.spec.js` imports `VisionSummarizationCard.vue` which does not exist. This test file will fail with an import error.

#### P2-6: v-html XSS Surface (4 instances)

| File | Line | Content Source |
|------|------|---------------|
| `DatabaseConnection.vue` | 125 | `formatTestResultMessage(connectionTestResult)` -- formatted from local API response |
| `MessageItem.vue` | 49 | `renderedContent` -- user/agent message content, potential XSS vector |
| `BroadcastPanel.vue` | 71 | `markdownPreview` -- markdown-rendered user input |
| `TemplateManager.vue` | 727 | `diffData.diff_html` -- API-generated diff HTML |

ESLint flags 2 of these as `vue/no-v-html` warnings. MessageItem and BroadcastPanel render user-provided content and should sanitize with DOMPurify or equivalent.

---

### P3 Low

#### P3-1: Excessive console.log Statements (178 occurrences)

**Total across `frontend/src/`**:
- `console.log`: 178 occurrences in 46 files
- `console.warn`: 51 occurrences in 26 files
- `console.error`: 226 occurrences in 60 files (mostly appropriate error handling)

**Top offenders by console.log count**:

| File | Count | Assessment |
|------|-------|------------|
| `views/UserSettings.vue` | 14 | Debug leftovers -- settings load/save tracing |
| `main.js` | 13 | Intentional boot sequence logging -- borderline |
| `layouts/DefaultLayout.vue` | 9 | Debug leftovers -- auth/WebSocket init tracing |
| `components/TemplateManager.vue` | 8 | Debug leftovers -- template operations |
| `components/UserManager.vue` | 7 | Debug leftovers -- user CRUD tracing |
| `components/navigation/NotificationDropdown.vue` | 7 | Debug leftovers -- lifecycle tracing |
| `views/SystemSettings.vue` | 7 | Debug leftovers -- settings load/save |
| `views/Login.vue` | 7 | Debug leftovers -- auth flow tracing |
| `composables/useAutoSave.js` | 6 | Debug leftovers -- cache operation tracing |
| `components/settings/ContextPriorityConfig.vue` | 6 | Debug leftovers -- config load/save |

**Categorization**:
- **Tagged logging** (e.g., `[ROUTER]`, `[DefaultLayout]`, `[API]`): ~160 occurrences. These follow a consistent pattern and could be converted to a debug utility with a production OFF switch.
- **Untagged debug** (e.g., `console.log('WebSocket update:', data)`): ~18 occurrences. Pure debug leftovers that should be removed.

**ESLint Impact**: All 178 `console.log` occurrences generate `no-console` warnings, accounting for ~56% of the total 316 ESLint warnings.

#### P3-2: ESLint Warnings -- Unused Variables (~138 warnings)

The remaining ~138 warnings are `no-unused-vars` for variables, imports, and function parameters. Notable patterns:

**Unused computed properties / functions (dead code)**:
- `getTaskProgress` -- `TasksView.vue`
- `getProductMetric`, `getProductInitial` -- `ProductsView.vue`
- `fetchHistoricalProjects` -- `ProjectsView.vue`
- `formatStatus`, `formatMessageMeta`, `formatCount` -- various views
- `canLaunchAgent` -- defined but unused in `LaunchTab.vue`
- `handleEditAgentMission` -- defined but unused
- `goNextTab`, `goPrevTab`, `isFirstTab`, `isLastTab` -- `StartupQuickStart.vue`

**Unused imports**:
- `api` imported but unused in `UserSettings.vue` (line 437)
- `watch` imported but unused in 3 files
- `computed` imported but unused in 3 files
- `nextTick` imported but unused in 2 files

#### P3-3: Inconsistent API Import Style

Two import patterns coexist:
- `import api from '@/services/api'` (default import) -- 54 files
- `import { api } from '@/services/api'` (named import) -- 5 files

Both work because `api.js` uses both `export const api = {` and `export default api`. However, mixing styles is inconsistent.

**Files using named import**:
- `stores/projects.js` (line 3)
- `views/LaunchRedirectView.vue` (line 21)
- `views/ProjectLaunchView.vue` (line 120)
- `components/projects/JobsTab.vue` (line 377)
- `services/api.spec.js` (line 9)

#### P3-4: Options API Hybrid in ActionIcons.vue

`F:\GiljoAI_MCP\frontend\src\components\StatusBoard\ActionIcons.vue` (line 134) uses Options API `export default { ... setup() }` instead of `<script setup>` Composition API used by 47 other components. This is not a bug but is inconsistent with the rest of the codebase.

---

## Metrics Summary

| Metric | Count | Notes |
|--------|-------|-------|
| Unused components | 7 | 5 components + 2 orphan views (~1,100 lines) |
| Orphaned utility modules | 4 | 2 JS utils + 2 TS integrations modules |
| Console.log statements | 178 | 56% of ESLint warnings |
| Console.warn statements | 51 | Mostly appropriate usage |
| Console.error statements | 226 | Appropriate error handling |
| ESLint errors | 0 | Maintained from 0720 |
| ESLint warnings | 316 | Unchanged from 0720 |
| Missing prop validation | 0 | All 47 components with props use typed `defineProps({})` |
| Dead API definitions | 12 | In `api.js` -- no matching backend routes |
| v-html XSS surface | 4 | 2 with user content (MessageItem, BroadcastPanel) |
| Stub views in router | 1 | ProjectDetailView.vue |
| Duplicate stores | 1 pair | agentJobs.js vs agentJobsStore.js |
| Orphan test specs | 1 | VisionSummarizationCard.spec.js (component deleted) |

---

## False Positive Analysis

20 samples were validated to ensure <5% false positive rate:

| # | Finding | File | Validated | Result |
|---|---------|------|-----------|--------|
| 1 | OrchestratorLaunchButton unused | `components/products/OrchestratorLaunchButton.vue` | Grep for all references | TRUE -- zero imports |
| 2 | ProductVisionPanel unused | `components/products/ProductVisionPanel.vue` | Grep for all references | TRUE -- zero imports |
| 3 | LaunchPromptIcons unused | `components/projects/LaunchPromptIcons.vue` | Grep for all references | TRUE -- only in .md files |
| 4 | AgentExecutionModal unused | `components/projects/AgentExecutionModal.vue` | Grep for all references | TRUE -- self-referential only |
| 5 | UsersView not in router | `views/UsersView.vue` | Checked router/index.js | TRUE -- Users.vue is registered instead |
| 6 | ApiKeysView not in router | `views/ApiKeysView.vue` | Checked router/index.js + all imports | TRUE -- zero references |
| 7 | configTemplates.js orphaned | `utils/configTemplates.js` | Grep across all src/ | TRUE -- only in test spec |
| 8 | pathDetection.js orphaned | `utils/pathDetection.js` | Grep across all src/ | TRUE -- only in test spec |
| 9 | api.orchestrator.launch dead | `services/api.js:517` | Checked backend app.py | TRUE -- no `/api/v1/orchestration/` prefix |
| 10 | api.agentJobs.terminate dead | `services/api.js:457` | Checked backend agent_jobs/ | TRUE -- no terminate endpoint |
| 11 | api.context.getSection dead | `services/api.js:332` | Checked context.py | TRUE -- no /section route |
| 12 | api.session.info dead | `services/api.js:367` | Checked statistics.py | TRUE -- no /session route |
| 13 | Duplicate agentJobs stores | `stores/agentJobs.js` + `agentJobsStore.js` | Verified both export same name | TRUE -- different Pinia IDs |
| 14 | StatusBadge.integration-example unused | `components/StatusBadge.integration-example.vue` | Grep for imports | TRUE -- zero imports |
| 15 | VisionSummarizationCard.spec orphaned | `settings/integrations/VisionSummarizationCard.spec.js` | Glob for .vue file | TRUE -- .vue file does not exist |
| 16 | ProjectDetailView is stub | `views/ProjectDetailView.vue` | Read file contents | TRUE -- 12-line placeholder |
| 17 | console.log in main.js | `main.js` lines 1-82 | Read file | TRUE -- 13 console.log calls |
| 18 | integrations/index.ts orphaned | `integrations/index.ts` | Grep across src/ | TRUE -- zero production imports |
| 19 | ActionIcons uses Options API | `StatusBoard/ActionIcons.vue:134` | Read file | TRUE -- `export default { setup() }` |
| 20 | No array-style defineProps | All .vue files | Grep for `defineProps([` | TRUE -- zero results, all use typed objects |

**False Positive Rate**: 0/20 = 0%

---

## Recommendations

### Immediate (P1 fixes)

1. **Consolidate agentJobs stores**: Merge `agentJobs.js` and `agentJobsStore.js` into a single store. The `agentJobsStore.js` (map-based, used by WebSocket router) is the more complete implementation. Update all consumers to import from one source.

2. **Clean up dead API definitions**: Remove the 12 dead endpoint definitions from `api.js` (orchestrator block lines 517-524, terminate/hierarchy/metrics, context.getSection, session, settings.getProduct). These create false expectations for developers and may cause silent runtime failures.

### Short-term (P2 fixes)

3. **Delete unused components**: Remove the 7 unused `.vue` files and their associated documentation. This removes ~1,100 lines of dead code.

4. **Delete orphaned utility modules**: Remove `configTemplates.js`, `pathDetection.js`, `integrations/index.ts`, `integrations/registry.ts` and their orphan test files.

5. **Remove or implement ProjectDetailView stub**: Either delete the stub and route, or implement the view. Currently accessible to users and shows "Awaiting implementation".

6. **Delete orphan test spec**: Remove `VisionSummarizationCard.spec.js` -- its component no longer exists.

7. **Sanitize v-html content**: Add DOMPurify to `MessageItem.vue` and `BroadcastPanel.vue` where user/agent content is rendered via `v-html`.

### Medium-term (P3 fixes)

8. **Replace console.log with debug utility**: Create a `logger.debug()` wrapper that is disabled in production builds. Convert all 178 `console.log` calls. This would eliminate ~56% of ESLint warnings.

9. **Clean up unused variables**: Address the ~138 `no-unused-vars` warnings. Many are dead computed properties and unused imports that indicate incomplete refactoring.

10. **Standardize API import style**: Pick one pattern (`import api from` or `import { api } from`) and apply consistently. Recommend keeping only the default export.

11. **Convert ActionIcons to `<script setup>`**: Align with the other 47 components using Composition API syntax.
