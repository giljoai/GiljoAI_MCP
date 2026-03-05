# Diagnostic Investigation: Critical Product/Project State Bugs

**Agent**: Deep Researcher (diagnostic mode)
**Mission**: Investigate critical bugs in product creation and project reactivation workflows
**Scope**: READ-ONLY investigation - NO CODE MODIFICATIONS

---

## CRITICAL INSTRUCTION: RESEARCH ONLY

🚫 **DO NOT MODIFY ANY CODE**
🚫 **DO NOT FIX ANY BUGS**
🚫 **DO NOT WRITE MIGRATIONS**
🚫 **DO NOT UPDATE TESTS**

✅ **DO: Read code thoroughly**
✅ **DO: Trace execution flows**
✅ **DO: Identify root causes**
✅ **DO: Document findings**
✅ **DO: Recommend fix approaches**

---

## Bug A: Creating New Product Destroys Active State

### User Report
- User created a NEW product (did NOT activate it)
- **Observed behavior**:
  - All tasks in `/tasks` list disappeared
  - All jobs disappeared
  - Current projects were deactivated (but stayed in list)
  - System behaved as if "create product" triggered "deactivate everything"

### Investigation Tasks

1. **Product Creation Endpoint**
   - Read `api/endpoints/products/crud.py` - look for product creation handler
   - Check if product creation calls activation/deactivation logic
   - Look for WebSocket events emitted on product creation
   - Check if creation sets `is_active` flag or modifies active_product state

2. **Frontend Store State**
   - Read frontend product store/composable
   - Check if creating a product changes "active product" state
   - Look for side effects in store mutations/actions
   - Check WebSocket event handlers for product creation

3. **Project Deactivation Cascade**
   - Search for code that deactivates projects when products change
   - Check `api/endpoints/projects/lifecycle.py` for deactivation triggers
   - Look for auto-deactivation logic in services
   - Check if there's a "deactivate all on new product" pattern

4. **0700 Series Impact Check**
   - Read comms_log entry `0700-006` about service fallback methods without tenant filtering
   - Check if 0700b's removal of `context_budget` from Project could affect queries
   - Check if 0700c's Product.product_memory changes affect product creation defaults
   - Look for any removed GUARDS that might have prevented this behavior

---

## Bug B: Reactivating Project Creates New Orchestrator

### User Report
- User reactivated a project they were previously working on
- **Observed behavior**:
  - A NEW orchestrator was spawned (should not happen)
  - Possible triggers: leaving project, coming back, reactivating

### Investigation Tasks

1. **Project Reactivation Flow**
   - Read `api/endpoints/projects/lifecycle.py` - find reactivation endpoint
   - Check if reactivation explicitly triggers orchestrator spawning
   - Look for conditions that decide when to spawn vs reuse orchestrator

2. **Orchestrator Auto-Spawn Logic**
   - Read `OrchestrationService` - find auto-spawn methods
   - Check if project activation always creates orchestrator
   - Look for "create orchestrator if none exists" logic
   - Determine distinction between "activate project" vs "resume project"

3. **0700d Impact on Succession**
   - Read 0700d completion notes - `trigger_succession` was STUBBED with NotImplementedError
   - Check if reactivation path calls `trigger_succession` (would now crash)
   - Look for fallback logic that creates new orchestrator on succession failure
   - Check if removal of succession code broke "continue with existing orchestrator" path

4. **Agent Lifecycle Checks**
   - Search for "reactivate" and "activate" in services
   - Check `AgentJobManager` for orchestrator reuse logic
   - Look for queries like "get active orchestrator for project"
   - Check if there's a "check if orchestrator exists before spawning" guard

---

## Files to Investigate (Priority Order)

### Product Bug (Bug A)
1. `api/endpoints/products/crud.py` - Product creation endpoint
2. `api/endpoints/products/lifecycle.py` - Product activation/deactivation
3. `src/giljo_mcp/services/product_service.py` - Product service ⚠️ (has known bugs per cleanup_index)
4. `src/giljo_mcp/services/project_service.py` - Project service ⚠️ (has 3 CRITICAL bugs per cleanup_index)
5. `frontend/src/stores/` - Frontend state management
6. `api/websocket.py` or `api/websocket_service.py` - WebSocket events

### Project Reactivation Bug (Bug B)
1. `api/endpoints/projects/lifecycle.py` - Project activation/reactivation
2. `src/giljo_mcp/services/orchestration_service.py` - Orchestrator spawning
3. `src/giljo_mcp/services/agent_job_manager.py` - Agent lifecycle
4. `src/giljo_mcp/services/project_service.py` - Project activation logic

---

## 0700 Series Changes (Potential Causes)

### 0700a: Light Mode Removal (~145 lines frontend)
- Removed light mode theme
- **Impact**: Low risk - purely UI theme changes

### 0700b: Database Column Purge (~1000 lines)
- Removed 7 columns: `decommissioned_at`, `succeeded_by`, `succession_reason`, `handover_summary`, `is_used`, `downloaded_at`, `context_budget`
- Deleted `orchestrator_succession.py` module
- **Impact**: HIGH RISK
  - Removed `context_budget` from Project - could affect queries
  - Removed succession columns - could affect orchestrator lifecycle
  - Deleted succession module - cascade effects unknown

### 0700c: JSONB Field Cleanup (~150 lines)
- Removed `AgentExecution.messages` JSONB
- Removed `Product.product_memory.sequential_history`
- **Impact**: MEDIUM RISK
  - Changed Product.product_memory structure - could affect defaults on creation

### 0700d: Succession System Removal (~750 lines)
- Deleted `api/endpoints/agent_jobs/succession.py`
- Stubbed `OrchestrationService.trigger_succession()` with `NotImplementedError`
- Removed 4 succession schemas
- **Impact**: HIGH RISK
  - Any code calling `trigger_succession()` will crash
  - Possible fallback to "create new orchestrator" on error

### 0709: Implementation Phase Gate
- Added `Project.implementation_launched_at` column
- **Impact**: LOW RISK - additive change only

---

## Known Issues from cleanup_index.json

### CRITICAL Bugs in project_service.py
Per cleanup_index entries `skip-bug-001`, `skip-bug-002`, `skip-bug-003`:

1. **UnboundLocalError**: `total_jobs` at line 1545
   - Blocks `test_get_project_summary_happy_path`
   - Blocks `test_get_project_orchestrator_happy_path`

2. **Validation Bug**: Complete endpoint causes 422 for valid projects
   - Blocks `test_complete_project_happy_path`

3. **Service Fallback Methods**: Without tenant filtering (entries `dep-019`, `dep-025`, `dep-026`)
   - Security concern per comms_log `0700-006`
   - Located at: `project_service.py:510`, `project_service.py:2181`
   - Also in: `message_service.py:157`

---

## Git Bisect Approach

For each 0700 series commit:
1. Check `git log --oneline` for 0700a, 0700b, 0700c, 0700d, 0709
2. For each commit, check modified files
3. Cross-reference with files related to product creation / project activation
4. Look for REMOVED code that might have been a GUARD against these behaviors

Example searches:
```bash
# Find recent changes to product creation
git log --oneline --all --grep="product" -- api/endpoints/products/

# Find recent changes to project activation
git log --oneline --all --grep="activate" -- api/endpoints/projects/

# Show what was removed in 0700b
git show <0700b-commit-hash> -- src/giljo_mcp/models/

# Check if any removed code called deactivation
git show <commit-hash> | grep -i "deactivate"
```

---

## Investigation Protocol

### Phase 1: Product Creation Bug (Bug A)
1. Read product creation endpoint - trace full execution
2. Read WebSocket event emission code
3. Read frontend product store - check state mutations
4. Search for auto-deactivation triggers
5. Check 0700b/0700c changes for removed guards
6. Identify root cause

### Phase 2: Reactivation Bug (Bug B)
1. Read project reactivation endpoint
2. Read orchestrator spawning logic in OrchestrationService
3. Check if reactivation calls stubbed trigger_succession
4. Look for "reuse existing orchestrator" logic
5. Check 0700d changes for broken continuation path
6. Identify root cause

### Phase 3: Pre-Existing vs 0700-Introduced
- For each bug, determine if 0700 series caused it OR exposed it
- Check if bug existed before 0700 (search handovers/docs for known issues)
- Look for TODO/FIXME markers about this behavior in affected files

---

## Output Format

Save diagnostic report to: `handovers/0700_series/bug_diagnostic_report.md`

### Required Sections

```markdown
# Bug Diagnostic Report

**Generated**: [timestamp]
**Investigation Scope**: Product creation and project reactivation bugs

---

## Bug A: Creating New Product Destroys Active State

### Root Cause
[Detailed explanation with file:line references]

### Evidence
- File: path/to/file.py, Line: 123
  ```python
  # Code snippet showing the issue
  ```
- [Additional evidence]

### 0700-Related?
[YES/NO] - [Explanation]
[If YES, which handover: 0700a/b/c/d/0709?]

### Recommended Fix Approach
1. [Step-by-step fix plan]
2. [Files to modify]
3. [Test strategy]

---

## Bug B: Reactivating Project Creates New Orchestrator

### Root Cause
[Detailed explanation with file:line references]

### Evidence
- File: path/to/file.py, Line: 456
  ```python
  # Code snippet showing the issue
  ```
- [Additional evidence]

### 0700-Related?
[YES/NO] - [Explanation]
[If YES, which handover: 0700a/b/c/d/0709?]

### Recommended Fix Approach
1. [Step-by-step fix plan]
2. [Files to modify]
3. [Test strategy]

---

## Priority Assessment

**Most Critical**: [Bug A or Bug B]
**Recommended Fix Order**: [A first, B first, or parallel]
**Estimated Complexity**: [LOW/MEDIUM/HIGH for each bug]

---

## Additional Findings

[Any other issues discovered during investigation]

---

## Recommended Subagents

- **Bug A Fix**: [system-architect / backend-integration-tester]
- **Bug B Fix**: [system-architect / backend-integration-tester]
```

---

## Success Criteria

✅ Root cause identified for Bug A with file:line references
✅ Root cause identified for Bug B with file:line references
✅ Determined if 0700 series caused or exposed each bug
✅ Recommended fix approach documented for each bug
✅ Evidence documented with code snippets
✅ Report saved to `handovers/0700_series/bug_diagnostic_report.md`

---

## Important Notes

- The cleanup_index.json noted 3 CRITICAL production bugs in project_service.py - these may be related
- The comms_log entry 0700-006 warned about "Service fallback methods without tenant filtering"
- 0700b removed `context_budget` from Project - could affect lifecycle queries
- 0700d stubbed `trigger_succession` with NotImplementedError - ANY call to it will crash
- Use Serena MCP for symbolic code navigation: `find_symbol`, `get_symbols_overview`, `find_referencing_symbols`
- DO NOT read entire files - use targeted searches and symbol lookups

---

## Handover Metadata

**Series**: 0700 (Code Cleanup)
**Type**: Diagnostic Investigation
**Risk**: Research only - no code changes
**Dependencies**: None
**Output**: bug_diagnostic_report.md
