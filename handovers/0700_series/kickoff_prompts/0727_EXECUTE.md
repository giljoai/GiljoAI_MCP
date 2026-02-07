# Execute Handover 0727: Test Import Fixes & Production Bugs

**Mission:** Fix 6 test import errors + 3 production bugs blocking test execution and coverage analysis.

**Working Directory:** `F:\GiljoAI_MCP`
**Estimated:** 3-5 hours
**Priority:** P0/P1 - CRITICAL

---

## Context

You are executing Handover 0727 based on **validated findings** from the 0725b re-audit (AST-based, <5% false positive rate).

**Parallel Work:** Handover 0433 (Task Product Binding) is handling tenant isolation - do NOT work on that area.

---

## Your Mission (9 Issues Total)

### Part 1: Import Errors (P0 - 1 hour)
1. **BaseGiljoException → BaseGiljoError** (5 test files)
2. **WebSocketManager import error** (1 test file)

### Part 2: Production Bugs (P1 - 2-4 hours)
3. **UnboundLocalError** in project_service.py:1545
4. **Complete endpoint returns 422** for valid projects
5. **Summary endpoint returns 404**

---

## Quick Start

```bash
cd F:/GiljoAI_MCP
source venv/Scripts/activate

# Read full instructions
cat handovers/0700_series/kickoff_prompts/0727_ORCHESTRATOR_KICKOFF.md

# Read validated findings
cat handovers/0725b_findings_real_issues.md
```

---

## Phase 1: Import Fixes (1 hour)

### Fix 1: BaseGiljoException → BaseGiljoError (5 files)

**Files:**
- `tests/services/test_agent_job_manager_exceptions.py`
- `tests/services/test_product_service_exceptions.py`
- `tests/services/test_project_service_exceptions.py`
- `tests/services/test_task_service_exceptions.py`
- `tests/services/test_user_service.py`

**Command:**
```bash
find tests/services/ -name "test_*_exceptions.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
find tests/services/ -name "test_user_service.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
```

**Validate:**
```bash
pytest tests/services/ --collect-only
# Should show "collected X items" with no import errors
```

---

### Fix 2: WebSocketManager Import (1 file)

**File:** `tests/integration/test_websocket_broadcast.py`

**Investigation:**
```python
# Use Serena MCP to locate WebSocketManager
mcp__serena__find_symbol(
    name_path_pattern="WebSocketManager",
    relative_path="api/",
    include_body=False
)
```

**Possible fixes:**
- Update import path if class moved
- Skip test if class removed: `@pytest.mark.skip(reason="WebSocketManager removed")`
- Update test to use new WebSocket API

---

## Phase 2: Production Bugs (2-4 hours)

**CRITICAL:** Use **Serena MCP tools** for code navigation (NOT grep):
- `mcp__serena__find_symbol()` - Locate functions/classes
- `mcp__serena__search_for_pattern()` - Find code patterns
- `mcp__serena__get_symbols_overview()` - Get file structure
- `mcp__serena__replace_symbol_body()` - Apply fixes

### Bug 1: UnboundLocalError (project_service.py:1545)

**Error:** Variable `total_jobs` referenced before assignment

**Investigation:**
```python
# Find the problematic code
mcp__serena__search_for_pattern(
    substring_pattern="total_jobs",
    relative_path="src/giljo_mcp/services/project_service.py",
    context_lines_before=10,
    context_lines_after=10
)
```

**Expected bug pattern:**
```python
# Bug:
if some_condition:
    total_jobs = calculate()
return {"total_jobs": total_jobs}  # ERROR if condition false

# Fix:
total_jobs = 0  # Initialize
if some_condition:
    total_jobs = calculate()
return {"total_jobs": total_jobs}  # Always defined
```

**Validate:**
```bash
# Re-enable tests in tests/api/test_projects_api.py (lines 695, 725)
pytest tests/api/test_projects_api.py::test_get_project_summary -v
```

---

### Bug 2: Complete Endpoint Returns 422

**Error:** Endpoint returns 422 (Unprocessable Entity) for valid projects

**Investigation:**
```python
# Find complete endpoint
mcp__serena__find_symbol(
    name_path_pattern="complete",
    relative_path="api/endpoints/projects/",
    include_body=True
)
```

**Check:**
- Pydantic validation schema (required fields, types)
- Request data matches schema
- Foreign key validation

**Validate:**
```bash
# Re-enable test in tests/api/test_projects_api.py (line 768)
pytest tests/api/test_projects_api.py::test_complete_project -v
```

---

### Bug 3: Summary Endpoint Returns 404

**Investigation:**
```python
# Find summary endpoint
mcp__serena__search_for_pattern(
    substring_pattern="@router.*summary",
    relative_path="api/endpoints/projects/",
    context_lines_after=5
)
```

**Check:**
- Endpoint exists
- Router registered in `__init__.py`
- URL path correct (no typos)

---

## Phase 3: Validation (30 minutes)

```bash
# Run full test suite
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ \
  --cov=src/giljo_mcp \
  --cov=api \
  --cov-report=html \
  --cov-report=json

# Target: >80% coverage
```

---

## Communication Protocol

**After each phase, update comms log:**

```bash
python3 << 'EOF'
import json
from datetime import datetime, timezone
from pathlib import Path

comms_log_path = Path("handovers/0700_series/comms_log.json")
with open(comms_log_path, 'r', encoding='utf-8') as f:
    comms_log = json.load(f)

new_entry = {
    "id": "0727-phase1-complete",  # Update phase number
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "from_handover": "0727",
    "to_handovers": ["orchestrator"],
    "type": "info",
    "subject": "Phase 1 complete - Import errors fixed",
    "message": "Fixed 6 import errors. All tests import successfully. Ready for Phase 2.",
    "files_affected": [],  # List files modified
    "action_required": False,
    "context": {"phase": 1, "issues_fixed": 6}
}

comms_log["entries"].append(new_entry)

with open(comms_log_path, 'w', encoding='utf-8') as f:
    json.dump(comms_log, f, indent=2, ensure_ascii=False)

print("Updated comms_log.json")
EOF
```

---

## Success Criteria

**Phase 1:**
- [ ] 6 import errors fixed
- [ ] All tests import successfully

**Phase 2:**
- [ ] 3 production bugs fixed
- [ ] Skipped tests re-enabled and passing

**Phase 3:**
- [ ] Full test suite runs without errors
- [ ] Coverage >80%
- [ ] Comms log updated

---

## Critical Instructions

### DO:
✅ Use Serena MCP for code navigation
✅ Focus ONLY on 6 imports + 3 bugs (validated by 0725b)
✅ Update comms log after each phase
✅ Reference full orchestrator kickoff for details

### DO NOT:
❌ Use grep/find for code navigation
❌ Work on tenant isolation (0433 handles)
❌ Fix issues not validated by 0725b
❌ Read entire files (use Serena symbols)

---

## Reference Materials

**Full Instructions:**
- `handovers/0700_series/kickoff_prompts/0727_ORCHESTRATOR_KICKOFF.md` (16 KB - detailed)

**Validated Findings:**
- `handovers/0725b_findings_real_issues.md` (summary)
- `handovers/0725b_AUDIT_REPORT.md` (full report)

**Context:**
- `handovers/0433_task_product_binding_and_tenant_isolation_fix.md` (parallel work)

**Serena Memories:**
- `0725_audit_invalidated` - Why 0725 was flawed
- `0720_delinting_project_status` - Delinting status

---

**Next Handover After 0727:** 0730 (Service Response Models - P2)

---

## Start Here

```bash
cd F:/GiljoAI_MCP
source venv/Scripts/activate

# Read full instructions first
cat handovers/0700_series/kickoff_prompts/0727_ORCHESTRATOR_KICKOFF.md

# Then start Phase 1
find tests/services/ -name "test_*_exceptions.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
```

---

**Created:** 2026-02-07
**Orchestrator:** Current session (0700 series coordinator)
**Estimated Duration:** 3-5 hours
**Priority:** P0/P1 - CRITICAL
