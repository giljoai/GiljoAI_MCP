# Handover: 0346 - Depth Config Field Standardization

**Date:** 2025-12-13
**Status:** COMPLETE
**Agent:** Claude Opus 4.5 (Claude Code CLI)

---

## Summary

Fixed the vision document depth toggle in Settings → Context which had **no effect** due to four bugs:

1. **Field name mismatch** across layers (frontend/backend/consumer)
2. **MCP tool using frozen config** instead of fetching fresh user settings
3. **ToolAccessor wrapper also using frozen config** (same issue in second code path)
4. **Execution mode read from frozen metadata** instead of Project table (live switching broken)

---

## Bugs Found & Fixed

### Bug 1: Field Name Inconsistency

| Layer | Old Field Name | Fixed To |
|-------|---------------|----------|
| Frontend | `vision_document_depth` | `vision_documents` |
| Backend (Pydantic) | `vision_chunking` | `vision_documents` |
| Consumer (MissionPlanner) | `vision_documents` | *(already correct)* |

### Bug 2: MCP Tool Using Frozen Config

**Location:** `src/giljo_mcp/tools/orchestration.py` (line ~1580)

**Problem:** The `get_orchestrator_instructions` MCP tool was reading `depth_config` from `job_metadata` (frozen at staging time) instead of fetching fresh from the `users` table.

**Fix:** Added logic to fetch fresh user config if `user_id` exists in job_metadata:
```python
if user_id:
    user_config = await _get_user_config(user_id, tenant_key, session)
    field_priorities = user_config["field_priorities"]
    depth_config = user_config["depth_config"]
else:
    # Fall back to frozen job_metadata config
    field_priorities = metadata.get("field_priorities", {})
    depth_config = metadata.get("depth_config", {})
```

### Bug 3: ToolAccessor Wrapper Also Using Frozen Config

**Location:** `src/giljo_mcp/tools/tool_accessor.py` (line ~550)

**Problem:** The `ToolAccessor.get_orchestrator_instructions()` method had the same issue as Bug 2, plus it was NOT passing `depth_config` to `_build_context_with_priorities` at all!

**Fix:** Applied same pattern - fetch fresh user config if `user_id` available, pass `depth_config` to mission planner.

### Bug 4: Execution Mode Read from Frozen Metadata

**Location:** Both `orchestration.py` (line ~1939) and `tool_accessor.py` (line ~665)

**Problem:** `execution_mode` was read from `job_metadata` (frozen at staging time), so toggling between Claude Code CLI and Multi-Terminal modes in the UI had no effect until re-staging.

**Fix:** Read `execution_mode` from `Project.execution_mode` column (live database value):
```python
# Handover 0346: Read from Project table for live switching (not frozen metadata)
execution_mode = getattr(project, 'execution_mode', None) or metadata.get("execution_mode", "multi_terminal")
```

---

## Files Modified

### Backend (7 files)
| File | Change |
|------|--------|
| `api/endpoints/users.py` | `vision_chunking` → `vision_documents` in DepthConfig Pydantic model |
| `src/giljo_mcp/models/auth.py` | Default dict key updated |
| `src/giljo_mcp/services/user_service.py` | 3 locations: defaults + validation |
| `src/giljo_mcp/services/project_service.py` | Default dict key |
| `src/giljo_mcp/thin_prompt_generator.py` | Docstring + default |
| `src/giljo_mcp/tools/orchestration.py` | **MCP tool: fresh user config + execution_mode from Project** |
| `src/giljo_mcp/tools/tool_accessor.py` | **ToolAccessor: fresh user config + depth_config + execution_mode from Project** |

### Frontend (2 files)
| File | Change |
|------|--------|
| `frontend/src/components/settings/ContextPriorityConfig.vue` | Load/save mapping fixed |
| `frontend/src/components/settings/ContextPriorityConfig.vision.spec.js` | Test assertions updated |

### Tests (2 files)
| File | Change |
|------|--------|
| `tests/services/test_depth_config_standardization.py` | **NEW** - 10 tests for field standardization |
| `tests/services/test_user_service.py` | 3 references updated to `vision_documents` |

---

## Commits

| Commit | Description |
|--------|-------------|
| `8a9482af` | test: Add failing tests for depth config field standardization (TDD RED) |
| `f2680bd8` | feat: Standardize vision document depth field to vision_documents |
| `d11d8a2a` | fix: Update existing tests to use vision_documents field name |
| `7e23a3fa` | fix: MCP tool fetches fresh user config instead of frozen job_metadata |
| `21897e35` | fix: Both execution modes now use fresh user config and live project settings |
| `b89b48d7` | docs: Update handover with execution mode fixes |

---

## Test Results

```
tests/services/test_depth_config_standardization.py: 10 passed, 1 skipped
tests/services/test_user_service.py: 41 passed, 1 skipped
Total: 51 passed, 2 skipped, 0 failed
```

---

## Architecture Understanding Gained

### Two Code Paths for get_orchestrator_instructions

There are **TWO separate implementations** that both needed fixing:

| Code Path | File | Purpose |
|-----------|------|---------|
| MCP Tool | `orchestration.py` (line ~1404) | `@mcp.tool()` decorated, called via HTTP |
| ToolAccessor | `tool_accessor.py` (line ~475) | Wrapper class, used internally |

Both now fetch fresh user config and read execution_mode from Project table.

### Prompt Assembly Flow

```
Stage Project (button)
  │
  ├── Creates orchestrator job in DB
  ├── Stores user_id, project_id, tenant_key in job_metadata
  └── Copies THIN PROMPT to clipboard
       └── "Call get_orchestrator_instructions(orch_id, tenant)"

  ❌ Full prompt NOT assembled yet
       │
       ↓
Agent calls MCP tool: get_orchestrator_instructions()
       │
       ├── Fetches FRESH user settings (field_priorities, depth_config)
       ├── Reads execution_mode from Project table (live switching!)
       ├── Loads product, project, vision docs
       ├── Applies Sumy summarization at configured depth
       └── Returns assembled mission prompt

  ✅ Prompt assembled ON-DEMAND with LIVE settings
```

### Vision Document Depth Levels

| Depth | Behavior |
|-------|----------|
| `"full"` | All chunks merged into one prompt section |
| `"heavy"` | Pre-computed `summary_heavy` (~25K tokens) |
| `"moderate"` | Pre-computed `summary_moderate` (~12.5K tokens) |
| `"light"` | Pre-computed `summary_light` (~5K tokens) |
| `"none"` | Vision excluded entirely |

Summaries are pre-computed via Sumy LSA during upload, stored in VisionDocument model.

### Execution Mode Storage

| Location | Purpose |
|----------|---------|
| `Project.execution_mode` column | **Source of truth** (live UI toggle) |
| `job_metadata["execution_mode"]` | Fallback only (legacy support) |

---

## What Now Works

```
┌─────────────────────────────────────────────────────────────────┐
│  BOTH modes (Claude Code CLI + Multi-Terminal):                 │
│                                                                 │
│  ✅ Depth config changes take effect immediately                │
│  ✅ Field priority changes take effect immediately              │
│  ✅ Execution mode toggle works without re-staging              │
│  ✅ No need to re-stage project after settings changes          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Verification Commands

```bash
# Check no legacy field names remain
grep -r "vision_chunking" src/ api/  # Should only show config_manager.py (feature flag)
grep -r "vision_document_depth" frontend/src/  # Should return nothing

# Run tests
pytest tests/services/test_depth_config_standardization.py -v --no-cov
pytest tests/services/test_user_service.py -v --no-cov

# Database check (user's depth_config)
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT depth_config FROM users WHERE tenant_key = 'YOUR_TENANT_KEY';"

# Database check (project's execution_mode)
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT id, name, execution_mode FROM projects WHERE tenant_key = 'YOUR_TENANT_KEY';"
```

---

## Remaining Work

None - handover complete.

---

## Notes for Future Agents

1. **Two get_orchestrator_instructions implementations exist:**
   - `orchestration.py` (MCP tool version, line ~1404) - `@mcp.tool()` decorated
   - `tool_accessor.py` (ToolAccessor wrapper, line ~475) - class method

   **Both** now fetch fresh user config and read execution_mode from Project table.

2. **config_manager.py still has `vision_chunking`** - this is a **feature flag** to enable/disable vision chunking functionality, NOT the depth config field. Do not rename.

3. **Settings changes are now live** - no need to re-stage a project to test different depth levels or execution modes. Just change settings and call the MCP tool again.

4. **CLI mode rules differ slightly** between the two code paths:
   - `tool_accessor.py` has detailed `cli_mode_rules` and `spawning_examples`
   - `orchestration.py` only has `agent_spawning_constraint`
   - Both enforce the same core behavior (agent type matching)

---

## Test Credentials Used

```
Orchestrator ID: 62af6b2f-404c-4332-bfbc-241d645765c1
Project ID: b25ebff8-2316-4ae1-b4f4-1c848e15088c
Tenant Key: ***REMOVED***
User ID: b5f92da5-01b1-4322-a716-1b887876f9ab
Username: patrik
```
