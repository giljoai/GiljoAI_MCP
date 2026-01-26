# Handover 0501: Remove file_exists MCP Tool

**Status**: Ready for Implementation
**Priority**: P2 (Medium)
**Effort**: E1 (Simple - 30 min)
**Source**: Architectural Flaw - WON'T FIX (see Problem Statement)
**Created**: 2026-01-25

## Problem Statement

The `file_exists` tool (added in Handover 0360) was designed based on a flawed architectural assumption - that the MCP server could access files in the user's workspace (`Product.project_path`).

**Reality**: The MCP server is passive HTTP and cannot access files on user laptops:
- MCP server runs as a service (possibly on different machine)
- Agents run in terminal sessions on user machines
- `project_path` is a path on the USER's machine, not accessible to server

**Correct approach**: Agents use their local CLI tools (Read, Bash, Glob, etc.) for file operations.

## Files to Modify

### 1. `api/endpoints/mcp_http.py`

**Remove from schema list** (around line 569-583):
```python
# DELETE THIS BLOCK:
# File Utilities (Handover 0360 Feature 3)
{
    "name": "file_exists",
    "description": "Check whether a file or directory exists within the allowed workspace. Prevents token waste from reading entire files just to check existence. Returns exists, is_file, is_dir flags. Respects workspace sandbox - blocks path traversal attacks.",
    "inputSchema": {
        "type": "object",
        ...
    },
},
```

**Remove from tool_map** (around line 717):
```python
# DELETE THIS LINE:
"file_exists": state.tool_accessor.file_exists,
```

### 2. `src/giljo_mcp/tools/tool_accessor.py`

**Remove method** (lines 1039-1082):
```python
# DELETE THIS ENTIRE METHOD:
# File Utilities (Handover 0360 Feature 3)

async def file_exists(
    self,
    path: str,
    tenant_key: str,
    workspace_root: str | None = None,
) -> dict[str, Any]:
    ...
```

### 3. `src/giljo_mcp/tools/file_utils.py`

**Delete entire file** - No other code uses `check_file_exists()`.

### 4. `tests/tools/test_file_utils_0360.py`

**Delete entire file** - All 7 tests are specific to the removed tool.

### 5. `tests/integration/test_mcp_http_tool_catalog.py`

**Remove from expected tools list** (around line 28):
```python
# REMOVE "file_exists" from this list:
"create_successor_orchestrator",
"create_task",
"fetch_context",
"file_exists",  # <-- DELETE THIS LINE
"get_agent_mission",
```

### 6. `handovers/0383_mcp_tool_surface_audit_legacy_download_tools_removed.md`

**Update audit document** - Remove `file_exists` from:
- Line 46: Tool inventory list
- Line 119: Context + templates section

## Implementation Steps

1. Remove tool schema from `handle_tools_list()` in `mcp_http.py`
2. Remove tool from `tool_map` in `handle_tools_call()` in `mcp_http.py`
3. Remove `file_exists` method from `ToolAccessor` class
4. Delete `src/giljo_mcp/tools/file_utils.py`
5. Delete `tests/tools/test_file_utils_0360.py`
6. Update `tests/integration/test_mcp_http_tool_catalog.py` - remove from expected list
7. Update `handovers/0383_mcp_tool_surface_audit_legacy_download_tools_removed.md`
8. Run tests to verify no regressions

## Verification

```bash
# Verify no remaining references
grep -r "file_exists" src/giljo_mcp/

# Verify tool removed from MCP schema
python -c "from api.endpoints.mcp_http import *; print([t['name'] for t in get_tools_schema()])" | grep file_exists

# Run tests
pytest tests/ -v
```

## Notes

**Unrelated matches** - The following files contain unrelated method names:
- `tests/slash_commands/test_gil_task.py` - `test_command_file_exists()` method
- `tests/unit/test_npm_installation_system.py` - `test_uses_npm_ci_when_lockfile_exists()` method
- `tests/unit/test_install.py` - `test_env_file_exists_before_migrations()` method
- `tests/test_startup_validation.py` - `test_bat_file_exists()` method
- `tests/migrations/test_0106_migration_simple.py` - `test_migration_file_exists()` method
- `tests/helpers/mock_servers.py` - `mock_fs.file_exists` mock attribute

These do NOT need modification.

## Acceptance Criteria

- [ ] Tool removed from MCP schema in `mcp_http.py`
- [ ] Tool removed from `tool_map` in `mcp_http.py`
- [ ] `file_exists` method removed from `ToolAccessor`
- [ ] `file_utils.py` deleted
- [ ] `test_file_utils_0360.py` deleted
- [ ] `test_mcp_http_tool_catalog.py` updated
- [ ] Audit document updated
- [ ] All tests pass
- [ ] `grep -r "file_exists" src/giljo_mcp/` returns no matches
