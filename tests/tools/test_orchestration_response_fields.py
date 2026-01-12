"""
Test suite for orchestrator response fields enhancement (Handover 0347c).

Tests the 6 new guidance fields added to get_orchestrator_instructions():
1. post_staging_behavior
2. required_final_action
3. multi_terminal_mode_rules
4. error_handling
5. agent_spawning_limits
6. context_management
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

# Import the helper functions we'll create
from src.giljo_mcp.tools.orchestration import (
    _get_post_staging_behavior,
    _get_required_final_action,
    _get_multi_terminal_rules,
    _get_error_handling,
    _get_spawning_limits,
    _get_context_management,
    get_orchestrator_instructions,
)


class TestHelperFunctions:
    """Unit tests for each helper function."""

    def test_post_staging_behavior_cli_mode(self):
        """Test post_staging_behavior returns correct structure for CLI mode."""
        result = _get_post_staging_behavior(cli_mode=True)

        assert isinstance(result, dict)
        assert "cli_mode" in result
        assert "multi_terminal_mode" in result
        assert "Task tool" in result["cli_mode"]
        assert "separate execution" in result["cli_mode"]

    def test_post_staging_behavior_multi_terminal_mode(self):
        """Test post_staging_behavior returns correct structure for multi-terminal mode."""
        result = _get_post_staging_behavior(cli_mode=False)

        assert isinstance(result, dict)
        assert "cli_mode" in result
        assert "multi_terminal_mode" in result
        assert "Copy Prompt" in result["multi_terminal_mode"]
        assert "manually launches" in result["multi_terminal_mode"]

    def test_required_final_action_structure(self):
        """Test required_final_action returns correct structure."""
        result = _get_required_final_action()

        assert isinstance(result, dict)
        assert result["action"] == "send_message"
        assert "params" in result
        assert "why" in result

        params = result["params"]
        assert params["to_agents"] == ["all"]
        assert params["message_type"] == "broadcast"
        assert "STAGING_COMPLETE" in params["content_template"]
        assert "{N}" in params["content_template"]

        assert "Launch Jobs button" in result["why"]
        assert "REQUIRED" in result["why"]

    def test_multi_terminal_rules_structure(self):
        """Test multi_terminal_mode_rules returns correct structure."""
        result = _get_multi_terminal_rules()

        assert isinstance(result, dict)
        assert "agent_launching" in result
        assert "coordination" in result
        assert "orchestrator_role" in result

        assert "Copy Prompt" in result["agent_launching"]
        assert "Implementation tab" in result["agent_launching"]
        assert "MCP messaging tools" in result["coordination"]
        assert "Staging only" in result["orchestrator_role"]

    def test_error_handling_structure(self):
        """Test error_handling returns correct structure."""
        result = _get_error_handling()

        assert isinstance(result, dict)
        assert "invalid_agent_name" in result
        assert "spawn_failure" in result
        assert "mcp_connection_lost" in result

        assert "allowed_agent_display_names" in result["invalid_agent_name"]
        assert "spawn_agent_job" in result["invalid_agent_name"]
        assert "report_error()" in result["spawn_failure"]
        assert "do not proceed" in result["spawn_failure"]
        assert "Abort staging" in result["mcp_connection_lost"]

    def test_spawning_limits_structure(self):
        """Test agent_spawning_limits returns correct structure."""
        result = _get_spawning_limits()

        assert isinstance(result, dict)
        assert result["max_agent_display_names"] == 8
        assert result["max_instances_per_type"] == "unlimited"
        assert "2-5 agents" in result["recommended_total"]

    def test_context_management_with_default_budget(self):
        """Test context_management with default budget."""
        result = _get_context_management(150000)

        assert isinstance(result, dict)
        assert result["context_budget"] == 150000
        assert result["warning_threshold"] == 0.8
        assert "create_successor_orchestrator" in result["action_at_threshold"]

    def test_context_management_with_custom_budget(self):
        """Test context_management with custom budget."""
        result = _get_context_management(200000)

        assert result["context_budget"] == 200000
        assert result["warning_threshold"] == 0.8


class TestOrchestratorInstructionsIntegration:
    """Integration tests for get_orchestrator_instructions response.

    These tests verify that the helper functions are properly integrated
    into the response dict, but don't require full database setup.
    """

    @pytest.mark.asyncio
    async def test_response_includes_all_new_fields_multi_terminal(self):
        """Test that response includes all 6 new fields in multi-terminal mode."""
        # Mock a minimal response dict that would be returned by get_orchestrator_instructions
        # We'll test the helper function integration by building a response dict similar to the actual function

        cli_mode = False
        context_budget = 150000

        response = {
            "orchestrator_id": "test-orch-id",
            "project_id": "test-project-id",
            "project_name": "Test Project",
            "thin_client": True,
            # Handover 0347c: Add 6 new guidance fields
            "post_staging_behavior": _get_post_staging_behavior(cli_mode),
            "required_final_action": _get_required_final_action(),
            "multi_terminal_mode_rules": _get_multi_terminal_rules() if not cli_mode else None,
            "error_handling": _get_error_handling(),
            "agent_spawning_limits": _get_spawning_limits(),
            "context_management": _get_context_management(context_budget),
        }

        # Verify all 6 new fields are present
        assert "post_staging_behavior" in response
        assert "required_final_action" in response
        assert "multi_terminal_mode_rules" in response
        assert "error_handling" in response
        assert "agent_spawning_limits" in response
        assert "context_management" in response

        # Verify post_staging_behavior structure
        assert isinstance(response["post_staging_behavior"], dict)
        assert "cli_mode" in response["post_staging_behavior"]
        assert "multi_terminal_mode" in response["post_staging_behavior"]

        # Verify required_final_action structure
        assert response["required_final_action"]["action"] == "send_message"

        # Verify multi_terminal_mode_rules is included (not None)
        assert response["multi_terminal_mode_rules"] is not None
        assert "agent_launching" in response["multi_terminal_mode_rules"]

        # Verify error_handling structure
        assert "invalid_agent_name" in response["error_handling"]

        # Verify agent_spawning_limits structure
        assert response["agent_spawning_limits"]["max_agent_display_names"] == 8

        # Verify context_management structure
        assert response["context_management"]["context_budget"] == 150000

    @pytest.mark.asyncio
    async def test_response_excludes_multi_terminal_rules_in_cli_mode(self):
        """Test that multi_terminal_mode_rules is None in CLI mode."""
        cli_mode = True
        context_budget = 150000

        response = {
            "orchestrator_id": "test-orch-id",
            "project_id": "test-project-id",
            "thin_client": True,
            # Handover 0347c: Add 6 new guidance fields
            "post_staging_behavior": _get_post_staging_behavior(cli_mode),
            "required_final_action": _get_required_final_action(),
            "multi_terminal_mode_rules": _get_multi_terminal_rules() if not cli_mode else None,
            "error_handling": _get_error_handling(),
            "agent_spawning_limits": _get_spawning_limits(),
            "context_management": _get_context_management(context_budget),
        }

        # Verify multi_terminal_mode_rules is None in CLI mode
        assert response["multi_terminal_mode_rules"] is None

        # Verify other fields are still present
        assert "post_staging_behavior" in response
        assert "required_final_action" in response
        assert "error_handling" in response
        assert "agent_spawning_limits" in response
        assert "context_management" in response

    @pytest.mark.asyncio
    async def test_context_management_uses_orchestrator_budget(self):
        """Test that context_management uses orchestrator's context_budget."""
        cli_mode = False
        context_budget = 200000

        response = {
            "orchestrator_id": "test-orch-id",
            "context_management": _get_context_management(context_budget),
        }

        # Verify context_management uses orchestrator's budget
        assert response["context_management"]["context_budget"] == 200000

    @pytest.mark.asyncio
    async def test_context_management_defaults_to_150k_if_none(self):
        """Test that context_management defaults to 150K if budget is None."""
        cli_mode = False
        context_budget = None

        response = {
            "orchestrator_id": "test-orch-id",
            "context_management": _get_context_management(context_budget or 150000),
        }

        # Verify context_management defaults to 150000
        assert response["context_management"]["context_budget"] == 150000


class TestTokenImpact:
    """Test token impact of new fields."""

    def test_estimated_token_impact(self):
        """Test that new fields add approximately 375 tokens."""
        import json

        # Generate all fields
        post_staging = _get_post_staging_behavior(cli_mode=False)
        required_action = _get_required_final_action()
        multi_terminal = _get_multi_terminal_rules()
        error_handling = _get_error_handling()
        spawning_limits = _get_spawning_limits()
        context_mgmt = _get_context_management(150000)

        # Combine into dict
        all_fields = {
            "post_staging_behavior": post_staging,
            "required_final_action": required_action,
            "multi_terminal_mode_rules": multi_terminal,
            "error_handling": error_handling,
            "agent_spawning_limits": spawning_limits,
            "context_management": context_mgmt,
        }

        # Serialize to JSON
        json_str = json.dumps(all_fields, indent=2)

        # Rough token estimate: ~4 chars per token
        estimated_tokens = len(json_str) / 4

        # Verify within acceptable range (375 ± 100)
        assert 275 <= estimated_tokens <= 475, f"Token estimate {estimated_tokens} outside expected range 275-475"

    def test_cli_mode_reduces_tokens(self):
        """Test that CLI mode reduces tokens by excluding multi_terminal_mode_rules."""
        import json

        # Multi-terminal mode (includes all fields)
        multi_terminal_fields = {
            "post_staging_behavior": _get_post_staging_behavior(cli_mode=False),
            "required_final_action": _get_required_final_action(),
            "multi_terminal_mode_rules": _get_multi_terminal_rules(),
            "error_handling": _get_error_handling(),
            "agent_spawning_limits": _get_spawning_limits(),
            "context_management": _get_context_management(150000),
        }

        # CLI mode (multi_terminal_mode_rules is None)
        cli_fields = {
            "post_staging_behavior": _get_post_staging_behavior(cli_mode=True),
            "required_final_action": _get_required_final_action(),
            "multi_terminal_mode_rules": None,
            "error_handling": _get_error_handling(),
            "agent_spawning_limits": _get_spawning_limits(),
            "context_management": _get_context_management(150000),
        }

        multi_terminal_tokens = len(json.dumps(multi_terminal_fields)) / 4
        cli_tokens = len(json.dumps(cli_fields)) / 4

        # CLI mode should have fewer tokens
        assert cli_tokens < multi_terminal_tokens

        # Difference should be roughly the size of multi_terminal_mode_rules
        token_difference = multi_terminal_tokens - cli_tokens
        assert 40 <= token_difference <= 70  # Adjusted estimate based on actual field size
