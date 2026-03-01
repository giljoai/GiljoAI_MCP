# 0750b: Test Suite Triage

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 2 of 7
**Branch:** `0750-cleanup-sprint`
**Priority:** HIGH — blocks all future validation

### Reference Documents
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 2 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md`
- **Dependency graph:** `docs/cleanup/dependency_graph.json` — 801 test nodes. Test orphan status is expected (tests are leaf nodes). Do NOT use orphan status to decide test fate.
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750a `notes_for_next` before starting.

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The test suite currently cannot run cleanly. `test_field_key_mismatches.py` causes a collection error that blocks the entire suite. Multiple test files have `TODO(0127a-2)` skip markers referencing the old MCPAgentJob model. The goal is a GREEN test suite — all pass or skip, zero failures, zero collection errors.

This is a triage, not a rewrite. Delete aggressively, preserve selectively.

---

## Scope

### 2A: Delete Known-Broken Tests

- [ ] **Delete `tests/unit/test_field_key_mismatches.py`** — causes collection error, blocks entire suite
- [ ] **Delete all `TODO(0127a-2)` skip-marked tests** — reference old MCPAgentJob model, will never pass without full rewrite:
  - `tests/integration/test_hierarchical_context.py`
  - `tests/integration/test_message_queue_integration.py`
  - `tests/integration/test_orchestrator_template.py`
  - `tests/integration/test_upgrade_validation.py`
  - `tests/performance/test_database_benchmarks.py`
- [ ] **Find other collection failures**: Run `python -m pytest tests/ --co -q 2>&1 | grep ERROR`. For each:
  - Read the file — understand what it tests
  - Is the error a simple import fix? Fix it.
  - Does it reference deleted code/models? Delete it.
  - Document what you deleted and why.
- [ ] **Run full suite, record baseline**: `python -m pytest tests/ -q --timeout=60`. Record pass/fail/skip counts.

### 2B: Identify Core Tests

- [ ] **Create `tests/CORE_TESTS.md`** listing critical test files that must always pass:
  - Tenant isolation tests (`test_tenant_isolation*`) — SaaS critical
  - Service layer tests (`test_*_service.py`) — business logic
  - Repository tests (`test_*_repository.py`) — data layer
  - Auth/security tests — any test covering authentication
- [ ] **Protect shared test infrastructure**: The dependency graph shows `tests/helpers/test_db_helper.py` has 54 test dependents. This file and any other shared helpers must NOT be deleted. Identify them.
- [ ] **Remove dead fixtures**: Check `tests/fixtures/` and `tests/conftest.py` for fixtures never imported by surviving test files. Grep for each fixture name before deleting.

### 2C: Fix Failing Core Tests (only if needed)

- [ ] If any test in CORE_TESTS.md fails: fix it
- [ ] If any test NOT in CORE_TESTS.md fails: delete it (you'll write better tests during feature work)
- [ ] **Final green run**: `python -m pytest tests/ -q --timeout=60` must exit 0

---

## What NOT To Do

- Do NOT rewrite tests — this is triage, not improvement
- Do NOT add new tests — that comes in later phases
- Do NOT modify production code to make tests pass — if a test fails because production code is broken, note it in chain log as a blocker for a future phase
- Do NOT delete test files just because the dependency graph shows them as orphans — all tests are leaf nodes
- Do NOT delete `tests/helpers/test_db_helper.py` or other shared test infrastructure

---

## Acceptance Criteria

- [ ] `python -m pytest tests/ --co -q` collects with zero errors
- [ ] `python -m pytest tests/ -q --timeout=60` runs green (all pass or skip, zero failures)
- [ ] `tests/CORE_TESTS.md` exists listing critical test files
- [ ] Dead fixtures removed
- [ ] Shared test infrastructure preserved
- [ ] Counts recorded: tests before, tests after, files deleted

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit
Stage only test files and CORE_TESTS.md. Do NOT stage production code changes.
```bash
git add tests/ -A
git commit -m "test(0750b): Triage test suite — delete broken tests, identify core, achieve green"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, update session `0750b`:
- `"status": "complete"`
- `"completed_at"`: timestamp
- `"tasks_completed"`: what you did
- `"deviations"`: changes from plan
- `"blockers_encountered"`: issues (especially production code bugs found via tests)
- `"notes_for_next"`: critical context — what tests remain, what coverage gaps exist, any production bugs discovered
- `"summary"`: 2-3 sentences

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, update `phases[1]`:
- `"status": "complete"`
- `"commits": ["<hash>"]`
- `"notes"`: brief summary including before/after test counts

### Step 6: Done
Do NOT spawn the next terminal. Print "0750b COMPLETE" as your final message.
