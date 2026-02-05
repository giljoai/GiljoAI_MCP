"""
Unit tests for template injection in spawn_agent_job (Handover 0417).

Tests backend auto-injection of agent templates for multi-terminal mode.
When spawn_agent_job() is called in multi-terminal mode, backend should
inject template content into AgentJob.mission.

Test Coverage:
1. Multi-terminal mode injects template
2. CLI mode does not inject
3. Template lookup uses agent_name
4. Missing template logs warning but proceeds
5. Injected mission structure is correct
6. Full mission contains template + work
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, mock_open
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models import Project, AgentTemplate, AgentJob


@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Create mock tenant manager."""
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
    return tenant_manager


@pytest.fixture
def mock_config_no_serena():
    """Mock config file to disable Serena instructions."""
    config_data = """
features:
  serena_mcp:
    use_in_prompts: false
"""
    with patch("builtins.open", mock_open(read_data=config_data)):
        with patch("pathlib.Path.exists", return_value=True):
            yield


@pytest.fixture
def sample_project():
    """Create sample project for testing."""
    return Project(
        id=str(uuid4()),
        tenant_key="test-tenant",
        product_id=str(uuid4()),
        name="Test Project",
        description="Test project description",
        status="active",
        execution_mode="multi_terminal",  # Default to multi-terminal
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_template():
    """Create sample agent template for testing."""
    return AgentTemplate(
        id=str(uuid4()),
        tenant_key="test-tenant",
        name="tdd-implementor",
        category="implementer",
        role="TDD Implementor",
        description="Master developer following TDD",
        system_instructions="""# TDD Implementor Agent

You are a master developer who follows strict test-driven development principles.

## CRITICAL: MCP TOOLS ARE NATIVE TOOL CALLS
[MCP usage instructions...]

## MCP TOOL SUMMARY
[Tool reference...]

## CHECK-IN PROTOCOL
[Check-in instructions...]

## INTER-AGENT MESSAGING PROTOCOL
[Messaging protocol...]

---

## Role-Specific Instructions
You implement features following TDD workflow:
1. Write tests first (RED)
2. Write minimal code to pass (GREEN)
3. Refactor and optimize (REFACTOR)

## Behavioral Rules
- Never skip tests
- Follow project coding standards
- Use cross-platform patterns

## Success Criteria
- All tests pass
- Code follows standards
- Implementation complete
""",
        user_instructions="",
        # Using system_instructions field
        cli_tool="claude-code",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_spawn_agent_job_injects_template_for_multi_terminal_mode(
    mock_db_manager, mock_tenant_manager, mock_config_no_serena, sample_project, sample_template
):
    """
    Test that spawn_agent_job injects template content in multi-terminal mode.

    Scenario:
    - Project execution_mode = "multi_terminal"
    - AgentTemplate exists for agent_name
    - AgentJob.mission should contain template + work
    """
    db_manager, session = mock_db_manager

    # Mock database queries
    project_result = AsyncMock()
    project_result.scalar_one_or_none = Mock(return_value=sample_project)

    template_result = AsyncMock()
    template_result.scalar_one_or_none = Mock(return_value=sample_template)

    session.execute = AsyncMock(side_effect=[
        project_result,
        template_result,
    ])

    # Create service instance
    service = OrchestrationService(db_manager, mock_tenant_manager)

    # Call spawn_agent_job
    result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="tdd-implementor",
        mission="Implement feature X with comprehensive tests",
        project_id=sample_project.id,
        tenant_key="test-tenant",
    )

    # Verify success
    assert result["success"] is True
    assert "job_id" in result
    assert "agent_id" in result

    # Verify AgentJob was created with injected template
    job_add_calls = [call for call in session.add.call_args_list if isinstance(call[0][0], AgentJob)]
    assert len(job_add_calls) == 1

    agent_job = job_add_calls[0][0][0]
    assert "TDD Implementor Agent" in agent_job.mission  # Template content
    assert "AGENT EXPERTISE & PROTOCOL" in agent_job.mission  # Tidy framing header (0417)
    assert "YOUR ASSIGNED WORK" in agent_job.mission  # Tidy framing work section (0417)
    assert "Implement feature X with comprehensive tests" in agent_job.mission  # Work


@pytest.mark.asyncio
async def test_spawn_agent_job_no_injection_for_cli_mode(mock_config_no_serena, 
    mock_db_manager, mock_tenant_manager, sample_project
):
    """
    Test that spawn_agent_job does NOT inject template in CLI mode.

    Scenario:
    - Project execution_mode = "claude_code_cli"
    - AgentTemplate exists but should NOT be injected
    - AgentJob.mission should contain only the work assignment
    """
    db_manager, session = mock_db_manager

    # Set project to CLI mode
    sample_project.execution_mode = "claude_code_cli"

    # Mock database queries
    project_result = AsyncMock()
    project_result.scalar_one_or_none = Mock(return_value=sample_project)

    session.execute = AsyncMock(side_effect=[
        project_result,
        # No template query should be made in CLI mode
    ])

    # Create service instance
    service = OrchestrationService(db_manager, mock_tenant_manager)

    # Call spawn_agent_job
    result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="tdd-implementor",
        mission="Implement feature X with comprehensive tests",
        project_id=sample_project.id,
        tenant_key="test-tenant",
    )

    # Verify success
    assert result["success"] is True

    # Verify AgentJob was created WITHOUT template injection
    job_add_calls = [call for call in session.add.call_args_list if isinstance(call[0][0], AgentJob)]
    assert len(job_add_calls) == 1

    agent_job = job_add_calls[0][0][0]
    assert agent_job.mission == "Implement feature X with comprehensive tests"  # Only work, no template
    assert "TDD Implementor Agent" not in agent_job.mission  # No template content
    assert "YOUR ASSIGNED WORK:" not in agent_job.mission  # No separator


@pytest.mark.asyncio
async def test_template_lookup_uses_agent_name(mock_config_no_serena, 
    mock_db_manager, mock_tenant_manager, sample_project, sample_template
):
    """
    Test that template lookup uses agent_name, not agent_display_name.

    Scenario:
    - agent_display_name = "implementer" (category)
    - agent_name = "tdd-implementor" (template key)
    - Template lookup should use agent_name
    """
    db_manager, session = mock_db_manager

    # Mock database queries
    project_result = AsyncMock()
    project_result.scalar_one_or_none = Mock(return_value=sample_project)

    template_result = AsyncMock()
    template_result.scalar_one_or_none = Mock(return_value=sample_template)

    session.execute = AsyncMock(side_effect=[
        project_result,
        template_result,
    ])

    # Create service instance
    service = OrchestrationService(db_manager, mock_tenant_manager)

    # Call spawn_agent_job
    await service.spawn_agent_job(
        agent_display_name="implementer",  # Category (NOT used for lookup)
        agent_name="tdd-implementor",  # Template key (USED for lookup)
        mission="Test mission",
        project_id=sample_project.id,
        tenant_key="test-tenant",
    )

    # Verify that the second query (template lookup) was made
    assert session.execute.call_count == 2
    # Verify template was injected
    job_add_calls = [call for call in session.add.call_args_list if isinstance(call[0][0], AgentJob)]
    agent_job = job_add_calls[0][0][0]
    assert "TDD Implementor Agent" in agent_job.mission


@pytest.mark.asyncio
async def test_template_not_found_logs_warning_proceeds(mock_config_no_serena, 
    mock_db_manager, mock_tenant_manager, sample_project
):
    """
    Test that missing template logs warning but proceeds with orchestrator's mission.

    Scenario:
    - Project execution_mode = "multi_terminal"
    - AgentTemplate does NOT exist for agent_name
    - Should log warning
    - Should proceed with mission as-is (graceful degradation)
    """
    db_manager, session = mock_db_manager

    # Mock database queries
    project_result = AsyncMock()
    project_result.scalar_one_or_none = Mock(return_value=sample_project)

    # Template query returns None (not found)
    template_result = AsyncMock()
    template_result.scalar_one_or_none = Mock(return_value=None)

    session.execute = AsyncMock(side_effect=[
        project_result,
        template_result,
    ])

    # Create service instance
    service = OrchestrationService(db_manager, mock_tenant_manager)

    # Call spawn_agent_job
    result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="nonexistent-agent",
        mission="Test mission without template",
        project_id=sample_project.id,
        tenant_key="test-tenant",
    )

    # Verify success (graceful degradation)
    assert result["success"] is True

    # Verify AgentJob was created with mission as-is (no template)
    job_add_calls = [call for call in session.add.call_args_list if isinstance(call[0][0], AgentJob)]
    assert len(job_add_calls) == 1

    agent_job = job_add_calls[0][0][0]
    assert agent_job.mission == "Test mission without template"


@pytest.mark.asyncio
async def test_injected_mission_structure(mock_config_no_serena,
    mock_db_manager, mock_tenant_manager, sample_project, sample_template
):
    """
    Test that injected mission has correct tidy framing structure.

    Structure should be (Handover 0417 - tidy framing):
    ╔═════════════════════════════════════════════════════════════════════════╗
    ║                     AGENT EXPERTISE & PROTOCOL                           ║
    ╚═════════════════════════════════════════════════════════════════════════╝

    [Template content]

    ╔═════════════════════════════════════════════════════════════════════════╗
    ║                       YOUR ASSIGNED WORK                                 ║
    ╚═════════════════════════════════════════════════════════════════════════╝

    [Orchestrator's mission]
    """
    db_manager, session = mock_db_manager

    # Mock database queries
    project_result = AsyncMock()
    project_result.scalar_one_or_none = Mock(return_value=sample_project)

    template_result = AsyncMock()
    template_result.scalar_one_or_none = Mock(return_value=sample_template)

    session.execute = AsyncMock(side_effect=[
        project_result,
        template_result,
    ])

    # Create service instance
    service = OrchestrationService(db_manager, mock_tenant_manager)

    # Call spawn_agent_job
    await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="tdd-implementor",
        mission="Specific work assignment",
        project_id=sample_project.id,
        tenant_key="test-tenant",
    )

    # Verify structure
    job_add_calls = [call for call in session.add.call_args_list if isinstance(call[0][0], AgentJob)]
    agent_job = job_add_calls[0][0][0]

    mission = agent_job.mission

    # Should start with tidy framing box header
    assert mission.startswith("╔")
    assert "AGENT EXPERTISE & PROTOCOL" in mission

    # Should contain template content after first header
    assert "# TDD Implementor Agent" in mission

    # Should contain work section header
    assert "YOUR ASSIGNED WORK" in mission

    # Should end with work assignment
    assert mission.endswith("Specific work assignment")


@pytest.mark.asyncio
async def test_full_mission_contains_template_plus_work(mock_config_no_serena,
    mock_db_manager, mock_tenant_manager, sample_project, sample_template
):
    """
    Test that full mission contains both template and work in correct order.

    Verifies:
    1. Template content is present
    2. Work assignment is present
    3. Order is correct (template first, then work)
    4. Tidy framing headers are present (Handover 0417)
    """
    db_manager, session = mock_db_manager

    # Mock database queries
    project_result = AsyncMock()
    project_result.scalar_one_or_none = Mock(return_value=sample_project)

    template_result = AsyncMock()
    template_result.scalar_one_or_none = Mock(return_value=sample_template)

    session.execute = AsyncMock(side_effect=[
        project_result,
        template_result,
    ])

    work_assignment = "Build authentication module with JWT tokens"

    # Create service instance
    service = OrchestrationService(db_manager, mock_tenant_manager)

    # Call spawn_agent_job
    await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="tdd-implementor",
        mission=work_assignment,
        project_id=sample_project.id,
        tenant_key="test-tenant",
    )

    # Get the created AgentJob
    job_add_calls = [call for call in session.add.call_args_list if isinstance(call[0][0], AgentJob)]
    agent_job = job_add_calls[0][0][0]

    mission = agent_job.mission

    # Verify tidy framing headers are present (Handover 0417)
    assert "AGENT EXPERTISE & PROTOCOL" in mission
    assert "YOUR ASSIGNED WORK" in mission

    # Verify template content is present
    assert "TDD Implementor Agent" in mission
    assert "MCP TOOLS ARE NATIVE TOOL CALLS" in mission
    assert "Role-Specific Instructions" in mission
    assert "Behavioral Rules" in mission
    assert "Success Criteria" in mission

    # Verify work assignment is present
    assert work_assignment in mission

    # Verify order: template content appears before work assignment
    template_index = mission.index("TDD Implementor Agent")
    work_section_index = mission.index("YOUR ASSIGNED WORK")
    work_index = mission.index(work_assignment)

    assert template_index < work_section_index < work_index
