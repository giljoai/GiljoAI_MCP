"""
Integration tests for multi-terminal template injection (Handover 0417).

Tests end-to-end flow of template injection when spawning agents
in multi-terminal mode through OrchestrationService.
"""

import pytest
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models import Project, AgentTemplate, Product


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_multi_terminal_spawn_with_template_injection(
    db_manager, tenant_manager, test_user
):
    """
    End-to-end test: Spawn agent in multi-terminal mode with template injection.

    Flow:
    1. Create product and project (multi-terminal mode)
    2. Create agent template
    3. Spawn agent via OrchestrationService
    4. Verify AgentJob.mission contains template + work
    5. Verify get_agent_mission() returns full content
    """
    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            name="Test Product",
            description="Integration test product",
        )
        session.add(product)

        # Create project in multi-terminal mode
        project = Project(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="Integration Test Project",
            description="Test project for template injection",
            mission="Test mission for multi-terminal spawn",  # Required NOT NULL column
            status="active",
            execution_mode="multi_terminal",
        )
        session.add(project)

        # Create agent template
        content = """# Integration Tester Agent

You are a specialist in integration testing.

## Core Responsibilities
- Design end-to-end test scenarios
- Validate system integration points
- Ensure data flow correctness

## Testing Approach
- Use real database connections
- Test actual API endpoints
- Verify business logic flows

## Success Criteria
- All integration tests pass
- System components integrate correctly
- No data corruption or leaks
"""
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            name="integration-tester",
            category="tester",
            role="Integration Tester",
            description="Test agent for integration testing",
            system_instructions=content,
            user_instructions="",
            cli_tool="claude-code",
            is_active=True,
        )
        session.add(template)

        await session.commit()
        await session.refresh(product)
        await session.refresh(project)
        await session.refresh(template)

    # Create service
    service = OrchestrationService(db_manager, tenant_manager)

    # Spawn agent
    result = await service.spawn_agent_job(
        agent_display_name="tester",
        agent_name="integration-tester",
        mission="Test the authentication flow end-to-end",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
    )

    # Verify spawn succeeded
    assert result["success"] is True
    assert "job_id" in result
    assert "agent_id" in result
    job_id = result["job_id"]

    # Verify mission was injected
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        from src.giljo_mcp.models import AgentJob

        result_query = await session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id)
        )
        agent_job = result_query.scalar_one()

        # Verify tidy framing headers (Handover 0417)
        assert "AGENT EXPERTISE & PROTOCOL" in agent_job.mission
        assert "YOUR ASSIGNED WORK" in agent_job.mission

        # Verify template content is present
        assert "Integration Tester Agent" in agent_job.mission
        assert "Core Responsibilities" in agent_job.mission
        assert "Testing Approach" in agent_job.mission
        assert "Success Criteria" in agent_job.mission

        # Verify work assignment is present
        assert "Test the authentication flow end-to-end" in agent_job.mission

        # Verify order: tidy framing header → template → work section → work
        expertise_header_index = agent_job.mission.index("AGENT EXPERTISE & PROTOCOL")
        template_index = agent_job.mission.index("Integration Tester Agent")
        work_section_index = agent_job.mission.index("YOUR ASSIGNED WORK")
        work_index = agent_job.mission.index("Test the authentication flow end-to-end")
        assert expertise_header_index < template_index < work_section_index < work_index


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_cli_mode_no_injection(db_manager, tenant_manager, test_user):
    """
    End-to-end test: Spawn agent in CLI mode without template injection.

    Flow:
    1. Create product and project (CLI mode)
    2. Create agent template (exists but not injected)
    3. Spawn agent via OrchestrationService
    4. Verify AgentJob.mission contains ONLY work (no template)
    """
    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            name="CLI Test Product",
            description="CLI mode integration test product",
        )
        session.add(product)

        # Create project in CLI mode
        project = Project(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="CLI Integration Test Project",
            description="Test project for CLI mode",
            mission="Test mission for CLI mode",  # Required NOT NULL column
            status="active",
            execution_mode="claude_code_cli",  # CLI mode
        )
        session.add(project)

        # Create agent template (exists but shouldn't be injected)
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            name="cli-tester",
            category="tester",
            role="CLI Tester",
            description="Test agent for CLI mode",
            system_instructions="# CLI Tester\n\nThis should NOT be injected.",
            user_instructions="",
            system_instructions="# CLI Tester\n\nThis should NOT be injected.",  # Required NOT NULL column
            cli_tool="claude-code",
            is_active=True,
        )
        session.add(template)

        await session.commit()
        await session.refresh(product)
        await session.refresh(project)
        await session.refresh(template)

    # Create service
    service = OrchestrationService(db_manager, tenant_manager)

    # Spawn agent
    result = await service.spawn_agent_job(
        agent_display_name="tester",
        agent_name="cli-tester",
        mission="Test CLI mode behavior",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
    )

    # Verify spawn succeeded
    assert result["success"] is True
    job_id = result["job_id"]

    # Verify mission was NOT injected
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        from src.giljo_mcp.models import AgentJob

        result_query = await session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id)
        )
        agent_job = result_query.scalar_one()

        # Verify NO template content
        assert "CLI Tester" not in agent_job.mission
        assert "should NOT be injected" not in agent_job.mission

        # Verify work assignment is present (may have Serena notice prepended)
        assert "Test CLI mode behavior" in agent_job.mission

        # Verify NO template framing headers (multi-terminal mode markers)
        assert "AGENT EXPERTISE & PROTOCOL" not in agent_job.mission
        assert "YOUR ASSIGNED WORK" not in agent_job.mission
