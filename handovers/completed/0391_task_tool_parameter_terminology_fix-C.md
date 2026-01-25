# Handover: Task Tool Parameter Terminology Fix

**Date:** 2026-01-25
**From Agent:** Investigation via Claude Opus 4.5
**Executed By:** tdd-implementor subagent
**Priority:** Medium
**Estimated Complexity:** 2-3 hours (E1)
**Status:** ✅ COMPLETE

---

## Completion Summary (2026-01-25)

### What Was Done
- Replaced all 27 occurrences of `subagent_display_name` with `subagent_type`
- Modified 8 files (2 source, 6 test)
- Zero occurrences of old terminology remain

### Files Modified
| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/orchestration.py` | 4 |
| `src/giljo_mcp/thin_prompt_generator.py` | 5 |
| `tests/api/test_prompts_execution_mode.py` | 1 |
| `tests/e2e/test_claude_code_mode_workflow.py` | 1 |
| `tests/services/test_orchestration_service_cli_rules.py` | 2 |
| `tests/tools/test_spawn_agent_job_clarity.py` | 5 |
| `tests/unit/test_thin_prompt_cli_validation.py` | 1 |
| `tests/unit/test_thin_prompt_generator_agent_name_truth.py` | 8 |

### Verification
```bash
grep -rn "subagent_display_name" src/ tests/ --include="*.py"
# Result: 0 matches ✅
```

### MCP Enhancement List Updated
- Item #8 status changed from "PARTIALLY RESOLVED" to "FULLY RESOLVED"
- Progress restored to 18/35 (51%)

---

## Task Summary

Fix terminology mismatch between GiljoAI MCP documentation and Claude Code's actual Task tool parameter. The documentation uses `subagent_display_name` but the real parameter is `subagent_type`.

**Why it matters:** Agents reading the protocol are confused when they try to use `Task(subagent_display_name=...)` and discover the actual parameter is `subagent_type`. This causes 30+ seconds of confusion per agent spawn.

**Expected outcome:** All documentation and code references use `subagent_type` consistently.

---

## Context and Background

### Source of Issue

Item #8 in `F:\TinyContacts\MCP_ENHANCEMENT_LIST.md` was marked as "RESOLVED" but agent testing revealed:

> "The CH3 chapter exists, but there's still terminology mismatch:
> - Implementation prompt says: Task(subagent_display_name="{agent_name}"...)
> - Actual tool parameter: subagent_type
> The content is documented, but the naming is inconsistent across docs."

### Claude Code Task Tool Definition

From the system prompt, the actual Task tool parameter is:
```
"subagent_type": {"description": "The type of specialized agent to use for this task", "type": "string"}
```

**NOT** `subagent_display_name` - this parameter does not exist.

### Historical Note

This appears to have originated from confusion between:
- `agent_display_name` - GiljoAI's spawn_agent_job parameter (display name for UI)
- `subagent_type` - Claude Code Task tool's actual parameter

Someone combined these into `subagent_display_name` which doesn't exist in either system.

---

## Technical Details

### Files to Modify

#### 1. `src/giljo_mcp/tools/orchestration.py`

**Line 687:**
```python
# BEFORE:
Task(subagent_display_name='{agent_name}', instructions='...')

# AFTER:
Task(subagent_type='{agent_name}', instructions='...')
```

**Line 696:**
```python
# BEFORE:
Task(subagent_display_name='tdd-implementor', ...)  # agent_name!

# AFTER:
Task(subagent_type='tdd-implementor', ...)  # agent_name from template!
```

**Line 731:**
```python
# BEFORE:
Task(subagent_display_name=X) where X = agent_name (NOT display_name)

# AFTER:
Task(subagent_type=X) where X = agent_name from spawn_agent_job
```

**Line 1718:**
```python
# BEFORE:
"task_tool_usage": f"Task(subagent_display_name='{agent_name}', ...)",

# AFTER:
"task_tool_usage": f"Task(subagent_type='{agent_name}', ...)",
```

#### 2. `src/giljo_mcp/thin_prompt_generator.py`

**Line 1339:**
```python
# BEFORE:
'    subagent_display_name="{agent_name}",  # CRITICAL: Use agent_name (template filename)',

# AFTER:
'    subagent_type="{agent_name}",  # CRITICAL: Use agent_name (template filename)',
```

**Line 1362:**
```python
# BEFORE:
f'    subagent_display_name="{first.agent_name}",',

# AFTER:
f'    subagent_type="{first.agent_name}",',
```

**Line 1445:**
```python
# BEFORE:
"- Task tool parameter `subagent_display_name` expects `agent_name`, NOT `agent_display_name`",

# AFTER:
"- Task tool parameter `subagent_type` expects `agent_name` (template filename), NOT `agent_display_name`",
```

#### 3. Test Files to Update

| File | Search Pattern |
|------|----------------|
| `tests/e2e/test_claude_code_mode_workflow.py` | Line 127 |
| `tests/api/test_prompts_execution_mode.py` | Line 275 |
| `tests/unit/test_thin_prompt_generator_agent_name_truth.py` | Lines 156, 164, 173, 174, 177, 185, 194, 195 |
| `tests/unit/test_thin_prompt_cli_validation.py` | Line 111 |
| `tests/services/test_orchestration_service_cli_rules.py` | Lines 347, 353 |
| `tests/tools/test_spawn_agent_job_clarity.py` | Lines 65, 182, 249-251 |

### Search Command

```bash
grep -rn "subagent_display_name" src/ tests/
```

This will find all occurrences that need updating.

---

## Implementation Plan

### Phase 1: Code Changes (1 hour)

1. Update `orchestration.py` (4 locations)
2. Update `thin_prompt_generator.py` (3 locations)
3. Run existing tests to see which fail

### Phase 2: Test Updates (1 hour)

1. Update all test files that reference `subagent_display_name`
2. Ensure tests still validate the correct behavior
3. Run full test suite: `pytest tests/ -v`

### Phase 3: Documentation (30 minutes)

1. Update `F:\TinyContacts\MCP_ENHANCEMENT_LIST.md` item #8 status
2. Mark this item as truly RESOLVED with git commit reference
3. Add note about the terminology correction

**Recommended Sub-Agent:** tdd-implementor (for test-driven approach)

---

## Testing Requirements

### Unit Tests
- All existing tests in `tests/unit/test_thin_prompt_*.py` must pass
- All existing tests in `tests/tools/test_spawn_agent_job_clarity.py` must pass

### Integration Tests
- Verify `get_orchestrator_instructions()` returns correct `subagent_type` syntax
- Verify `spawn_agent_job()` returns correct `task_tool_usage` field

### Manual Testing
1. Start MCP server
2. Call `get_orchestrator_instructions()` via HTTP
3. Verify CH3 (AGENT SPAWNING RULES) mentions `subagent_type`, not `subagent_display_name`
4. Call `spawn_agent_job()` for any agent
5. Verify `task_tool_usage` response field shows `Task(subagent_type=...)`

---

## Success Criteria

- [ ] Zero occurrences of `subagent_display_name` in `src/` directory
- [ ] All test assertions updated to use `subagent_type`
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Manual verification of MCP responses shows correct terminology
- [ ] `MCP_ENHANCEMENT_LIST.md` item #8 updated with git commit reference

---

## Rollback Plan

If issues arise:
- Revert commit with `git revert <commit-hash>`
- This is a pure documentation/string change with no behavioral impact

---

## Additional Resources

- **MCP Enhancement List:** `F:\TinyContacts\MCP_ENHANCEMENT_LIST.md` (item #8)
- **Claude Code Task Tool Spec:** System prompt `Task` function definition
- **Related Handover:** 0382 (uses correct `subagent_type` terminology)
- **Git Evidence Search:** `git log --all --oneline --grep="subagent"`

---

## Notes

This is a **pure terminology fix** - no behavioral changes. The Task tool already works correctly; agents just need the documentation to match the actual parameter name.

The confusion arose because GiljoAI has `agent_display_name` as a spawn parameter, and someone incorrectly merged concepts with Claude Code's `subagent_type` to create the non-existent `subagent_display_name`.
