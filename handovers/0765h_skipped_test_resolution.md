# Handover 0765h: Skipped Test Resolution

**Date:** 2026-03-03
**Priority:** HIGH
**Estimated effort:** 8-12 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765h)
**Depends on:** 0765g (all code quality changes landed)
**Blocks:** Manual product testing by user

---

## Objective

Analyze and resolve ALL ~342 skipped tests. Every skipped test must be triaged into one of three outcomes: DELETE (dead/obsolete), REPLACE (rewrite for current API), or FIX (minor update to pass). Zero skipped tests should remain when this handover is complete.

After this handover, the user will manually test the product end-to-end.

**Target state:** All tests either pass or are deleted. Zero skips.

---

## Pre-Conditions

1. 0765a-g all complete — full code quality sprint landed
2. Read chain log for all predecessor deviations and notes
3. Baseline: ~1,410 passed, ~342 skipped, 0 failed

---

## Phase 1: Inventory and Triage (~2 hours)

### 1.1 Collect All Skipped Tests

Run pytest to get the full skip list:
```bash
pytest tests/ --co -q 2>/dev/null | grep -c "test"  # total count
pytest tests/ -v --no-header 2>/dev/null | grep "SKIPPED"  # full list with reasons
```

Also search for skip markers in code:
```bash
grep -rn "@pytest.mark.skip" tests/ --include="*.py"
grep -rn "pytest.skip(" tests/ --include="*.py"
```

### 1.2 Categorize Each Skip

For EVERY skipped test, assign one of three verdicts:

| Verdict | Criteria | Action |
|---------|----------|--------|
| **DELETE** | Tests dead functionality, removed endpoints, or obsolete patterns | Delete the test function/file |
| **REPLACE** | Tests valid behavior but uses old API (dict returns instead of exceptions/Pydantic models) | Rewrite assertions for current API |
| **FIX** | Minor issue — missing fixture, wrong import, small assertion update | Fix and un-skip |

### 1.3 Common Skip Reasons (Expected)

Based on the 0750 sprint history, most skips fall into these buckets:

| Skip Reason | Expected Count | Likely Verdict |
|-------------|---------------|----------------|
| `0750b: needs dict-to-Pydantic rewrite` | ~200+ | REPLACE — rewrite assertions |
| `0750b: needs dict-to-exception rewrite` | ~80+ | REPLACE — change from dict checks to exception checks |
| Async fixture issues | ~30 | FIX or DELETE — pytest-asyncio auto mode may have resolved these |
| Missing fixture / stale import | ~20 | FIX or DELETE |
| Manual/interactive tests | ~10 | DELETE — not automated tests |

### 1.4 Triage Output

Create a triage table (in-memory, not committed) with columns:
- Test file
- Test function
- Skip reason
- Verdict (DELETE / REPLACE / FIX)
- Estimated effort

Use this to plan execution order: DELETE first (instant), FIX second (quick), REPLACE last (most work).

---

## Phase 2: Delete Obsolete Tests (~1 hour)

Delete all tests verdicted as DELETE:
- Tests for removed endpoints/services
- Tests for dict-return patterns on code that no longer exists
- Manual/interactive tests that aren't part of CI
- Duplicate tests (same behavior tested in multiple places)

**After deletion:** Run `pytest tests/ -x -q` to verify no collection errors.

---

## Phase 3: Fix Quick Wins (~1-2 hours)

Fix all tests verdicted as FIX:
- Update imports for moved/renamed symbols
- Fix fixture references broken by 0765e file splitting
- Remove skip markers where pytest-asyncio auto mode resolved the issue
- Update small assertion mismatches

**After fixes:** Run `pytest tests/ -x -q` — count should increase.

---

## Phase 4: Rewrite Dict-Return Tests (~4-6 hours)

This is the bulk of the work. Tests that assert on `{"success": True, "data": ...}` dict responses need rewriting to assert on Pydantic model responses or exception handling.

### 4.1 Pattern: Service Layer Dict-to-Exception

```python
# BEFORE (dict return)
result = await service.do_thing(...)
assert result["success"] is True
assert result["data"]["id"] == expected_id

# AFTER (exception-based)
result = await service.do_thing(...)
assert result.id == expected_id
# Error case:
with pytest.raises(ResourceNotFoundError):
    await service.do_thing(bad_id)
```

### 4.2 Pattern: API Endpoint Dict-to-Pydantic

```python
# BEFORE (raw dict)
response = await client.get("/api/v1/projects/123")
data = response.json()
assert data["success"] is True

# AFTER (Pydantic response)
response = await client.get("/api/v1/projects/123")
assert response.status_code == 200
data = response.json()
assert data["id"] == "123"
```

### 4.3 Execution Strategy

Use subagents — one per service/domain area:
- Project service tests
- Product service tests
- Task service tests
- Orchestration service tests
- Auth/org tests
- Tool tests
- API endpoint tests

Each subagent takes a batch of skipped tests, rewrites them, and verifies they pass.

---

## Phase 5: Final Verification (~30 min)

1. `pytest tests/ -x -q` — ALL tests pass
2. `pytest tests/ -v 2>/dev/null | grep "SKIPPED"` — ZERO skips
3. `npm run build` in frontend/ — clean
4. Record final counts in chain log

---

## Cascading Impact Analysis

- **No production code changes** in Phases 2-3 (delete/fix are test-only)
- **Phase 4 rewrites** are test-only — they adapt tests to the current API, not the other way around
- **If a rewrite reveals a real bug** (test was skipped because the feature is actually broken): document it, create a separate fix, don't leave the test skipped

---

## Testing Requirements

The ENTIRE POINT of this handover is tests. The success metric is simple:
- **Before:** ~1,410 passed, ~342 skipped, 0 failed
- **After:** X passed (higher), 0 skipped, 0 failed

---

## Success Criteria

- [ ] All ~342 skipped tests triaged (DELETE / REPLACE / FIX)
- [ ] Zero skipped tests remain
- [ ] Zero test failures
- [ ] Total passed count documented
- [ ] Frontend builds clean
- [ ] Chain log updated: 0765h = `complete`
- [ ] Product ready for manual testing by user

---

## Completion Protocol (FINAL IN CHAIN)

1. Run full test suite — document final counts
2. Update chain log:
   - Set 0765h status to `complete`
   - Set `final_status` to `complete`
   - Write `chain_summary` summarizing the entire 0765 series including test resolution
3. Write completion summary to THIS handover (max 400 words)
4. Commit: `tests(0765h): Resolve all 342 skipped tests — zero skips remaining`
5. Report to user: "Product is ready for manual testing"
6. Do NOT spawn another terminal — chain is complete, user takes over
