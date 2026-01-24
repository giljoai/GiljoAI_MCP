# Handover 0461a: Remove 90% Auto-Succession Dead Code

**Series**: Handover Simplification Series (0461)
**Color**: Green (#4CAF50)
**Estimated Effort**: 3-4 hours
**Subagent**: `tdd-implementor`
**Dependencies**: None (can start immediately)

---

## Mission Statement

Remove dead code and misleading documentation that claims "automatic succession at 90% context threshold". This feature is **architecturally impossible** because:

1. MCP server is passive (HTTP request/response only)
2. Server cannot push to agents
3. Agents cannot introspect their own token count

The 90% threshold code exists but is NEVER called. This handover removes it.

---

## Background

### Why This Code Is Dead

The MCP architecture is fundamentally request/response:
- Agent calls MCP tool → Server responds
- Server **cannot** initiate calls to agents
- Server has no way to "watch" an agent's context and trigger succession

The `should_trigger_succession()` method in `orchestrator_succession.py` has **ZERO callers**. It was written with the assumption that something would poll it, but nothing does.

### Impact

- ~200 lines of dead code in `orchestrator_succession.py`
- 40+ documentation files with false claims
- Frontend tests checking for non-existent behavior
- User confusion about "automatic" vs "manual" succession

---

## Tasks

### Task 1: Delete Dead Code from `orchestrator_succession.py`

**File**: `src/giljo_mcp/orchestrator_succession.py`

Delete the following:

1. **Lines 46-66**: `calculate_context_usage()` function
   - This helper is only used by `should_trigger_succession()` which is dead

2. **Lines 101-102**: `CONTEXT_THRESHOLD = 0.90` constant
   - Never used in any active code path

3. **Lines 118-158**: `should_trigger_succession()` method
   - ZERO references anywhere in codebase
   - Was designed to be polled but nothing polls it

4. **Update docstring (lines 7-17)**: Remove misleading claims
   - Change "Context threshold detection (90% trigger point)" to "Manual succession support"
   - Remove "- context_limit: Context usage >= 90% of budget" from valid reasons

**After deletion**, the file should only contain:
- `OrchestratorSuccessionManager` class with:
  - `__init__()`
  - `create_successor()` (still needed for manual succession)
  - `generate_handover_summary()` (still needed)
  - `complete_handover()` (still needed)
  - Private helper methods (`_estimate_project_status`, etc.)

### Task 2: Fix Misleading Code Comments

**File**: `src/giljo_mcp/tools/orchestration.py`

Lines 914-926 in `_build_orchestrator_protocol()` contain:
```python
Succession Trigger: 90% ({int(context_budget * 0.9)} tokens)

If approaching 90%:
  - System auto-triggers succession (creates successor orchestrator)
```

**Change to**:
```python
Manual Succession: Available via /gil_handover command or UI "Hand Over" button

When context is high:
  - User can manually trigger succession
  - Orchestrator generates handover summary
  - Successor retrieves condensed context
```

---

**File**: `api/endpoints/agent_jobs/succession.py`

1. **Line 11**: Change module docstring from:
   ```
   - Auto-succession at 90% context threshold (from OrchestrationService)
   ```
   To:
   ```
   - Manual succession via UI or slash command
   ```

2. **Lines 267-268**: Change docstring from:
   ```
   Succession is recommended at >= 90% context usage.
   ```
   To:
   ```
   Returns context usage metrics for user decision on manual succession.
   ```

3. **Line 325**: Change comment from:
   ```
   # Recommend succession at >= 90% threshold
   ```
   To:
   ```
   # Calculate whether succession would be advisable based on context usage
   ```

---

**File**: `src/giljo_mcp/models/schemas.py`

Search for any 90% threshold mentions in schema docstrings and update.

### Task 3: Update CLAUDE.md (Highest Visibility)

**File**: `CLAUDE.md`

1. **Line 74**: Change:
   ```
   - Orchestrator succession with context tracking (90% auto-trigger)
   ```
   To:
   ```
   - Orchestrator succession with context tracking (manual trigger)
   ```

2. **Lines 332-333**: Change:
   ```
   - Automatic succession trigger at 90% capacity (configurable)
   ```
   To:
   ```
   - Manual succession via `/gil_handover` slash command or UI "Hand Over" button
   ```

### Task 4: Update Active Documentation

Update the following **active** documentation files (not archived):

1. **`docs/ORCHESTRATOR.md`** - Multiple references:
   - Line 14: "Automatic Succession: Spawns successor at 90% context capacity" → "Manual Succession: User-triggered via UI or slash command"
   - Line 64: Remove "Context tracking (90% → auto succession)"
   - Lines 880, 945-948: Remove auto-succession sections
   - Lines 1153, 1234, 1330: Remove or update test examples

2. **`docs/SERVICES.md`** - Lines 235-238:
   - Remove "Auto-Succession Flow" section or rename to "Manual Succession Flow"

3. **`docs/user_guides/agent_monitoring_guide.md`** - Lines 68-88:
   - Update succession trigger scenarios to be manual-only

4. **`docs/README_FIRST.md`** - Lines 700-702:
   - Change "Automatic succession at 90% context usage" to "Manual succession when context is high"

5. **`docs/user_guides/orchestrator_succession_guide.md`**:
   - Line 69: Update threshold descriptions
   - Lines 294, 333, 338, 413: Update FAQ answers about automatic succession

6. **`docs/guides/succession_quick_ref.md`** - Lines 16, 208:
   - Update to reflect manual-only succession

7. **`docs/guides/orchestrator_succession_developer_guide.md`**:
   - Lines 34, 803, 968: Update code examples and test scenarios

8. **`docs/guides/devpanel_flow_inventory.md`** - Line 24:
   - Remove "automatic 90% context succession"

### Task 5: Fix/Remove Outdated Frontend Tests

Search for tests that verify 90% auto-succession behavior:

```bash
grep -r "90.*succession\|auto.*succession" tests/ frontend/
```

Expected files to review:
- `tests/integration/SUCCESSION_TEST_REPORT.md` - Line 83
- Any test files with `test_auto_succession` functions

**Action**: Either remove these tests or update them to test manual succession only.

---

## Verification

After completing all tasks:

1. **Code search** - Verify no active 90% auto-succession references:
   ```bash
   grep -r "auto.*succession\|automatic.*succession" src/ api/
   grep -r "CONTEXT_THRESHOLD\|should_trigger_succession" src/
   ```
   Should return nothing (or only historical/archived references).

2. **Tests pass**:
   ```bash
   pytest tests/ -v
   ```

3. **Linting**:
   ```bash
   ruff src/ api/
   black src/ api/ --check
   ```

---

## Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/giljo_mcp/orchestrator_succession.py` | Delete dead code | ~80 lines removed |
| `src/giljo_mcp/tools/orchestration.py` | Fix comments | ~15 lines |
| `api/endpoints/agent_jobs/succession.py` | Fix comments | ~10 lines |
| `CLAUDE.md` | Update claims | ~5 lines |
| `docs/ORCHESTRATOR.md` | Major update | ~50 lines |
| `docs/SERVICES.md` | Update section | ~10 lines |
| `docs/README_FIRST.md` | Update text | ~5 lines |
| `docs/user_guides/*.md` | Update guides | ~30 lines |
| `docs/guides/*.md` | Update guides | ~20 lines |
| Tests | Remove/update | ~20 lines |

**Total**: ~25 files, ~250 lines changed (mostly deletions)

---

## Success Criteria

- [ ] `calculate_context_usage()` function deleted
- [ ] `CONTEXT_THRESHOLD = 0.90` constant deleted
- [ ] `should_trigger_succession()` method deleted
- [ ] No code references to "auto succession" in `src/` or `api/`
- [ ] CLAUDE.md updated with "manual" succession
- [ ] All documentation reflects manual-only succession
- [ ] All tests pass
- [ ] Linting passes

---

## Rollback

This is a safe deletion of dead code. If any issues:
```bash
git checkout HEAD -- src/giljo_mcp/orchestrator_succession.py
```

---

## Next Handover

After 0461a completes, proceed to **0461b: Database Schema Cleanup**.
