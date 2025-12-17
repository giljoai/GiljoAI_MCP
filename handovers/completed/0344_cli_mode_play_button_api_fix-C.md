# Handover 0344: CLI Mode Play Button API Fix

**Date:** 2025-12-11
**From Agent:** Claude Opus 4.5 (Research Complete)
**To Agent:** TDD Implementor
**Priority:** Critical
**Estimated Complexity:** 30 minutes
**Status:** Ready for Implementation

---

## Task Summary

The orchestrator play button (▶) on the Jobs Tab ({} IMPLEMENT) is broken in Claude Code CLI mode. Three bugs prevent the implementation prompt from being copied to clipboard.

**Why it matters:** Users cannot copy the CLI mode implementation prompt, blocking the entire Stage 2 execution workflow.

**Expected outcome:** Clicking the orchestrator play button copies the implementation prompt to clipboard.

---

## Root Causes (3 Bugs)

### Bug 1: `api.get` Does Not Exist (CRITICAL)

**File:** `frontend/src/components/projects/JobsTab.vue:598`

```javascript
const response = await api.get(`/api/prompts/implementation/${props.project.id}`)
```

**Problem:** The `api` object is a namespace, NOT an axios client. It has no `.get()` method.

**Result:** `TypeError: api.get is not a function` - crashes before making HTTP request.

### Bug 2: Wrong URL Path

Even if `api.get` existed:
- **Calls:** `/api/prompts/implementation/...`
- **Backend expects:** `/api/v1/prompts/implementation/...`

Missing `/v1` prefix causes 404.

### Bug 3: No Helper Method

`api.prompts.implementation()` doesn't exist in `api.js`.

---

## Files to Modify

| File | Line | Change |
|------|------|--------|
| `frontend/src/services/api.js` | ~564 | Add `implementation()` method |
| `frontend/src/components/projects/JobsTab.vue` | 598 | Use `api.prompts.implementation()` |

---

## Implementation Plan

### Step 1: Add API Helper (api.js)

**File:** `frontend/src/services/api.js`

Find the `prompts:` object (around line 554-564) and add:

```javascript
prompts: {
  estimateTokens: (data) => apiClient.post('/api/v1/prompts/estimate-tokens', data),
  staging: (projectId, params) =>
    apiClient.get(`/api/v1/prompts/staging/${projectId}`, { params }),
  execution: (orchestratorJobId, claudeCodeMode) =>
    apiClient.get(`/api/v1/prompts/execution/${orchestratorJobId}`, {
      params: { claude_code_mode: claudeCodeMode },
    }),
  agentPrompt: (agentJobId) => apiClient.get(`/api/v1/prompts/agent/${agentJobId}`),
  // ADD THIS LINE:
  implementation: (projectId) => apiClient.get(`/api/v1/prompts/implementation/${projectId}`),
},
```

### Step 2: Update JobsTab Handler

**File:** `frontend/src/components/projects/JobsTab.vue`

Change line 598:

```javascript
// FROM:
const response = await api.get(`/api/prompts/implementation/${props.project.id}`)

// TO:
const response = await api.prompts.implementation(props.project.id)
```

---

## Testing Requirements

### Manual Test
1. Navigate to a project with `execution_mode === 'claude_code_cli'`
2. Complete staging (orchestrator status should be `'working'`)
3. Go to Jobs Tab ({} IMPLEMENT)
4. Click orchestrator's play button (▶)
5. **Expected:** Toast shows "Implementation prompt copied!"
6. **Verify:** Paste from clipboard - should contain 7-section implementation prompt

### Error Cases
- Project not in CLI mode → Toast: "Project is not in CLI mode..."
- No active orchestrator → Toast: "No active orchestrator found..."
- No spawned agents → Toast: "No agent jobs spawned yet..."

---

## Success Criteria

- [ ] `api.prompts.implementation()` method exists
- [ ] JobsTab uses the new method (not `api.get`)
- [ ] Clicking play button copies prompt to clipboard
- [ ] Error handling shows appropriate toast messages
- [ ] Follows existing api.js patterns

---

## Backend Validation (Already Working)

Endpoint `GET /api/v1/prompts/implementation/{project_id}` requires:
1. Project exists and belongs to tenant
2. `execution_mode === 'claude_code_cli'`
3. Active orchestrator with `status === 'working'`
4. At least one spawned agent with status `'waiting'` or `'working'`

---

## Related Handovers

- 0337: CLI Mode Implementation Prompt (created the backend endpoint)
- 0341: CLI Mode Stage 2 Implementation Prompt (workflow documentation)
- 0260: Claude Code CLI Mode (execution mode toggle)

---

## Commands

```bash
# Frontend dev server
cd frontend && npm run dev

# Verify API registration
grep -n "implementation" api/endpoints/prompts.py
grep -n "prompts.router" api/app.py
```
