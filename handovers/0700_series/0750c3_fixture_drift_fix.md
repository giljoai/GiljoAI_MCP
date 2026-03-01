# 0750c3: Fix Project Test Fixtures — Unskip ~300 Tests

**Series:** 0750 (Code Quality Cleanup Sprint) — Point Fix
**Branch:** `0750-cleanup-sprint`
**Priority:** HIGH — 300+ tests blocked by a single fixture bug

### Reference Documents
- **Orchestrator handover:** `handovers/0700_series/0750_ORCHESTRATOR_HANDOVER.md` (Point Fixes section, item 4)

---

## Context

Phase 2 (0750b) skipped 522 tests across 42 files with `0750b:` skip markers. ~300 of these are skipped because the base project fixture doesn't satisfy the `uq_project_taxonomy` constraint added in Handover 0440a. The fix is a one-line change to the fixture helper, then removing skip markers from files that now pass.

---

## Root Cause

The `uq_project_taxonomy` constraint in the Project model enforces uniqueness on `(tenant_key, project_type_id, series_number, subseries)` with `NULLS NOT DISTINCT` (PostgreSQL 15+). The test fixture creates projects with all taxonomy fields as NULL, so any second project with the same tenant_key violates the constraint.

**Constraint definition** (`src/giljo_mcp/models/projects.py` lines 186-193):
```python
UniqueConstraint(
    "tenant_key", "project_type_id", "series_number", "subseries",
    name="uq_project_taxonomy",
    postgresql_nulls_not_distinct=True,
)
```

---

## Scope

### Step 1: Fix the fixture helper

**File:** `tests/fixtures/base_fixtures.py` (lines 34-44)

**Current code:**
```python
@staticmethod
def generate_project_data(tenant_key: str) -> dict[str, Any]:
    """Generate test project data"""
    return {
        "id": str(uuid.uuid4()),
        "name": f"Test Project {uuid.uuid4().hex[:8]}",
        "description": "Test project description for automated testing",
        "mission": "Test mission for automated testing",
        "status": "active",
        "tenant_key": tenant_key,
        "metadata": {"test": True},
    }
```

**Fix:** Add a unique `series_number` to avoid constraint violations:
```python
@staticmethod
def generate_project_data(tenant_key: str) -> dict[str, Any]:
    """Generate test project data"""
    import random
    return {
        "id": str(uuid.uuid4()),
        "name": f"Test Project {uuid.uuid4().hex[:8]}",
        "description": "Test project description for automated testing",
        "mission": "Test mission for automated testing",
        "status": "active",
        "tenant_key": tenant_key,
        "metadata": {"test": True},
        "series_number": random.randint(1, 999999),
    }
```

Also check if `random` is already imported at the top of the file. If not, add `import random`.

### Step 2: Check for other project creation patterns

Search for other places in tests that create Project objects without using the fixture:
```bash
grep -rn "Project(" tests/ | grep -v ".pyc" | grep -v "__pycache__"
```

For any that create projects without `series_number`, add it.

Also check `tests/conftest.py` — there's a `test_project_id` fixture (lines 279-297) that may also need the fix.

### Step 3: Remove skip markers and test

Go through ALL 42 files with `0750b:` skip markers. For each file:

1. Check the skip reason
2. If the reason mentions `uq_project_taxonomy` or `NOT NULL constraints` or `fixture update`:
   - Remove the `pytestmark = pytest.mark.skip(...)` line
   - Run just that test file: `python -m pytest <file> -x -q --timeout=60`
   - If it passes: keep the skip marker removed
   - If it fails for a DIFFERENT reason: add a NEW skip marker with the actual failure reason
3. If the reason mentions `dict-return API` or `bcrypt` or something unrelated to fixtures:
   - LEAVE the skip marker in place — those are separate issues

**Files likely to be fixed by the fixture update (remove skip markers):**
```
tests/test_tenant_isolation.py — "uq_project_taxonomy constraint"
tests/test_tenant_isolation_demo.py — "uq_project_taxonomy constraint"
tests/test_tenant_key_fix.py — "uq_project_taxonomy and NOT NULL constraints"
tests/test_multi_tenant_comprehensive.py — "uq_project_taxonomy and NOT NULL constraints"
tests/test_vision_document_repository.py — "NOT NULL constraints"
tests/smoke/test_tenant_isolation_smoke.py — "Project creation API returns 422"
tests/repositories/test_configuration_repository.py — "fixture data update"
tests/repositories/test_statistics_repository.py — "fixture data update"
tests/integration/test_field_priority_tenant_isolation.py — "uq_project_taxonomy constraint"
tests/integration/test_multi_tenant_isolation.py — "uq_project_taxonomy and NOT NULL constraints"
tests/integration/test_project_service_lifecycle.py — "uq_project_taxonomy constraint"
tests/integration/test_product_service_integration.py — "NOT NULL constraints"
tests/integration/test_message_service_receive.py — "NOT NULL constraints"
tests/integration/test_auth_endpoints.py — "bcrypt/async fixture updates"
tests/integration/test_auth_org_flow.py — "fixture updates for schema changes"
tests/services/test_project_tenant_isolation_regression.py — "uq_project_taxonomy constraint"
tests/services/test_orchestration_service_dual_model.py — "display name dedup logic"
tests/services/test_orchestration_service_phase_labels.py — "display name dedup logic"
tests/services/test_message_service_counters_0387f.py — "project fixture with description field"
tests/services/test_orchestration_service_websocket_emissions.py — "complete_job test needs update"
tests/services/test_product_service_project_deactivation.py — "description NOT NULL constraint"
tests/services/test_task_service_enhanced.py — "project fixture with description field"
tests/services/test_task_service_exceptions.py — "project fixture with description field"
tests/services/test_template_service.py — "old tool name acknowledge_job"
tests/unit/test_auth_manager_unified.py — "bcrypt timeout failures on Windows"
tests/unit/test_auth_manager_v3.py — "bcrypt timeout failures on Windows"
tests/unit/test_auth_models.py — "project fixture updates for NOT NULL constraints"
tests/unit/test_project_service_deleted_state.py — "NOT NULL constraints" + "dict-return API"
tests/unit/test_project_service_field_priorities.py — "NOT NULL constraints" + "dict-return API"
```

**Files to LEAVE skipped (different issues):**
```
tests/unit/test_message_service.py — "dict-return API" (separate issue)
tests/unit/test_orchestration_service.py — "dict-return API"
tests/unit/test_product_service.py — "dict-return API"
tests/unit/test_project_service.py — "dict-return API" + "uq_project_taxonomy"
tests/unit/test_project_service_deleted_state.py — "dict-return API"
tests/unit/test_project_service_field_priorities.py — "dict-return API"
tests/unit/test_task_service.py — "dict-return API"
tests/unit/test_vision_repository_async.py — "dict-return API"
tests/unit/test_auth_manager_unified.py — "bcrypt timeout"
tests/unit/test_auth_manager_v3.py — "bcrypt timeout"
```

Note: Some files have TWO skip markers (one for fixtures, one for dict-return). For those, remove only the fixture skip marker and keep the dict-return one.

### Step 4: Run full test suite

```bash
python -m pytest tests/ -q --timeout=60
```

Record the new baseline: expecting ~1500+ passed, ~200 skipped, 0 failed.

---

## What NOT To Do

- Do NOT modify production code — this is a test-only fix
- Do NOT rewrite tests — just fix the fixture and remove skip markers
- Do NOT use `random.randint()` in production code (this is test code only, it's fine)
- Do NOT remove skip markers from tests that fail for non-fixture reasons
- Do NOT delete any test files

---

## Acceptance Criteria

- [ ] `generate_project_data()` includes `series_number` field
- [ ] All project creation patterns in tests include taxonomy fields
- [ ] Skip markers removed from tests that now pass
- [ ] Tests with non-fixture skip reasons still have their skip markers
- [ ] Full test suite runs: 0 failures, significantly fewer skips (target: <250 skipped)
- [ ] No production code changes

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit
```bash
git add tests/
git commit -m "fix(0750c3): Fix project test fixtures — add series_number, unskip ~300 tests"
```

### Step 3: Record results
```bash
git rev-parse --short HEAD
python -m pytest tests/ -q --timeout=60 2>&1 | tail -5
```

### Step 4: Done
Do NOT update chain_log.json for this point fix.
Do NOT spawn the next terminal.
Print "0750c3 COMPLETE" as your final message, including the new test counts.
