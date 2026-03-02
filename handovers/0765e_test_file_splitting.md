# Handover 0765e: Test File Splitting

**Date:** 2026-03-02
**Priority:** LOW-MEDIUM
**Estimated effort:** 8-12 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765e)
**Depends on:** 0765a (dead code removed), 0765d (exception narrowing may change test assertions)
**Blocks:** None

---

## Objective

Split 19 oversized test files (>500 lines each) into focused, maintainable modules. The largest file is 1,161 lines. This improves test discoverability, reduces fixture scope creep, and enables parallelized test execution.

**Score impact:** ~9.3 -> ~9.4

---

## Pre-Conditions

1. 0765a and 0765d complete — dead code and exception changes settled
2. Full test suite green before starting
3. Understand pytest fixture sharing: `conftest.py` at directory level shares fixtures across sibling test files

---

## Target Files

19 test files over 500 lines (sorted by size descending):

| # | File | Lines | Test Count (approx) | Split Strategy |
|---|------|-------|-------------------|----------------|
| 1 | `tests/services/test_orchestration_service.py` | 1,161 | ~30 | Split by orchestration phase: spawn, handoff, closeout, state machine |
| 2 | `tests/services/test_service_responses.py` | 1,143 | ~35 | Split by service: project, product, task, agent |
| 3 | `tests/services/test_project_service_integration.py` | ~900 | ~25 | Split by CRUD operation: create, read, update, delete, lifecycle |
| 4 | `tests/services/test_product_service_integration.py` | ~850 | ~22 | Split by domain: CRUD, memory, settings, templates |
| 5 | `tests/services/test_orchestration_service_websocket_emissions.py` | ~800 | ~20 | Split by event type: agent updates, project events, product events |
| 6 | `tests/api/test_project_endpoints.py` | ~750 | ~20 | Split by HTTP method: GET, POST, PUT, DELETE |
| 7 | `tests/api/test_agent_management_endpoints.py` | ~700 | ~18 | Split by agent lifecycle: create, status, commands, decommission |
| 8 | `tests/services/test_task_service.py` | ~680 | ~18 | Split by operation: create, update, complete, query |
| 9 | `tests/services/test_orchestration_service_agent_mission.py` | ~650 | ~16 | Split by mission phase: plan, execute, complete |
| 10 | `tests/services/test_successor_spawning.py` | ~630 | ~15 | Split by scenario: normal, failure, edge cases |
| 11-19 | Various | 500-620 | varies | Assess individually during execution |

**Note:** The exact line counts and test counts should be verified during execution — these are from the research report and may have shifted after 0765a deletions.

---

## Splitting Strategy

### General Principles

1. **Group by behavior, not by implementation.** Tests for "create project" go together regardless of which internal method they test.
2. **Shared fixtures go to `conftest.py`.** If a fixture is used by multiple split files, move it to the directory-level `conftest.py`.
3. **Private fixtures stay in the file.** If a fixture is only used by one test file, keep it in that file.
4. **Maintain test names.** Do not rename test functions — this preserves git blame and CI history.
5. **Target: 200-400 lines per file.** A 1,000-line file should become 3-4 files.

### Naming Convention

Split files follow the pattern:
```
test_orchestration_service.py
  -> test_orchestration_service_spawn.py
  -> test_orchestration_service_handoff.py
  -> test_orchestration_service_closeout.py
  -> test_orchestration_service_state.py
```

### Fixture Migration

When splitting a file:
1. Identify all fixtures defined in the file
2. For each fixture, determine which split files need it
3. If multiple split files need it: move to `conftest.py`
4. If only one split file needs it: keep in that file
5. Verify no circular fixture dependencies

---

## Execution Approach

### Per-File Process (~30-45 min each)

For each file:

1. **Read the file** — understand its test structure and fixture dependencies
2. **Identify natural split boundaries** — group tests by behavior/feature
3. **Map fixture usage** — which fixtures does each test group need?
4. **Create new files** — write the split files with proper imports
5. **Move shared fixtures to conftest.py** if needed
6. **Delete the original file** — the splits replace it entirely
7. **Run tests** — `pytest <directory>/ -v` to verify all tests pass
8. **Commit** — one commit per split (or batch 2-3 small splits per commit)

### Priority Order

Process the largest files first (highest value) and the most stable files first (lowest regression risk):

1. `test_service_responses.py` (natural split by service — cleanest)
2. `test_orchestration_service.py` (largest file)
3. `test_project_service_integration.py`
4. `test_product_service_integration.py`
5. Remaining files in descending size order

---

## Testing Requirements

### Per-Split Verification

After each file split:
- `pytest <split_file_1> <split_file_2> ... -v` — all tests from original file pass
- Test count matches original: no tests lost, no tests duplicated

### Final Verification

After all splits:
- `pytest tests/ -x -q` — full green suite
- Test count matches pre-split count (1238+ passed)
- No new test collection warnings

---

## Cascading Impact Analysis

- **No production code changes** — only test files are modified
- **CI configuration:** If CI runs specific test file paths, update those paths
- **Test discovery:** pytest discovers tests by pattern, not explicit path — splits should be auto-discovered
- **Fixture scope:** Moving fixtures to `conftest.py` may change their scope (function -> session). Be careful to preserve the original scope decorator.

---

## Success Criteria

- [ ] All 19 oversized test files split into focused modules
- [ ] No file over 500 lines (target: 200-400 per file)
- [ ] All tests pass — count matches pre-split baseline
- [ ] Shared fixtures properly migrated to conftest.py
- [ ] No circular fixture dependencies
- [ ] Chain log updated: 0765e = `complete`

---

## Completion Protocol

1. Run full test suite — verify count matches baseline
2. Update chain log
3. Write completion summary (max 400 words) — include split count and line reduction
4. Commit: `cleanup(0765e): Split 19 oversized test files into focused modules`
