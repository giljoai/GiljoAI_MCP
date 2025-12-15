# Handover 0347c: Orchestrator Response Fields Enhancement

**Date**: 2024-12-14
**Agent**: Documentation Manager
**Status**: Ready for Implementation
**Estimated Effort**: 2 hours
**Dependencies**: None (can run parallel with 0347a/0347b)

---

## Executive Summary

Add 6 new guidance fields to the `get_orchestrator_instructions()` MCP tool response to improve orchestrator behavior during staging. These fields provide explicit guidance on post-staging behavior, error handling, spawning limits, and context management.

**Impact**: ~175 tokens added to response, but reduces orchestrator confusion and staging errors by providing explicit operational guidance.

---

## Objective

Enhance the orchestrator instructions response with 6 new fields that clarify operational behavior:

1. **`post_staging_behavior`** - What orchestrator does after staging completes (mode-aware)
2. **`required_final_action`** - STAGING_COMPLETE broadcast requirement (enables UI Launch button)
3. **`multi_terminal_mode_rules`** - Execution rules when `cli_mode=false` (parity with `cli_mode_rules`)
4. **`error_handling`** - Guidance for handling spawn failures and errors
5. **`agent_spawning_limits`** - Explicit limits (max 8 types, unlimited instances)
6. **`context_management`** - How to use `context_budget` field for succession decisions

**Problem Statement**: Orchestrators currently lack explicit guidance on post-staging behavior, error handling, and context management. This leads to:
- Missed STAGING_COMPLETE broadcasts (breaks Launch Jobs button)
- Confusion about when to terminate vs. wait for agents
- Unclear error handling during spawn failures
- Uncertainty about context budget usage

**Solution**: Add structured guidance fields to the response that orchestrators can reference during staging.

---

## Technical Specification

### Modified Files

1. **`src/giljo_mcp/tools/orchestration.py`** - Add helper functions and update response dict construction

### Implementation Details

#### 1. Add Helper Functions

Add these 6 helper functions before the `get_orchestrator_instructions` function (around line 1400):

```python
def _get_post_staging_behavior(cli_mode: bool) -> dict:
    """
    Generate post_staging_behavior field (mode-aware).

    Clarifies what orchestrator should do after staging completes.
    Different guidance for CLI vs Multi-Terminal modes.

    Args:
        cli_mode: Whether Claude Code CLI mode is enabled

    Returns:
        Dict with mode-specific post-staging behavior guidance
    """
    return {
        "cli_mode": (
            "Orchestrator completes after STAGING_COMPLETE broadcast. "
            "Implementation happens via Task tool in separate execution."
        ),
        "multi_terminal_mode": (
            "Orchestrator completes after STAGING_COMPLETE broadcast. "
            "User manually launches agents via [Copy Prompt] buttons."
        )
    }


def _get_required_final_action() -> dict:
    """
    Generate required_final_action field.

    Reinforces the critical STAGING_COMPLETE broadcast requirement.
    This broadcast enables the "Launch Jobs" button in the UI.

    Returns:
        Dict with broadcast action specification and rationale
    """
    return {
        "action": "send_message",
        "params": {
            "to_agents": ["all"],
            "message_type": "broadcast",
            "content_template": "STAGING_COMPLETE: Mission created, {N} agents spawned"
        },
        "why": "Enables Launch Jobs button in UI - REQUIRED"
    }


def _get_multi_terminal_rules() -> dict:
    """
    Generate multi_terminal_mode_rules field.

    Provides parity with cli_mode_rules. When cli_mode is disabled,
    orchestrator needs explicit guidance about Multi-Terminal execution model.

    Returns:
        Dict with Multi-Terminal mode execution rules
    """
    return {
        "agent_launching": "User clicks [Copy Prompt] button in Implementation tab",
        "coordination": "Agents communicate via MCP messaging tools",
        "orchestrator_role": "Staging only - no active coordination after broadcast"
    }


def _get_error_handling() -> dict:
    """
    Generate error_handling field.

    Provides guidance for common error scenarios during staging:
    - Invalid agent types
    - Spawn failures
    - MCP connection issues

    Returns:
        Dict with error handling guidance
    """
    return {
        "invalid_agent_type": "Verify against allowed_agent_types list before calling spawn_agent_job",
        "spawn_failure": "Log via report_error(), do not proceed with remaining agents",
        "mcp_connection_lost": "Abort staging, notify user"
    }


def _get_spawning_limits() -> dict:
    """
    Generate agent_spawning_limits field.

    Makes architecture limits explicit. Per docs/ARCHITECTURE.md,
    system supports max 8 agent types with unlimited instances per type.

    Returns:
        Dict with spawning limits and recommendations
    """
    return {
        "max_agent_types": 8,
        "max_instances_per_type": "unlimited",
        "recommended_total": "2-5 agents for typical projects"
    }


def _get_context_management(context_budget: int) -> dict:
    """
    Generate context_management field.

    Explains how to use the context_budget field for succession decisions.
    Currently, context_budget is returned but orchestrators don't know
    what to do with it.

    Args:
        context_budget: Context budget value from orchestrator record

    Returns:
        Dict with context management guidance
    """
    return {
        "context_budget": context_budget,
        "warning_threshold": 0.8,
        "action_at_threshold": "Consider triggering succession via create_successor_orchestrator"
    }
```

#### 2. Modify Response Dictionary Construction

In the `get_orchestrator_instructions` function (inside `register_orchestration_tools`), update the return statement around line 1701-1713 to add the new fields:

**BEFORE:**
```python
return {
    "orchestrator_id": orchestrator_id,
    "project_id": str(project.id),
    "project_name": project.name,
    "project_description": project.description or "",
    "mission": condensed_mission,
    "context_budget": orchestrator.context_budget or 150000,
    "context_used": orchestrator.context_used or 0,
    "agent_discovery_tool": "get_available_agents()",
    "field_priorities": field_priorities,
    "token_reduction_applied": bool(field_priorities),
    "estimated_tokens": estimated_tokens,
    "instance_number": orchestrator.instance_number or 1,
    "thin_client": True,
}
```

**AFTER:**
```python
# Determine execution mode for conditional fields (Handover 0346)
execution_mode = getattr(project, 'execution_mode', None) or metadata.get("execution_mode", "multi_terminal")
cli_mode = execution_mode == "claude_code_cli"

return {
    "orchestrator_id": orchestrator_id,
    "project_id": str(project.id),
    "project_name": project.name,
    "project_description": project.description or "",
    "mission": condensed_mission,
    "context_budget": orchestrator.context_budget or 150000,
    "context_used": orchestrator.context_used or 0,
    "agent_discovery_tool": "get_available_agents()",
    "field_priorities": field_priorities,
    "token_reduction_applied": bool(field_priorities),
    "estimated_tokens": estimated_tokens,
    "instance_number": orchestrator.instance_number or 1,
    "thin_client": True,

    # Handover 0347c: Enhancement fields for improved orchestrator guidance
    "post_staging_behavior": _get_post_staging_behavior(cli_mode),
    "required_final_action": _get_required_final_action(),
    "multi_terminal_mode_rules": _get_multi_terminal_rules() if not cli_mode else None,
    "error_handling": _get_error_handling(),
    "agent_spawning_limits": _get_spawning_limits(),
    "context_management": _get_context_management(orchestrator.context_budget or 150000),
}
```

#### 3. Update Standalone Function (Testing)

Apply the same changes to the standalone `get_orchestrator_instructions` function (around line 1941-1955) that's used for testing:

Add the same helper function calls to the response dict before the return statement.

**Note**: The standalone function also needs access to `cli_mode`. Extract it from metadata or project just like in the MCP tool version.

---

## Test-Driven Development (TDD) Approach

### Phase 1: Write Tests First

Create comprehensive tests in `tests/tools/test_orchestration_response_fields.py`:

```python
"""
Tests for Handover 0347c: Orchestrator Response Fields Enhancement

Test Strategy:
1. Test each helper function independently (unit tests)
2. Test field presence in MCP tool response (integration tests)
3. Test mode-aware conditional logic (CLI vs Multi-Terminal)
4. Test token impact estimation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from giljo_mcp.tools.orchestration import (
    _get_post_staging_behavior,
    _get_required_final_action,
    _get_multi_terminal_rules,
    _get_error_handling,
    _get_spawning_limits,
    _get_context_management,
)


class TestHelperFunctions:
    """Test individual helper functions for response fields."""

    def test_post_staging_behavior_returns_mode_aware_dict(self):
        """Test post_staging_behavior field structure."""
        result = _get_post_staging_behavior(cli_mode=True)

        assert isinstance(result, dict)
        assert "cli_mode" in result
        assert "multi_terminal_mode" in result
        assert "STAGING_COMPLETE broadcast" in result["cli_mode"]
        assert "Task tool" in result["cli_mode"]
        assert "[Copy Prompt]" in result["multi_terminal_mode"]

    def test_required_final_action_includes_broadcast_spec(self):
        """Test required_final_action field includes broadcast specification."""
        result = _get_required_final_action()

        assert result["action"] == "send_message"
        assert result["params"]["to_agents"] == ["all"]
        assert result["params"]["message_type"] == "broadcast"
        assert "{N}" in result["params"]["content_template"]
        assert "STAGING_COMPLETE" in result["params"]["content_template"]
        assert "Launch Jobs button" in result["why"]

    def test_multi_terminal_rules_structure(self):
        """Test multi_terminal_mode_rules field structure."""
        result = _get_multi_terminal_rules()

        assert "agent_launching" in result
        assert "coordination" in result
        assert "orchestrator_role" in result
        assert "[Copy Prompt]" in result["agent_launching"]
        assert "MCP messaging" in result["coordination"]
        assert "Staging only" in result["orchestrator_role"]

    def test_error_handling_covers_common_scenarios(self):
        """Test error_handling field covers key error scenarios."""
        result = _get_error_handling()

        assert "invalid_agent_type" in result
        assert "spawn_failure" in result
        assert "mcp_connection_lost" in result
        assert "allowed_agent_types" in result["invalid_agent_type"]
        assert "report_error()" in result["spawn_failure"]
        assert "Abort staging" in result["mcp_connection_lost"]

    def test_spawning_limits_matches_architecture(self):
        """Test agent_spawning_limits matches architecture spec."""
        result = _get_spawning_limits()

        assert result["max_agent_types"] == 8
        assert result["max_instances_per_type"] == "unlimited"
        assert "2-5 agents" in result["recommended_total"]

    def test_context_management_uses_budget_value(self):
        """Test context_management field uses provided budget."""
        budget = 200000
        result = _get_context_management(budget)

        assert result["context_budget"] == budget
        assert result["warning_threshold"] == 0.8
        assert "succession" in result["action_at_threshold"]
        assert "create_successor_orchestrator" in result["action_at_threshold"]

    def test_context_management_default_budget(self):
        """Test context_management with default budget value."""
        result = _get_context_management(150000)

        assert result["context_budget"] == 150000


class TestResponseFieldsIntegration:
    """Test response fields in get_orchestrator_instructions MCP tool."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator job."""
        return MagicMock(
            job_id=str(uuid4()),
            project_id=uuid4(),
            tenant_key="test-tenant",
            context_budget=150000,
            context_used=0,
            instance_number=1,
            mission_acknowledged_at=None,
            job_metadata={
                "field_priorities": {},
                "depth_config": {},
                "execution_mode": "multi_terminal"
            }
        )

    @pytest.fixture
    def mock_project(self):
        """Create mock project."""
        return MagicMock(
            id=uuid4(),
            name="Test Project",
            description="Test description",
            product_id=uuid4(),
            tenant_key="test-tenant",
            execution_mode="multi_terminal"
        )

    @pytest.mark.asyncio
    async def test_response_includes_post_staging_behavior(self, mock_orchestrator, mock_project):
        """Test response includes post_staging_behavior field."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            # Setup mocks
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                # Call function
                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                # Verify post_staging_behavior field exists
                assert "post_staging_behavior" in result
                assert isinstance(result["post_staging_behavior"], dict)
                assert "cli_mode" in result["post_staging_behavior"]
                assert "multi_terminal_mode" in result["post_staging_behavior"]

    @pytest.mark.asyncio
    async def test_response_includes_required_final_action(self, mock_orchestrator, mock_project):
        """Test response includes required_final_action field."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                assert "required_final_action" in result
                assert result["required_final_action"]["action"] == "send_message"

    @pytest.mark.asyncio
    async def test_multi_terminal_rules_conditional_on_mode(self, mock_orchestrator, mock_project):
        """Test multi_terminal_mode_rules only present when cli_mode=false."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Test Multi-Terminal mode (should include field)
        mock_project.execution_mode = "multi_terminal"

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                assert "multi_terminal_mode_rules" in result
                assert result["multi_terminal_mode_rules"] is not None

        # Test CLI mode (should exclude field)
        mock_project.execution_mode = "claude_code_cli"
        mock_orchestrator.job_metadata["execution_mode"] = "claude_code_cli"

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                # Field should be None in CLI mode
                assert result["multi_terminal_mode_rules"] is None

    @pytest.mark.asyncio
    async def test_response_includes_error_handling(self, mock_orchestrator, mock_project):
        """Test response includes error_handling field."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                assert "error_handling" in result
                assert "invalid_agent_type" in result["error_handling"]
                assert "spawn_failure" in result["error_handling"]

    @pytest.mark.asyncio
    async def test_response_includes_spawning_limits(self, mock_orchestrator, mock_project):
        """Test response includes agent_spawning_limits field."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                assert "agent_spawning_limits" in result
                assert result["agent_spawning_limits"]["max_agent_types"] == 8

    @pytest.mark.asyncio
    async def test_response_includes_context_management(self, mock_orchestrator, mock_project):
        """Test response includes context_management field."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                assert "context_management" in result
                assert result["context_management"]["context_budget"] == 150000
                assert result["context_management"]["warning_threshold"] == 0.8

    @pytest.mark.asyncio
    async def test_all_six_fields_present_in_response(self, mock_orchestrator, mock_project):
        """Test all 6 enhancement fields are present in response."""
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        with patch('giljo_mcp.tools.orchestration.db_manager') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session_async.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.side_effect = [mock_orchestrator, mock_project, None]
            mock_session.execute.return_value = mock_result

            with patch('giljo_mcp.mission_planner.MissionPlanner') as mock_planner:
                mock_planner_instance = AsyncMock()
                mock_planner_instance._build_context_with_priorities.return_value = "Test mission"
                mock_planner.return_value = mock_planner_instance

                result = await get_orchestrator_instructions(
                    orchestrator_id=mock_orchestrator.job_id,
                    tenant_key="test-tenant"
                )

                # Verify all 6 fields present
                required_fields = [
                    "post_staging_behavior",
                    "required_final_action",
                    "multi_terminal_mode_rules",  # May be None in CLI mode
                    "error_handling",
                    "agent_spawning_limits",
                    "context_management"
                ]

                for field in required_fields:
                    assert field in result, f"Missing required field: {field}"


class TestTokenImpact:
    """Test token impact of new fields."""

    def test_token_estimate_includes_new_fields(self):
        """Test estimated token count for all 6 fields combined."""
        # Generate all fields
        post_staging = _get_post_staging_behavior(cli_mode=True)
        required_action = _get_required_final_action()
        multi_terminal = _get_multi_terminal_rules()
        error_handling = _get_error_handling()
        spawning_limits = _get_spawning_limits()
        context_mgmt = _get_context_management(150000)

        # Convert to JSON and estimate tokens (1 token ≈ 4 chars)
        import json
        combined_json = json.dumps({
            "post_staging_behavior": post_staging,
            "required_final_action": required_action,
            "multi_terminal_mode_rules": multi_terminal,
            "error_handling": error_handling,
            "agent_spawning_limits": spawning_limits,
            "context_management": context_mgmt
        })

        estimated_tokens = len(combined_json) // 4

        # Should be approximately 175 tokens (allow ±50 token variance)
        assert 125 <= estimated_tokens <= 225, \
            f"Token count {estimated_tokens} outside expected range (125-225)"
```

### Phase 2: Run Tests (Should Fail)

Run the test suite - all tests should fail because helper functions don't exist yet:

```bash
pytest tests/tools/test_orchestration_response_fields.py -v
```

Expected output:
```
FAILED - ImportError: cannot import name '_get_post_staging_behavior'
FAILED - ImportError: cannot import name '_get_required_final_action'
... (all tests fail)
```

### Phase 3: Implement Code

Implement the helper functions and response modifications as specified in Technical Specification section.

### Phase 4: Run Tests Again (Should Pass)

Run tests again after implementation:

```bash
pytest tests/tools/test_orchestration_response_fields.py -v
```

Expected output:
```
test_post_staging_behavior_returns_mode_aware_dict PASSED
test_required_final_action_includes_broadcast_spec PASSED
test_multi_terminal_rules_structure PASSED
... (all tests pass)
```

### Phase 5: Integration Testing

Test with actual orchestrator flow:

```bash
# Start server
python startup.py

# Create test project and trigger orchestrator
# Verify response fields via API or database inspection

# Check orchestrator logs for field presence
tail -f ~/.giljo_mcp/logs/mcp_adapter.log
```

---

## Acceptance Criteria

- [ ] All 6 helper functions implemented and working
- [ ] Response dict includes all new fields
- [ ] `multi_terminal_mode_rules` conditionally included based on `cli_mode`
- [ ] All unit tests pass (100% coverage of helper functions)
- [ ] All integration tests pass (response field presence verified)
- [ ] Token impact within expected range (~175 tokens ±50)
- [ ] No breaking changes to existing response structure
- [ ] Standalone test function also updated with same changes
- [ ] Orchestrator logs confirm field presence in real execution

---

## Success Metrics

**Token Impact**:
- Post-staging behavior: ~40 tokens
- Required final action: ~35 tokens
- Multi-terminal rules: ~25 tokens
- Error handling: ~30 tokens
- Spawning limits: ~20 tokens
- Context management: ~25 tokens
- **Total**: ~175 tokens

**Quality Metrics**:
- Test coverage: 100% of new helper functions
- Integration test pass rate: 100%
- Zero regression in existing tests

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token budget exceeded | Medium | Fields are small (~175 tokens total), well under 500 token safety margin |
| Breaking changes to response | High | Add fields to END of response dict, preserve all existing fields |
| Helper function naming conflicts | Low | Use underscore prefix (`_get_*`) to indicate private/internal functions |
| Mode detection failure | Medium | Use same pattern as existing `agent_spawning_constraint` logic (proven code) |

---

## Rollback Plan

If issues arise:

1. **Immediate Rollback**: Comment out helper function calls in response dict
2. **Partial Rollback**: Remove specific problematic fields while keeping others
3. **Git Revert**: `git revert <commit-hash>` to undo entire handover

No database changes required, so rollback is safe and immediate.

---

## Related Documentation

- **Parent Handover**: [0347_mission_response_yaml_restructuring.md](0347_mission_response_yaml_restructuring.md)
- **Architecture**: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) (max 8 agent types)
- **Orchestrator Guide**: [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md)
- **Testing Guide**: [docs/TESTING.md](../docs/TESTING.md)

---

## Implementation Checklist

### Phase 1: Setup & Tests
- [ ] Create test file `tests/tools/test_orchestration_response_fields.py`
- [ ] Write all unit tests for helper functions
- [ ] Write integration tests for response fields
- [ ] Run tests (verify they fail)

### Phase 2: Implementation
- [ ] Add 6 helper functions to `orchestration.py` (before `get_orchestrator_instructions`)
- [ ] Extract `cli_mode` determination logic in MCP tool response
- [ ] Add helper function calls to MCP tool response dict
- [ ] Update standalone `get_orchestrator_instructions` function (testing)
- [ ] Run tests (verify they pass)

### Phase 3: Validation
- [ ] Run full test suite: `pytest tests/tools/test_orchestration_response_fields.py -v`
- [ ] Check test coverage: `pytest --cov=src/giljo_mcp/tools/orchestration --cov-report=html`
- [ ] Manual testing: Create test project and verify response
- [ ] Token impact verification: Measure actual token count

### Phase 4: Documentation
- [ ] Update function docstrings with new field descriptions
- [ ] Add code comments explaining conditional logic
- [ ] Mark handover as COMPLETE in status

---

## Post-Implementation Notes

**For Future Reference**:
- Helper functions are private (underscore prefix) - not exposed in module exports
- `multi_terminal_mode_rules` uses same conditional pattern as `agent_spawning_constraint`
- Context budget value passed from orchestrator record to `_get_context_management()`
- Token count uses standard 1 token ≈ 4 characters heuristic

**Known Limitations**:
- Error handling guidance is static - doesn't adapt to specific error context
- Spawning limits hardcoded to architecture spec (max 8 types)
- Context threshold (0.8) not configurable - fixed value

**Future Enhancements**:
- Make context warning threshold configurable (My Settings → Orchestrator)
- Add dynamic error recovery suggestions based on error type
- Track actual spawning patterns and suggest optimal agent counts
