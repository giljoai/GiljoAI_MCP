# 0700g Kickoff: Enums and Exceptions Cleanup

**Series**: 0700 Code Cleanup
**Handover**: 0700g
**Priority**: LOW
**Risk**: LOW
**Dependencies**: 0700e (complete), 0700f (complete)

---

## Your Mission

Remove unused enums and exception classes from the codebase. This is a targeted cleanup of two specific files, plus import cleanup across files that reference them.

**CRITICAL CONTEXT**: You are working AFTER a major cleanup series (0700a-f) that removed:
- Succession module, schemas, and all decommissioning code (0700b, 0700d)
- AgentExecution.messages JSONB column (0700c)
- template_content column and TemplateManager alias (0700e)
- Deprecated API endpoints, generate_execution_prompt(), query_with_tenant() (0700f)

Many items that were "in use" before are now orphaned. Verify each item is truly unused BEFORE removing.

---

## Files to Read First

1. `handovers/0700_series/WORKER_PROTOCOL.md` (your execution protocol)
2. `handovers/0700_series/0700g_enums_exceptions_cleanup.md` (detailed spec)
3. `handovers/0700_series/comms_log.json` (read entries where to_handovers includes "0700g")
4. `src/giljo_mcp/enums.py` (PRIMARY TARGET - enum definitions)
5. `src/giljo_mcp/exceptions.py` (PRIMARY TARGET - exception definitions, 28 dependents - HIGH-RISK file)

---

## Tasks

### Task 1: Remove Unused Enum Values
- `AgentStatus.DECOMMISSIONED` - Deprecated in 0461b, decommissioning code purged in 0700b/0700d
- **Verify**: `grep -r "DECOMMISSIONED" src/ api/ --include="*.py"` should show only the enum definition

### Task 2: Remove Entire Unused Enums
- `AugmentationType` enum (~8 lines) - Never implemented
- `ArchiveType` enum (~8 lines) - Never implemented
- `InteractionType` enum (~7 lines) - **VERIFY USAGE FIRST** with grep before removing
- **Verify each**: `grep -r "AugmentationType\|ArchiveType\|InteractionType" src/ api/ frontend/ --include="*.py" --include="*.js" --include="*.vue"`

### Task 3: Remove Unused Exception Classes
- `TemplateValidationError` (~5 lines) - Template system simplified in 0700e
- `TemplateRenderError` (~5 lines) - Same
- `GitOperationError` (~5 lines) - Never raised in production code
- `GitAuthenticationError` (~5 lines) - Never raised
- `GitRepositoryError` (~5 lines) - Never raised
- **Verify each**: `grep -r "TemplateValidationError\|TemplateRenderError\|GitOperationError\|GitAuthenticationError\|GitRepositoryError" src/ api/ tests/ --include="*.py"`
- **WARNING**: `exceptions.py` has 28 dependents (HIGH-RISK file from 0701 dependency analysis). Only remove exception CLASSES that are never raised or caught. Do NOT remove the file itself or any actively-used exceptions.

### Task 4: Clean Up Imports of Removed Items
- Search all files importing deleted enums/exceptions
- Remove those import statements
- Check `__init__.py` re-exports (especially `src/giljo_mcp/__init__.py`, `src/giljo_mcp/models/__init__.py`)

### Task 5: Update `__all__` Exports
- Remove deleted items from `__all__` in `enums.py` and `exceptions.py`

### Task 6: Also Clean Up (Bonus - Low Hanging Fruit)
These deprecated frontend components were orphaned by 0700d succession removal:
- `frontend/src/components/projects/LaunchSuccessorDialog.vue` - DELETE entire file (dep-045)
- `frontend/src/components/projects/SuccessionTimeline.vue` - DELETE entire file (dep-046)
- `frontend/src/components/projects/__tests__/LaunchSuccessorDialog.spec.js` - DELETE test file (skip-fe-003)
- `frontend/src/components/projects/__tests__/SuccessionTimeline.spec.js` - DELETE test file (skip-fe-002)
- Verify no imports remain for these components in other Vue files
- Also clean up these dead code items:
  - `api/endpoints/users.py:1021` - Remove "# REMOVED:" comment block (dead-002)
  - `api/app.py:246` - Remove commented-out agents tag (dead-003)

---

## Verification

After all changes:
1. `grep -r "AugmentationType\|ArchiveType\|InteractionType" src/ api/ --include="*.py"` = 0 results
2. `grep -r "TemplateValidationError\|TemplateRenderError\|GitOperationError\|GitAuthenticationError\|GitRepositoryError" src/ api/ --include="*.py"` = 0 results (tests OK)
3. `grep -r "DECOMMISSIONED" src/ api/ --include="*.py"` = 0 results
4. `grep -r "LaunchSuccessorDialog\|SuccessionTimeline" frontend/src/ --include="*.vue" --include="*.js"` = 0 results
5. Python models load: `python -c "from src.giljo_mcp.models import *; from src.giljo_mcp.enums import *; from src.giljo_mcp.exceptions import *; print('OK')"`
6. Run: `pytest tests/ -x -q --timeout=30` (quick sanity check)

---

## Comms Log Entry

When complete, append to `handovers/0700_series/comms_log.json`:
```json
{
  "id": "0700g-001",
  "timestamp": "<ISO timestamp>",
  "from_handover": "0700g",
  "to_handovers": ["0700h", "orchestrator"],
  "type": "info",
  "subject": "Enums and exceptions cleanup complete",
  "message": "<summary of what was removed, line counts, any items that were NOT removed because they're still in use>",
  "files_affected": ["<list of files modified/deleted>"],
  "action_required": false,
  "context": {
    "enums_removed": "<count>",
    "exceptions_removed": "<count>",
    "frontend_components_deleted": "<count>",
    "lines_removed": "<count>",
    "items_kept": "<any items that turned out to be still in use>"
  }
}
```

Also update `handovers/0700_series/orchestrator_state.json`:
- Set 0700g status to "complete"
- Set started_at and completed_at timestamps
- Add files_deleted and lines_removed fields

---

## Rules
- VERIFY before deleting - grep for each item first
- Do NOT remove actively-used exceptions from exceptions.py (28 dependents!)
- Do NOT touch enums/exceptions that are still raised or caught somewhere
- If in doubt, KEEP the item and note it in comms_log
- Follow WORKER_PROTOCOL.md 6-phase execution
