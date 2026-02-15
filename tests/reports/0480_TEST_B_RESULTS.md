# 0480-TEST-B Results: MCP Tool Tests

**Date:** 2026-01-27
**Executor:** 0480-TEST-B session
**Branch:** 0480-exception-handling-remediation

## Executive Summary

| Metric | Value |
|--------|-------|
| Tests Collected | 240 |
| Passed | 162 (67.5%) |
| Failed | 46 (19.2%) |
| Errors | 20 (8.3%) |
| Skipped | 12 (5.0%) |
| Execution Time | 26.84s |

**Overall Status:** PARTIAL PASS - Core MCP tools work but error response format inconsistencies detected.

---

## Critical Finding: Error Response Format Inconsistency

### Expected Format (per 0480 Test Plan)
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Human-readable error",
    "context": {"job_id": "..."}
  }
}
```

### Actual Formats Found

**Format A** (most tools in tool_accessor.py, agent.py, context.py):
```python
{"success": False, "error": "some error message"}
```

**Format B** (orchestration.py functions):
```python
{"error": "NOT_FOUND", "message": "..."}
```

**Impact:** Neither format matches the expected nested error object structure. This explains many test failures.

---

## Files With Import Issues (Fixed/Skipped)

| File | Issue | Resolution |
|------|-------|------------|
| `test_agent_communication_0360.py` | Import `message_service_0366b` (nonexistent) | Fixed to `message_service` |
| `test_amendments_a_b.py` | Import `register_orchestration_tools` (nonexistent) | Excluded from run |

---

## Test Results by Category

### Passed Tests (162)

**Core Tool Accessor Delegation** (13/13 passed):
- `test_tool_accessor_delegation.py` - All delegation tests pass
- Confirms service layer properly delegates to OrchestrationService

**Agent Lifecycle Tests** (9/10 passed):
- `test_agent_0358c.py` - Core agent lifecycle works
- 1 skipped: `test_spawn_sub_agent_creates_execution`

**Agent Coordination** (7/7 passed):
- `test_agent_coordination_0360.py` - Team agent retrieval works

**Closeout Verification** (17/17 passed):
- `test_closeout_verification.py` - All blocking/success/edge case tests pass

**Context Priority Framing** (19/20 passed):
- `test_context_priority_framing_critical.py` - 18/18 passed
- `test_context_priority_framing.py` - 4/5 passed

**Context Tools Reads** (11/11 passed):
- `test_context_tools_reads.py` - 360 Memory and Git History reads work

**Fetch Context** (9/9 passed):
- `test_fetch_context.py` and `test_fetch_context_self_identity_integration.py` - All pass

**Project Closeout Table** (17/17 passed):
- `test_project_closeout_table.py` - All table operations work

**Spawn Agent Job Clarity** (5/5 passed):
- `test_spawn_agent_job_clarity.py` - Response format improvements work

**Write 360 Memory Table** (11/11 passed):
- `test_write_360_memory_table.py` - All table writes work

### Failed Tests (46)

**test_agent_communication_0360.py** (8 failures):
- `test_receive_messages_*` - All 8 tests fail
- Cause: MessageService API changes from 0366b migration
- These tests reference old filtering behavior

**test_context_orchestration.py** (4 failures):
- `test_get_orchestrator_instructions_accepts_user_id`
- `test_get_user_config_*`
- `test_get_orchestrator_instructions_without_user_id_backward_compatibility`
- Cause: User config retrieval changes

**test_deprecated_tools.py** (12 failures):
- All 11 deprecated tool tests fail
- `test_all_deprecated_tools_have_consistent_format` fails
- Cause: Tools were removed, not deprecated with error returns

**test_orchestration_mission_read.py** (2 failures):
- `test_get_orchestrator_instructions_sets_mission_acknowledged_at`
- `test_mission_acknowledged_at_multi_tenant_isolation`
- Cause: `mission_acknowledged_at` field handling

**test_orchestration_response_fields.py** (3 failures):
- `test_post_staging_behavior_cli_mode`
- `test_required_final_action_structure`
- `test_error_handling_structure`
- Cause: Response structure changes

**test_thin_client_mcp_tools.py** (5 failures):
- `test_get_orchestrator_instructions_not_found`
- `test_get_agent_mission_thin_client`
- `test_spawn_agent_job_thin_prompt`
- `test_error_handling_structured_responses`
- `test_input_validation_sanitization`
- Cause: Error response format mismatches

**test_tool_accessor_0358c.py** (5 failures):
- `test_get_orchestrator_instructions_joins_tables`
- `test_get_orchestrator_instructions_returns_both_ids`
- `test_multi_tenant_isolation_for_mcp_tools`
- `test_succession_preserves_job_id_changes_agent_id`
- `test_error_handling_missing_ids`
- Cause: API changes, error format mismatches

**test_tool_accessor_mcp_catalog.py** (4 failures):
- All MCP catalog tests fail
- Cause: Catalog generation or priority handling changes

**Other** (3 failures):
- `test_vision_document_includes_framing` - Framing format change
- `test_depth_none_returns_empty_response` - Response format change
- `test_update_agent_mission_not_found` - Error format mismatch

### Error Tests (20)

**test_tenant_isolation_mcp_tools.py** (12 errors):
- All tests error at fixture setup
- Error: `TypeError: 'project_id' is an invalid keyword argument for AgentExecution`
- Cause: Model schema changed - `AgentExecution` no longer has `project_id` field

**test_thin_client_mcp_tools.py** (5 errors):
- Same fixture issue with `AgentExecution`

**test_tool_accessor_update_agent_mission.py** (3 errors):
- Same fixture issue

### Skipped Tests (12)

**test_context_depth_config.py** (11 skipped):
- Vision chunking tests
- Memory pagination tests
- Git commit limiting tests
- Agent template detail tests
- Reason: Tests marked with skip decorators (likely pending implementation)

**test_agent_0358c.py** (1 skipped):
- `test_spawn_sub_agent_creates_execution`

---

## MCP Error Response Analysis

### Functions Analyzed

| Function | File | Current Error Format | Matches Expected? |
|----------|------|---------------------|-------------------|
| `get_agent_mission` | orchestration.py | `{"error": "NOT_FOUND", "message": "..."}` | NO |
| `get_orchestrator_instructions` | orchestration.py | `{"error": "NOT_FOUND", "message": "..."}` | NO |
| `spawn_agent_job` | orchestration.py | `{"success": False, "error": "..."}` | NO |
| `activate_project` | tool_accessor.py | `{"success": False, "error": "..."}` | NO |
| `get_workflow_status` | tool_accessor.py | `{"success": False, "error": "..."}` | NO |

### Recommendation

Standardize MCP error responses to match the expected format:
```python
{
    "success": False,
    "error": {
        "code": "NOT_FOUND",  # or "VALIDATION_ERROR", "INTERNAL_ERROR"
        "message": "Human-readable error message",
        "context": {"resource_id": "...", "resource_type": "..."}
    }
}
```

---

## Model Schema Issues

The `AgentExecution` model no longer has a `project_id` field directly. Tests using:
```python
AgentExecution(project_id="...")
```
Will fail with `TypeError`.

**Fix:** Update fixtures to use the correct relationship:
```python
# Instead of:
AgentExecution(project_id="...")

# Use:
AgentExecution(job_id="...", ...)  # project_id comes from AgentJob
```

---

## Passing Test Categories (Verification)

The following test categories confirm that core MCP tool functionality works:

1. **Tool Accessor Delegation** - All 13 tests pass
   - Confirms service layer integration works correctly

2. **Agent Coordination** - All 7 tests pass
   - `get_team_agents` works correctly

3. **Context Tools** - 20+ tests pass
   - `fetch_context`, 360 memory reads, git history reads all work

4. **Project Closeout** - All 17 tests pass
   - `close_project_and_update_memory` works correctly

5. **Write 360 Memory** - All 11 tests pass
   - `write_360_memory` creates proper table entries

---

## Recommendations

### High Priority (Before Merge)

1. **Fix Model Fixtures** (affects 20 error tests)
   - Update test fixtures to not use `project_id` directly on `AgentExecution`

2. **Standardize Error Response Format** (affects 15+ failed tests)
   - Create utility function: `make_mcp_error(code, message, context=None)`
   - Apply consistently across all MCP tools

### Medium Priority

3. **Update Deprecated Tools Tests**
   - Either implement proper deprecation stubs or remove tests

4. **Fix Message Filtering Tests**
   - Update to match current MessageService API

### Low Priority

5. **Review Skipped Tests**
   - Determine if they should be enabled or removed

---

## Next Steps

1. Run 0480-TEST-C (MessageService Unit Tests)
2. Fix identified issues before running 0480-TEST-E (API Endpoint Integration)

---

## Appendix: Command Used

```bash
python -m pytest tests/tools/ --ignore=tests/tools/test_amendments_a_b.py -v --tb=short
```

**Files Modified During Test:**
- `tests/tools/test_agent_communication_0360.py` - Fixed import from `message_service_0366b` to `message_service`

---

**Document Version:** 1.0
**Test Plan Reference:** `F:\GiljoAI_MCP\handovers\0480_TEST_PLAN.md`
