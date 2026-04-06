# Handover 0909: gil_discovery MCP Tool

**Edition Scope:** CE
**Date:** 2026-04-06
**Priority:** Medium
**Estimated Effort:** 2-3 hours
**Status:** COMPLETE

---

## Task Summary

Add a `gil_discovery` MCP tool that lets agents query what categories, types, and configuration options exist in the system before acting. This eliminates guesswork when agents create projects, select types, or reference system entities.

## Context / Background

During Codex CLI testing (2026-04-06), the agent used `project_type: "TST"` when creating a project — a type that doesn't exist in the preloaded taxonomy. The server silently created the project without taxonomy, and the agent displayed "SCAFFOLD-0001" as if it was confirmed. The root cause: agents have no way to discover what project types are available before calling `create_project`.

The `create_project` tool now warns when a type isn't recognized (commit `8af8c4c8`), but agents still guess blindly. A discovery tool lets them query first, act correctly.

**Design principle:** One tool with a `category` switch parameter — not one tool per lookup. This keeps the tool surface minimal while being extensible. New categories are a single switch case addition, not a new tool registration.

## Technical Details

### New MCP Tool: `gil_discovery`

**Registration:** `api/endpoints/mcp_sdk_server.py`

```python
@mcp.tool(
    description=(
        "Discover available system categories and configuration. "
        "Use this BEFORE creating projects or referencing system entities. "
        "Returns live data for the current tenant."
    ),
)
async def gil_discovery(
    category: str,
    ctx: Context = None,
) -> dict:
```

**Parameter:**
- `category` (required, string): What to look up. Valid values:
  - `"project_types"` — available taxonomy types (abbreviation, label, color)

**Response format:**
```json
{
  "category": "project_types",
  "items": [
    {"abbreviation": "FE", "label": "Frontend", "color": "#6DB3E4"},
    {"abbreviation": "BE", "label": "Backend", "color": "#E07872"},
    ...
  ],
  "count": 8,
  "hint": "Use the abbreviation value as project_type when calling create_project"
}
```

**Error response for unknown category:**
```json
{
  "error": "Unknown category 'foo'. Valid categories: project_types",
  "valid_categories": ["project_types"]
}
```

### Implementation Path

**Backend (tool accessor):**

Add `async def discovery(self, category: str, tenant_key: str) -> dict` to `ToolAccessor` in `src/giljo_mcp/tools/tool_accessor.py`.

This method:
1. Validates `category` against a known set
2. Dispatches to the appropriate query
3. For `"project_types"`: calls `list_project_types()` from `api/endpoints/project_types/crud_ops.py` (already exists, used by the REST API)
4. Returns structured response with items, count, and a hint

**Key constraint:** The discovery method must use the existing `list_project_types` query — do NOT create a new DB query. The REST endpoint `GET /api/v1/project-types` already triggers lazy seeding and returns all types. Reuse that logic.

**MCP registration:**

Add the `@mcp.tool` decorated function in `mcp_sdk_server.py`. Follow the existing pattern: thin wrapper that calls `_call_tool(ctx, "discovery", {"category": category})`.

### Files to Modify

| File | Change |
|------|--------|
| `api/endpoints/mcp_sdk_server.py` | Add `gil_discovery` tool registration |
| `src/giljo_mcp/tools/tool_accessor.py` | Add `discovery()` method |

### Files to Read (do NOT modify)

| File | Why |
|------|-----|
| `api/endpoints/project_types/crud_ops.py` | Existing `list_project_types()` to reuse |
| `api/endpoints/project_types/routes.py` | Reference for response shape |

### What NOT to Do

- Do NOT create a new service class for discovery — this is a simple query dispatch, not a service
- Do NOT add categories that aren't proven needed yet — only `project_types` for now
- Do NOT modify `create_project` — the warning message is already in place
- Do NOT add database tables or migrations — this reads existing data only
- Do NOT exceed 200 lines in the discovery method — it's a switch/dispatch, keep it lean

## Implementation Plan

### Phase 1: Backend (tool_accessor.py)

1. Add `discovery()` method to `ToolAccessor`
2. Method validates `category` parameter
3. For `"project_types"`: query ProjectType model filtered by `tenant_key`, return abbreviation/label/color
4. Return structured dict with `category`, `items`, `count`, `hint`
5. Raise `ValidationError` for unknown categories (includes valid list in error)

### Phase 2: MCP Registration (mcp_sdk_server.py)

1. Add `@mcp.tool` decorated `gil_discovery` function
2. Thin wrapper: validates category, calls `_call_tool(ctx, "discovery", {"category": category})`
3. Tool description must list valid categories so agents know options without calling first

### Phase 3: Update create_project Description

1. Update `create_project` tool description to reference `gil_discovery`:
   "Call gil_discovery(category='project_types') to see available types before creating."

### Phase 4: Tests

1. Add unit test for `ToolAccessor.discovery()` with valid and invalid categories
2. Test that `project_types` returns expected structure
3. Test that unknown category returns error with valid_categories list
4. Run full test suite — zero regressions

### Phase 5: Gemini Agent Tool List

1. Add `mcp_giljo_mcp_gil_discovery` to the literal tool list in:
   - `template_renderer.py` (Gemini frontmatter tools array)
   - `slash_command_templates.py` (Gemini skill format reference)

## Testing Requirements

- `source venv/bin/activate && export PYTHONPATH=.`
- `python -c "from api.app import create_app; print('OK')"` — startup check
- `python -m pytest tests/unit/ -q --timeout=60 --no-cov` — zero regressions
- `ruff check src/ api/` — zero issues
- Manual: call `gil_discovery(category="project_types")` via MCP and verify response

## Dependencies / Blockers

- None. Reads from existing `ProjectType` model and `list_project_types` query.
- Depends on 0950 being merged (done).

## Success Criteria

- [ ] `gil_discovery(category="project_types")` returns all tenant project types with abbreviation, label, color
- [ ] Unknown category returns helpful error with valid categories list
- [ ] `create_project` description references `gil_discovery`
- [ ] Gemini tool list includes the new tool
- [ ] All existing tests pass (BE + FE)
- [ ] No function exceeds 200 lines
- [ ] `discovery()` method in tool_accessor.py is under 50 lines

## Rollback Plan

Remove the tool registration from `mcp_sdk_server.py` and the method from `tool_accessor.py`. No migrations, no schema changes, no downstream dependencies.
