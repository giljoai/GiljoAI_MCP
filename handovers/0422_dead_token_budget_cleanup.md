# Handover 0422: Dead Token Budget Code Cleanup

**Status**: COMPLETE
**Branch**: `feature/0422-dead-token-budget-cleanup`
**Commits**: `bb416ce5`, `c4543629`

---

## Objective

Remove dead token/context budget management code that was never fully integrated. The MCP server is passive and cannot track external CLI tool context usage.

---

## Background

The GiljoAI MCP Server included token budget tracking infrastructure that was never activated:
- `update_context_usage()` - existed but was NEVER called in production (only tests)
- `_trigger_auto_succession()` - auto-succession at 90% threshold never executed
- Context monitoring methods (`_start_context_monitor`, `_monitor_project_context`) - never ran
- Orchestrator templates contained instructions for impossible token tracking

**Root Cause**: This is a PASSIVE MCP server - it provides data to CLI tools but cannot track their context usage. The CLI tools (Claude Code, etc.) run externally and don't report their token consumption back to the server.

**What Still Works**: Manual succession via `/gil_handover` slash command and UI "Hand Over" button.

---

## Changes Made

### Production Code (~535 lines removed)

| File | Lines | Changes |
|------|-------|---------|
| `orchestrator.py` | ~334 | Removed 10 dead methods + constant |
| `orchestration_service.py` | ~122 | Removed 3 dead methods |
| `tools/context.py` | ~59 | Removed 1 dead function |
| `template_seeder.py` | ~45 | Updated orchestrator template |
| `thin_prompt_generator.py` | ~3 | Removed token budget instructions |

### Removed Methods

**From `orchestrator.py`:**
- `DEFAULT_AGENT_CONTEXT_BUDGET` constant
- `handle_context_limit()`
- `handoff()` (dead - tests only)
- `check_handoff_needed()`
- `get_context_status()`
- `update_context_usage()`
- `get_agent_context_status()`
- `_start_context_monitor()`
- `_stop_context_monitor()`
- `_monitor_project_context()`
- `_get_handoff_reason()`
- `_context_monitors` instance variable

**From `orchestration_service.py`:**
- `update_context_usage()`
- `estimate_message_tokens()`
- `_trigger_auto_succession()`

**From `tools/context.py`:**
- `update_context_usage()`

### Template Changes

**Removed from orchestrator template:**
- "managing context budgets" from description
- "Monitor project progress and context budget usage"
- "Trigger succession when context reaches 90% capacity"
- Context Budget Management table (70-85-90% thresholds)

**Kept:**
- "Monitor project progress" (relates to messaging platform)
- Manual succession instructions (`/gil_handover`)

### Test Files Updated (~2,200+ lines removed)

| File | Action |
|------|--------|
| `test_orchestrator.py` | Removed dead method tests |
| `test_orchestrator_comprehensive.py` | Removed dead method tests |
| `test_orchestrator_final.py` | Removed dead method tests |
| `test_orchestrator_integration.py` | Removed dead method tests |
| `test_orchestrator_simple.py` | Removed dead method tests |
| `test_orchestration_service_dual_model.py` | Removed update_context_usage test |
| `test_orchestration_service_context.py` | Removed 9 dead method tests |
| `test_0367a_mcpagentjob_removal.py` | Removed 2 trigger_succession tests |
| `test_claude_code_mode_workflow.py` | Removed workflow with removed methods |
| `test_multi_terminal_mode_workflow.py` | Removed workflow with removed methods |
| `test_succession_mode_preservation_e2e.py` | **DELETED** (entire file) |
| `test_full_stack_mode_flow.py` | Removed trigger_succession test |
| `test_multi_tenant_isolation.py` | Removed succession_isolation test |
| `test_concurrent_agents.py` | Removed context monitoring cleanup |
| `conftest.py` | Updated comment |

---

## What Was Kept

| Component | Reason |
|-----------|--------|
| Manual succession (`gil_handover`, `create_successor_orchestrator`) | Works correctly |
| `check_succession_status` MCP tool | Returns data (even if stale) |
| `context_used`/`context_budget` DB columns | Used by succession display |
| `trigger_succession()` in OrchestrationService | Manual succession (not auto) |
| "Monitor project progress" instructions | Relates to messaging platform |
| `orchestrator_succession.py` | Used by manual succession |

---

## Verification

1. All production code imports successfully
2. No references to removed methods in production code
3. Test cleanup complete - removed tests that called dead methods
4. Manual succession (`/gil_handover`) still works

---

## Net Impact

- **Lines Removed**: ~2,758
- **Lines Added**: ~131
- **Files Modified**: 19
- **Files Deleted**: 1

---

## Related Handovers

- 0080: Orchestrator Succession (introduced the succession system)
- 0246a-c: Orchestrator Workflow & Token Optimization
- 0350a-c: On-Demand Context Fetch Architecture

---

## Future Considerations

If automatic context tracking is desired in the future, it would require:
1. CLI tools (Claude Code) to report their context usage back to the server
2. A standardized API for CLI → Server context reporting
3. Server-side accumulation and threshold monitoring

This is a significant architectural change that was never implemented.
