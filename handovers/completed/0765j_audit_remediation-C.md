# Handover 0765j: Audit Remediation

**Date:** 2026-03-03
**Priority:** CRITICAL (3 security items)
**Estimated effort:** 2 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765j)
**Depends on:** 0765i (audit findings)
**Blocks:** Branch merge to master

---

## Objective

Fix all 10 findings from the 0765i quality audit. The audit scored 8.2/10 against a 9.5 target. These fixes should bring the score to >= 9.0/10.

**Target state:** All 10 items resolved, all tests passing, frontend clean.

---

## Pre-Conditions

1. Read `handovers/0765i_quality_audit.md` — the full audit report with line numbers
2. Read `prompts/0765_chain/chain_log.json` — verify 0765i = complete
3. Baseline: 1453 passed, 0 skipped, 0 failed

---

## Bucket 1: SECURITY + HIGH Bugs (~22 min)

Fix these FIRST. These are real correctness and security issues.

### Item 1: SECURITY — VisionDocument tenant filter missing
**File:** `api/endpoints/context.py:246`
**Problem:** VisionDocument query lacks tenant_key filter — cross-tenant data leak
**Fix:** Add `.where(VisionDocument.tenant_key == tenant_key)` to the query
**Test:** Verify with existing tenant isolation tests

### Item 2: SECURITY — MCP session tenant filter missing
**File:** `api/endpoints/mcp_session.py:195`
**Problem:** MCP session lookup lacks tenant_key filter
**Fix:** Add tenant_key filter to the session query
**Test:** Verify with existing tenant isolation tests

### Item 3: SECURITY — Debug cross-tenant query + log leak
**File:** `api/endpoints/vision_documents.py:170-176`
**Problem:** Debug code queries across tenants and leaks tenant_key to logs
**Fix:** Remove the debug cross-tenant query entirely. Remove tenant_key from log output.
**Test:** Verify endpoint still works for same-tenant queries

### Item 4: HIGH — Broken SQLAlchemy NULL filter
**File:** `api/endpoints/downloads.py:315`
**Problem:** Python `is None` doesn't work in SQLAlchemy — generates broken SQL
**Fix:** Change `column is None` to `column.is_(None)` (SQLAlchemy proper NULL check)
**Test:** Verify download query works for NULL column values

**After Bucket 1:** Run `pytest tests/ -x -q` — all must pass.

---

## Bucket 2: Cleanup (~1.5 hrs)

### Item 5: HIGH — Delete 55 dead test fixtures
**Files:** `tests/conftest.py`, `tests/integration/conftest.py`, and 4 other conftest files
**Problem:** 55 fixtures defined but never used by any test
**Fix:** For each fixture, verify it has zero references (grep across all test files), then delete
**CAUTION:** Some fixtures may be used via pytest's automatic fixture injection by name. Check carefully — if a fixture name matches a test parameter name, it IS used even without an import.

### Item 6: HIGH — Delete dead tool files + functions
**Files:**
- `src/giljo_mcp/tools/agent.py` — dead file (verify zero imports)
- `src/giljo_mcp/tools/claude_export.py` — dead file (verify zero imports)
- Dead functions in `agent_coordination.py`, `context.py`, `agent_job_manager.py`
**Fix:** Verify zero references with grep/find_referencing_symbols, then delete
**CAUTION:** These files may be imported dynamically. Check for `importlib`, `__import__`, or string-based imports.

### Item 7: HIGH — Migrate AgentJobModal colors
**File:** `frontend/src/components/projects/AgentJobModal.vue`
**Problem:** Uses hash-based color palette from constants.js instead of centralized agentColors.js
**Fix:** Import from `agentColors.js` like the other 4 components do (JobsTab, LaunchTab, AgentDetailsModal, TemplateManager)

### Item 8: MEDIUM — Remove fabricated peak_hour metric
**File:** `api/endpoints/statistics.py:412`
**Problem:** `peak_hour_messages` uses fabricated/random data
**Fix:** Remove the fake metric entirely (or replace with a real query if one exists)

### Item 9: MEDIUM — Remove dead message store exports
**File:** `frontend/src/stores/messages.js`
**Problem:** 11 exports that are never imported by any component
**Fix:** Verify each export has zero imports across frontend/src/, then remove

### Item 10: MEDIUM — Clean stale pycache + dead orchestration
**Files:**
- `tests/__pycache__/` — 80 stale .pyc files (3.3 MB) from deleted test modules
- `api/endpoints/orchestration.py` — dead wrapper file
**Fix:**
- Delete stale pycache: `find tests/ -name "__pycache__" -exec rm -rf {} +` then let pytest regenerate
- Verify orchestration.py has zero imports, then delete

**After Bucket 2:** Run `pytest tests/ -x -q` and `npm run build --prefix frontend` — all must pass/clean.

---

## Cascading Impact Analysis

- **Items 1-3:** Tenant isolation fixes — query-level changes only, no schema changes
- **Item 4:** Bug fix — SQL generation change, no schema change
- **Items 5-6:** Dead code deletion — test-only and unused source files
- **Items 7-9:** Frontend cleanup — no backend impact
- **Item 10:** Cache cleanup + dead file deletion

**Risk:** LOW for all items. Each is isolated and independently verifiable.

---

## Testing Requirements

After ALL items:
- `pytest tests/ -x -q` — all pass, zero skips, zero failures
- `npm run build` in frontend/ — clean
- `ruff check src/ api/` — zero issues

---

## Success Criteria

- [ ] All 3 SECURITY items fixed (tenant filters added, debug query removed)
- [ ] SQLAlchemy NULL filter fixed
- [ ] 55 dead fixtures deleted (only truly dead ones — verify each)
- [ ] Dead tool files and functions deleted
- [ ] AgentJobModal migrated to centralized colors
- [ ] Fabricated metric removed
- [ ] Dead store exports removed
- [ ] Stale pycache cleaned
- [ ] All tests pass, frontend builds clean

---

## Commit Strategy

Two commits:
1. `security(0765j): Fix 3 tenant isolation gaps + broken NULL filter`
2. `cleanup(0765j): Remove dead code, fixtures, exports, and stale cache`

---

## Completion Protocol

1. Run full test suite and frontend build
2. Update chain log: set 0765j status to `complete`
3. Write completion summary to THIS handover (max 300 words)
4. Report to user: items fixed, test counts, ready for re-audit
