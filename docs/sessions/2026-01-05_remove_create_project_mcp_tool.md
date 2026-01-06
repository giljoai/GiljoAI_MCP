# Session: Remove create_project MCP Tool References

**Date**: 2026-01-05
**Agent**: Documentation Manager
**Context**: The `create_project` MCP tool has been removed from the codebase. Projects are now created exclusively via the REST API endpoint `POST /api/v1/projects/`.

## Objective

Remove all references to the `create_project` MCP tool from documentation while preserving REST API documentation for project creation.

## Key Decisions

1. **REST API is the Single Source**: Project creation is handled by REST API endpoints, not MCP tools
2. **Clear Documentation**: Added explicit notes in affected files explaining that project creation uses REST API
3. **Renumbered Tools**: Updated tool numbering in API_REFERENCE to account for removed tool
4. **Preserved REST Documentation**: All REST API documentation for project creation remains intact

## Files Modified

### 1. docs/MCP_OVER_HTTP_INTEGRATION.md
- **Lines 254-268**: Replaced `create_project` example in tools/list response with `get_orchestrator_instructions`
- **Lines 350-363**: Updated example tool calls to remove "Create a new project" example

### 2. docs/manuals/MCP_TOOLS_MANUAL__URGENT.md
- **Line 24**: Removed `create_project` row from Project Management Tools table
- **Line 32**: Added note: "Projects are created via REST API (`POST /api/v1/projects/`), not MCP tools"
- **Lines 93-101**: Updated usage example to show REST API approach with comments

### 3. docs/guides/MCP_INTEGRATION_GUIDE__URGENT.md
- **Line 615**: Updated tool list example from `"create_project", "spawn_agent"` to `"get_orchestrator_instructions", "spawn_agent_job"`
- **Lines 621-624**: Changed verification example from `@giljo-mcp list_projects` to `@giljo-mcp health_check`

### 4. docs/guides/API_REFERENCE__URGENT.md
- **Lines 16-48**: Removed entire `create_project` MCP tool section
- **Line 16**: Added note explaining REST API is used for project creation
- **Lines 18-153**: Renumbered all tools (1. list_projects, 2. switch_project, etc.)
- **Lines 220-1110**: Renumbered Agent Management (6-11), Message Communication (12-17), and Context & Vision (18-25) tools
- **Lines 1091-1110**: Updated help tool response to show 25 total tools (down from 26), project_management count 5 (down from 6)

### 5. docs/GILJOAI_MCP_PURPOSE.md
- **Line 196**: Changed `- \`create_project()\` - Initialize new development projects` to `- REST API for project creation (\`POST /api/v1/projects/\`)`

### 6. src/giljo_mcp/tools/__init__.py
- **Lines 23-26**: Updated Projects section docstring to list `activate_project, list_projects, etc.` instead of `create_project, activate_project, etc.`
- **Line 26**: Added note: "Project creation uses REST API (POST /api/v1/projects/), not MCP tools"

## Remaining References (Intentionally Left)

The following files contain references to `create_project` but were intentionally NOT modified:

1. **docs/archive/** - Archived documentation preserved for historical reference
2. **docs/ORCHESTRATION_ARCHITECTURE.md** - May contain service layer or REST API documentation (not MCP tools)
3. **docs/SERVER_ARCHITECTURE_TECH_STACK.md** - Contains REST API/service layer code examples
4. **docs/SERVICES.md** - Service layer documentation for `ProjectService.create_project()`
5. **docs/SERVICES_ARCHITECTURE.md** - Service layer architecture showing internal implementation
6. **docs/guides/USER_GUIDE__URGENT.md** - May contain SDK/client library examples (different from MCP tools)

These files document the **REST API endpoint** or **service layer implementation**, not the removed MCP tool interface. They remain accurate and should not be modified.

## Technical Details

### What Changed
- **MCP Tool Interface**: Removed - no longer exposed via MCP-over-HTTP endpoint
- **REST API**: Unchanged - `POST /api/v1/projects/` remains the canonical way to create projects
- **Service Layer**: Unchanged - `ProjectService.create_project()` internal method still exists

### Why This Change
The MCP tool layer was redundant since projects are created through the web dashboard UI, which calls the REST API directly. MCP tools are designed for orchestration operations (spawning agents, sending messages), not for initial project setup.

## Lessons Learned

1. **Clear Architecture Boundaries**: MCP tools vs REST API serve different purposes
   - MCP tools: Agent orchestration and coordination
   - REST API: CRUD operations and user-facing actions

2. **Documentation Consistency**: When removing a feature, search all documentation thoroughly
   - Used `grep -r "create_project" docs/` to find all references
   - Verified context of each reference (MCP tool vs REST API vs service layer)

3. **Preserve Historical Context**: Archive directories intentionally left unchanged
   - Maintains project history for future reference
   - Prevents confusion about what was removed vs what was never implemented

## Verification

All changes verified by:
1. Searching for remaining MCP tool references: `grep -r "create_project" docs/ --include="*.md"`
2. Confirming remaining references are for REST API/service layer (legitimate)
3. Ensuring all MCP-specific documentation has been updated

## Next Steps

✅ Complete - All MCP tool references to `create_project` have been removed from active documentation.

**Recommendation**: If any new documentation is created that references the 25 available MCP tools, ensure `create_project` is not included in the list.
