# Handover 0823b: Move Depth Config from GOI to fetch_context Runtime

**Edition Scope:** CE
**Status:** Ready to implement
**Depends on:** Handover 0823 (committed `6cf62fce`), depth persistence fixes (`f92fee2f`, `f1111d00`, `98a0ec37`)

## Problem Statement

Currently, `_build_ch2_fetch_calls()` in `protocol_builder.py` embeds `depth_config` parameters directly into the GOI CH2 fetch call signatures. These values are **snapshotted at GOI build time** (project creation/staging). If the user later changes their depth settings in the UI (e.g., memory_360 from 3 to 10), existing projects keep using the stale snapshotted values. Only newly created projects pick up the updated settings.

This was confirmed via live testing: old project showed 3/25 (stale), new project showed 10/100 (current).

## Solution

Move depth application from GOI (build-time snapshot) to fetch_context (runtime lookup):

1. **GOI CH2** should only list WHICH categories to fetch (the mandatory list), NOT how much depth
2. **fetch_context server-side** should read the user's current `depth_config` from the DB at call time

This gives users live tuning — change a toggle, and the next fetch_context call respects it immediately.

## Files to Modify

### 1. `src/giljo_mcp/services/protocol_builder.py`

**Function:** `_build_ch2_fetch_calls()` (lines 586-708)

**Current behavior:** Generates numbered fetch calls WITH depth_config params:
```
1. fetch_context(categories=["memory_360"], product_id="...", tenant_key="...",
                 depth_config={"memory_360": 10})
   -> Last 10 product project closeouts (cumulative knowledge).
```

**Target behavior:** Generate simpler calls WITHOUT depth_config params:
```
1. fetch_context(categories=["memory_360"], product_id="...", tenant_key="...")
   -> Recent product project closeouts (cumulative knowledge).
```

**Specific changes:**
- Remove the `depth_param` building logic (lines ~677-682) that creates the `depth_config={...}` parameter string
- Remove `depth_config` from the `call_str` format string (line ~685)
- Simplify framing text to remove depth-specific values (e.g., "Last {depth} project closeouts" becomes "Recent product project closeouts")
- Keep the `agent_templates` skip logic: if `depth_config.get("agent_templates") == "type_only"`, still skip generating that fetch call (this is a "skip entirely" decision, not a depth parameter)
- The function signature still needs `depth_config` parameter for the agent_templates skip check
- Update the `_get_user_config()` function if needed (lines 444-547) — it currently normalizes depth keys, which is still needed for the skip check

### 2. `src/giljo_mcp/tools/context_tools/fetch_context.py`

**Current behavior:** The fetch_context MCP tool accepts optional `depth_config` parameter from the calling agent. If provided, uses those values. If not, uses defaults.

**Target behavior:** When `depth_config` is NOT provided by the agent (which will be the new normal since GOI no longer includes it), fetch_context should:
1. Look up the current user from the request context (user_id + tenant_key are already available)
2. Read the user's `depth_config` from the DB
3. Apply those values

Check how `depth_config` flows through the tool:
- `fetch_context.py` → `tool_accessor.py` → individual category handlers (get_memory_360, get_git_history, etc.)
- The user's depth_config is stored in the `users.depth_config` JSONB column
- Keys in DB: `memory_last_n_projects`, `git_commits`, `vision_documents`, `agent_templates`
- Keys used internally: `memory_360`, `git_history`, `vision_documents`, `agent_templates`
- Key mapping exists in `_get_user_config()` in protocol_builder.py — may need to reuse or extract

### 3. Tests

**Update:** `tests/services/test_protocol_builder_ch2_fetch.py`
- Tests that verify depth_config appears in CH2 calls need updating
- `test_ch2_depth_config_in_memory_360_call`, `test_ch2_depth_config_in_git_history_call`, `test_ch2_depth_config_in_vision_call` — these should now verify depth_config is NOT in the call signatures
- `test_ch2_framing_reflects_memory_depth`, `test_ch2_framing_reflects_git_depth` — framing text should no longer include specific depth values
- Keep `test_ch2_agent_templates_type_only_skipped` — this behavior stays

**Add:** Test that fetch_context reads user depth_config from DB when not provided by agent

## Key Architecture Notes

- `_build_ch2_fetch_calls()` is called from `_build_ch2_startup()` which is called from `_build_orchestrator_protocol()`
- The protocol builder reads user config via `_get_user_config()` which already does the DB lookup and key normalization
- `depth_config` parameter should still be accepted by fetch_context for backwards compatibility (agents may still pass it), but if omitted, the server reads from DB
- The `DEFAULT_DEPTH_CONFIG` in `src/giljo_mcp/config/defaults.py` uses internal keys (`memory_360`, `git_history`)
- The DB column `users.depth_config` uses API keys (`memory_last_n_projects`, `git_commits`)

## What NOT to Change

- The depth settings UI (ContextPriorityConfig.vue) — works correctly now
- The depth persistence backend (user_service.py) — fixed in recent commits
- The field-priority toggle system — separate concern, works correctly
- The `execution_mode` key in depth_config — preserved by merge logic, unrelated

## Verification

1. Change depth settings in UI (memory_360 to 10, git_history to 100)
2. Create a new project — GOI CH2 should show simple fetch calls WITHOUT depth_config params
3. Run fetch_context on the new project — should return 10 memories and 100 git commits (read from user's current DB settings)
4. Change depth settings again (memory_360 to 5) WITHOUT recreating the project
5. Run fetch_context again — should now return 5 memories (proving runtime lookup works)
6. Run existing tests: `pytest tests/services/test_protocol_builder_ch2_fetch.py tests/services/test_fetch_context_cleanup.py -v`

## Recent Commit History (for context)

```
98a0ec37 fix: Export apiClient from api.js and use named import in ContextPriorityConfig
03d47ffb docs: Update license v1.1, contributing guide, and UI assets
f1111d00 fix: Use apiClient instead of bare axios in ContextPriorityConfig
f92fee2f fix: Depth config save now merges instead of overwriting JSONB column
6cf62fce feat: Context fetch protocol injection (Handover 0823)
```
