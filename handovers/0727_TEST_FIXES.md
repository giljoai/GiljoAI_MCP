# Handover 0727: Test Import Fixes & Production Bugs

**Series:** 0700 Code Health Audit Follow-Up
**Priority:** P0/P1 - CRITICAL (Blocking Coverage)
**Risk Level:** HIGH
**Estimated Effort:** 4-6 hours
**Prerequisites:** Handover 0725 Audit Complete
**Status:** READY

---

## Mission Statement

Fix import errors blocking test execution and resolve production bugs preventing critical tests from running. Enable accurate coverage analysis.

**Current Status:** 6 test files cannot import, 5 tests skipped due to bugs.

---

## Part 1: Fix Import Errors (P0 - 1 hour)

### Issue 1: BaseGiljoException → BaseGiljoError

**Root Cause:** Tests import `BaseGiljoException` but actual class is `BaseGiljoError`

**Location:** `src/giljo_mcp/exceptions.py:11`
```python
class BaseGiljoError(Exception):  # NOT BaseGiljoException
```

**Affected Files (9 total):**
1. `tests/services/test_agent_job_manager_exceptions.py:20`
2. `tests/services/test_product_service_exceptions.py:30`
3. `tests/services/test_project_service_exceptions.py:12`
4. `tests/services/test_task_service_exceptions.py:18`
5. `tests/services/test_user_service.py:32`
6. `tests/unit/test_task_service.py`
7. `tests/unit/test_product_service.py`
8. `tests/unit/test_message_service.py`
9. `tests/test_exception_handlers.py`

**Fix:**
```bash
# Search and replace across test suite
find tests/ -name "*.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +

# Or manually in each file:
# WRONG
from src.giljo_mcp.exceptions import BaseGiljoException

# CORRECT
from src.giljo_mcp.exceptions import BaseGiljoError
```

**Impact:** Unblocks exception handling tests, enables verification of 0480 series migration.

---

### Issue 2: WebSocketManager Import Error

**Root Cause:** Tests import `WebSocketManager` class that doesn't exist

**Location:** `tests/integration/test_websocket_broadcast.py:25`
```python
from api.websocket_manager import ConnectionInfo, WebSocketManager
# ERROR: WebSocketManager does not exist
```

**What Exists:** `api/websocket_manager.py` only exports `ConnectionInfo` dataclass

**Actual WebSocket Module Structure:**
- `api/websocket.py` - Main WebSocket handling
- `api/websocket_service.py` - WebSocket service layer
- `api/websocket_manager.py` - Compatibility shim (ConnectionInfo only)
- `api/dependencies/websocket.py` - WebSocket dependencies

**Fix Options:**

**Option A:** Update test import
```python
# Find correct WebSocketManager location
from api.websocket import WebSocketManager  # Or wherever it moved
```

**Option B:** Create compatibility shim
```python
# In api/websocket_manager.py
from api.websocket import WebSocketManager  # Re-export

__all__ = ["ConnectionInfo", "WebSocketManager"]
```

**Recommendation:** Option A (update test) - cleaner, no new tech debt.

**Impact:** Unblocks WebSocket broadcast integration tests.

---

## Part 2: Fix Production Bugs (P1 - 4-6 hours)

### Bug 1: UnboundLocalError in project_service.py:1545

**Severity:** HIGH
**Blocked Tests:** 2 (`test_projects_api.py` lines 695, 725)

**Error:** Variable `total_jobs` referenced before assignment

**Location:** `src/giljo_mcp/services/project_service.py:1545`

**Investigation Steps:**
1. Read project_service.py around line 1545
2. Find where `total_jobs` is used without initialization
3. Add initialization before first use

**Expected Fix:**
```python
# BEFORE (bug)
if some_condition:
    total_jobs = ...
# Later
return {"total_jobs": total_jobs}  # ERROR if condition was false

# AFTER (fixed)
total_jobs = 0  # Initialize
if some_condition:
    total_jobs = ...
return {"total_jobs": total_jobs}  # Always defined
```

**Tests to Re-enable:**
- `tests/api/test_projects_api.py:695`
- `tests/api/test_projects_api.py:725`

---

### Bug 2: Project Complete Validation Error

**Severity:** HIGH
**Blocked Tests:** 1 (`test_projects_api.py` line 768)

**Error:** Complete endpoint returns 422 for valid projects

**Investigation Steps:**
1. Find project complete endpoint
2. Review validation logic
3. Identify why valid projects fail validation
4. Fix validation or update test

**Possible Causes:**
- Missing required field in request
- Incorrect Pydantic schema
- Database constraint violation
- Business logic validation too strict

**Tests to Re-enable:**
- `tests/api/test_projects_api.py:768`

---

### Bug 3: Statistics Repository Message Model

**Severity:** MEDIUM
**Blocked Tests:** 2 (`test_statistics_repository.py` lines 355, 370)

**Error:** Message model doesn't have `from_agent` field (removed in Handover 0116)

**Location:** Statistics repository still references removed field

**Investigation Steps:**
1. Read `src/giljo_mcp/repositories/statistics_repository.py`
2. Find references to `from_agent` field
3. Update to use current Message model fields
4. Verify statistics aggregation still works

**Tests to Re-enable:**
- `tests/repositories/test_statistics_repository.py:355`
- `tests/repositories/test_statistics_repository.py:370`

---

## Part 3: Run Coverage Analysis (30 minutes)

After fixes complete:

```bash
# Activate virtual environment
cd F:/GiljoAI_MCP && source venv/Scripts/activate

# Run full test suite with coverage
pytest tests/ \
  --cov=src/giljo_mcp \
  --cov=api \
  --cov-report=term-missing \
  --cov-report=json \
  --cov-report=html

# Check results
cat coverage.json | jq '.totals.percent_covered'

# Open HTML report
# coverage_html_report/index.html
```

**Target:** >80% overall coverage

---

## Success Criteria

- [ ] All 9 BaseGiljoException imports fixed
- [ ] WebSocketManager import fixed (1 file)
- [ ] All test files import successfully
- [ ] UnboundLocalError fixed in project_service.py
- [ ] Project complete validation fixed
- [ ] Statistics repository message model fixed
- [ ] All previously blocked tests re-enabled and passing
- [ ] Coverage analysis runs without errors
- [ ] Coverage report generated (HTML + JSON)
- [ ] Coverage >80% overall

---

## Files to Modify

**Test Files (Import Fixes):**
1. `tests/services/test_agent_job_manager_exceptions.py`
2. `tests/services/test_product_service_exceptions.py`
3. `tests/services/test_project_service_exceptions.py`
4. `tests/services/test_task_service_exceptions.py`
5. `tests/services/test_user_service.py`
6. `tests/unit/test_task_service.py`
7. `tests/unit/test_product_service.py`
8. `tests/unit/test_message_service.py`
9. `tests/test_exception_handlers.py`
10. `tests/integration/test_websocket_broadcast.py`

**Production Files (Bug Fixes):**
1. `src/giljo_mcp/services/project_service.py:1545`
2. `api/endpoints/projects/*.py` (complete endpoint)
3. `src/giljo_mcp/repositories/statistics_repository.py`

---

## Reference

**Audit Report:** `handovers/0725_AUDIT_REPORT.md` (Lines 60-99, 101-133)
**Coverage Findings:** `handovers/0725_findings_coverage.md` (Lines 23-103)
