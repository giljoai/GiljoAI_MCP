# Session: Remove switch_project from Documentation

**Date**: 2026-01-05
**Agent**: Documentation Manager
**Context**: The `switch_project` MCP tool is being removed from the codebase. All documentation references need to be updated to use `gil_activate` instead, which is the proper way to activate projects for orchestrator staging.

## Objective

Update all documentation to remove references to the deprecated `switch_project` MCP tool and replace with `gil_activate`, ensuring consistency across all user-facing and developer documentation.

## Files Updated

### 1. docs/manuals/MCP_TOOLS_MANUAL__URGENT.md
**Changes**:
- Updated Project Management Tools table
- Changed: `switch_project` → `gil_activate`
- Updated description: "Activate a project to prepare orchestrator staging"
- Added note: "Use `gil_activate` to activate projects for orchestrator staging"

**Location**: Line 25 (tools table)

### 2. docs/manuals/SLASH_COMMANDS__URGENT.md
**Changes**:
- Updated `/gil-run` command instructions
- Changed: "Switch project: Use `mcp__giljo-mcp__switch_project`" → "Activate project: Use `mcp__giljo-mcp__gil_activate`"
- Updated example code from `switch_project()` to `gil_activate()`

**Locations**:
- Line 413 (instructions section)
- Line 439 (code example)

### 3. docs/guides/API_REFERENCE__URGENT.md
**Changes**:
- Replaced entire `switch_project` section with `gil_activate`
- Updated request/response examples
- Changed message: "Switched to project" → "Project activated: X. Orchestrator staging ready."

**Location**: Section 2 (lines 60-87)

### 4. docs/guides/USER_GUIDE__URGENT.md
**Changes**:
- Updated Managing Project Lifecycle section
- Changed: `client.switch_project(project_id)` → `client.gil_activate(project_id)`
- Updated comment: "Activate a project for orchestrator staging"

**Location**: Line 227 (code example)

### 5. docs/SERVICES_ARCHITECTURE.md
**Changes**:
- Updated ProjectService Status & Metrics section
- Changed: `switch_project()` → `gil_activate()`
- Updated description: "Activate project for orchestrator staging"

**Location**: Line 128 (service methods list)

## Files Verified (No Changes Needed)

### 1. docs/MCP_OVER_HTTP_INTEGRATION.md
- ✅ No `switch_project` references found
- No changes required

### 2. src/giljo_mcp/tools/__init__.py
- ✅ No `switch_project` references found
- Docstring already clean (HTTP-only architecture documented)
- No changes required

## Files Excluded (Historical Records)

### 1. docs/sessions/2026-01-05_remove_create_project_mcp_tool.md
- Historical session file - should not be modified
- Contains reference to `switch_project` as part of historical context

### 2. docs/archive/backup_pre_subagent/PROJECT_CARDS_current_with_subagent__FRAGMENTED.md
- Archive/backup file - should not be modified
- Historical snapshot preserved for reference

## Key Decisions

### 1. Replacement Strategy
**Decision**: Replace `switch_project` with `gil_activate` throughout documentation.

**Rationale**:
- `gil_activate` is the proper MCP tool for activating projects
- Aligns with the project activation workflow
- Prepares orchestrator staging correctly
- Maintains consistency with REST API (`POST /api/v1/projects/{id}/activate`)

### 2. Message Clarity
**Decision**: Update response messages to clearly indicate "orchestrator staging ready".

**Rationale**:
- Helps users understand what `gil_activate` does
- Distinguishes from simple context switching
- Provides clear feedback about the action performed

### 3. Archive Preservation
**Decision**: Do not modify session files or archive files.

**Rationale**:
- Session files are historical records of work done
- Archive files are snapshots for reference
- Modifying historical records would be misleading
- Future developers may need to understand the evolution

## Documentation Patterns Established

### Tool Naming Convention
- **MCP Tool**: `gil_activate` (not `switch_project`)
- **REST API**: `POST /api/v1/projects/{id}/activate`
- **Client Method**: `client.gil_activate(project_id)`
- **Slash Command**: `/gil-run` uses `gil_activate` internally

### Description Template
```
"Activate a project to prepare orchestrator staging"
```

### Response Template
```json
{
  "success": true,
  "project": {
    "id": "uuid",
    "name": "Project Name",
    "status": "active"
  },
  "message": "Project activated: Project Name. Orchestrator staging ready."
}
```

## Verification Steps Completed

1. ✅ Searched all documentation files for `switch_project` references
2. ✅ Updated all user-facing documentation (manuals, guides)
3. ✅ Updated all developer documentation (architecture, services)
4. ✅ Verified MCP_OVER_HTTP_INTEGRATION.md (clean)
5. ✅ Verified tools/__init__.py (clean)
6. ✅ Confirmed only historical files contain references
7. ✅ Verified consistency of replacement terminology

## Impact Analysis

### User-Facing Impact
- **Low**: Users will see updated documentation reflecting current MCP tool names
- **Benefit**: Clear understanding that `gil_activate` is the correct tool
- **Migration**: No breaking changes - documentation only update

### Developer Impact
- **Low**: Developers will reference correct tool names in new code
- **Benefit**: Consistent naming across codebase and documentation
- **Migration**: Existing code continues to work (tool removal handled separately)

### Documentation Quality
- **Improved**: All documentation now consistent
- **Clarity**: Clear distinction between activation and context switching
- **Accuracy**: Documentation matches current MCP tool implementation

## Related Work

### Upstream Context
This documentation update follows the removal of `switch_project` from the MCP tools implementation. The tool was replaced with `gil_activate` to better reflect its purpose and align with the orchestrator staging workflow.

### Downstream Impact
No further documentation updates needed. All references to `switch_project` have been successfully migrated to `gil_activate`.

## Lessons Learned

### Documentation Hygiene
- **Pattern**: Always update documentation immediately when tools/APIs change
- **Search Strategy**: Use comprehensive grep across all docs directories
- **Verification**: Double-check both user and developer documentation

### Historical Preservation
- **Pattern**: Never modify session files or archive files
- **Rationale**: Historical context is valuable for understanding evolution
- **Alternative**: Create new session files documenting changes (like this one)

### Consistency Matters
- **Pattern**: Use consistent terminology across all documentation
- **Examples Found**: Tool name, method name, description, response message
- **Benefit**: Reduces confusion and improves developer experience

## Testing Notes

No automated testing required for documentation changes. Manual verification completed:
- ✅ All updated files render correctly in Markdown
- ✅ Code examples use correct syntax
- ✅ Links to related documentation remain valid
- ✅ Table formatting preserved

## Next Steps

This session is complete. No follow-up work required for documentation.

### Future Considerations
If `switch_project` is completely removed from the codebase:
1. ✅ Documentation already updated (this session)
2. Consider: Update any remaining comments in source code
3. Consider: Update any integration tests that reference the old tool name
4. Consider: Update any migration guides if they exist

---

**Session Status**: ✅ Complete
**Files Modified**: 5
**Files Verified**: 2
**Files Preserved**: 2 (historical)
**Total Documentation Coverage**: 100% (excluding historical files)
