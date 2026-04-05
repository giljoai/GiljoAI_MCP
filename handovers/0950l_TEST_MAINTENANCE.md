# Handover 0950l: Test Suite: Fix Skips, Dead Fixtures, Coverage Gaps

**Date:** 2026-04-05
**From Agent:** Planning Session
**To Agent:** Next Session (testing-focused)
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0950l of 0950a–0950n — read `prompts/0950_chain/chain_log.json` first

---

## 1. Task Summary

This is the convergence point for both sprint tracks. After all backend splits (0950g–0950j) and frontend splits (0950k) are complete, run both test suites, eliminate every skip, remove every dead fixture, and fill coverage gaps on newly created composables and services. The 0950m final audit requires zero skips and counts of >= 1893 frontend and >= 661 backend before it can produce a PASS verdict.

---

## 2. Context and Background

The 0769 sprint baseline is 1,893 frontend tests / 0 skipped and 661 backend unit tests / 0 failures. The 0950 backend god-class splits (0950g–0950j) and frontend component splits (0950k) will create new code paths. Some pre-existing skips may also become stale after those refactors. This handover cleans up both.

**This handover depends on both 0950j AND 0950k being complete.** Confirm both sessions show `"status": "complete"` in the chain log before writing any code.

**Critical agent rules — read before touching any file:**
- Before deleting ANY code: verify zero upstream/downstream references using grep
- Tests that fail must be fixed or deleted — never skip
- No commented-out code — delete it
- Commit with descriptive message prefixed `cleanup(0950l):`
- Update chain log session entry at `prompts/0950_chain/chain_log.json` before stopping
- Do NOT spawn the next terminal — orchestrator handles that
- Read `orchestrator_directives` in chain log FIRST before starting work

---

## 3. Technical Details

### Scope

- `tests/` — all Python test files
- `frontend/tests/` — Vitest setup and shared utilities
- `frontend/src/**/*.spec.js` — co-located component and composable specs

---

## 4. Implementation Plan

### Phase A: Backend test suite

**Step A1: Record baseline**

```bash
cd /media/patrik/Work/GiljoAI_MCP
python -m pytest tests/unit/ -q --timeout=60 --no-cov 2>&1 | tail -5
```

Record the exact pass/fail/skip counts in the chain log.

**Step A2: Find all skipped tests**

```bash
grep -rn "@pytest.mark.skip\|pytest.skip\|skipIf\|skipUnless" /media/patrik/Work/GiljoAI_MCP/tests/
```

For each skip, apply this triage:
- Was the skip added because of a bug that the 0950 splits have now fixed? Remove the skip and confirm the test passes.
- Is the test genuinely broken and the feature still exists? Fix the test — do not leave the skip.
- Does the test cover functionality that was deleted during this sprint? Delete the test.

There is no fourth option. Zero skips is the only acceptable outcome.

**Step A3: Find dead fixtures**

```bash
grep -rn "def [a-z_]*\|@pytest.fixture" /media/patrik/Work/GiljoAI_MCP/tests/
```

For each fixture: run `grep -rn "<fixture_name>" tests/` to verify it is imported by at least one test. If zero matches: delete the fixture. If it lives in a `conftest.py` shared by multiple test files, check all files in that directory before deleting.

**Step A4: Detect stale imports from split classes**

The backend splits in 0950g–0950j may have moved classes to new module paths. Search for broken imports:

```bash
python -m pytest tests/unit/ --collect-only -q 2>&1 | grep -i "import\|error\|cannot"
```

For each stale import in a test file: update the import path to match the new module location. Do not change the test logic — only the import line.

**Step A5: Coverage gaps for new services from 0950g–0950j**

Read `notes_for_next` from chain log sessions 0950g, 0950h, 0950i, and 0950j to learn which new service modules were created. For each new module that lacks a test file: add a test file targeting >= 80% coverage on public methods. Write tests using TDD conventions (behaviour-focused, descriptive names).

**Step A6: Re-run and confirm**

```bash
python -m pytest tests/unit/ -q --timeout=60 --no-cov 2>&1 | tail -5
```

Must report >= 661 pass, 0 fail, 0 skip.

---

### Phase B: Frontend test suite

**Step B1: Record baseline**

```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run 2>&1 | tail -10
```

Record the exact pass/fail/skip counts in the chain log.

**Step B2: Find all skipped tests**

```bash
grep -rn "it\.skip\|describe\.skip\|test\.skip\|xit\b\|xdescribe\b\|xtest\b" /media/patrik/Work/GiljoAI_MCP/frontend/
```

Same triage as backend:
- Skip no longer relevant after 0950 refactor? Remove and confirm the test passes.
- Test broken and feature exists? Fix the test.
- Test covers deleted functionality? Delete the test.

Zero skips is the only acceptable outcome.

**Step B3: Coverage gaps for new composables from 0950k**

Read `notes_for_next` from chain log session 0950k to get the list of new composables. For each composable that was created in 0950k without a `.spec.js` file (or whose spec file is below 80% coverage):

1. Create or extend the `.spec.js` file in `frontend/src/composables/`
2. Mock Pinia stores with `createTestingPinia` from `@pinia/testing`
3. Mock API calls using the `vi.mock` pattern from `frontend/tests/setup.js`
4. Cover the composable's public interface — inputs, outputs, and error paths

**Step B4: Detect stale component references**

The 0950k splits will have introduced new component paths. Check for broken imports in existing tests:

```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run --reporter=verbose 2>&1 | grep -i "cannot find\|error\|failed to resolve"
```

For each broken import: update the path to the new component location.

**Step B5: Re-run full suite**

```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run 2>&1 | tail -10
```

Must report >= 1893 pass, 0 skip, 0 fail.

---

### Phase C: Commit

```bash
git add tests/ frontend/src/ frontend/tests/
git commit -m "cleanup(0950l): fix skipped tests, remove dead fixtures, fill coverage gaps"
```

---

## 5. Testing Requirements

This handover IS the testing phase. Success criteria double as testing requirements:

- Backend: `python -m pytest tests/unit/ -q --timeout=60 --no-cov` — >= 661 pass, 0 fail, 0 skip
- Frontend: `cd frontend && npx vitest run` — >= 1893 pass, 0 skip, 0 fail
- New composable spec files exist for every composable created in 0950k
- New service test files exist (or are extended) for every service split in 0950g–0950j
- No dead fixtures remain in `tests/conftest.py` or any test directory `conftest.py`

---

## 6. Dependencies and Blockers

**Must complete first (both required):**
- 0950j (god-class split: OrchestrationService + remaining backend classes) — provides new service module paths and notes for test coverage
- 0950k (frontend component splits) — provides new composable paths and notes for coverage gaps

**Must complete before:**
- 0950m (final audit) — 0950m reads the test counts as hard gates

**Known blockers:** None. If a test requires a running PostgreSQL database (integration tests), note it in the chain log and confirm it is not part of the `tests/unit/` subset.

---

## 7. Success Criteria

- Zero skipped tests in both frontend and backend suites
- Frontend: >= 1893 tests pass, 0 skip
- Backend unit: >= 661 tests pass, 0 fail, 0 skip
- Zero dead fixtures in any `conftest.py`
- Every composable created in 0950k has a `.spec.js` file with >= 80% coverage
- Every new service module from 0950g–0950j has test coverage >= 80% on public methods
- `ruff check src/ api/` — 0 issues (no regressions introduced by test file additions)

---

## 8. Rollback Plan

Test files are additive. If something goes wrong:

```bash
git checkout -- tests/
git checkout -- frontend/src/
git checkout -- frontend/tests/
```

No backend services, no migrations, no config changes in this handover.

---

## 9. Additional Resources

- Vitest setup and global mocks: `frontend/tests/setup.js`
- Existing composable spec examples: `frontend/src/composables/*.spec.js`
- pytest fixture patterns: `tests/conftest.py`
- Coverage command: `cd frontend && npx vitest run --coverage`

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 0950l** in the 0950 Pre-Release Quality Sprint. This is the convergence point for both tracks.

### Step 1: Read Chain Log and Directives

```
Read prompts/0950_chain/chain_log.json
```

Check `orchestrator_directives` for session `0950l`. If it contains "STOP", halt immediately. Read `notes_for_next` from sessions 0950g, 0950h, 0950i, 0950j, and 0950k — these list the new files you need to cover.

### Step 2: Confirm Prerequisites

Verify the chain log shows BOTH of these as `"status": "complete"`:
- `0950j`
- `0950k`

If either is not complete, halt and write a blocker in the chain log.

### Step 3: Mark Session Started

Update your session entry in `prompts/0950_chain/chain_log.json`:
```json
"status": "in_progress"
```

### Step 4: Execute

Work through Phase A (backend) then Phase B (frontend) in full. Use the `backend-integration-tester` and `frontend-tester` subagent profiles.

### Step 5: Update Chain Log Before Stopping

Update your session entry with:
- `tasks_completed`: skip count before and after (both suites), fixture deletions, new test files created
- `deviations`: any test that could not be re-enabled and was deleted instead (with reason)
- `blockers_encountered`: any issues
- `notes_for_next`: final pass/fail/skip counts for both suites, any coverage gaps that remain, any dimension concerns for 0950m
- `cascading_impacts`: none expected
- `summary`: 2-3 sentences including commit hash
- `status`: "complete"

### Step 6: Commit and STOP

```bash
git add tests/ frontend/src/ frontend/tests/
git commit -m "cleanup(0950l): fix skipped tests, remove dead fixtures, fill coverage gaps on 0950g-k new code"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950l chain log — session complete"
```

**Do NOT spawn the next terminal.** The orchestrator reviews the chain log and spawns 0950m when this session is complete.
