# Handover 0840h: Integration & Shutdown Test Fixes

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Monitoring)
**To Agent:** Next Session (tdd-implementor + backend-tester)
**Priority:** Low
**Estimated Complexity:** 1-2 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Fix the 8 remaining integration/shutdown test failures identified during the 0840 chain. These are pre-existing failures unrelated to JSONB normalization. Cleaning them up gives us a fully green test suite.

**IMPORTANT:** You are on branch `feature/0840-jsonb-normalization`. Other agents (0840e/f) are working concurrently. Only touch test files and the specific production code causing failures. Do NOT modify files being changed by the 0840 chain (message_service.py, product_service.py, user_service.py, context_manager.py, etc.) unless absolutely necessary.

## Implementation Plan

1. Run the full test suite: `pytest tests/ --timeout=60 -v 2>&1 | tail -100` to identify all 8 failing tests
2. For each failure:
   - Run in isolation: `pytest <file>::<test> -xvs`
   - Diagnose root cause
   - Fix the test (or production code if genuinely buggy)
3. Run full suite again to confirm all green
4. Commit and report

## Coding Principles

- Fix tests to test BEHAVIOR, not implementation details
- If a test mocks something that was renamed/removed, update the mock
- If a test depends on shutdown/teardown order, make it robust
- Do NOT use `--no-verify` on commits
- `ruff check src/ api/` must pass clean

## Reporting

Write results to `prompts/0840_chain/0840h_results.json`:
```json
{
  "session_id": "0840h",
  "title": "Integration & Shutdown Test Fixes",
  "status": "complete|partial|failed",
  "started_at": "<timestamp>",
  "completed_at": "<timestamp>",
  "fixes": [
    {"test": "<test_name>", "file": "<file_path>", "root_cause": "<description>", "fix": "<what was done>", "status": "fixed|skipped|blocked"}
  ],
  "total_tests_passing": "<number>",
  "total_tests_failing": "<number>",
  "summary": "<2-3 sentences>"
}
```

## Success Criteria

- [ ] All 8 integration/shutdown test failures diagnosed
- [ ] As many as possible fixed (some may be environment-specific)
- [ ] No regressions introduced
- [ ] `ruff check src/ api/` clean
- [ ] Results written to `prompts/0840_chain/0840h_results.json`
- [ ] Committed to `feature/0840-jsonb-normalization`
