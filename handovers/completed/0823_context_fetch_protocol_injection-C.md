# Handover 0823: Context Fetch Protocol Injection

**Date:** 2026-03-16
**From Agent:** Research session (context fetch pipeline analysis)
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 1 day
**Status:** Completed
**Edition Scope:** CE (core orchestration)

---

## Task Summary

Replace the broken `context_fetch_instructions` mechanism with inline protocol injection in CH2. Currently, `get_orchestrator_instructions()` returns a list of fetch instruction dicts that agents treat as optional suggestions and that contain phantom parameters (`limit`) the `fetch_context` tool doesn't accept. The user's depth settings from the DB are effectively ignored at fetch time due to `apply_user_config` being a no-op.

**Why it matters:** MCP server trial proved agents skip 4/7 context categories because instructions read as a menu, not a checklist. Depth params in instructions don't map to the tool schema. The `apply_user_config=True` flag does nothing.

**Expected outcome:** CH2 contains explicit, mandatory, pre-configured fetch calls. Agents cannot skip categories. User depth settings actually control what comes back. No phantom params. No wasted round-trips.

---

## Context and Background

### Trial Findings (2026-03-16)

An orchestrator agent received `context_fetch_instructions` with 7 categories but only fetched 4, judging the rest "non-essential." Investigation revealed:

1. **CH2 Step 2 is toothless** - says "Call: get_orchestrator_instructions()" but never mentions context_fetch_instructions or that fetching all categories is mandatory
2. **Phantom `limit` param** - `_build_fetch_instructions()` generates `params["limit"]` for memory_360 and git_history, but `fetch_context()` doesn't accept a `limit` parameter
3. **`apply_user_config=True` is a no-op** - the flag exists in `fetch_context()` signature and is stored in response metadata, but ZERO code reads user settings from the DB when it's True
4. **Two disagreeing defaults** - `DEFAULT_DEPTHS` in `fetch_context.py` (memory_360=5, git_history=25) vs `DEFAULT_DEPTH_CONFIG` in `defaults.py` (memory_360=3, git_history=5)
5. **Git history returns empty** - `get_git_history()` queries the DB, returns `[]` with no directive when no data exists. Git history lives in the local repo, not the MCP server
6. **`tool_accessor.py` dead default** - `categories or ["all"]` generates an error since 0351 enforced single-category calls

### How 360 Memory Works Today

360 memory is effectively **per-user, per-product** due to tenant isolation design:
- `tenant_key` is generated **per-user** (not per-org): `TenantManager.generate_tenant_key(username)` in `auth_service.py:554`
- `product_memory_entries` filters by `tenant_key + product_id`
- Since each user has their own `tenant_key`, users in the same org CANNOT see each other's product memories
- "Last N product memories" always means the current user's last N project closeouts under that product
- The `last_n_projects` parameter controls how many are returned (default: 5 from `DEFAULT_DEPTHS`, 3 from `DEFAULT_DEPTH_CONFIG`)
- **Future SaaS note:** When multi-user product collaboration is built, the tenant model will need to shift from per-user to per-org (or add a sharing layer). Tracked in `docs/saas/user_collab_criteria.md`

### Depth Resolution Flow (Current - Broken)

```
User sets memory_last_n_projects=3 in UI
  -> _get_user_config() normalizes to depth_config["memory_360"] = 3
  -> _build_fetch_instructions() sets params["limit"] = 3
  -> Agent receives instruction with limit: 3
  -> Agent calls fetch_context(categories=["memory_360"]) -- CANNOT pass limit
  -> fetch_context() uses DEFAULT_DEPTHS["memory_360"] = 5  (hardcoded, ignores user)
  -> _fetch_category() passes last_n_projects=5 to get_360_memory()
  -> Returns 5 memories (not 3 as user configured)
```

### Depth Resolution Flow (Proposed - Fixed)

```
User sets memory_last_n_projects=3 in UI
  -> _get_user_config() normalizes to depth_config["memory_360"] = 3
  -> CH2 protocol text says: fetch_context(..., depth_config={"memory_360": 3})
  -> Agent calls fetch_context(categories=["memory_360"], depth_config={"memory_360": 3})
  -> fetch_context() merges: effective_depths["memory_360"] = 3  (user's value wins)
  -> _fetch_category() passes last_n_projects=3 to get_360_memory()
  -> Returns 3 memories (correct!)
```

---

## Technical Details

### Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `src/giljo_mcp/services/protocol_builder.py` | `_build_ch2_startup()` - accept toggles+depth, generate inline fetch calls | ~587-702 |
| `src/giljo_mcp/mission_planner.py` | `_build_fetch_instructions()` - repurpose as data source for CH2 generation | ~34-167 |
| `src/giljo_mcp/services/orchestration_service.py` | `get_orchestrator_instructions()` - remove `context_fetch_instructions` from response, pass config to protocol builder | ~2377-2620 |
| `src/giljo_mcp/tools/context_tools/fetch_context.py` | Remove `apply_user_config` dead flag, consolidate `DEFAULT_DEPTHS` | ~58-69, ~80, ~207-212 |
| `src/giljo_mcp/tools/context_tools/get_git_history.py` | Return directive when no DB data instead of empty array | ~159-210 |
| `src/giljo_mcp/tools/tool_accessor.py` | Fix dead `categories or ["all"]` default in `fetch_context()` wrapper | ~594-637 |
| `src/giljo_mcp/config/defaults.py` | Consolidate `DEFAULT_DEPTH_CONFIG` as single source of truth | ~58-82 |

### Key Code Sections

**`_build_ch2_startup()` in `protocol_builder.py` (line ~587)**
Currently generates generic Step 2 text:
```
── STEP 2: Fetch Context ───
Call: get_orchestrator_instructions(job_id='{orchestrator_id}')
```
Must become dynamic, injecting actual fetch calls based on user toggles.

**`_build_fetch_instructions()` in `mission_planner.py` (line ~34)**
Currently builds a list of instruction dicts with phantom `limit` params. Must be repurposed to generate CH2-compatible text with `depth_config` format.

**`fetch_context()` in `fetch_context.py` (line ~207)**
```python
effective_depths = DEFAULT_DEPTHS.copy()  # hardcoded defaults
if depth_config:
    effective_depths.update(depth_config)  # agent-passed overrides
# apply_user_config is NEVER used despite being a parameter
```

**`get_git_history()` in `get_git_history.py` (line ~159)**
Queries DB directly. When git integration is disabled or no data exists, returns empty array with no directive.

---

## Implementation Plan

### Phase 1: Consolidate Depth Defaults

**What:** Single source of truth for depth config.

1. In `defaults.py`, ensure `DEFAULT_DEPTH_CONFIG` is the canonical source
2. In `fetch_context.py`, replace `DEFAULT_DEPTHS` with values derived from `DEFAULT_DEPTH_CONFIG` (unwrap the `"depths"` key)
3. Verify `_get_user_config()` in `protocol_builder.py` correctly unwraps the `"depths"` key from `DEFAULT_DEPTH_CONFIG` when used as fallback
4. Ensure the values align (currently disagree: memory_360 is 5 in one, 3 in the other)

**Decision needed:** Which values are correct? `memory_360: 3` or `5`? `git_history: 5` or `25`? Recommend using `DEFAULT_DEPTH_CONFIG` values since those match what the UI sets as defaults.

**Tests:**
- Unit test: `DEFAULT_DEPTHS` values match `DEFAULT_DEPTH_CONFIG["depths"]`
- Unit test: `fetch_context()` with no `depth_config` uses canonical defaults

### Phase 2: CH2 Protocol Injection

**What:** `_build_ch2_startup()` generates inline, mandatory fetch instructions.

1. Add parameters to `_build_ch2_startup()`: `field_toggles: dict`, `depth_config: dict`, `product_id: str`, `tenant_key: str`
2. For each category where `field_toggles[category] == True` (and not inlined like `project_description`), generate an inline fetch call:

```
── STEP 2: Fetch Context ──────────────────────────
You MUST call fetch_context() for EVERY category below.
These are configured by the user and are NOT optional.
Do NOT skip any.

1. fetch_context(categories=["product_core"], product_id="<uuid>", tenant_key="<key>")
   -> Product name, description, and core features.

2. fetch_context(categories=["tech_stack"], product_id="<uuid>", tenant_key="<key>")
   -> Programming languages, frameworks, and databases.

3. fetch_context(categories=["memory_360"], product_id="<uuid>", tenant_key="<key>",
                 depth_config={"memory_360": 3})
   -> Last 3 product project closeouts (cumulative knowledge).

4. fetch_context(categories=["vision_documents"], product_id="<uuid>", tenant_key="<key>",
                 depth_config={"vision_documents": "medium"})
   -> 66% summarized vision document (single response).

5. fetch_context(categories=["git_history"], product_id="<uuid>", tenant_key="<key>",
                 depth_config={"git_history": 25})
   -> Last 25 recent git commits.
```

3. Categories toggled OFF in user settings do NOT appear in the list
4. Depth-aware categories include `depth_config={}` in the call signature; non-depth categories omit it
5. Framing text includes depth-specific phrasing (e.g., "Last 3" not just "Historical project outcomes")
6. Reuse logic from `_build_fetch_instructions()` for category configs, framing text, and depth mapping

**Keep the CRITICAL context variables block** that currently exists in Step 2 (project_path, product_name, tenant_key reminders).

**Tests:**
- Unit test: CH2 output contains exactly N fetch calls matching enabled toggles
- Unit test: disabled toggle category does NOT appear in CH2
- Unit test: depth_config values in CH2 text match user's depth_config
- Unit test: framing text reflects depth (e.g., "Last 3" when memory_360=3)

### Phase 3: Remove `context_fetch_instructions` from Response

**What:** Clean up the response from `get_orchestrator_instructions()`.

1. In `orchestration_service.py`, remove `context_fetch_instructions` key from the response dict
2. Pass `field_toggles`, `depth_config`, `product_id`, `tenant_key` through to `_build_orchestrator_protocol()` and down to `_build_ch2_startup()`
3. The `_build_fetch_instructions()` method in `mission_planner.py` can either:
   - Be deleted entirely (if CH2 builder reimplements the logic)
   - Be refactored to return data that CH2 builder formats into text (recommended - keeps category configs in one place)

**Tests:**
- Unit test: response dict does NOT contain `context_fetch_instructions` key
- Unit test: response still contains `orchestrator_protocol.ch2_startup_sequence` with fetch calls
- Integration test: full `get_orchestrator_instructions()` returns valid protocol with inline fetches

### Phase 4: Fix `fetch_context` Dead Code

**What:** Clean up `fetch_context.py` and `tool_accessor.py`.

1. Remove `apply_user_config` parameter from `fetch_context()` signature (it's a no-op)
2. Remove `apply_user_config` from response metadata
3. Update `tool_accessor.py`: remove `categories or ["all"]` default (change to `categories` pass-through; let `fetch_context` handle None with its existing error response)
4. Remove `apply_user_config` from `tool_accessor.py` wrapper signature

**Tests:**
- Unit test: `fetch_context()` no longer accepts `apply_user_config`
- Unit test: `tool_accessor.fetch_context(categories=None)` returns SINGLE_CATEGORY_REQUIRED error

### Phase 5: Git History Directive

**What:** When git data is not in the DB, return a directive instead of empty array.

1. In `get_git_history()`, when git integration is disabled OR no commits in DB, return:
```python
{
    "source": "git_history",
    "depth": commits,
    "data": [],
    "directive": {
        "action": "fetch_from_local_repo",
        "command": f"git log --oneline -{commits}",
        "project_path": project_path,  # from product or project context
        "note": "Git history is not stored on the server. Run this command in the project directory."
    },
    "metadata": { ... }
}
```
2. The `project_path` should come from the Product's associated project or from the orchestrator context. If not available, omit the path and let the agent use the project_path from their context variables.

**Tests:**
- Unit test: empty DB returns directive with command string
- Unit test: directive includes correct commit count from depth parameter
- Unit test: populated DB still returns data normally (no directive)

---

## Testing Requirements

### Unit Tests (pytest)
- `tests/services/test_protocol_builder_ch2.py` - CH2 inline fetch generation
- `tests/tools/test_fetch_context.py` - depth resolution, no apply_user_config
- `tests/tools/test_get_git_history.py` - directive return path

### Integration Tests
- `tests/services/test_orchestration_service_protocol.py` - full response structure
- Verify response no longer contains `context_fetch_instructions`
- Verify CH2 text contains correct fetch calls for given toggles

### Manual Testing
1. Call `get_orchestrator_instructions()` with various toggle configs
2. Verify CH2 Step 2 only lists enabled categories
3. Verify depth values in CH2 match user's `depth_config`
4. Call `fetch_context(categories=["memory_360"], depth_config={"memory_360": 3})` and verify 3 entries returned
5. Call `fetch_context(categories=["git_history"])` with empty DB and verify directive returned

---

## Dependencies and Blockers

**Dependencies:** None - all changes are to existing code, no new tables or migrations.

**Blockers:** None identified.

**Decision needed from user:**
- Default depth values: `memory_360` should be 3 (from `DEFAULT_DEPTH_CONFIG`) or 5 (from `DEFAULT_DEPTHS`)? Recommend 3.
- Default depth values: `git_history` should be 5 (from `DEFAULT_DEPTH_CONFIG`) or 25 (from `DEFAULT_DEPTHS`)? Recommend 25.

---

## Success Criteria

1. CH2 protocol text contains explicit, numbered fetch calls for all user-enabled categories
2. Disabled categories do NOT appear in CH2
3. `depth_config` values in CH2 match user's actual DB settings
4. `fetch_context()` with passed `depth_config` returns correct depth of data
5. No phantom `limit` params anywhere in the pipeline
6. `apply_user_config` flag removed (dead code cleanup)
7. `DEFAULT_DEPTHS` consolidated with `DEFAULT_DEPTH_CONFIG` (single source of truth)
8. Git history returns directive when no DB data
9. `context_fetch_instructions` removed from response
10. All existing tests pass; new tests cover inline protocol generation

---

## Rollback Plan

All changes are to existing Python code with no DB migrations. Rollback is a simple `git revert` of the commit(s). The `context_fetch_instructions` mechanism can be restored from git history if needed.

---

## Recommended Sub-Agent

**Primary:** `tdd-implementor` - TDD approach for protocol builder changes and fetch_context fixes
**Support:** `backend-tester` - integration tests for orchestration service response

---

## Additional Notes

### 360 Memory Clarification
360 memory returns the last N project closeouts under a **product**, NOT user activity logs. However, because `tenant_key` is per-user (generated from username in `auth_service.py:554`), each user's 360 memory is fully isolated — even users in the same organization cannot see each other's product memories today. "Last 5 product memories" means the current user's last 5 project closeouts under that product. When SaaS multi-user collaboration is built, this isolation model will need to evolve. See `docs/saas/user_collab_criteria.md`.

### Token Impact
- Removing `context_fetch_instructions` from response saves ~200-400 tokens
- Adding inline fetch calls to CH2 adds ~150-300 tokens (depends on number of enabled categories)
- Net impact: roughly neutral, but the tokens are now in the right place (mandatory protocol vs optional reference)

### Related Handovers
- 0351: Single-category enforcement in `fetch_context` (code-level)
- 0350 series: On-demand context fetch architecture
- 0390 series: 360 memory normalization (JSONB to table)
- 0820: Remove context priority framing

---

## Progress Updates

### 2026-03-16 - Implementation Session
**Status:** Completed
**Work Done:**
- All 5 phases implemented in commit `6cf62fce`
- CH2 inline fetch calls replace broken `context_fetch_instructions` mechanism
- `context_fetch_instructions` removed from GOI response
- `apply_user_config` dead flag removed from `fetch_context()`
- `DEFAULT_DEPTHS` consolidated with `DEFAULT_DEPTH_CONFIG`
- Dead `categories or ["all"]` default fixed in `tool_accessor.py`
- Git history directive added for empty DB case

**Final Notes:**
- Follow-up 0823b created for moving depth config from GOI snapshot to runtime DB lookup
