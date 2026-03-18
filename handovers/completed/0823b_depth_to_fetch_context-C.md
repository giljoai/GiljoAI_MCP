# Handover 0823b: Move Depth Config from GOI to fetch_context Runtime

**Date:** 2026-03-18
**From Agent:** Previous Session
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Completed
**Edition Scope:** CE

## Task Summary

Move depth configuration application from GOI build-time (snapshotted at project creation/staging) to fetch_context runtime (DB lookup at call time). Currently, if a user changes depth settings in the UI after a project is created, existing projects keep using stale snapshotted values. This handover makes depth settings live-tunable: change a toggle, and the next fetch_context call respects it immediately.

## Context and Background

**Depends on:** Handover 0823 (committed `6cf62fce`), depth persistence fixes (`f92fee2f`, `f1111d00`, `98a0ec37`)

**Problem confirmed via live testing:** Old project showed 3/25 (stale), new project showed 10/100 (current). The root cause is `_build_ch2_fetch_calls()` in `protocol_builder.py` embedding `depth_config` parameters directly into GOI CH2 fetch call signatures at project creation time.

**Solution approach:**
1. GOI CH2 should only list WHICH categories to fetch (the mandatory list), NOT how much depth
2. fetch_context server-side should read the user's current `depth_config` from the DB at call time

## Technical Details

### Files to Modify

#### 1. `src/giljo_mcp/services/protocol_builder.py`

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
- Update the `_get_user_config()` function if needed (lines 444-547) -- it currently normalizes depth keys, which is still needed for the skip check

#### 2. `src/giljo_mcp/tools/context_tools/fetch_context.py`

**Current behavior:** Accepts optional `depth_config` parameter from the calling agent. If provided, uses those values. If not, uses defaults.

**Target behavior:** When `depth_config` is NOT provided by the agent (which will be the new normal since GOI no longer includes it), fetch_context should:
1. Look up the current user from the request context (user_id + tenant_key are already available)
2. Read the user's `depth_config` from the DB
3. Apply those values

**Key data flow:** `fetch_context.py` -> `tool_accessor.py` -> individual category handlers (get_memory_360, get_git_history, etc.)

**Key mapping:**
- DB column `users.depth_config` uses API keys: `memory_last_n_projects`, `git_commits`, `vision_documents`, `agent_templates`
- Internal keys: `memory_360`, `git_history`, `vision_documents`, `agent_templates`
- Key mapping exists in `_get_user_config()` in protocol_builder.py -- may need to reuse or extract

#### 3. Tests

**Update:** `tests/services/test_protocol_builder_ch2_fetch.py`
- `test_ch2_depth_config_in_memory_360_call`, `test_ch2_depth_config_in_git_history_call`, `test_ch2_depth_config_in_vision_call` -- should now verify depth_config is NOT in the call signatures
- `test_ch2_framing_reflects_memory_depth`, `test_ch2_framing_reflects_git_depth` -- framing text should no longer include specific depth values
- Keep `test_ch2_agent_templates_type_only_skipped` -- this behavior stays

**Add:** Test that fetch_context reads user depth_config from DB when not provided by agent

**Database Changes:** None (uses existing `users.depth_config` JSONB column)

**API Changes:** None (fetch_context tool signature unchanged, `depth_config` param becomes optional fallback)

**Frontend Changes:** None (UI works correctly, no changes needed)

## Implementation Plan

### Phase 1: Write Failing Tests (RED)

1. Update existing CH2 tests to expect NO depth_config in call signatures
2. Update framing text tests to expect generic text (not depth-specific)
3. Add test for fetch_context DB-based depth lookup when no depth_config provided
4. Run tests -- all new/updated tests should FAIL

**Testing criteria:** All updated tests fail (RED), existing passing tests unaffected

### Phase 2: Modify protocol_builder.py (GREEN - part 1)

1. In `_build_ch2_fetch_calls()`, remove depth_param building logic
2. Remove depth_config from call_str format string
3. Simplify framing text to remove depth-specific values
4. Preserve agent_templates skip logic
5. Run CH2 tests -- should now PASS

**Testing criteria:** CH2 tests pass, agent_templates skip test still passes

### Phase 3: Modify fetch_context.py (GREEN - part 2)

1. When `depth_config` is not provided by agent, look up user's depth_config from DB
2. Map API keys to internal keys (extract or reuse key mapping from protocol_builder)
3. Apply DB values as depth_config, fall back to DEFAULT_DEPTH_CONFIG if no user setting
4. Run fetch_context tests -- should now PASS

**Testing criteria:** fetch_context DB lookup test passes, backwards compatibility preserved (agent-provided depth_config still works)

### Phase 4: Verification

1. Run full test suite: `pytest tests/services/test_protocol_builder_ch2_fetch.py tests/services/test_fetch_context_cleanup.py -v`
2. Verify no regressions
3. Linting: `ruff check src/giljo_mcp/services/protocol_builder.py src/giljo_mcp/tools/context_tools/fetch_context.py`

**Recommended Sub-Agent:** tdd-implementor (TDD workflow), with Serena MCP for codebase navigation

## Testing Requirements

### Unit Tests
- CH2 call signatures no longer contain depth_config params
- CH2 framing text uses generic descriptions (not depth-specific numbers)
- agent_templates skip logic still works
- fetch_context reads depth_config from DB when not provided
- fetch_context still accepts agent-provided depth_config (backwards compat)
- Key mapping between API keys and internal keys works correctly

### Manual Testing
1. Change depth settings in UI (memory_360 to 10, git_history to 100)
2. Create a new project -- GOI CH2 should show simple fetch calls WITHOUT depth_config params
3. Run fetch_context on the new project -- should return 10 memories and 100 git commits
4. Change depth settings again (memory_360 to 5) WITHOUT recreating the project
5. Run fetch_context again -- should now return 5 memories (proving runtime lookup works)

## Dependencies and Blockers

**Dependencies:**
- Handover 0823 committed (`6cf62fce`) -- provides the CH2 fetch call framework
- Depth persistence fixes landed (`f92fee2f`, `f1111d00`, `98a0ec37`) -- UI save works correctly

**Known Blockers:** None

## Success Criteria

- GOI CH2 output no longer contains depth_config parameters in fetch call signatures
- fetch_context reads current user depth_config from DB at runtime
- Changing depth settings in UI immediately affects next fetch_context call (no project recreation needed)
- All existing tests pass (no regressions)
- agent_templates skip logic preserved
- Backwards compatible: agent-provided depth_config still honored if passed

## Rollback Plan

Changes are limited to two files (protocol_builder.py, fetch_context.py) plus tests. Rollback via `git revert` of the implementation commit. No schema changes, no migration needed.

## What NOT to Change

- The depth settings UI (ContextPriorityConfig.vue) -- works correctly now
- The depth persistence backend (user_service.py) -- fixed in recent commits
- The field-priority toggle system -- separate concern, works correctly
- The `execution_mode` key in depth_config -- preserved by merge logic, unrelated

## Key Architecture Notes

- `_build_ch2_fetch_calls()` is called from `_build_ch2_startup()` which is called from `_build_orchestrator_protocol()`
- The protocol builder reads user config via `_get_user_config()` which already does the DB lookup and key normalization
- `depth_config` parameter should still be accepted by fetch_context for backwards compatibility (agents may still pass it), but if omitted, the server reads from DB
- The `DEFAULT_DEPTH_CONFIG` in `src/giljo_mcp/config/defaults.py` uses internal keys (`memory_360`, `git_history`)
- The DB column `users.depth_config` uses API keys (`memory_last_n_projects`, `git_commits`)

## Recent Commit History (for context)

```
5118571f docs: Add handover 0823b - Move depth config from GOI to fetch_context runtime
98a0ec37 fix: Export apiClient from api.js and use named import in ContextPriorityConfig
03d47ffb docs: Update license v1.1, contributing guide, and UI assets
f1111d00 fix: Use apiClient instead of bare axios in ContextPriorityConfig
f92fee2f fix: Depth config save now merges instead of overwriting JSONB column
6cf62fce feat: Context fetch protocol injection (Handover 0823)
```

---

## Progress Updates

### 2026-03-18 - Implementation Session
**Status:** Completed
**Work Done:**
- Implemented in commit `c3899cf7`
- GOI CH2 fetch calls no longer embed `depth_config` parameters (removed snapshot-at-creation behavior)
- `fetch_context` now reads user's current `depth_config` from DB at runtime
- Depth settings are live-tunable: changes take effect on next fetch without project recreation
- Framing text uses generic descriptions instead of depth-specific numbers
- Agent templates skip logic preserved
- Backwards compatible: agent-provided depth_config still honored if passed

**Final Notes:**
- Depth config is now fully runtime-resolved, eliminating stale snapshot problem
