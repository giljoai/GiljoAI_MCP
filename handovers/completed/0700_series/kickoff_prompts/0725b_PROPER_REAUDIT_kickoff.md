# Kickoff Prompt: Handover 0725b - Proper Code Health Re-Audit

**Copy this entire prompt into a fresh Claude Code session**

---

## Mission

Execute Handover 0725b: Conduct a **proper** code health audit using FastAPI-aware tooling to replace the fundamentally flawed 0725 audit.

**Working Directory:** `F:\GiljoAI_MCP`

---

## Critical Context: Why Re-Audit is Needed

The original 0725 audit (completed 2026-02-07) is **INVALIDATED** due to 75%+ false positive rate.

### What Went Wrong in 0725

**Flawed Methodology:** Used naive static analysis (grep/import scanning) that failed to detect:
1. FastAPI router registration: `router.include_router(executions.router)`
2. Frontend API calls: `api.js` → backend endpoints
3. Dynamic imports: `importlib.import_module()`, `__import__()`
4. Test infrastructure: `conftest.py` patterns
5. Already-deleted files: Counted files removed in 0700 series

**False Positive Examples:**
- **Orphan Code**: Claimed 129 files (50%) → Reality: 2-5 actual orphans (95% false positive)
- **Tenant Isolation**: Claimed 25 issues → Reality: 1 issue (96% false positive)
- **Dead Functions**: Claimed 444 → Reality: Mostly live FastAPI endpoints (75% false positive)

**Dangerous Outcome:** Handover 0729 (Orphan Code Removal) would have **deleted production code** including login endpoints, workflow_engine.py, job_coordinator.py, etc.

---

## Your Mission: Proper Re-Audit

Use **FastAPI-aware, AST-based analysis** to identify REAL issues only.

### Phase 1: Tool Setup & Resource Review (1 hour)

#### Required Reading (Read First)
```bash
# 1. Handover spec
cat handovers/0725b_PROPER_CODE_HEALTH_REAUDIT.md

# 2. Invalidation notice
cat handovers/0725_INVALIDATED_README.md

# 3. Original flawed findings (for comparison)
cat handovers/0725_findings_orphans.md
cat handovers/0725_findings_architecture.md

# 4. What was already cleaned in 0700 series
cat handovers/0700_series/orchestrator_state.json | grep -A 10 '"0700b"'
cat handovers/0700_series/orchestrator_state.json | grep -A 10 '"0700f"'
```

#### Available Resources
1. **Dependency Graph** (Visual)
   - File: `docs/cleanup/dependency_graph.html`
   - Open in browser: `file:///F:/GiljoAI_MCP/docs/cleanup/dependency_graph.html`
   - Shows import relationships, circular deps, orphan candidates

2. **Dependency Analysis JSON**
   - File: `handovers/0700_series/dependency_analysis.json`
   - Contains: Import graph, orphan candidates (use with caution - may be outdated)

3. **0700 Series Logs**
   - `handovers/0700_series/orchestrator_state.json` - What was deleted
   - `handovers/0700_series/comms_log.json` - Inter-handover communications
   - `handovers/0700_series/cleanup_index.json` - Original cleanup targets

4. **Serena Memories**
   ```
   Use mcp__serena__read_memory tool:
   - 0720_delinting_project_status (delinting completion)
   - 0700_orchestrator_session_state (0700 series state)
   - 0725_audit_invalidated (false positive documentation)
   - project_overview (general context)
   ```

### Phase 2: Orphan Code Analysis (2 hours)

**Goal:** Find 2-10 ACTUAL orphans (not 129!)

#### Step 1: Build Import Graph with AST
```python
import ast
from pathlib import Path
import json

def get_imports_from_file(filepath):
    """Parse Python file and extract imports using AST"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        return imports
    except:
        return set()

# Scan all Python files
all_files = list(Path('src').rglob('*.py')) + list(Path('api').rglob('*.py'))
import_graph = {}
for f in all_files:
    imports = get_imports_from_file(f)
    import_graph[str(f)] = list(imports)
```

#### Step 2: Detect FastAPI Router Registrations
```python
def find_router_registrations(filepath):
    """Find router.include_router() calls"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        registrations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'attr') and node.func.attr == 'include_router':
                    # Found router.include_router(some_router)
                    registrations.append(node)
        return registrations
    except:
        return []

# Find all router files
router_files = []
for f in Path('api/endpoints').rglob('*.py'):
    if '__init__.py' in str(f) or 'router' in open(f).read():
        router_files.append(f)
```

#### Step 3: Parse Frontend API Calls
```bash
# Extract all API endpoint paths called from frontend
grep -r "apiClient\." frontend/src/ --include="*.js" --include="*.vue" | \
  grep -E "get\(|post\(|put\(|delete\(" | \
  sed 's/.*['"'"'"`]\(\/api\/[^'"'"'"`]*\)['"'"'"`].*/\1/' | \
  sort -u > /tmp/frontend_endpoints.txt

cat /tmp/frontend_endpoints.txt
```

#### Step 4: Find Dynamic Imports
```bash
# Search for dynamic import patterns
grep -rn "importlib.import_module\|__import__" src/ api/ --include="*.py"
grep -rn "getattr.*__import__" src/ api/ --include="*.py"
```

#### Step 5: Cross-Check Against 0700 Deletions
```bash
# What was already deleted?
cat handovers/0700_series/orchestrator_state.json | \
  jq '[.handovers[] | select(.files_deleted != null) | {id, files_deleted}]'
```

#### Step 6: Identify ACTUAL Orphans
**Validation Checklist (Must Pass All):**
- [ ] File exists in current codebase (not already deleted)
- [ ] Not imported by any Python file (AST verification)
- [ ] Not registered via FastAPI router (AST verification)
- [ ] Not called from frontend (api.js check)
- [ ] Not dynamically imported (grep check)
- [ ] Not test infrastructure (conftest.py, pytest fixtures)
- [ ] Not in `__init__.py` re-exports

**Expected Result:** 2-5 actual orphans max

**Known Candidates:**
- `src/giljo_mcp/cleanup/visualizer.py` - Analysis script for 0700 series
- `src/giljo_mcp/mcp_http_stdin_proxy.py` - Deprecated stdio proxy (Handover 0397)

### Phase 3: Architecture Review (2 hours)

#### Skip These (Already Validated)
- ✅ **Tenant Isolation** - Already validated (7.5/10, mostly safe)
- ✅ **Repository Statelessness** - Already validated (100% good)
- ✅ **Pydantic Validation** - Already validated (excellent)

#### Focus On These

**1. Service Layer Dict Returns (REAL Finding)**
```bash
# Find services returning dicts instead of Pydantic models
grep -rn 'return {"' src/giljo_mcp/services/ --include="*.py" | wc -l

# Count by service
for svc in src/giljo_mcp/services/*.py; do
  echo "$(basename $svc): $(grep -c 'return {' $svc 2>/dev/null || echo 0)"
done
```

**Expected:** ~120+ instances (this is REAL technical debt)

**2. Error Handling Patterns**
```bash
# Find direct dict error returns in endpoints
grep -rn 'return {.*"error"' api/endpoints/ --include="*.py"
```

### Phase 4: Test Coverage (2 hours)

#### REAL Findings (Validated)

**1. Test Import Errors (P0 - CRITICAL)**
```bash
# Try to import tests and catch errors
pytest tests/ --collect-only 2>&1 | grep -A 5 "ImportError\|ModuleNotFoundError"
```

**Known Issues:**
- BaseGiljoException → BaseGiljoError (9 files affected)
- WebSocketManager import error (1 file)

**2. Production Bugs Blocking Tests (P1 - HIGH)**
```bash
# Find skipped tests
pytest tests/ --collect-only -m skip 2>&1 | grep "SKIPPED"
grep -rn "@pytest.mark.skip\|pytest.skip" tests/ --include="*.py"
```

**Known Bugs:**
- UnboundLocalError in project_service.py:1545
- Project complete validation returns 422
- Statistics repository references removed message model field

**3. Skipped Tests Analysis**
```bash
# Count and categorize
pytest tests/ -v 2>&1 | grep "SKIPPED" | wc -l
pytest tests/ -v 2>&1 | grep "SKIPPED" | head -20
```

**Expected:** ~92 skipped tests (validate reasons)

#### Run Coverage Analysis (If Import Errors Fixed)
```bash
cd F:/GiljoAI_MCP
source venv/Scripts/activate
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=term-missing --cov-report=html
```

### Phase 5: Deprecation & Naming (1 hour)

#### REAL Findings (Validated)

**1. Placeholder API Key (P3 - LOW)**
```bash
grep -rn "placeholder.*api.*key\|api.*key.*placeholder" api/ --include="*.py" -i
```

**Known:** `api/endpoints/ai_tools.py:217`

**2. Naming Conventions (99.5% Compliant - EXCELLENT)**
```bash
ruff check src/ api/ --select N --statistics
```

**Expected:** 0-1 violations (already excellent)

---

## Communication Protocol

### Update Comms Log

**After completing each phase, add entry to comms log:**

```bash
cd F:/GiljoAI_MCP
python3 << 'EOF'
import json
from datetime import datetime, timezone
from pathlib import Path

comms_log_path = Path("handovers/0700_series/comms_log.json")
with open(comms_log_path, 'r', encoding='utf-8') as f:
    comms_log = json.load(f)

# Add your entry
new_entry = {
    "id": "0725b-phase1-complete",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "from_handover": "0725b",
    "to_handovers": ["orchestrator"],
    "type": "info",
    "subject": "Phase 1 complete - Tool setup and resource review",
    "message": "Completed tool setup and resource review. Read all required docs. Built AST-based import graph. Detected FastAPI router registrations. Parsed frontend API calls. Ready for Phase 2.",
    "files_affected": [],
    "action_required": False,
    "context": {
        "phase": 1,
        "methodology": "AST-based with FastAPI awareness",
        "resources_reviewed": [
            "0725b handover spec",
            "0725 invalidation notice",
            "0700 orchestrator state",
            "dependency_graph.html"
        ]
    }
}

comms_log["entries"].append(new_entry)

with open(comms_log_path, 'w', encoding='utf-8') as f:
    json.dump(comms_log, f, indent=2, ensure_ascii=False)

print("✓ Updated comms_log.json")
EOF
```

**Entry Types:**
- `"info"` - Progress update
- `"warning"` - Found issue or concern
- `"blocker"` - Critical issue blocking progress

### Update Orchestrator State

**After completing the re-audit:**

```bash
python3 << 'EOF'
import json
from datetime import datetime, timezone
from pathlib import Path

state_path = Path("handovers/0700_series/orchestrator_state.json")
with open(state_path, 'r', encoding='utf-8') as f:
    state = json.load(f)

# Add 0725b entry
reaudit_entry = {
    "id": "0725b",
    "title": "Proper Code Health Re-Audit",
    "status": "complete",
    "effort_hours": "6-8",
    "priority": "HIGH",
    "dependencies": ["0720", "0725-INVALIDATED"],
    "scope": "FastAPI-aware re-audit replacing flawed 0725",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "methodology": "AST-based with FastAPI awareness",
    "false_positive_rate": "<10%",
    "real_findings": {
        "actual_orphans": "2-5 files",
        "test_import_errors": 6,
        "production_bugs": 3,
        "service_dict_returns": 120,
        "placeholder_api_key": 1
    }
}

state["handovers"].append(reaudit_entry)
state["status"] = "reaudit_complete"

with open(state_path, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

print("✓ Updated orchestrator_state.json")
EOF
```

---

## Deliverables

### 1. Audit Report
Create `handovers/0725b_AUDIT_REPORT.md`:

```markdown
# Handover 0725b: Proper Code Health Re-Audit Report

**Date:** 2026-02-07
**Status:** COMPLETE
**Replaces:** Handover 0725 (invalidated)

## Executive Summary

Architecture: **HEALTHY** (0700 series already did thorough cleanup)

## Real Findings (Validated with Proper Methodology)

### P0 - Critical
1. Test import errors (6 files) - BaseGiljoException → BaseGiljoError
2. Production bugs (3 bugs) - Blocking tests

### P1 - High
3. Service dict returns (120+ instances) - Architecture debt

### P3 - Low
4. Actual orphans (2-5 files max)
5. Placeholder API key (1 instance)

## Architecture Assessment

- ✅ 0700 series removed 5,000+ lines of dead code
- ✅ Only 2 circular dependencies (very low coupling)
- ✅ FastAPI router pattern properly used
- ✅ Frontend-backend integration working
- ✅ Tenant isolation mostly safe (7.5/10)
- ✅ Naming conventions 99.5% compliant

## Methodology Improvements Over 0725

- ✅ AST-based import analysis (not grep)
- ✅ FastAPI router detection
- ✅ Frontend API call parsing
- ✅ Dynamic import detection
- ✅ Cross-checked with 0700 cleanup logs
- ✅ False positive rate <10% (vs 75%+ in 0725)

## Follow-Up Handovers

- ✅ **0727: Test Fixes** - Execute (validated as real)
- ✅ **0730: Service Response Models** - Execute (validated as real)
- ❌ **0726: Tenant Isolation** - Skip (false positive)
- ❌ **0729: Orphan Removal** - Skip (dangerous)
```

### 2. Real Issues Report
Create `handovers/0725b_findings_real_issues.md`:

List only VALIDATED real issues with:
- File paths
- Line numbers
- Exact problem description
- Proposed fix
- Priority

### 3. Comms Log Updates
- Add entry for each phase completion
- Add final summary entry

### 4. Orchestrator State Update
- Add 0725b entry with results
- Update status to "reaudit_complete"

---

## Success Criteria

- [ ] AST-based analysis completed (not naive grep)
- [ ] FastAPI router registrations detected
- [ ] Frontend API calls cross-referenced
- [ ] Dynamic imports checked
- [ ] Cross-checked with 0700 cleanup logs
- [ ] Actual orphans: 2-10 files (not 129)
- [ ] False positive rate <10%
- [ ] Real issues properly prioritized
- [ ] Architecture assessment: HEALTHY
- [ ] Comms log updated with progress
- [ ] Orchestrator state updated
- [ ] Audit report created

---

## Anti-Patterns to AVOID

❌ **DO NOT:**
- Use grep/simple import scanning
- Flag FastAPI endpoints as "dead functions"
- Count test infrastructure as orphans
- Ignore dynamic imports
- Forget frontend-backend integration
- Count already-deleted files (check 0700 logs!)
- Create massive lists without validation

✅ **DO:**
- Use AST parsing
- Detect FastAPI decorators
- Parse frontend API calls
- Check against 0700 cleanup logs
- Validate each finding individually
- Focus on actionable issues
- Trust the architecture (it's healthy!)

---

## Quick Start Commands

```bash
# Navigate to project
cd F:/GiljoAI_MCP

# Activate virtualenv
source venv/Scripts/activate

# Read required docs
cat handovers/0725b_PROPER_CODE_HEALTH_REAUDIT.md
cat handovers/0725_INVALIDATED_README.md

# Open dependency graph in browser
# file:///F:/GiljoAI_MCP/docs/cleanup/dependency_graph.html

# Check what was already cleaned
cat handovers/0700_series/orchestrator_state.json | jq '.handovers[] | select(.files_deleted != null)'

# Read Serena memories
# Use mcp__serena__read_memory with: 0725_audit_invalidated, 0720_delinting_project_status
```

---

## Key Files Reference

**Handover Specs:**
- `handovers/0725b_PROPER_CODE_HEALTH_REAUDIT.md` - Your mission
- `handovers/0725_INVALIDATED_README.md` - What went wrong

**Resources:**
- `docs/cleanup/dependency_graph.html` - Visual import graph
- `handovers/0700_series/dependency_analysis.json` - Import data
- `handovers/0700_series/orchestrator_state.json` - 0700 cleanup log
- `handovers/0700_series/comms_log.json` - Communication log

**Flawed Original (For Comparison Only):**
- `handovers/0725_AUDIT_REPORT.md` - INVALIDATED
- `handovers/0725_findings_orphans.md` - 95% false positive
- `handovers/0729_ORPHAN_CODE_REMOVAL.md` - DANGEROUS

**Serena Memories:**
- `0725_audit_invalidated` - False positive documentation
- `0720_delinting_project_status` - Delinting completion
- `0700_orchestrator_session_state` - 0700 series state

---

**Created:** 2026-02-07
**Mission:** Replace flawed 0725 audit with proper FastAPI-aware analysis
**Expected Duration:** 6-8 hours
**False Positive Target:** <10% (vs 75%+ in 0725)

---

**COPY THIS ENTIRE PROMPT INTO A FRESH CLAUDE CODE SESSION TO BEGIN**
