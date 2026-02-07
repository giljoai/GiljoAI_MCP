# Orchestrator Kickoff: Handover 0727 - Test Import Fixes & Production Bugs

**Orchestrator:** Current session (0700 series coordinator)
**Agent Type:** `backend-integration-tester` or `tdd-implementor`
**Working Directory:** `F:\GiljoAI_MCP`
**Estimated Effort:** 3-5 hours
**Priority:** P0/P1 - CRITICAL

---

## Orchestrator Context

I'm assigning you Handover 0727 based on **validated findings** from two parallel workstreams:

### Workstream 1: 0725b Re-Audit (Research Agent)
- **Status:** COMPLETE
- **Mission:** Proper code health re-audit with AST-based analysis
- **Findings:** Validated 6 test import errors + 3 production bugs
- **False Positive Rate:** <5% (vs 75%+ in flawed 0725)
- **Materials Created:** Detailed handover spec + implementation guide

### Workstream 2: 0433 Task Product Binding (User-Led)
- **Status:** Phases 1-4 COMPLETE (Phase 5 testing pending)
- **Mission:** Fix tenant isolation vulnerability via design change
- **Impact:** Removed "unassigned tasks" pattern
- **Scope:** Database, service layer, MCP tools, API endpoints
- **Tests Created:** 23 comprehensive tests

### Integration Decision
You should **NOT** work on tenant isolation - that's handled by 0433. Focus **ONLY** on the 6 import errors + 3 production bugs validated by 0725b.

---

## Your Mission

Fix **9 validated issues** blocking test execution and coverage analysis:

**P0 - Import Errors (1 hour):**
1. BaseGiljoException → BaseGiljoError (5 test files)
2. WebSocketManager import error (1 test file)

**P1 - Production Bugs (2-4 hours):**
3. UnboundLocalError in project_service.py:1545
4. Complete endpoint returns 422 for valid projects
5. Summary endpoint returns 404

**Success Criteria:**
- All 6 import errors fixed
- All 3 production bugs resolved
- Test suite runs without import errors
- Coverage analysis enabled (>80% target)

---

## Resources Available

### 1. 0725b Handover Spec (Detailed Implementation Guide)
**File:** `handovers/0727_TEST_FIXES_REVISED.md` (7.8 KB)

This contains:
- Root cause analysis for each issue
- Exact file locations and line numbers
- Step-by-step fix instructions
- Validation commands
- Expected fix patterns

**Read this first** - it's your primary reference.

### 2. 0725b Kickoff Prompt (Detailed Methodology)
**File:** `handovers/0700_series/kickoff_prompts/0727_TEST_FIXES_kickoff.md` (13.2 KB)

This contains:
- Serena MCP tool usage examples
- Investigation steps for each bug
- Validation commands
- Anti-patterns to avoid

**Use as methodology reference** when investigating bugs.

### 3. Communication Log
**File:** `handovers/0700_series/comms_log.json`

Contains:
- 0725b validation results
- 0433 progress updates
- Orchestrator coordination notes

**Update this** after each phase completion (see protocol below).

### 4. Project Context
**Serena Memories** (Use `mcp__serena__read_memory`):
- `0725_audit_invalidated` - Why 0725 was flawed
- `0720_delinting_project_status` - Delinting completion
- `project_overview` - General context

---

## Phase 1: Import Error Fixes (1 hour)

### Task 1.1: BaseGiljoException → BaseGiljoError (5 files)

**Context:** Exception handling remediation (Handover 0480) renamed the base exception class but tests weren't updated.

**Files to Fix:**
```
tests/services/test_agent_job_manager_exceptions.py
tests/services/test_product_service_exceptions.py
tests/services/test_project_service_exceptions.py
tests/services/test_task_service_exceptions.py
tests/services/test_user_service.py
```

**Fix Command:**
```bash
cd F:/GiljoAI_MCP

# Find and replace across all 5 files
find tests/services/ -name "test_*_exceptions.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
find tests/services/ -name "test_user_service.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
```

**Validation:**
```bash
# Verify imports work (should show "collected X items" with no errors)
pytest tests/services/test_agent_job_manager_exceptions.py --collect-only
pytest tests/services/test_product_service_exceptions.py --collect-only
pytest tests/services/test_project_service_exceptions.py --collect-only
pytest tests/services/test_task_service_exceptions.py --collect-only
pytest tests/services/test_user_service.py --collect-only
```

---

### Task 1.2: WebSocketManager Import Error (1 file)

**Context:** WebSocket refactoring moved or removed the `WebSocketManager` class.

**File to Fix:** `tests/integration/test_websocket_broadcast.py`

**Investigation Steps:**

1. **Find where WebSocketManager lives** (if it exists):
   ```python
   # Use Serena MCP to locate symbol
   mcp__serena__find_symbol(
       name_path_pattern="WebSocketManager",
       relative_path="api/",
       include_body=False
   )
   ```

2. **Check WebSocket module structure:**
   ```python
   # Get overview of what exists
   mcp__serena__get_symbols_overview(relative_path="api/websocket.py", depth=1)
   mcp__serena__get_symbols_overview(relative_path="api/websocket_service.py", depth=1)
   ```

3. **Apply appropriate fix:**
   - **If class exists elsewhere:** Update import path in test
   - **If class removed:** Skip test with reason `@pytest.mark.skip(reason="WebSocketManager removed in refactoring")`
   - **If replaced:** Update test to use new WebSocket handler pattern

**Validation:**
```bash
pytest tests/integration/test_websocket_broadcast.py --collect-only
```

---

## Phase 2: Production Bug Fixes (2-4 hours)

**IMPORTANT:** Use **Serena MCP tools** for code navigation:
- `mcp__serena__find_symbol()` - Locate functions/classes
- `mcp__serena__get_symbols_overview()` - Get file structure
- `mcp__serena__search_for_pattern()` - Find patterns
- `mcp__serena__replace_symbol_body()` - Apply fixes

**DO NOT use grep** - Serena is more accurate and context-aware.

### Bug 1: UnboundLocalError in project_service.py:1545

**Error:** `UnboundLocalError: local variable 'total_jobs' referenced before assignment`

**Source:** Tests skipped in `tests/api/test_projects_api.py` (lines 695, 725)

**Investigation:**

1. **Read the problematic function:**
   ```python
   # Use Serena to find and read the function containing line 1545
   mcp__serena__search_for_pattern(
       substring_pattern="total_jobs",
       relative_path="src/giljo_mcp/services/project_service.py",
       context_lines_before=10,
       context_lines_after=10
   )
   ```

2. **Identify bug pattern:**
   ```python
   # Expected bug pattern:
   if some_condition:
       total_jobs = calculate_something()
   # Later (ERROR if condition was false):
   return {"total_jobs": total_jobs}
   ```

3. **Fix:**
   ```python
   # Add initialization before conditional
   total_jobs = 0  # or appropriate default
   if some_condition:
       total_jobs = calculate_something()
   return {"total_jobs": total_jobs}  # Always defined
   ```

4. **Apply fix using Serena or Edit tool**

**Validation:**
```bash
# Re-enable skipped tests
# Remove @pytest.mark.skip from tests/api/test_projects_api.py lines 695, 725
pytest tests/api/test_projects_api.py::test_get_project_summary -v
pytest tests/api/test_projects_api.py::test_project_summary_stats -v
```

---

### Bug 2: Complete Endpoint Returns 422

**Error:** Complete endpoint returns 422 (Unprocessable Entity) for valid projects

**Source:** Test skipped in `tests/api/test_projects_api.py` (line 768)

**Investigation:**

1. **Find the complete endpoint:**
   ```python
   # Use Serena to locate
   mcp__serena__find_symbol(
       name_path_pattern="complete",
       relative_path="api/endpoints/projects/",
       include_body=True,
       depth=0
   )
   ```

2. **Check Pydantic validation schema:**
   - Look for schema that validates project completion
   - Check required fields
   - Verify field types match what's being sent

3. **Common causes:**
   - Missing required field in request schema
   - Type mismatch (string vs UUID)
   - Enum validation too strict
   - Foreign key validation failing

4. **Fix validation logic or update test data**

**Validation:**
```bash
# Re-enable test
pytest tests/api/test_projects_api.py::test_complete_project -v
```

---

### Bug 3: Summary Endpoint Returns 404

**Error:** Summary endpoint returns 404 (Not Found)

**Source:** Test fails or is skipped

**Investigation:**

1. **Verify endpoint exists:**
   ```python
   # Find summary endpoint
   mcp__serena__search_for_pattern(
       substring_pattern="@router.*summary",
       relative_path="api/endpoints/projects/",
       context_lines_after=5
   )
   ```

2. **Check route registration:**
   - Verify router is included in main app
   - Check for URL prefix issues
   - Verify FastAPI router inclusion

3. **Common causes:**
   - Endpoint removed but tests not updated
   - Router not registered in `__init__.py`
   - URL path typo (e.g., `/summery` vs `/summary`)

**Validation:**
```bash
# Test the endpoint
pytest tests/api/test_projects_api.py -k summary -v
```

---

## Phase 3: Full Test Suite Validation (30 minutes)

After all fixes:

```bash
cd F:/GiljoAI_MCP
source venv/Scripts/activate

# Run full test suite
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ \
  --cov=src/giljo_mcp \
  --cov=api \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=json

# Check coverage
cat coverage.json | grep -A 2 '"totals"'
# Target: >80% overall coverage

# Open HTML report
# coverage_html_report/index.html
```

---

## Communication Protocol

### After Each Phase

Update the comms log with your progress:

```bash
cd F:/GiljoAI_MCP
python3 << 'EOF'
import json
from datetime import datetime, timezone
from pathlib import Path

comms_log_path = Path("handovers/0700_series/comms_log.json")
with open(comms_log_path, 'r', encoding='utf-8') as f:
    comms_log = json.load(f)

new_entry = {
    "id": "0727-phase1-complete",  # Change phase number
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "from_handover": "0727",
    "to_handovers": ["orchestrator"],
    "type": "info",
    "subject": "Phase 1 complete - Import errors fixed",  # Update subject
    "message": "Fixed 6 import errors: 5 BaseGiljoException→BaseGiljoError, 1 WebSocketManager. All tests now import successfully. Ready for Phase 2 (production bugs).",  # Update message
    "files_affected": [
        # List files you modified
    ],
    "action_required": False,
    "context": {
        "phase": 1,
        "issues_fixed": 6,
        "tests_validated": True
    }
}

comms_log["entries"].append(new_entry)

with open(comms_log_path, 'w', encoding='utf-8') as f:
    json.dump(comms_log, f, indent=2, ensure_ascii=False)

print("Updated comms_log.json")
EOF
```

### Final Report

After completing all phases, create a summary:

```bash
python3 << 'EOF'
import json
from datetime import datetime, timezone
from pathlib import Path

comms_log_path = Path("handovers/0700_series/comms_log.json")
with open(comms_log_path, 'r', encoding='utf-8') as f:
    comms_log = json.load(f)

final_entry = {
    "id": "0727-complete",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "from_handover": "0727",
    "to_handovers": ["orchestrator"],
    "type": "info",
    "subject": "0727 COMPLETE - Test suite restored",
    "message": "All 9 issues fixed: 6 import errors + 3 production bugs. Test suite runs without errors. Coverage analysis enabled. Ready for next handover.",
    "files_affected": [
        # List all files modified
    ],
    "action_required": False,
    "context": {
        "import_errors_fixed": 6,
        "production_bugs_fixed": 3,
        "tests_passing": True,
        "coverage_enabled": True,
        "coverage_percentage": 0.0,  # Fill in actual coverage
        "estimated_hours": 0.0,  # Fill in actual time spent
        "next_handover": "0730 (Service Response Models - P2)"
    }
}

comms_log["entries"].append(new_entry)

with open(comms_log_path, 'w', encoding='utf-8') as f:
    json.dump(comms_log, f, indent=2, ensure_ascii=False)

print("0727 marked COMPLETE in comms_log")
EOF
```

---

## Critical Instructions

### DO:
- ✅ Use Serena MCP symbolic tools for code navigation
- ✅ Focus ONLY on 6 import errors + 3 production bugs (validated by 0725b)
- ✅ Update comms log after each phase
- ✅ Run full test suite to validate fixes
- ✅ Reference 0725b materials (`0727_TEST_FIXES_REVISED.md` and kickoff prompt)

### DO NOT:
- ❌ Use grep/find for code navigation (use Serena MCP instead)
- ❌ Trust findings from original 0725 audit (75%+ false positives)
- ❌ Work on tenant isolation (handled by 0433)
- ❌ Fix issues not validated by 0725b
- ❌ Read entire files when Serena can find symbols
- ❌ Create new handovers or specifications (orchestrator's job)

### Scope Boundaries
- ✅ **IN SCOPE:** 6 import errors, 3 production bugs
- ❌ **OUT OF SCOPE:** Tenant isolation (0433 handles), orphan code (separate handover), service dicts (separate handover)

---

## Reference Materials

**Primary References (0725b Materials):**
- `handovers/0727_TEST_FIXES_REVISED.md` - Detailed handover spec
- `handovers/0700_series/kickoff_prompts/0727_TEST_FIXES_kickoff.md` - Methodology guide

**Project Documentation:**
- `CLAUDE.md` - Project overview and coding guidelines
- `docs/TESTING.md` - Testing strategy
- `docs/SERVICES.md` - Service layer patterns

**Related Handovers:**
- `handovers/0433_task_product_binding_and_tenant_isolation_fix.md` - Tenant isolation fix (parallel work)
- `handovers/0725b_PROPER_CODE_HEALTH_REAUDIT.md` - Source of validated findings

**Tracking:**
- `handovers/0700_series/comms_log.json` - Communication log (update this)
- `handovers/0700_series/orchestrator_state.json` - Orchestrator state (read-only)

---

## Success Criteria Checklist

Phase 1 (Import Errors):
- [ ] BaseGiljoException → BaseGiljoError fixed (5 files)
- [ ] WebSocketManager import fixed (1 file)
- [ ] All test imports successful (pytest --collect-only passes)

Phase 2 (Production Bugs):
- [ ] UnboundLocalError fixed (project_service.py:1545)
- [ ] Complete endpoint 422 error resolved
- [ ] Summary endpoint 404 error resolved
- [ ] Skipped tests re-enabled and passing

Phase 3 (Validation):
- [ ] Full test suite runs without import errors
- [ ] Coverage analysis runs successfully
- [ ] Coverage >80% overall
- [ ] Comms log updated with results

Communication:
- [ ] Comms log updated after each phase
- [ ] Final summary entry added to comms log
- [ ] Files committed with descriptive message
- [ ] Orchestrator notified of completion

---

## Quick Start Commands

```bash
# Navigate and activate
cd F:/GiljoAI_MCP
source venv/Scripts/activate

# Read reference materials
cat handovers/0727_TEST_FIXES_REVISED.md
cat handovers/0700_series/kickoff_prompts/0727_TEST_FIXES_kickoff.md

# Phase 1: Import fixes
find tests/services/ -name "test_*_exceptions.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
find tests/services/ -name "test_user_service.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
pytest tests/services/ --collect-only

# Phase 2: Production bug investigation
# Use Serena MCP tools to locate and fix bugs

# Phase 3: Full validation
pytest tests/ -v
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=html
```

---

**Created:** 2026-02-07
**Orchestrator:** Current session (0700 series coordinator)
**Mission:** Fix validated test issues from 0725b re-audit
**Context Integration:** 0433 (tenant isolation), 0725b (validation), orchestrator state
**Expected Duration:** 3-5 hours
**Next Handover:** 0730 (Service Response Models - P2)

---

**COPY THIS ENTIRE PROMPT INTO FRESH CLAUDE CODE SESSION TO BEGIN 0727 EXECUTION**
