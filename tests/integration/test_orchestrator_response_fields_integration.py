"""
Integration test for Handover 0347c - verify new response fields in real database scenario.

This test creates a real database scenario and verifies that all 6 new fields
are properly returned by get_orchestrator_instructions().
"""

import pytest
from uuid import uuid4

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions


@pytest.mark.asyncio
async def test_new_fields_in_real_response():
    """Integration test: verify 6 new fields appear in actual MCP tool response."""
    # Setup database
    config = get_config()
    db_url = config.database.database_url
    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    tenant_key = f"test-tenant-{uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=uuid4(),
            name="Test Product",
            description="Test product for response fields",
            tenant_key=tenant_key,
        )
        session.add(product)

        # Create project
        project = Project(
            id=uuid4(),
            name="Test Project",
            description="Test project for response fields",
            product_id=product.id,
            tenant_key=tenant_key,
            execution_mode="multi_terminal",
        )
        session.add(project)

        # Create orchestrator job
        orchestrator = AgentExecution(
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator",
            status="pending",
            project_id=project.id,
            tenant_key=tenant_key,
            context_budget=150000,
            context_used=0,
            mission="Test mission",
        )
        session.add(orchestrator)
        await session.commit()

        # Call get_orchestrator_instructions
        result = await get_orchestrator_instructions(
            orchestrator_id=orchestrator.job_id,
            tenant_key=tenant_key,
            db_manager=db_manager,
        )

    # Verify response structure
    assert "error" not in result, f"Unexpected error: {result.get('message')}"

    # Verify all 6 new fields are present
    assert "post_staging_behavior" in result
    assert "required_final_action" in result
    assert "multi_terminal_mode_rules" in result
    assert "error_handling" in result
    assert "agent_spawning_limits" in result
    assert "context_management" in result

    # Verify post_staging_behavior structure
    assert isinstance(result["post_staging_behavior"], dict)
    assert "cli_mode" in result["post_staging_behavior"]
    assert "multi_terminal_mode" in result["post_staging_behavior"]

    # Verify required_final_action structure
    assert result["required_final_action"]["action"] == "send_message"
    assert "STAGING_COMPLETE" in result["required_final_action"]["params"]["content_template"]

    # Verify multi_terminal_mode_rules is included (not None) for multi-terminal mode
    assert result["multi_terminal_mode_rules"] is not None
    assert "agent_launching" in result["multi_terminal_mode_rules"]

    # Verify error_handling structure
    assert "invalid_agent_display_name" in result["error_handling"]
    assert "spawn_failure" in result["error_handling"]
    assert "mcp_connection_lost" in result["error_handling"]

    # Verify agent_spawning_limits structure
    assert result["agent_spawning_limits"]["max_agent_types"] == 8
    assert result["agent_spawning_limits"]["max_instances_per_type"] == "unlimited"

    # Verify context_management structure
    assert result["context_management"]["context_budget"] == 150000
    assert result["context_management"]["warning_threshold"] == 0.8

    # Cleanup
    await db_manager.close_async()


@pytest.mark.asyncio
async def test_cli_mode_excludes_multi_terminal_rules():
    """Integration test: verify multi_terminal_mode_rules is None in CLI mode."""
    # Setup database
    config = get_config()
    db_url = config.database.database_url
    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    tenant_key = f"test-tenant-{uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=uuid4(),
            name="Test Product CLI",
            description="Test product for CLI mode",
            tenant_key=tenant_key,
        )
        session.add(product)

        # Create project with CLI mode
        project = Project(
            id=uuid4(),
            name="Test Project CLI",
            description="Test project with CLI execution mode",
            product_id=product.id,
            tenant_key=tenant_key,
            execution_mode="claude_code_cli",  # CLI mode
        )
        session.add(project)

        # Create orchestrator job
        orchestrator = AgentExecution(
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator CLI",
            status="pending",
            project_id=project.id,
            tenant_key=tenant_key,
            context_budget=200000,
            context_used=0,
            mission="Test mission for CLI mode",
        )
        session.add(orchestrator)
        await session.commit()

        # Call get_orchestrator_instructions
        result = await get_orchestrator_instructions(
            orchestrator_id=orchestrator.job_id,
            tenant_key=tenant_key,
            db_manager=db_manager,
        )

    # Verify multi_terminal_mode_rules is None in CLI mode
    assert result["multi_terminal_mode_rules"] is None

    # Verify other fields are still present
    assert "post_staging_behavior" in result
    assert "required_final_action" in result
    assert "error_handling" in result
    assert "agent_spawning_limits" in result
    assert "context_management" in result

    # Verify context_management uses orchestrator's budget
    assert result["context_management"]["context_budget"] == 200000

    # Cleanup
    await db_manager.close_async()
