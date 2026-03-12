# 0815 -- Code Review Remediation (March 2026 Commits)

**Status:** Complete
**Priority:** High
**Edition Scope:** CE
**Estimated Effort:** 4-6 hours
**Branch:** `master`

---

## Problem Statement

A comprehensive 5-agent code review of 8 commits (Mar 9-11, 2026) identified 2 HIGH, 6 MEDIUM, and 5 LOW findings across backend services, frontend components, and utility modules. The two HIGH findings involve message loss risk in `message_service.py` when deadlock retries exhaust.

---

## Findings

### HIGH-1: Send path catches wrong exception type

**File:** `src/giljo_mcp/services/message_service.py:451-459`
**Root cause:** `except (ValueError, KeyError)` does not catch `RetryExhaustedError` (which inherits `ResourceError -> BaseGiljoError`). When deadlock retries exhaust, the error propagates to the API endpoint even though the message is already committed at line 243.
**Impact:** Agent receives error, retries send, creates duplicate messages.
**Fix:** Replace `except (ValueError, KeyError)` with `except RetryExhaustedError`. Log warning, continue. Counter skew is recoverable; duplicate messages are not.

### HIGH-2: Receive path has no exception handling around retry

**File:** `src/giljo_mcp/services/message_service.py:1007-1012`
**Root cause:** `with_deadlock_retry` call has no try/except. Messages are already acknowledged (committed at line 993). If counter update deadlocks exhaust, `RetryExhaustedError` propagates, agent gets error instead of messages. Re-calling `receive_messages` returns empty (already acked).
**Impact:** Messages lost from agent's perspective. Most severe finding.
**Fix:** Wrap in `except RetryExhaustedError`. Log warning, return the messages anyway.

### MEDIUM-1: WebSocket broadcast before commit (blocked->working)

**File:** `src/giljo_mcp/services/orchestration_service.py:1436`
**Root cause:** `broadcast_event_to_tenant` fires inside the `async with` session block before `session.commit()` at line 1514. If commit fails, dashboard shows stale "working" status.
**Pattern:** `get_agent_mission()` in the same file correctly broadcasts AFTER commit.
**Fix:** Accumulate event into a local variable, broadcast after the `async with` block exits.

### MEDIUM-2: logger.exception() outside except block

**File:** `src/giljo_mcp/utils/db_retry.py:113`
**Root cause:** `logger.exception()` is designed to log `sys.exc_info()` traceback. Outside an except block, it logs nothing useful.
**Fix:** Change to `logger.error(..., exc_info=last_error)`.

### MEDIUM-3: Two-commit window in receive path

**File:** `src/giljo_mcp/services/message_service.py:993,1005`
**Root cause:** Message acknowledgment committed at line 993, counter update committed separately at line 1005. Crash between = permanent counter skew.
**Fix:** Document the design trade-off. Full fix (single transaction) would require rethinking the deadlock retry boundary -- defer to future handover if counter skew is observed in production.

### MEDIUM-4: `__all__` missing Message event classes

**File:** `api/events/schemas.py:830-846`
**Root cause:** Pre-existing omission. `MessageSentData/Event`, `MessageReceivedData/Event`, `MessageAcknowledgedData/Event` defined and used but not in `__all__`.
**Fix:** Add all 6 classes to `__all__`.

### MEDIUM-5: `duration:` silently ignored in JobsTab.vue

**File:** `frontend/src/components/projects/JobsTab.vue` (14 instances)
**Root cause:** Migration from local v-snackbar to `useToast()` carried over `duration:` keys, but `ToastManager` only recognizes `timeout:`.
**Impact:** Error toasts never auto-dismiss (default `timeout: 0`). Other timeouts incorrect.
**Fix:** Replace all `duration:` with `timeout:` in this file.

### MEDIUM-6: Stale `_get_template_metadata()` function

**File:** `src/giljo_mcp/template_seeder.py:490-617`
**Root cause:** `_get_template_metadata()` still has populated `behavioral_rules`/`success_criteria` while `_get_default_templates_v103()` has them empty. Creates inconsistency.
**Fix:** Clear rules/criteria in `_get_template_metadata()` to match v103. Update layer separation test.

### LOW-1: No parameter validation in db_retry

**File:** `src/giljo_mcp/utils/db_retry.py:58-66`
**Fix:** Add `if max_retries < 1: raise ValueError(...)` and `if base_delay < 0: raise ValueError(...)`.

### LOW-2: Broadcast API inconsistency

**File:** `src/giljo_mcp/services/orchestration_service.py:1436`
**Fix:** Switch to `broadcast_to_tenant(event_type=..., data=...)` to match the 6 other broadcasts in the same file.

### LOW-3: `color:` without `type:` in TemplateManager.vue

**File:** `frontend/src/components/TemplateManager.vue` (lines 754, 759, 765, 926)
**Fix:** Change `color: 'warning'` to `type: 'warning'`, etc.

### LOW-4: Dead 3rd argument in ProjectLaunchView.vue

**File:** `frontend/src/views/ProjectLaunchView.vue` (lines 180, 206)
**Fix:** Remove the unused icon arguments.

### LOW-5: Dead guard in orchestration_service.py

**File:** `src/giljo_mcp/services/orchestration_service.py:1434`
**Fix:** Simplify `str(job.project_id) if job else None` to `str(job.project_id)` since job is guaranteed non-None (exception raised at line 1401).

---

## Implementation Plan

### Phase 1: HIGH -- Message Service Resilience (TDD)

1. Write tests for `RetryExhaustedError` handling on send path (message committed, counter exhausted -> no error to caller)
2. Write tests for `RetryExhaustedError` handling on receive path (messages acknowledged, counter exhausted -> messages still returned)
3. Fix send path: `except RetryExhaustedError as e: self._logger.warning(...)`
4. Fix receive path: wrap `_acknowledge_counters` in try/except, return messages regardless
5. Run existing 12 deadlock retry tests + new tests

### Phase 2: MEDIUM -- Backend Fixes

1. **orchestration_service.py**: Move broadcast to after commit, switch to `broadcast_to_tenant` API
2. **db_retry.py**: Fix logger, add parameter validation
3. **schemas.py**: Add 6 missing classes to `__all__`
4. **template_seeder.py**: Clear stale `_get_template_metadata()` rules/criteria, fix test

### Phase 3: MEDIUM+LOW -- Frontend Fixes

1. **JobsTab.vue**: `duration:` -> `timeout:` (14 instances)
2. **TemplateManager.vue**: `color:` -> `type:` (4 instances)
3. **ProjectLaunchView.vue**: Remove dead icon arguments (2 instances)

### Phase 4: Cleanup

1. Remove dead guard in orchestration_service.py:1434
2. Document MEDIUM-3 (two-commit window) as known design trade-off
3. Run full test suite

---

## Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `src/giljo_mcp/services/message_service.py` | 1 | Fix exception handling on both send and receive paths |
| `tests/unit/test_broadcast_deadlock_retry.py` | 1 | Add exhaustion-resilience tests |
| `src/giljo_mcp/services/orchestration_service.py` | 2 | Move broadcast, fix API, remove dead guard |
| `src/giljo_mcp/utils/db_retry.py` | 2 | Fix logger, add validation |
| `api/events/schemas.py` | 2 | Add missing `__all__` exports |
| `src/giljo_mcp/template_seeder.py` | 2 | Clear stale metadata function |
| `tests/unit/test_template_seeder_layer_separation.py` | 2 | Update assertion |
| `frontend/src/components/projects/JobsTab.vue` | 3 | duration -> timeout |
| `frontend/src/components/TemplateManager.vue` | 3 | color -> type |
| `frontend/src/views/ProjectLaunchView.vue` | 3 | Remove dead args |

---

## What NOT to Do

- Do NOT merge counter update into the same transaction as message ack (MEDIUM-3) -- this changes deadlock retry semantics and needs separate analysis
- Do NOT add new exception types -- use existing `RetryExhaustedError`
- Do NOT change the `with_deadlock_retry` utility contract -- it correctly raises `RetryExhaustedError`
- Do NOT modify ToastManager.vue -- the issue is callers using wrong parameter names

---

## Verification Checklist

- [x] Send path: message committed + counter deadlock exhausted = API returns success (not error)
- [x] Receive path: messages acknowledged + counter deadlock exhausted = messages returned to agent
- [x] Blocked->working broadcast only fires after successful commit
- [x] `db_retry.py` logs traceback on exhaustion
- [x] `db_retry.py` rejects `max_retries=0` with ValueError
- [x] Error toasts in JobsTab auto-dismiss at configured timeout
- [x] TemplateManager toasts show icons
- [x] All existing tests pass (621 passed, 0 failed)
- [x] `ruff check` passes on all modified files
- [ ] `npx eslint frontend/src/` within budget (deferred -- no eslint in dev env)

---

## Cascading Analysis

**Downstream:** `with_deadlock_retry` is only used by `message_service.py` (2 call sites). Fixing callers has zero downstream impact.
**Upstream:** No schema changes, no migration needed.
**Sibling:** ToastManager.vue is unchanged -- only callers fixed.
**Installation:** No impact on `install.py` or startup.
