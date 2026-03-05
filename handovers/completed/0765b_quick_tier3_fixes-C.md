# Handover 0765b: Quick Tier 3 Fixes

**Date:** 2026-03-02
**Priority:** MEDIUM
**Estimated effort:** 4-5 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765b)
**Depends on:** 0765a (dead code baseline must be clean)
**Blocks:** None (independent from 0765c-g)

---

## Objective

Execute the quick-win subset of Tier 3 items — fixes that individually take under 2 hours and collectively push the score from ~8.8 to ~9.1. These are low-risk, high-confidence changes.

**Score impact:** ~8.8 -> ~9.1

---

## Pre-Conditions

1. 0765a complete — chain log confirms `status: "complete"`
2. All tests pass, frontend builds clean
3. Read `prompts/0765_chain/chain_log.json` for 0765a deviations/notes

---

## Task 1: NPM Health Check Hardening [Proposal 3H] (~30 min)

**Files:**
- `src/giljo_mcp/startup.py` line ~619
- `src/giljo_mcp/control_panel.py` line ~1192

**Problem:** Both files check `node_modules.exists()` which passes for corrupted skeleton directories (e.g., `node_modules/` with no actual packages — can happen after interrupted `npm install`).

**Fix:** Replace `node_modules.exists()` with a more reliable check:
```python
# Check for actual installed package marker
(frontend_dir / "node_modules" / ".package-lock.json").exists()
```

**Reference:** Full analysis in `handovers/NPM_VITE_corruption_report.md`

**Testing:** Verify behavior with both valid and corrupted `node_modules/` directories.

---

## Task 2: Orphan CSS Cleanup [Proposal 3C] (~60 min)

### 2.1 Remove 6 Orphan CSS Selectors

Verify each selector is truly unused (not referenced in template, not targeted by parent component):

| File | Selector | Evidence |
|------|----------|---------|
| `frontend/src/components/projects/JobsTab.vue` | 5 orphan selectors | Selectors reference deleted elements or unused classes |
| `frontend/src/components/projects/ProjectTabs.vue` | 2 orphan selectors | Left over from refactoring |
| `frontend/src/components/AgentTableView.vue` | 1 orphan selector | Unused after component restructure |
| `frontend/src/components/StatusBoard/ActionIcons.vue` | 1 orphan selector | Will be cleaned during 0765a 2F conversion, but verify |

**Verification method:** For each CSS selector, search the component's `<template>` section for the class name or element. If not found, the selector is orphan.

### 2.2 Convert 2 Static Computeds to Constants

| File | Computed | Line | Fix |
|------|----------|------|-----|
| `frontend/src/components/StatusBoard/ActionIcons.vue` | `giljoFaceIcon` | varies | Convert from `computed(() => ...)` to `const giljoFaceIcon = ...` — value never changes |
| `frontend/src/components/StatusBoard/ActionIcons.vue` | `actionIconColor` | varies | Same treatment — static value, not reactive |

---

## Task 3: Remove Dead ProjectTabs Emits [Proposal 3D] (~60 min)

**File:** `frontend/src/components/projects/ProjectTabs.vue`

**Problem:** ProjectTabs declares 11 emits but the parent component handles only 3. The 8 unhandled emits are fire-and-forget — the child emits them but nobody listens.

**Action plan:**
1. Read ProjectTabs.vue to identify all 11 declared emits
2. Read the parent component to identify which 3 are handled
3. For the 8 unhandled emits:
   - Remove the emit declaration from `defineEmits`
   - Remove the `emit('event-name', ...)` call site in the component
   - If the emit trigger logic is ONLY used for the emit (not for other state changes), remove the trigger logic too
4. Verify the parent still receives the 3 handled emits correctly

**Risk:** VERY LOW — removing emits that nobody listens to has zero behavioral impact.

---

## Task 4: Unify Agent Sort Priority [Proposal 3E] (~60 min)

**Problem:** Two stores sort agents differently:
- `agentJobsStore`: working > silent > blocked > waiting > complete > decommissioned
- `useAgentData` composable: blocked/silent > waiting > working > complete > decommissioned

**This is a product/UX decision.** The sort order determines what users see first in the agent list.

**Recommended resolution:**
- **Active-first** (agentJobsStore pattern): working > blocked > silent > waiting > complete > decommissioned
- Rationale: Users want to see what's happening NOW first, then what's stuck, then what's idle

**Implementation:**
1. Define the canonical sort order as a shared constant (e.g., `AGENT_STATUS_PRIORITY` in a shared config)
2. Update both `agentJobsStore` and `useAgentData` to use the shared constant
3. Document the chosen order in a code comment

---

## Task 5: CORS Method/Header Restriction [Proposal 3F] (~60 min)

**Files:**
- `api/app.py` lines ~401-402
- `dev_tools/devpanel/backend/app.py` lines ~68-69

**Problem:** Both use `allow_methods=["*"]` and `allow_headers=["*"]`.

**Fix for production API (`api/app.py`):**
```python
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Tenant-Key", "X-CSRF-Token"],
```

**Fix for dev panel (`dev_tools/devpanel/backend/app.py`):**
- Dev panel can keep `["*"]` for development convenience, but add a comment explaining why
- OR restrict to the same set if the dev panel should mirror production

**Verification:** After the change, test that:
1. Normal API calls still work (GET, POST, PUT, DELETE)
2. The X-API-Key and X-Tenant-Key headers are accepted
3. OPTIONS preflight requests succeed

---

## Task 6: Remove H-24 Speculative Prefetch (~15 min)

**File:** `frontend/src/views/ProjectsView.vue` lines ~1438-1444

**Problem:** `agentStore.fetchAgents()` is called on mount even though agents are project-scoped and the data is fetched again when a project is selected. This is a speculative prefetch that loads data for ALL projects before the user picks one.

**Fix:** Remove the `agentStore.fetchAgents()` call from the mount hook. Agents should only be fetched when a specific project is selected.

**Verification:** Navigate to Projects view, verify agents load correctly when selecting a project.

---

## Execution Order

1. Task 1 (NPM) — standalone, quick
2. Task 6 (H-24) — standalone, quick
3. Task 5 (CORS) — standalone
4. Task 2 (CSS) — needs careful selector verification
5. Task 3 (Emits) — needs parent/child analysis
6. Task 4 (Sort) — product decision, do last

**Commit strategy:** One commit per task or batch related tasks. Prefix with `cleanup(0765b):`.

---

## Testing Requirements

- `npm run build` in `frontend/` — clean after CSS and emit changes
- `pytest tests/ -x -q` — full green suite
- Manual: verify agent list displays correctly after sort unification
- Manual: verify Projects view loads agents correctly after H-24 removal

---

## Cascading Impact Analysis

- **NPM check:** Only affects developer experience during `npm install` detection. No production runtime impact.
- **CSS removal:** Purely visual — verify no layout shifts in affected components.
- **Emit removal:** Zero downstream impact (emits were unhandled).
- **Sort unification:** Visual change only — agents appear in different order. No data impact.
- **CORS restriction:** Could break clients sending unexpected headers. Verify X-API-Key and X-Tenant-Key are in the allow list.
- **H-24 prefetch:** Reduces unnecessary API calls. Verify agents still load per-project.

---

## Success Criteria

- [ ] NPM health checks use `.package-lock.json` instead of `node_modules.exists()`
- [ ] 6 orphan CSS selectors removed
- [ ] 2 static computeds converted to constants
- [ ] 8 dead emits removed from ProjectTabs
- [ ] Agent sort priority unified with shared constant
- [ ] CORS methods and headers restricted to explicit lists
- [ ] H-24 speculative prefetch removed
- [ ] All tests pass, frontend builds clean
- [ ] Chain log updated: session 0765b status = `complete`

---

## Completion Protocol

1. Run full test suite and frontend build
2. Update `prompts/0765_chain/chain_log.json` — set 0765b to `complete`
3. Write completion summary back to THIS handover (max 400 words)
4. Commit: `cleanup(0765b): Quick Tier 3 fixes — CORS, CSS, emits, sort, NPM`
