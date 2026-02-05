# Bug Diagnostic Report

**Generated**: 2026-02-05
**Investigation Scope**: Product creation and project reactivation bugs
**Investigators**: 3 parallel deep-researcher agents (Bug A, Bug B, Git History)
**Methodology**: Symbolic code tracing via Serena MCP + git diff analysis

---

## Bug A: Creating New Product Destroys Active State

### Root Cause

**Frontend store design flaw** in `frontend/src/stores/products.js:177`. When a new product is created, the `createProduct()` function immediately calls `setCurrentProduct(response.data.id)`, which switches the UI's "current product" context to the newly created (empty) product. This triggers a cascade of UI state changes that make tasks, jobs, and projects appear to vanish.

**There is no backend bug.** The server correctly creates the product with `is_active=False` and does NOT activate it, deactivate other products, or deactivate any projects.

### Evidence

**Evidence 1: The auto-switch trigger**

File: `frontend/src/stores/products.js`, lines 170-187

```javascript
async function createProduct(productData) {
    loading.value = true
    error.value = null
    try {
      const response = (await api.products?.create(productData)) || { data: null }
      if (response.data) {
        products.value.push(response.data)
        await setCurrentProduct(response.data.id)  // <-- BUG: Auto-switches to new (empty) product
      }
      return response.data
    ...
}
```

**Evidence 2: Task store watcher clears tasks on product change**

File: `frontend/src/stores/tasks.js`, lines 232-243

```javascript
watch(
    () => productStore.currentProductId,
    async (newProductId) => {
      if (newProductId) {
        await fetchTasks({ product_id: newProductId })  // Fetches tasks for NEW (empty) product
        await fetchTaskSummary(newProductId)
      } else {
        tasks.value = []
        taskSummary.value = null
      }
    },
)
```

When `currentProductId` changes to the new product ID, this watcher fires and re-fetches tasks filtered by the new product. Since the new product has zero tasks, the task list appears empty.

**Evidence 3: Task view filters by effectiveProductId**

File: `frontend/src/views/TasksView.vue`, lines 611-618

```javascript
const userFilteredTasks = computed(() => {
  if (taskFilter.value === 'product_tasks') {
    const productId = productStore.effectiveProductId  // Now points to NEW product
    if (!productId) {
      return []
    }
    return tasks.value.filter((task) => task.product_id === productId)
  }
  ...
})
```

File: `frontend/src/stores/products.js`, lines 44-46

```javascript
const effectiveProductId = computed(() => {
    return currentProductId.value || activeProduct.value?.id || null
})
```

`effectiveProductId` prefers `currentProductId` (now the new product) over `activeProduct` (the server-side active product). So all task-filtered views show nothing.

**Evidence 4: Backend is clean - no side effects on creation**

File: `src/giljo_mcp/services/product_service.py`, line 200

```python
product = Product(
    ...
    is_active=False,  # Products start inactive - no activation side effects
    ...
)
```

No WebSocket events are emitted. No activation/deactivation cascade occurs. No projects are modified.

**Evidence 5: Jobs are project-scoped, not product-scoped**

File: `frontend/src/composables/useAgentJobs.js`, lines 18-27

```javascript
async function loadJobs(projectId) {
    if (!projectId) {
      store.$reset?.()
      return []
    }
    ...
}
```

Jobs load per-project. When the product context shifts, the job display may reset if the project context is lost.

### Execution Flow (Step-by-Step)

1. User fills form and submits in `ProductsView.vue`
2. `productStore.createProduct()` called
3. API `POST /api/products/` creates product on server with `is_active=False` (no side effects)
4. Backend returns product data -- no WebSocket events, no deactivation
5. Frontend pushes to local array: `products.value.push(response.data)`
6. **THE TRIGGER**: Frontend calls `setCurrentProduct(newProductId)` (line 177)
7. `currentProductId` changes to the new product's ID
8. Task store watcher fires: re-fetches tasks with `product_id = newProductId` -- returns EMPTY list
9. `effectiveProductId` resolves to new product: all task-filtered computed properties show nothing
10. `projectStore.fetchProjects()` called: fetches ALL tenant projects (no change on backend)
11. **UI now shows empty state** -- viewing the new (empty) product context

### 0700-Related?

**NO.** The 0700 series did not cause or expose this bug.

- No 0700 commit modified `frontend/src/stores/products.js` (verified via `git log`)
- No 0700 commit modified `api/endpoints/products/crud.py` (verified via `git log`)
- No 0700 commit changed the `createProduct()` store action
- 0700c's JSONB cleanup only changed `product_memory` defaults, which is irrelevant to product creation's UI context switching
- This is a pre-existing frontend design flaw in the product store

### Recommended Fix Approach

**Primary Fix: Remove auto-switch from `createProduct()`**

1. **File**: `frontend/src/stores/products.js`, line 177
2. **Change**: Remove `await setCurrentProduct(response.data.id)` from the `createProduct` function
3. Creating a product should add it to the list without switching the user's active viewing context

```javascript
// BEFORE (buggy):
if (response.data) {
    products.value.push(response.data)
    await setCurrentProduct(response.data.id)  // REMOVE THIS LINE
}

// AFTER (fixed):
if (response.data) {
    products.value.push(response.data)
    // Do NOT switch to the new product - keep viewing current product
}
```

4. **Optional**: Add a success toast/snackbar showing "Product created" without switching context
5. **Test strategy**: Write unit test verifying `currentProductId` does NOT change after `createProduct()`; write integration test verifying task list remains populated after product creation

**Alternative (if UX wants auto-switch)**: Keep the switch but add a "Return to [previous product]" button and suppress the task store watcher during transition.

---

## Bug B: Reactivating Project Creates New Orchestrator

### Root Cause

**Incomplete status guard** in `ProjectService._ensure_orchestrator_fixture()` at `src/giljo_mcp/services/project_service.py:1150-1161`. This method is called every time a project is activated, and it only looks for orchestrators in `"waiting"` or `"working"` status. If the previous orchestrator reached any terminal status (`"complete"`, `"failed"`, `"cancelled"`), the check fails and a brand new orchestrator is unconditionally created.

### Evidence

**Evidence 1: The incomplete status guard**

File: `src/giljo_mcp/services/project_service.py`, lines 1150-1161

```python
# Check if orchestrator already exists for this project
existing_stmt = (
    select(AgentExecution)
    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
    .where(
        AgentJob.project_id == project.id,
        AgentExecution.agent_display_name == "orchestrator",
        AgentExecution.tenant_key == tenant_key,
        AgentExecution.status.in_(["waiting", "working"]),  # <-- THE BUG
    )
)
```

The filter `status.in_(["waiting", "working"])` means any orchestrator in `"complete"`, `"failed"`, `"cancelled"`, or `"blocked"` status is invisible. When the user reactivates a project, no "active" orchestrator is found, and a new one is spawned.

**Evidence 2: activate_project always calls the fixture method**

File: `src/giljo_mcp/services/project_service.py`, line 1068

```python
# At end of activate_project():
await self._ensure_orchestrator_fixture(...)
```

Every activation triggers the fixture check, which creates a new orchestrator if none matches the narrow filter.

**Evidence 3: deactivate_project does NOT change orchestrator status**

File: `src/giljo_mcp/services/project_service.py`, lines 1253-1343

`deactivate_project()` only changes `project.status` to `"inactive"`. It does NOT touch orchestrator status. So when a project is deactivated and reactivated, the orchestrator stays in whatever terminal state it was in.

**Evidence 4: Duplicate path in ThinClientPromptGenerator**

File: `src/giljo_mcp/thin_prompt_generator.py`, lines 206-218

```python
# Same incomplete status check exists here:
AgentExecution.status.in_(["waiting", "working"])
```

This is a SECOND occurrence of the same pattern, meaning the staging flow also creates duplicates.

**Evidence 5: launch_project creates unconditionally**

File: `src/giljo_mcp/services/project_service.py`, lines 1916-2096

The `launch_project()` method creates a new `AgentJob` + `AgentExecution` with NO dedup check at all. The `continue_project` endpoint (lifecycle.py:504-547) calls BOTH `continue_working()` and `launch_project()` in sequence, always creating a new orchestrator.

### Execution Flow (Step-by-Step)

**Phase 1: Initial Project Work**
1. User creates and activates project
2. `activate_project()` -> `_ensure_orchestrator_fixture()` creates orchestrator #1 (status: `"waiting"`)
3. Orchestrator works (status: `"working"`)
4. Orchestrator completes (status: `"complete"`)

**Phase 2: User Leaves**
5. User switches to another project or deactivates
6. `deactivate_project()` sets project to `"inactive"` but does NOT touch orchestrator status
7. Orchestrator #1 remains in status `"complete"`

**Phase 3: User Returns (THE BUG)**
8. User reactivates the project -> `activate_project()` called
9. `_ensure_orchestrator_fixture()` runs status check: `status.in_(["waiting", "working"])`
10. Orchestrator #1 has status `"complete"` -- does NOT match the filter
11. Check returns `None` (no existing orchestrator found)
12. **NEW orchestrator #2 created** (new `AgentJob` + `AgentExecution` with status `"waiting"`)
13. User sees a brand new orchestrator, losing continuity

### 0700-Related?

**NO.** The 0700 series did not cause this bug. It has been present since Handover 0431 (commit `0bde61d9`, 2026-01-22).

**Evidence against 0700 causation:**
- `trigger_succession()` (stubbed by 0700d) is NOT called from any activation path -- only from test files
- The succession endpoint was for explicit manual handovers, not project activation
- The old `trigger_succession` did NOT create new orchestrators -- it merely reset context and wrote to 360 Memory
- 0700b changed `"decommissioned"` to `"complete"` status, but `"decommissioned"` was NEVER in the fixture guard's allowlist either
- The tech debt document (commit `5a59c4d7`) explicitly identifies this as a known pre-existing issue

**Indirect relationship**: Before 0700d, if an orchestrator completed, users could use the succession mechanism for a graceful handover. With succession removed, the "create new orchestrator on reactivation" behavior is more visible because there is no graceful continuation path.

### Recommended Fix Approach

**Step 1: Expand status filter in `_ensure_orchestrator_fixture()` (CRITICAL)**

File: `src/giljo_mcp/services/project_service.py`, lines 1150-1161

```python
# BEFORE (buggy):
AgentExecution.status.in_(["waiting", "working"])

# AFTER - Option A (allowlist non-terminal):
AgentExecution.status.in_(["waiting", "working", "blocked"])

# AFTER - Option B (denylist terminal - more robust):
AgentExecution.status.notin_(["complete", "failed", "cancelled"])
```

**Design decision**: When a completed orchestrator is found, should the system:
- **Option A (Recommended)**: Leave it as-is, let user re-stage to get a new orchestrator explicitly
- **Option B**: Reset it to `"waiting"` status (simpler but loses completion state)

**Step 2: Align `ThinClientPromptGenerator.generate()` dedup check**

File: `src/giljo_mcp/thin_prompt_generator.py`, lines 206-218

Apply the same status filter expansion to prevent staging from creating duplicates.

**Step 3: Add dedup guard to `launch_project()`**

File: `src/giljo_mcp/services/project_service.py`, lines 1916-2096

Add a check similar to `_ensure_orchestrator_fixture()` before unconditionally creating a new orchestrator.

**Step 4: Test strategy**
- Unit test: activate project with completed orchestrator, verify no new orchestrator created
- Unit test: activate project with failed orchestrator, verify no new orchestrator created
- Integration test: full deactivate -> reactivate cycle, verify single orchestrator
- Integration test: `continue_project` does not create duplicate orchestrator

---

## Priority Assessment

**Most Critical**: **Bug A** -- Users perceive total data loss when creating a product. The UI shows an empty state for tasks, jobs, and projects, creating a high-severity UX panic moment. Even though data is intact (just viewing wrong product), users will believe their work is lost.

**Recommended Fix Order**: Bug A first (1-line frontend fix), then Bug B (multi-file backend fix)

**Estimated Complexity**:

| Bug | Complexity | Scope | Files to Modify |
|-----|-----------|-------|-----------------|
| Bug A | **LOW** | Single line removal in frontend store | 1 file (`products.js`) |
| Bug B | **MEDIUM** | Status filter expansion in 3 locations + design decision on orchestrator reuse | 3 files (`project_service.py`, `thin_prompt_generator.py`, `lifecycle.py`) |

---

## Additional Findings

### Finding 1: Double Orchestrator Creation Path via launch_project()
`launch_project()` at `project_service.py:1916-2096` creates a new orchestrator unconditionally with NO dedup check. The `continue_project` endpoint (lifecycle.py:504-547) calls both `continue_working()` and `launch_project()`, always creating a new orchestrator. This is a secondary source of orchestrator duplication beyond Bug B.

### Finding 2: Known Production Bugs in project_service.py
Per `cleanup_index.json` entries `skip-bug-001` through `skip-bug-003`:
1. **UnboundLocalError**: `total_jobs` at line 1545 -- blocks `test_get_project_summary_happy_path` and `test_get_project_orchestrator_happy_path`
2. **Validation Bug**: Complete endpoint causes 422 for valid projects -- blocks `test_complete_project_happy_path`
3. **Service Fallback Methods**: Without tenant filtering at `project_service.py:510` and `:2181`, and `message_service.py:157` (security concern per comms_log 0700-006)

### Finding 3: Product Activation's Intentional Deactivation Cascade
`ProductService.activate_product()` at lines 616-643 intentionally deactivates ALL other products for the tenant AND all projects in those deactivated products. This is by-design "Single Active Product" constraint enforcement. If a user activates the new product (separate action from creating), this cascade is expected. Bug A is specifically about CREATE (not activate) triggering the appearance of this cascade via UI context switching.

### Finding 4: effectiveProductId Priority Issue
`effectiveProductId` in `products.js:44-46` prefers `currentProductId` over `activeProduct`. This means any frontend action that sets `currentProductId` (like creating a product) overrides the server-side active product for all UI filtering. This design choice amplifies Bug A's impact.

### Finding 5: Tech Debt Doc Already Identified Bug B
Commit `5a59c4d7` (2026-02-04 17:15) documented the orchestrator duplication bug in `TECHNICAL_DEBT_v2.md` during alpha testing, confirming it was a known issue before the 0700 series code changes.

---

## 0700 Series Impact Summary

| Handover | Code Changes | Bug A Impact | Bug B Impact |
|----------|-------------|-------------|-------------|
| 0700a (Light Mode) | Frontend theme only | NONE | NONE |
| 0700b (DB Column Purge) | 7 columns removed, succession module deleted | NONE | NONE (decommissioned was never in guard) |
| 0700c (JSONB Cleanup) | messages + sequential_history removed | NONE | NONE |
| 0700d (Succession Removal) | Endpoint deleted, trigger_succession stubbed | NONE | NONE (not called from activation path) |
| 0709 (Phase Gate) | Additive column + endpoint | NONE | NONE |

**Verdict**: Both bugs are **pre-existing**, not introduced by the 0700 series. The 0700 cleanup correctly removed deprecated code without breaking activation or creation flows.

---

## Recommended Subagents for Fixes

- **Bug A Fix**: `ux-designer` (frontend store refactor, 1-file change, UX decision on post-creation behavior)
- **Bug B Fix**: `backend-integration-tester` (status filter expansion across 3 files, with TDD for each change)
- **Finding 1 (launch_project dedup)**: `system-architect` (design decision on orchestrator lifecycle management)
- **Finding 2 (Known bugs)**: `tdd-implementor` (fix UnboundLocalError and validation bug with tests)
