"""
Tests for Handover 0383: Spawn Response Task Tool Clarity

Validates that spawn_agent_job response includes:
1. task_tool_usage field with correct Task tool example
2. Warning when agent_name != agent_display_name
3. No warning when agent_name == agent_display_name
"""

import pytest
from uuid import uuid4

from src.giljo_mcp.models import Project, AgentTemplate


@pytest.mark.asyncio
async def test_spawn_response_includes_task_tool_usage(db_session, db_manager):
    """Option B: Response includes explicit Task tool example."""
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_0383"
    project_id = str(uuid4())

    # Create project (foreign key requirement)
    project = Project(
        id=project_id,
        name="Test Project 0383",
        description="Test project for spawn clarity",
        mission="Test mission",
        tenant_key=tenant_key,
        status="staging",
    )
    db_session.add(project)

    # Create agent template (Handover 0351: required for validation)
    template = AgentTemplate(
        id=str(uuid4()),
        name="implementer-frontend",  # Must match agent_name
        role="Frontend Implementer",
        description="Implements frontend components",
        tenant_key=tenant_key,
        product_id=None,
        is_active=True,
        version="1.0.0",
        system_instructions="# Frontend Implementer\n\nBuilds frontend."
    )
    db_session.add(template)
    await db_session.commit()

    # Spawn agent with different name/type
    result = await spawn_agent_job(
        agent_display_name="implementer",
        agent_name="implementer-frontend",
        mission="Build frontend components",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session,
    )

    # Verify task_tool_usage field exists
    assert "task_tool_usage" in result, "Response must include task_tool_usage field"

    # Verify it uses agent_name (not agent_display_name)
    expected_usage = "Task(subagent_type='implementer-frontend', ...)"
    assert result["task_tool_usage"] == expected_usage, (
        f"task_tool_usage should use agent_name. "
        f"Expected: {expected_usage}, Got: {result['task_tool_usage']}"
    )


@pytest.mark.asyncio
async def test_spawn_response_warning_when_names_differ(db_session, db_manager):
    """Option C: Warning shown when agent_name != agent_display_name."""
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_0383_warn"
    project_id = str(uuid4())

    # Create project
    project = Project(
        id=project_id,
        name="Test Project Warning",
        description="Test project for warning tests",
        mission="Test mission",
        tenant_key=tenant_key,
        status="staging",
    )
    db_session.add(project)

    # Create agent template
    template = AgentTemplate(
        id=str(uuid4()),
        name="implementer-frontend",
        role="Frontend Implementer",
        description="Implements frontend components",
        tenant_key=tenant_key,
        product_id=None,
        is_active=True,
        version="1.0.0",
        system_instructions="# Frontend Implementer\n\nBuilds frontend."
    )
    db_session.add(template)
    await db_session.commit()

    # Spawn agent with different name/type
    result = await spawn_agent_job(
        agent_display_name="implementer",
        agent_name="implementer-frontend",  # Different from agent_display_name!
        mission="Build frontend components",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session,
    )

    # Verify warning field exists
    assert "warning" in result, "Response must include warning when agent_name != agent_display_name"

    # Verify warning content mentions both fields
    warning = result["warning"]
    assert "agent_name" in warning, "Warning should mention agent_name"
    assert "agent_display_name" in warning, "Warning should mention agent_display_name"
    assert "implementer-frontend" in warning, "Warning should include actual agent_name value"
    assert "implementer" in warning, "Warning should include actual agent_display_name value"
    assert "MUST use agent_name" in warning, "Warning should emphasize using agent_name"


@pytest.mark.asyncio
async def test_spawn_response_no_warning_when_names_match(db_session, db_manager):
    """No warning when agent_name == agent_display_name."""
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_0383_nowarn"
    project_id = str(uuid4())

    # Create project
    project = Project(
        id=project_id,
        name="Test Project No Warning",
        description="Test project for no-warning tests",
        mission="Test mission",
        tenant_key=tenant_key,
        status="staging",
    )
    db_session.add(project)

    # Create agent template with matching name
    template = AgentTemplate(
        id=str(uuid4()),
        name="analyzer",  # Same as agent_display_name
        role="Code Analyzer",
        description="Analyzes codebase",
        tenant_key=tenant_key,
        product_id=None,
        is_active=True,
        version="1.0.0",
        system_instructions="# Analyzer\n\nAnalyzes code."
    )
    db_session.add(template)
    await db_session.commit()

    # Spawn agent with matching name/type
    result = await spawn_agent_job(
        agent_display_name="analyzer",
        agent_name="analyzer",  # Same as agent_display_name!
        mission="Analyze codebase",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session,
    )

    # Verify NO warning field when names match
    assert "warning" not in result, (
        "Response should NOT include warning when agent_name == agent_display_name. "
        f"Got warning: {result.get('warning')}"
    )

    # But task_tool_usage should still be present
    assert "task_tool_usage" in result, "task_tool_usage should always be present"
    assert result["task_tool_usage"] == "Task(subagent_type='analyzer', ...)"


@pytest.mark.asyncio
async def test_spawn_response_preserves_existing_fields(db_session, db_manager):
    """Verify new fields don't break existing response structure."""
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_0383_existing"
    project_id = str(uuid4())

    # Create project
    project = Project(
        id=project_id,
        name="Test Project Existing Fields",
        description="Test project for existing fields",
        mission="Test mission",
        tenant_key=tenant_key,
        status="staging",
    )
    db_session.add(project)

    # Create agent template
    template = AgentTemplate(
        id=str(uuid4()),
        name="backend-tester",
        role="Backend Tester",
        description="Tests backend code",
        tenant_key=tenant_key,
        product_id=None,
        is_active=True,
        version="1.0.0",
        system_instructions="# Backend Tester\n\nTests backend."
    )
    db_session.add(template)
    await db_session.commit()

    # Spawn agent
    result = await spawn_agent_job(
        agent_display_name="tester",
        agent_name="backend-tester",
        mission="Run backend tests",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session,
    )

    # Verify all existing fields are still present
    assert result["success"] is True, "Response must include success field"
    assert "job_id" in result, "Response must include job_id"
    assert "agent_id" in result, "Response must include agent_id"
    assert "agent_prompt" in result, "Response must include agent_prompt"
    assert "prompt_tokens" in result, "Response must include prompt_tokens"
    assert "mission_tokens" in result, "Response must include mission_tokens"

    # Verify new fields are present
    assert "task_tool_usage" in result, "Response must include task_tool_usage"
    assert "warning" in result, "Response should include warning (names differ)"


@pytest.mark.asyncio
async def test_task_tool_usage_format_is_correct(db_session, db_manager):
    """Verify task_tool_usage follows correct format."""
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    test_cases = [
        ("backend-tester", "backend-tester", "Task(subagent_type='backend-tester', ...)", False),
        ("implementer", "frontend-dev", "Task(subagent_type='frontend-dev', ...)", True),
        ("analyzer", "code-reviewer", "Task(subagent_type='code-reviewer', ...)", True),
    ]

    for idx, (agent_display_name, agent_name, expected_usage, should_warn) in enumerate(test_cases):
        # Setup unique project for each test case
        tenant_key = f"test_tenant_0383_format_{idx}"
        project_id = str(uuid4())

        project = Project(
            id=project_id,
            name=f"Test Project Format {idx}",
            description="Test project for format tests",
            mission="Test mission",
            tenant_key=tenant_key,
            status="staging",
        )
        db_session.add(project)

        # Create agent template
        template = AgentTemplate(
            id=str(uuid4()),
            name=agent_name,  # Must match agent_name parameter
            role=f"Test Role {idx}",
            description=f"Test description {idx}",
            tenant_key=tenant_key,
            product_id=None,
            is_active=True,
            version="1.0.0",
            system_instructions=f"# {agent_name}\n\nTest template."
        )
        db_session.add(template)
        await db_session.commit()

        # Spawn agent
        result = await spawn_agent_job(
            agent_display_name=agent_display_name,
            agent_name=agent_name,
            mission=f"Mission for {agent_name}",
            project_id=project_id,
            tenant_key=tenant_key,
            session=db_session,
        )

        # Verify task_tool_usage format
        assert result["task_tool_usage"] == expected_usage, (
            f"For agent_name='{agent_name}', expected: {expected_usage}, "
            f"got: {result['task_tool_usage']}"
        )

        # Verify warning presence
        if should_warn:
            assert "warning" in result, f"Expected warning for {agent_name} != {agent_display_name}"
        else:
            assert "warning" not in result, f"Did not expect warning for {agent_name} == {agent_display_name}"
