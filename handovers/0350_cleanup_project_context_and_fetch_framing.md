# Handover 0350 Cleanup: Project Context Pointer & Framing Verification

**Date**: 2025-12-15  
**Status**: Completed  
**Series**: 0350 (Context Management On-Demand Architecture)  

## Objective

Tighten the 0350-series implementation by:
- Surfacing the developer’s **project path** in orchestrator framing so agents know where the local codebase lives.
- Verifying that `get_orchestrator_instructions` framing and the unified `fetch_context` tool are wired correctly end-to-end.
- Confirming frontend Context Priority UI alignment with backend priorities and categories.

## Changes Implemented

### 1) Inline Project Path in Orchestrator Framing

**File**: `src/giljo_mcp/tools/tool_accessor.py`  
**Method**: `ToolAccessor.get_orchestrator_instructions(...)`

- After loading the `Product` for the project’s `product_id`, the code now resolves the project path:
  - `project_path = product.project_path` (or `None` if not set).
- `project_path` is included in the always-inline project context block:

  ```json
  "project_description_inline": {
    "description": "...",
    "mission": "...",
    "project_path": "F:\\TinyContacts"  // example
  }
  ```

- Semantics:
  - This path is a **pointer to the developer’s local folder**, not a server filesystem path.
  - It is treated as opaque data: the MCP server simply passes through whatever the product record stores.
  - Agents can now reliably know where the product lives on the developer PC without an extra fetch.

### 2) Framing + fetch_context Wiring (Validation)

- Confirmed that `get_orchestrator_instructions` now returns:
  - `identity` (orchestrator_id, project_id, tenant_key, instance_number).
  - `project_description_inline` (description, mission, project_path).
  - `context_fetch_instructions` – built by `MissionPlanner._build_fetch_instructions(...)`:
    - Each instruction uses `tool: "fetch_context"` and a `category` matching the unified dispatcher:
      - `product_core`, `vision_documents`, `tech_stack`, `architecture`,
        `testing`, `memory_360`, `git_history`, `agent_templates`.
    - Depth-aware fields (`vision_documents`, `memory_360`, `git_history`, `agent_templates`) have
      `limit` / `depth` params derived from `depth_config`.
  - `mcp_tools_available` includes `"fetch_context"` so thin-client prompts can rely on a single context entrypoint.

- Verified unified dispatcher:
  - **File**: `src/giljo_mcp/tools/context_tools/fetch_context.py`
  - Categories map to internal tools:
    - `"product_core"` → `get_product_context`
    - `"vision_documents"` → `get_vision_document`
    - `"tech_stack"` → `get_tech_stack`
    - `"architecture"` → `get_architecture`
    - `"testing"` → `get_testing`
    - `"memory_360"` → `get_360_memory`
    - `"git_history"` → `get_git_history`
    - `"agent_templates"` → `get_agent_templates`
    - `"project"` → `get_project`
  - `fetch_context` is exposed via MCP HTTP in `api/endpoints/mcp_http.py` and wrapped in `ToolAccessor.fetch_context(...)`.

### 3) Context Priority UI Alignment (Verification)

- **File**: `frontend/src/components/settings/ContextPriorityConfig.vue`
- Verified:
  - Locked row now reads **“Project Description”** with a CRITICAL (Locked) chip.
  - Priority selector uses descriptive 3-tier labels plus OFF:
    - 1 → CRITICAL – “Orchestrator MUST call this MCP tool”.
    - 2 → IMPORTANT – “Orchestrator SHOULD call if budget allows”.
    - 3 → REFERENCE – “Orchestrator MAY call if project scope requires”.
    - 4 → OFF – “Tool not mentioned in orchestrator instructions”.
  - UI ↔ backend category mapping:
    - `product_description` ⇔ `product_core`
    - `tech_stack` ⇔ `tech_stack`
    - `architecture` ⇔ `architecture`
    - `testing` ⇔ `testing`
    - `vision_documents` ⇔ `vision_documents`
    - `memory_360` ⇔ `memory_360`
    - `git_history` ⇔ `git_history`
    - `agent_templates` ⇔ `agent_templates`
  - Depth controls in the UI (vision depth, 360 memory count, git commit count, agent template depth) are consistent with
    the categories and parameters used by `fetch_context` and `_build_fetch_instructions`.

### 4) Tests Run

- **Command**:

  ```bash
  pytest tests/tools/test_fetch_context.py tests/integration/test_orchestrator_framing_response.py -q
  ```

- Results:
  - All targeted tests pass (fetch_context and framing response).
  - Global coverage gate (`fail-under=80%`) still fails due to overall project coverage, not due to 0350 changes.
  - No test regressions were introduced by the project_path addition.

## Known Limitations / Deferred Work

- `fetch_context` still uses `DEFAULT_DEPTHS` plus explicit `depth_config` parameters.
  - `_load_user_depth_config()` remains a stub; orchestrators should rely on the **depth params** baked into
    `context_fetch_instructions` when calling `fetch_context()`.
  - Future work (separate handover) can map `User.depth_config` into the category-specific depth values if
    we decide to make `apply_user_config=True` fully automatic.
- Legacy `_build_context_with_priorities()` remains for backward compatibility and uses its own default
  field priorities; the framing path (recommended for new clients) uses `DEFAULT_FIELD_PRIORITY` and
  `fetch_context`.

## Summary

- Project path is now part of the always-inline project context, giving agents a clear pointer to the local codebase folder.
- Framing-based `get_orchestrator_instructions` and unified `fetch_context` are wired coherently and tested.
- The Context Priority UI is aligned with backend category names and tier semantics, closing the main 0350-series gaps without changing public MCP tool contracts.

