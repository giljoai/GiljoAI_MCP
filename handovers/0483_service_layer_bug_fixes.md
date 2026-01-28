# Handover 0483: Agent Jobs Service Layer Bug Fixes

**Status**: Ready for Execution
**Priority**: High
**Depends On**: 0480, 0482 (completed)
**Branch**: `0480-exception-handling-remediation`

---

## Problem Statement

After fixing endpoint exception handling (0482), 29 Agent Jobs tests still fail due to SERVICE LAYER bugs, not endpoint issues.

---

## Test Failures

Run to see current failures:
```bash
python -m pytest tests/api/test_agent_jobs_api.py tests/api/test_agent_jobs_mission.py -v --no-cov --tb=short 2>&1 | head -100
```

---

## Known Bugs to Fix

### Bug 1: Unawaited Coroutine

**Symptom**: Tests fail with coroutine warnings or unexpected results
**Location**: Service layer calling repository without `await`

Search for the issue:
```bash
grep -rn "get_job_by_job_id" src/giljo_mcp/services/
grep -rn "get_job_by_job_id" src/giljo_mcp/repositories/
```

**Fix**: Add `await` to async repository calls

### Bug 2: Wrong Exception Types

**Symptom**: Tests expect 404 but get 422 (or vice versa)
**Cause**: Services raising `ValidationError` when `ResourceNotFoundError` appropriate

**Fix Pattern**:
```python
# WRONG - raises ValidationError for not found
if not job:
    raise ValidationError("Job not found")

# CORRECT - raises ResourceNotFoundError
if not job:
    raise ResourceNotFoundError("Job", job_id)
```

### Bug 3: FK Constraint Violations in Tests

**Symptom**: `ForeignKeyViolationError: agent_jobs_project_id_fkey`
**Files**: `tests/api/test_agent_jobs_api.py`, `tests/api/test_agent_jobs_mission.py`

**Fix Pattern** (already applied in `test_agent_jobs_messages.py`):
```python
# Create Product -> Project -> AgentJob chain
product = Product(id=product_id, name="Test", tenant_key=tenant_key)
session.add(product)

project = Project(
    id=project_id,
    product_id=product_id,
    name="Test Project",
    description="Test",
    mission="Test mission",
    tenant_key=tenant_key
)
session.add(project)

agent_job = AgentJob(
    job_id=job_id,
    project_id=project_id,  # Valid FK!
    ...
)
```

### Bug 4: Invalid Status Values

**Symptom**: Check constraint violation on `status`
**Valid values**: `waiting`, `working`, `blocked`, `complete`, `failed`, `cancelled`, `decommissioned`
**Common mistake**: Using `"active"` which is invalid

---

## Execution Order

1. **First**: Fix test fixtures (FK constraints, status values) - TEST CODE
2. **Second**: Fix unawaited coroutines - SERVICE CODE
3. **Third**: Fix wrong exception types - SERVICE CODE
4. **Verify**: Run tests after each fix category

---

## Files to Investigate

**Service Layer** (may need fixes):
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/services/agent_job_service.py` (if exists)

**Repository Layer** (check async/await):
- `src/giljo_mcp/repositories/agent_job_repository.py`

**Test Files** (FK fixtures):
- `tests/api/test_agent_jobs_api.py`
- `tests/api/test_agent_jobs_mission.py`

**Reference** (already fixed):
- `tests/api/test_agent_jobs_messages.py` - Shows correct fixture pattern

---

## Verification

After each fix category, run:
```bash
python -m pytest tests/api/test_agent_jobs_api.py tests/api/test_agent_jobs_mission.py -v --no-cov --tb=short
```

**Target**: Reduce from 29 failures to < 5 (some may be genuine production bugs to skip)

---

## Commit Guidelines

Commit after each fix category:
```bash
# After test fixture fixes
git add tests/ && git commit -m "test(0480): Fix FK constraints in agent jobs API tests"

# After service layer fixes
git add src/ && git commit -m "fix(services): Fix async/await and exception types in agent job services"
```

---

## Safety Notes

1. **Distinguish test bugs from service bugs** - Fix tests first, then service
2. **Check exception types carefully** - `ResourceNotFoundError` vs `ValidationError`
3. **Verify async/await** - All repository calls must be awaited
4. **Do NOT touch endpoints** - Those are already fixed (0482)
5. **Commit frequently** for recovery

---

## Success Criteria

- [ ] All FK constraint errors resolved in tests
- [ ] All invalid status values fixed in tests
- [ ] Unawaited coroutine issues fixed in services
- [ ] Exception types corrected in services
- [ ] Test pass rate improved significantly (target: 40+ passing)
- [ ] Changes committed with descriptive messages
