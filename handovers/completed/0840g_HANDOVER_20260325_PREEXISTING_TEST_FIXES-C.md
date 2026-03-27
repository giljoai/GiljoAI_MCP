# Handover 0840g: Pre-Existing Test Failure Fixes

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Monitoring)
**To Agent:** Next Session (tdd-implementor)
**Priority:** Medium
**Estimated Complexity:** 1-2 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Fix 3 pre-existing test failures that were identified during the 0840 JSONB normalization chain. These failures existed before the 0840 work and are unrelated to JSONB normalization. Fixing them now cleans the test suite so 0840f (final validation) gets a truly clean run.

**IMPORTANT:** You are on branch `feature/0840-jsonb-normalization`. Other agents are working on this branch concurrently (0840d/e/f chain). Commit your fixes independently — do NOT touch files being modified by the 0840 chain unless strictly necessary for the fix.

## Technical Details

### Failure 1: test_orchestrator_todowrite_scoped_to_coordination

**Location:** Search for this test name in `tests/`
**Problem:** Pre-existing failure — exact cause unknown. Investigate:
1. Find the test file
2. Run it in isolation: `pytest <file>::<test_name> -xvs`
3. Diagnose the root cause
4. Fix it

### Failure 2: test_auto_block_fires_websocket_event

**Location:** Likely in `tests/services/test_message_auto_block_0827b.py`
**Problem:** Test asserts `broadcast_job_status_change` but the actual code calls `broadcast_job_status_update`. This is a simple method name mismatch in the test assertion.
**Fix:** Update the mock assertion to use the correct method name.

### Failure 3: Tuning service tests mock non-existent methods

**Location:** `tests/services/test_product_tuning_service.py`
**Problem:** Tests mock `_get_memory_entries` and `_get_user_settings` methods that don't exist on `ProductTuningService`. These are likely left over from a refactor that renamed or removed these methods.
**Fix:**
1. Find what the methods were renamed to (search for similar functionality in `product_tuning_service.py`)
2. Update the mocks to patch the correct methods
3. If the methods were removed entirely, rewrite the tests to test the current behavior

## Implementation Plan

1. Find all 3 failing tests
2. Run each in isolation to confirm the failure
3. Diagnose root cause for each
4. Fix each test (fix the TEST, not production code, unless production code is genuinely wrong)
5. Run full test suite to confirm no regressions
6. Commit and report to JSON

## Coding Principles

- TDD: Fix tests to test BEHAVIOR, not implementation details
- Clean Code: If a mock patches a non-existent method, fix it properly — don't add a stub method
- Do NOT use `--no-verify` on commits

## Reporting

After completing, write results to `prompts/0840_chain/0840g_results.json`:
```json
{
  "session_id": "0840g",
  "title": "Pre-Existing Test Fixes",
  "status": "complete|failed|partial",
  "started_at": "<timestamp>",
  "completed_at": "<timestamp>",
  "fixes": [
    {"test": "<test_name>", "root_cause": "<description>", "fix": "<what was done>", "status": "fixed|skipped|blocked"}
  ],
  "total_tests_passing": "<number>",
  "summary": "<2-3 sentences>"
}
```

## Success Criteria

- [ ] All 3 pre-existing test failures fixed
- [ ] No regressions introduced
- [ ] `ruff check src/ api/` clean
- [ ] Results written to `prompts/0840_chain/0840g_results.json`
- [ ] Committed to `feature/0840-jsonb-normalization`
