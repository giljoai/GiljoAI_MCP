# Kickoff: Handover 0700e - Template System Cleanup

**Series:** 0700 Code Cleanup Series
**Handover:** 0700e
**Risk Level:** LOW
**Estimated Time:** 1-2 hours
**Date:** 2026-02-04

---

## Mission Statement

Remove deprecated template system components and ALL code that references them. This is a PURGE operation, not a migration. Delete the deprecated fields from the database model AND all code that reads/writes/references them.

**Critical Context:** 0700b deferred template_content column removal to this handover. You are authorized to delete this column AND all code using it. No backward compatibility needed - we are shipping clean v1.0 with no external users.

---

## Phase 1: Context Acquisition

### Required Reads

1. **Your Spec**: `handovers/0700_series/0700e_template_system_cleanup.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
   - Read entry `0700b-complete-001` - Context on template_content deferral
   - Read entry `0700-003` - Template adapter findings from cleanup index
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
4. **Dependencies**: Depends on 0700c (COMPLETE)

### Key Context from Previous Handovers

**From 0700b-complete-001:**
- template_content column removal was DEFERRED to 0700e
- 0700b said: "template_content (AgentTemplate) - Deferred to 0700e (Template System Cleanup)"
- 50+ usages identified across template system
- The column is still in the model and actively used

**From 0700-003 (Template adapter findings):**
- TemplateManager alias at `src/giljo_mcp/template_manager.py:1048` - primary target
- Related entries in cleanup_index.json:
  - dep-014: TemplateManager alias
  - dep-015: template_content field in seeder
  - dep-012: AgentTemplate.template_content model field
  - dep-039: TemplateUpdate.template_content API schema
- All marked for v4.0 removal (but there is no v4.0 - we're shipping v1.0 clean)

**PURGE Authorization (from orchestrator-002):**
> "There is no v4.0. We ARE v1.0. No external users exist. Delete the columns AND all code that uses them."

---

## Phase 2: Scope Investigation

### Primary Targets

1. **TemplateManager Alias** - `src/giljo_mcp/template_manager.py:1048-1051`
   ```python
   # DEPRECATED: Use UnifiedTemplateManager directly. This alias will be removed in v4.0.
   TemplateManager = UnifiedTemplateManager  # DEPRECATED
   ```
   - ACTION: Delete alias
   - ACTION: Find all imports using `from template_manager import TemplateManager`
   - ACTION: Replace with `UnifiedTemplateManager`

2. **template_content Database Column** - `src/giljo_mcp/models/templates.py:76`
   ```python
   comment="DEPRECATED (v3.1): Use system_instructions + user_instructions. Kept for backward compatibility."
   ```
   - ACTION: Delete column from AgentTemplate model
   - ACTION: Find ALL code reading/writing template_content (~50+ usages)
   - ACTION: Delete that code or replace with system_instructions + user_instructions

3. **Template Seeder Legacy Field** - `src/giljo_mcp/template_seeder.py:248`
   ```python
   # DEPRECATED: Legacy field for backward compatibility
   ```
   - ACTION: Remove code populating template_content
   - ACTION: Verify seeder still creates valid templates

4. **Template Manager Field Handling** - `src/giljo_mcp/template_manager.py:133`
   ```python
   - template_content: DEPRECATED (v3.0 compatibility only)
   ```
   - ACTION: Remove template_content parameter handling
   - ACTION: Update docstrings to remove deprecated references

5. **API Schema** - `TemplateUpdate.template_content`
   - ACTION: Remove from Pydantic schemas
   - ACTION: Remove from API endpoint responses

### Investigation Tasks

Use Serena MCP tools for efficient searching:

```python
# Find all references to template_content
mcp__serena__search_for_pattern(
    substring_pattern="template_content",
    restrict_search_to_code_files=True,
    output_mode="files_with_matches"
)

# Find all references to TemplateManager alias
mcp__serena__search_for_pattern(
    substring_pattern="from.*template_manager import TemplateManager",
    restrict_search_to_code_files=True,
    output_mode="content"
)

# Check template model
mcp__serena__find_symbol(
    name_path_pattern="AgentTemplate",
    relative_path="src/giljo_mcp/models/templates.py",
    include_body=True
)
```

### Expected Files to Modify

Based on spec:
- `src/giljo_mcp/template_manager.py` - Remove alias, remove parameter handling
- `src/giljo_mcp/models/templates.py` - Remove column
- `src/giljo_mcp/template_seeder.py` - Remove legacy field population
- `src/giljo_mcp/models/schemas.py` - Remove from API schemas
- `migrations/versions/baseline_v32_unified.py` - Remove column from migration
- **ANY file that imports TemplateManager** - Replace with UnifiedTemplateManager
- **ANY file that reads/writes template_content** - Delete or refactor

---

## Phase 3: Execution Plan

### Recommended Subagents

- **deep-researcher** - Find all references to deprecated items
- **tdd-implementor** - Execute removal with tests

### Execution Order

**Step 1: Discovery**
- Use Serena to find ALL usages of:
  - `template_content` (column/field/property)
  - `TemplateManager` (alias)
- Create comprehensive list of files to modify

**Step 2: TemplateManager Alias Removal**
- Delete alias from `template_manager.py`
- Update all imports to use `UnifiedTemplateManager`
- Verify no references remain

**Step 3: template_content Column Purge**
- Remove column from `src/giljo_mcp/models/templates.py`
- Remove from baseline migration
- Delete ALL code that:
  - Reads from template_content
  - Writes to template_content
  - Passes template_content as parameter
  - Returns template_content in API responses
- Update schemas to remove template_content field

**Step 4: Seeder Cleanup**
- Remove template_content population code
- Verify seeder still creates valid templates
- Test: `python install.py` should seed templates correctly

**Step 5: Test Updates**
- Find tests that reference template_content
- Update or delete them
- Ensure all template tests still pass

**Step 6: Verification**
```bash
# Should return ZERO results (except historical docs)
grep -r "template_content" src/
grep -r "TemplateManager" src/ | grep -v "UnifiedTemplateManager"

# Models should load
python -c "from giljo_mcp.models import AgentTemplate; print('OK')"

# Tests should pass
pytest tests/unit/test_template_manager.py -v
pytest tests/services/test_template_service.py -v
```

---

## Phase 4: Documentation

### Files to Check (from doc_impacts.json)

The spec mentions these areas:
- Template system documentation
- API documentation (if template_content exposed)
- Service layer docs (if template methods documented)

### Updates Needed

- Remove any mentions of TemplateManager alias
- Remove any mentions of template_content field
- Update code examples to use only system_instructions + user_instructions
- Update architecture docs if template system structure changed

---

## Phase 5: Communication

### Write to comms_log.json

After completion, write an entry for downstream handovers:

```json
{
  "id": "0700e-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0700e",
  "to_handovers": ["0700g", "orchestrator"],
  "type": "info",
  "subject": "Template system cleanup complete - TemplateManager and template_content removed",
  "message": "Removed TemplateManager alias (X files updated to use UnifiedTemplateManager). Removed template_content column from AgentTemplate model (Y files modified/deleted). Template seeding verified working. All template operations now use system_instructions + user_instructions exclusively. Lines removed: ~[ESTIMATE]. Baseline migration updated.",
  "files_affected": [
    "[list all modified files]"
  ],
  "action_required": false,
  "context": {
    "lines_removed": "[ESTIMATE]",
    "files_modified": "[COUNT]",
    "import_updates": "[COUNT of TemplateManager -> UnifiedTemplateManager]",
    "template_content_usages_removed": "[COUNT]"
  }
}
```

**Who needs to know:**
- **0700g** - Might clean up related enums/exceptions
- **orchestrator** - Track progress

---

## Phase 6: Commit & Report

### Update orchestrator_state.json

```json
{
  "id": "0700e",
  "status": "complete",
  "started_at": "[ISO timestamp]",
  "completed_at": "[ISO timestamp]",
  "worker_session_id": "[your session]",
  "docs_updated": ["[list docs you updated]"],
  "columns_removed": ["template_content"],
  "aliases_removed": ["TemplateManager"],
  "lines_removed": "[ESTIMATE]"
}
```

### Commit Message

```
cleanup(0700e): Remove deprecated template system components

Removed TemplateManager alias and template_content column as part of v1.0 cleanup.
No backward compatibility needed - shipping clean.

Changes:
- Deleted TemplateManager alias from template_manager.py
- Updated X imports to use UnifiedTemplateManager directly
- Removed template_content column from AgentTemplate model
- Removed template_content from all API schemas
- Cleaned template_seeder.py legacy field handling
- Updated baseline migration to exclude template_content
- Deleted/refactored Y files that used template_content

Verification:
- Template seeding works: python install.py
- All template tests pass
- Zero grep matches for removed items

Docs Updated:
- [list docs]

```

---

## Risk Mitigation

**LOW RISK** - Template system is self-contained

### Rollback Plan
- Git revert if something breaks
- Fresh install will work (baseline migration won't have removed column)

### Pre-Flight Checks
- [ ] UnifiedTemplateManager is the active implementation (verify in code)
- [ ] system_instructions + user_instructions are present in model
- [ ] Template seeder already uses new format (verify before changes)

### Parallel Execution Note

**0700f is running in PARALLEL** - Do NOT modify these files:
- `api/endpoints/prompts.py` (0700f target)
- `api/endpoints/mcp_http.py` (0700f target)
- `src/giljo_mcp/database.py` (0700f target)
- `api/app.py` (0700f target)

If you discover overlap, STOP and write to comms_log immediately.

---

## Success Criteria

- [ ] TemplateManager alias removed
- [ ] All imports updated to UnifiedTemplateManager
- [ ] template_content column removed from model
- [ ] template_content removed from baseline migration
- [ ] All code using template_content deleted or refactored
- [ ] Template seeding works: `python install.py`
- [ ] All template tests pass: `pytest tests/unit/test_template_manager.py tests/services/test_template_service.py`
- [ ] Zero grep matches for removed items
- [ ] Documentation updated
- [ ] comms_log entry written
- [ ] orchestrator_state.json updated
- [ ] Changes committed with proper message

---

**Remember:** This is a PURGE, not a migration. Delete the deprecated code ruthlessly. If something breaks, we can git revert. Fresh installs will work because the baseline migration won't include removed columns.

**When in doubt:** Write to comms_log and ask the orchestrator.

**Start time:** When you begin Phase 2 (Scope Investigation)
