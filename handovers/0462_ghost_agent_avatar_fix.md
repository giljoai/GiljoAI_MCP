# Handover 0462: Ghost Agent Avatar Fix ("??" Display Bug)

**Status:** READY FOR IMPLEMENTATION
**Priority:** CRITICAL (Production Bug)
**Type:** Bug Fix - Frontend Race Condition
**Estimated Effort:** 30-45 minutes (code change is small)
**Date Created:** 2026-01-25
**Last Updated:** 2026-01-25 (with actual code state verified)

---

## Executive Summary

Spawned agents display "??" avatars instead of proper initials (e.g., "AN", "DO", "TE"). The bug:
- Appears immediately after agent spawning in LaunchTab
- Goes away on page refresh (database has complete data)
- Affects spawned agents but NOT the orchestrator
- Was introduced during the Agent ID Swap complexity work (0460) and persists after simplification (0461)

**Root Cause:** Frontend `setJobs()` function uses a destructive replace pattern that races with WebSocket events, causing data loss when multiple agents spawn in rapid succession.

**Key Insight:** The `upsertJob()` function is already well-implemented with proper merge logic. The bug is ONLY in `setJobs()`.

---

## Current Code State (Verified 2026-01-25)

### File: `frontend/src/stores/agentJobsStore.js`

**THE BUG - Lines 111-120** (`setJobs()` function):
```javascript
function setJobs(rows = []) {
  const next = new Map()  // <-- BUG: Creates EMPTY map, discarding ALL existing data
  for (const rawJob of ensureArray(rows)) {
    const job = normalizeJob(rawJob)
    if (!job.unique_key) continue
    // Use unique_key (job_id + instance_number) to allow multiple succession instances
    next.set(job.unique_key, job)
  }
  jobsById.value = next  // <-- Replaces entire state with only API data
}
```

**Lines 8-23** (`normalizeJob()` - reference, may need minor update):
```javascript
function normalizeJob(rawJob) {
  const job_id = rawJob?.job_id || rawJob?.id || rawJob?.agent_id
  const instance_number = rawJob?.instance_number || 1
  // Unique key for Map storage - prefer execution_id (true unique row ID)
  // Fallback to composite key for backward compatibility
  const unique_key = rawJob?.execution_id || `${job_id}-${instance_number}`
  return {
    ...rawJob,
    job_id,
    instance_number,
    unique_key,  // Used as Map key - execution_id when available (production-grade)
    messages_sent_count: rawJob?.messages_sent_count ?? 0,
    messages_waiting_count: rawJob?.messages_waiting_count ?? 0,
    messages_read_count: rawJob?.messages_read_count ?? 0,
  }
}
```

**Lines 122-187** (`upsertJob()` - ALREADY CORRECT, DO NOT MODIFY):
The `upsertJob()` function already has proper merge logic with multi-ID search (agent_id, execution_id, job_id). This is NOT the bug.

---

## Historical Context

### Timeline of Bug Origin

| Handover | Date | Event | Impact |
|----------|------|-------|--------|
| - | Dec 25, 2025 | `agentJobsStore.js` created | setJobs() had destructive replace from day 1 |
| 0460 | Jan 2026 | Agent ID Swap introduced | Multiple IDs per agent made race condition VISIBLE |
| 0460 | Jan 2026 | Documented similar bug | "duplicate agent entries appeared in UI" |
| 0461 | Jan 2026 | Agent ID Swap removed | Backend simplified, frontend race condition NOT addressed |
| 0461g | Jan 2026 | Quality polish | Surface-level fixes, architectural issue remains |

### The `_orchestrator_tool_accessor_consolidation` Branch

This branch was NOT the cause. It actually **REDUCED** complexity by 9,222 lines (consolidating orchestrator logic into OrchestrationService). The bug predates this work.

### Why The Bug Became Visible with 0460

Before 0460, agents had a simpler identity model. The Agent ID Swap introduced:
- **agent_id**: Executor instance UUID (the WHO)
- **execution_id**: Another UUID for execution tracking
- **job_id**: Work order identifier (the WHAT)
- **instance_number**: For succession tracking

This created `unique_key` calculation inconsistencies:

| Source | Has execution_id? | Resulting unique_key |
|--------|-------------------|---------------------|
| agent:created WebSocket | Sometimes | May be `${job_id}-1` |
| API /api/agent-jobs/ | Always | `execution_id` (UUID) |

The same agent can have TWO different keys, creating duplicate entries where one has data and one shows "??".

---

## Technical Root Cause Analysis

### Finding 1: Frontend Build Status

**Check if build exists:**
```bash
ls -la F:/GiljoAI_MCP/frontend/dist/
```

If missing, source file changes aren't deployed. Run `npm run build`.

### Finding 2: WebSocket Payload is CORRECT

Backend IS sending `agent_display_name` correctly in all events:

| Event Type | Broadcast Location | `agent_display_name` Present |
|------------|-------------------|------------------------------|
| `agent:created` | `orchestration.py:1680-1704` | YES |
| `agent:created` | `websocket.py:802-817` | YES |
| `job:progress_update` | `orchestration_service.py:1532-1547` | YES |
| `job:mission_acknowledged` | `orchestration_service.py:1538` | YES |

**Proof from logs:**
```
23:47:21 - Broadcasting agent:created for analyzer (analyzer) via direct WebSocket
```
Format is `"for {agent_name} ({agent_display_name})"` - both values present.

**NO BACKEND CHANGES NEEDED.**

### Finding 3: The Race Condition (ARCHITECTURAL)

**Race Condition Timeline:**
```
T0: WebSocket: agent:created for ANALYZER arrives
T1: upsertJob() adds ANALYZER with complete data - Avatar shows "AN"
T2: API call loadJobs() triggered (by component mount or refetch)
T3: WebSocket: agent:created for DOCUMENTER arrives
T4: upsertJob() adds DOCUMENTER with complete data - Avatar shows "DO"
T5: API response returns (from T2) - contains only ANALYZER (DOCUMENTER not in DB yet)
T6: setJobs() REPLACES entire map with only ANALYZER - DOCUMENTER DATA IS LOST
T7: Later WebSocket event for DOCUMENTER creates orphan entry with different unique_key
T8: User sees DOCUMENTER with "??" because the entry with data was overwritten
```

**Why TESTER Often Works:**
TESTER was typically the LAST agent created, so no subsequent `setJobs()` call overwrote its data.

---

## Implementation Plan

### Task 1: Build Frontend (1 minute)

```bash
cd F:/GiljoAI_MCP/frontend
npm run build
```

### Task 2: Fix `setJobs()` (CRITICAL - Lines 111-120)

**File:** `frontend/src/stores/agentJobsStore.js`

**Replace lines 111-120 with:**

```javascript
function setJobs(rows = []) {
  // Handover 0462: Start with existing data to prevent race condition data loss
  // WebSocket events may have delivered data that API response doesn't contain yet
  const next = new Map(jobsById.value)

  for (const rawJob of ensureArray(rows)) {
    const job = normalizeJob(rawJob)
    if (!job.unique_key) continue

    // Check if this job already exists under a different key (identity matching)
    let existingKey = null
    if (job.agent_id) {
      for (const [key, existing] of next.entries()) {
        if (existing.agent_id === job.agent_id) {
          existingKey = key
          break
        }
      }
    }
    // Also try job_id if agent_id didn't match
    if (!existingKey && job.job_id) {
      for (const [key, existing] of next.entries()) {
        if (existing.job_id === job.job_id && existing.instance_number === job.instance_number) {
          existingKey = key
          break
        }
      }
    }

    if (existingKey && existingKey !== job.unique_key) {
      // Job exists under different key - merge and migrate to new key
      const existingJob = next.get(existingKey)
      next.delete(existingKey)
      next.set(job.unique_key, {
        ...existingJob,
        ...job,
        // Preserve identity fields if API response lacks them (the core fix)
        agent_display_name: job.agent_display_name || existingJob.agent_display_name,
        agent_name: job.agent_name || existingJob.agent_name,
      })
    } else if (next.has(job.unique_key)) {
      // Same key exists - merge preserving identity fields
      const existingJob = next.get(job.unique_key)
      next.set(job.unique_key, {
        ...existingJob,
        ...job,
        agent_display_name: job.agent_display_name || existingJob.agent_display_name,
        agent_name: job.agent_name || existingJob.agent_name,
      })
    } else {
      // New job from API
      next.set(job.unique_key, job)
    }
  }

  jobsById.value = next
}
```

### Task 3: Update `normalizeJob()` (OPTIONAL but recommended - Lines 8-23)

**Standardize unique_key to prefer agent_id:**

```javascript
function normalizeJob(rawJob) {
  const job_id = rawJob?.job_id || rawJob?.id || rawJob?.agent_id
  const instance_number = rawJob?.instance_number || 1
  // Handover 0462: Prefer agent_id (executor UUID) - always present and unique after spawn
  // This prevents unique_key mismatches between WebSocket and API data
  const unique_key = rawJob?.agent_id ||
                     rawJob?.execution_id ||
                     `${job_id}-${instance_number}`
  return {
    ...rawJob,
    job_id,
    instance_number,
    unique_key,
    messages_sent_count: rawJob?.messages_sent_count ?? 0,
    messages_waiting_count: rawJob?.messages_waiting_count ?? 0,
    messages_read_count: rawJob?.messages_read_count ?? 0,
  }
}
```

### Task 4: Rebuild Frontend

```bash
cd F:/GiljoAI_MCP/frontend
npm run build
```

---

## Alternative Simpler Fix

If the full merge logic seems complex, here's a minimal fix that just preserves identity fields:

**Replace lines 111-120 with:**
```javascript
function setJobs(rows = []) {
  const next = new Map()
  for (const rawJob of ensureArray(rows)) {
    const job = normalizeJob(rawJob)
    if (!job.unique_key) continue

    // Handover 0462: Preserve identity fields from existing entry if API lacks them
    const existing = jobsById.value.get(job.unique_key)
    if (existing) {
      job.agent_display_name = job.agent_display_name || existing.agent_display_name
      job.agent_name = job.agent_name || existing.agent_name
    }

    next.set(job.unique_key, job)
  }
  jobsById.value = next
}
```

**Trade-off:** This simpler fix won't handle cases where WebSocket created an entry with a different `unique_key` than API uses. The full merge logic handles that edge case.

---

## Files Modified

| Priority | File | Change | Lines |
|----------|------|--------|-------|
| CRITICAL | `frontend/src/stores/agentJobsStore.js` | Replace `setJobs()` | 111-120 |
| OPTIONAL | `frontend/src/stores/agentJobsStore.js` | Update `normalizeJob()` unique_key | 13 |

---

## Verification Steps

### Post-Fix Verification

1. Run `npm run build` in frontend/
2. Restart server or hard refresh browser
3. Clear browser cache (Ctrl+Shift+R)
4. Open DevTools Console (F12)
5. Create new project
6. Stage with 6+ agents
7. **Expected:** ALL avatars show correct initials:
   - Orchestrator → "OR"
   - Analyzer → "AN"
   - Implementer → "IM"
   - Tester → "TE"
   - Documenter → "DO"
   - Reviewer → "RE"

### Debug Logging (Optional)

Add temporarily to `handleCreated()` (line 209):
```javascript
function handleCreated(payload) {
  console.debug('[handleCreated]', {
    agent_display_name: payload?.agent_display_name,
    agent_name: payload?.agent_name,
    store_size: jobsById.value.size,
  })
  upsertJob(payload)
}
```

---

## Why This Fix is Production-Grade

1. **Non-Breaking:** Merge pattern is additive - existing functionality preserved
2. **Defensive:** Searches by multiple identifiers (agent_id, job_id, unique_key)
3. **Consistent:** Preserves identity fields even when API lacks them
4. **Observable:** Debug logging available for verification
5. **Tested Pattern:** Map merge pattern is industry-standard

---

## Relationship to Previous Work

| Handover | What It Did | Frontend Fix? |
|----------|-------------|---------------|
| 0460 | Introduced Agent ID Swap complexity | NO |
| 0461 | Removed Agent ID Swap from backend | NO |
| 0461g | Quality polish | NO |
| **0462** | **Fixes frontend race condition** | **YES** |

---

## Commit Message Template

```
fix(frontend): Ghost agent avatar race condition (0462)

Root cause: setJobs() replaced entire Map, losing WebSocket data
when API responses raced with real-time events.

Changes:
- setJobs() now merges with existing data instead of replacing
- Preserves agent_display_name from WebSocket when API lacks it
- Searches by agent_id/job_id for identity matching

Fixes: Ghost "??" avatars on spawned agents
Related: 0460 (introduced visibility), 0461 (simplified backend)
```

---

## Success Criteria

- [ ] `npm run build` completes successfully
- [ ] All 6+ spawned agents show correct initials immediately
- [ ] No "??" avatars appear during rapid spawning
- [ ] Page refresh shows consistent data
- [ ] No regressions in existing agent job functionality

---

## Notes for Implementing Agent

1. **DO NOT modify `upsertJob()`** - it's already correct with proper merge logic
2. The core fix is ONLY in `setJobs()` - make it merge-aware
3. Build frontend after making changes (`npm run build`)
4. The backend is correct - NO Python changes needed
5. Test with 6+ agents spawned rapidly to verify the race condition is fixed
6. The simpler fix works for most cases; use full merge if edge cases appear

---

## Relationship to Handover 0463 (Cross-Project Ghost Rows)

**IMPORTANT:** There are TWO distinct "ghost agent" bugs. This handover (0462) and handover 0463 are **COMPLEMENTARY, not duplicative**.

### Comparison Table

| Aspect | 0462 (THIS HANDOVER) | 0463 (SEPARATE) |
|--------|---------------------|-----------------|
| **Bug** | "??" avatars (missing `agent_display_name`) | Cross-project ghost rows |
| **Symptom** | Avatar shows "??" instead of "AN", "DO" | Agent from Project B appears in Project A |
| **Root Cause** | `setJobs()` replaces Map, losing WebSocket data | `agent:status_changed` broadcast tenant-wide without `project_id` |
| **Scope** | Frontend only | Backend + Frontend |
| **Fix Location** | `agentJobsStore.js` lines 111-120 | `websocket.py` + `websocketEventRouter.js` |
| **Disappears On** | Never (stays as "??") | Refresh/navigation (API reload fixes it) |
| **Effort** | 30-45 minutes | 6-10 hours |

### How They're Connected

Both bugs trace back to the **0460/0461 "complexity era"**:
- 0460 introduced Agent ID Swap → more events → exposed latent bugs
- 0461 simplified backend but left frontend issues
- 0462 fixes: data race **within** correct project scope
- 0463 fixes: events **crossing** project boundaries

### Implementation Order

1. **Implement 0462 FIRST** (this handover) - simpler, frontend-only
2. **Implement 0463 SECOND** - larger scope, requires backend changes

### Optional Hardening (From 0463)

0463 suggests an additional safeguard that could be added here:

> *"Consider a strict mode: refuse to `upsertJob` from status-only events unless the job already exists in the project store"*

This is **optional** if the core `setJobs()` fix is implemented correctly, but provides defense-in-depth.

**Implementation (if desired):**
```javascript
function handleStatusChanged(payload) {
  // Handover 0462 hardening (from 0463 recommendation):
  // Only update existing jobs, don't create new ones from status events
  const existingKey = resolveJobId(payload?.job_id) || resolveJobId(payload?.agent_id)
  if (!existingKey) {
    // Job not in store - this might be cross-project leak, ignore
    console.debug('[handleStatusChanged] Ignoring status for unknown job:', payload?.job_id)
    return
  }
  upsertJob(payload)
}
```

This prevents ghost rows from `status_changed` events while 0463's proper fix is pending.
