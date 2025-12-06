"""
Comprehensive integration tests for Orchestrator Routing Logic (Handover 0045 - Phase 3).

Tests intelligent routing of agents to Claude Code OR Codex/Gemini based on template.tool field.
Validates Agent-Job record synchronization, template resolution cascade, and multi-tenant isolation.

Coverage target: >90%
"""

import pytest

from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.enums import AgentRole, ProjectStatus
from src.giljo_mcp.models import AgentTemplate, MCPAgentJob, Project
from src.giljo_mcp.orchestrator import ProjectOrchestrator


@pytest.fixture
def db_manager():
    """Database manager fixture."""
    return get_db_manager()


@pytest.fixture
async def test_project(db_manager):
    """Create test project."""
    async with db_manager.get_session_async() as session:
        project = Project(
            tenant_key="test-tenant-123",
            name="Test Project",
            mission="Test mission",
            status=ProjectStatus.ACTIVE.value,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        yield project


@pytest.fixture
async def claude_template(db_manager):
    """Create Claude Code template."""
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            tenant_key="test-tenant-123",
            name="implementer",
            role="implementer",
            category="development",
            template_content="You are an implementer agent.",
            tool="claude",
            is_active=True,
            is_default=False,
            behavioral_rules=["Write clean code", "Follow TDD"],
            success_criteria=["All tests pass", "Code reviewed"],
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        yield template


@pytest.fixture
async def codex_template(db_manager):
    """Create Codex template."""
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            tenant_key="test-tenant-123",
            name="tester",
            role="tester",
            category="testing",
            template_content="You are a tester agent.",
            tool="codex",
            is_active=True,
            is_default=False,
            behavioral_rules=["Write comprehensive tests"],
            success_criteria=["95% coverage"],
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        yield template


@pytest.fixture
async def gemini_template(db_manager):
    """Create Gemini template."""
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            tenant_key="test-tenant-123",
            name="reviewer",
            role="reviewer",
            category="quality",
            template_content="You are a reviewer agent.",
            tool="gemini",
            is_active=True,
            is_default=False,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        yield template


@pytest.fixture
def orchestrator():
    """ProjectOrchestrator fixture."""
    return ProjectOrchestrator()


# ========================================================================
# TEMPLATE RESOLUTION TESTS
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_template_tenant_specific(orchestrator, claude_template):
    """Test template resolution returns tenant-specific template."""
    template = await orchestrator._get_agent_template(
        role="implementer",
        tenant_key="test-tenant-123",
    )

    assert template is not None
    assert template.id == claude_template.id
    assert template.role == "implementer"
    assert template.tool == "claude"


@pytest.mark.asyncio
async def test_get_agent_template_product_specific(db_manager, orchestrator):
    """Test template resolution prefers product-specific over tenant-specific."""
    async with db_manager.get_session_async() as session:
        # Create tenant-specific template
        tenant_template = AgentTemplate(
            tenant_key="test-tenant-123",
            name="implementer",
            role="implementer",
            category="development",
            template_content="Tenant template",
            tool="claude",
            is_active=True,
            product_id=None,
        )
        session.add(tenant_template)

        # Create product-specific template (should win)
        product_template = AgentTemplate(
            tenant_key="test-tenant-123",
            name="implementer",
            role="implementer",
            category="development",
            template_content="Product template",
            tool="codex",
            is_active=True,
            product_id="product-123",
        )
        session.add(product_template)
        await session.commit()
        await session.refresh(product_template)

        # Query with product_id
        template = await orchestrator._get_agent_template(
            role="implementer",
            tenant_key="test-tenant-123",
            product_id="product-123",
        )

        assert template is not None
        assert template.id == product_template.id
        assert template.product_id == "product-123"
        assert template.tool == "codex"


@pytest.mark.asyncio
async def test_get_agent_template_system_default(db_manager, orchestrator):
    """Test template resolution falls back to system default."""
    async with db_manager.get_session_async() as session:
        # Create system default template
        default_template = AgentTemplate(
            tenant_key="system",
            name="analyzer",
            role="analyzer",
            category="analysis",
            template_content="Default analyzer",
            tool="claude",
            is_active=True,
            is_default=True,
        )
        session.add(default_template)
        await session.commit()
        await session.refresh(default_template)

        # Query for role with no tenant-specific template
        template = await orchestrator._get_agent_template(
            role="analyzer",
            tenant_key="test-tenant-123",
        )

        assert template is not None
        assert template.is_default is True
        assert template.role == "analyzer"


@pytest.mark.asyncio
async def test_get_agent_template_not_found(orchestrator):
    """Test template resolution returns None if no template found."""
    template = await orchestrator._get_agent_template(
        role="nonexistent-role",
        tenant_key="test-tenant-123",
    )

    assert template is None


@pytest.mark.asyncio
async def test_get_agent_template_multi_tenant_isolation(db_manager, orchestrator):
    """Test templates are isolated by tenant."""
    async with db_manager.get_session_async() as session:
        # Create template for tenant A
        template_a = AgentTemplate(
            tenant_key="tenant-a",
            name="implementer",
            role="implementer",
            category="development",
            template_content="Tenant A template",
            tool="claude",
            is_active=True,
        )
        session.add(template_a)
        await session.commit()

        # Query from tenant B should not find tenant A's template
        template = await orchestrator._get_agent_template(
            role="implementer",
            tenant_key="tenant-b",
        )

        assert template is None


# ========================================================================
# CLAUDE CODE AGENT SPAWNING TESTS
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_claude_code_agent_creates_agent(orchestrator, test_project, claude_template):
    """Test Claude Code agent spawning creates MCPAgentJob record."""
    job = await orchestrator._spawn_claude_code_agent(
        project=test_project,
        role=AgentRole.IMPLEMENTER,
        template=claude_template,
    )

    assert job is not None
    assert job.tool_type == "claude"
    assert job.agent_type == "implementer"
    assert job.status == "active"
    assert job.job_id is not None  # Job ID always exists in MCPAgentJob
    assert job.tenant_key == test_project.tenant_key
    assert job.project_id == test_project.id


@pytest.mark.asyncio
async def test_spawn_claude_code_agent_includes_mcp_instructions(orchestrator, test_project, claude_template):
    """Test Claude Code agent mission includes MCP coordination protocol."""
    job = await orchestrator._spawn_claude_code_agent(
        project=test_project,
        role=AgentRole.IMPLEMENTER,
        template=claude_template,
    )

    # Verify mission includes MCP instructions
    assert "MCP Coordination Protocol" in job.mission
    assert "acknowledge_job" in job.mission
    assert "report_progress" in job.mission
    assert "complete_job" in job.mission
    assert test_project.tenant_key in job.mission


@pytest.mark.asyncio
async def test_spawn_claude_code_agent_stores_metadata(orchestrator, test_project, claude_template):
    """Test Claude Code agent stores template metadata."""
    job = await orchestrator._spawn_claude_code_agent(
        project=test_project,
        role=AgentRole.IMPLEMENTER,
        template=claude_template,
    )

    assert job.job_metadata["template_id"] == claude_template.id
    assert job.job_metadata["template_name"] == claude_template.name
    assert job.job_metadata["tool"] == "claude"
    # Auto-export removed (Handover 0074): orchestrator no longer writes files.
    # Ensure core template metadata preserved without exported_path.
    assert "template_id" in job.job_metadata
    assert "template_name" in job.job_metadata
    assert "tool" in job.job_metadata


# ========================================================================
# GENERIC AGENT SPAWNING TESTS (Codex/Gemini)
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_generic_agent_creates_job(orchestrator, test_project, codex_template, db_manager):
    """Test generic agent spawning creates MCP job."""
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.TESTER,
        template=codex_template,
    )

    # Verify job was created
    assert job.job_id is not None

    # Query job from database to verify persistence
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job.job_id)
        result = await session.execute(stmt)
        db_job = result.scalar_one_or_none()

        assert db_job is not None
        assert db_job.agent_type == "tester"
        assert db_job.status == "pending"
        assert db_job.tenant_key == test_project.tenant_key


@pytest.mark.asyncio
async def test_spawn_generic_agent_links_agent_to_job(orchestrator, test_project, codex_template):
    """Test generic agent job has correct tool type and status."""
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.TESTER,
        template=codex_template,
    )

    assert job.tool_type == "codex"
    assert job.job_id is not None
    assert job.status == "waiting"


@pytest.mark.asyncio
async def test_spawn_generic_agent_generates_cli_prompt(orchestrator, test_project, gemini_template):
    """Test generic agent generates CLI prompt in metadata."""
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.REVIEWER,
        template=gemini_template,
    )

    assert "cli_prompt" in job.job_metadata
    cli_prompt = job.job_metadata["cli_prompt"]

    # Verify CLI prompt structure
    assert "Job Information" in cli_prompt
    assert job.job_id in cli_prompt
    assert "Getting Started" in cli_prompt
    assert "acknowledge_job" in cli_prompt
    assert test_project.tenant_key in cli_prompt


@pytest.mark.asyncio
async def test_spawn_generic_agent_includes_behavioral_rules(orchestrator, test_project, codex_template):
    """Test generic agent CLI prompt includes behavioral rules."""
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.TESTER,
        template=codex_template,
    )

    cli_prompt = job.job_metadata["cli_prompt"]
    assert "Behavioral Rules" in cli_prompt
    assert "Write comprehensive tests" in cli_prompt


# ========================================================================
# SPAWN_AGENT ROUTING TESTS
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_routes_to_claude_code(orchestrator, test_project, claude_template, db_manager):
    """Test spawn_agent routes to Claude Code when template.tool='claude'."""
    job = await orchestrator.spawn_agent(
        project_id=test_project.id,
        role=AgentRole.IMPLEMENTER,
    )

    assert job.tool_type == "claude"
    assert job.job_id is not None
    assert job.status == "active"


@pytest.mark.asyncio
async def test_spawn_agent_routes_to_codex(orchestrator, test_project, codex_template, db_manager):
    """Test spawn_agent routes to Codex when template.tool='codex'."""
    job = await orchestrator.spawn_agent(
        project_id=test_project.id,
        role=AgentRole.TESTER,
    )

    assert job.tool_type == "codex"
    assert job.job_id is not None
    assert job.status == "waiting"


@pytest.mark.asyncio
async def test_spawn_agent_routes_to_gemini(orchestrator, test_project, gemini_template, db_manager):
    """Test spawn_agent routes to Gemini when template.tool='gemini'."""
    job = await orchestrator.spawn_agent(
        project_id=test_project.id,
        role=AgentRole.REVIEWER,
    )

    assert job.tool_type == "gemini"
    assert job.job_id is not None
    assert job.status == "waiting"


@pytest.mark.asyncio
async def test_spawn_agent_fallback_when_no_template(orchestrator, test_project, db_manager):
    """Test spawn_agent falls back to legacy logic when no template found."""
    # Spawn agent for role with no template
    job = await orchestrator.spawn_agent(
        project_id=test_project.id,
        role=AgentRole.ANALYZER,
    )

    assert job is not None
    assert job.tool_type == "claude"  # Default fallback
    assert job.status == "active"


# ========================================================================
# JOB STATUS TRANSITION TESTS (Agent table removed)
# ========================================================================


@pytest.mark.asyncio
async def test_acknowledge_job_transitions_status(orchestrator, test_project, codex_template, db_manager):
    """Test acknowledge_job transitions MCPAgentJob status to active."""
    from src.giljo_mcp.tools.agent_coordination import register_agent_coordination_tools

    # Spawn generic agent (creates MCPAgentJob)
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.TESTER,
        template=codex_template,
    )

    # Persist job
    async with db_manager.get_session_async() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)

    # Register MCP tools
    tools = {}
    register_agent_coordination_tools(tools, db_manager)

    # Acknowledge job
    result = tools["acknowledge_job"](
        job_id=job.job_id,
        agent_id="tester",
        tenant_key=test_project.tenant_key,
    )

    assert result["status"] == "success"

    # Verify MCPAgentJob status transitioned to active
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job.job_id)
        result = await session.execute(stmt)
        updated_job = result.scalar_one()

        assert updated_job.status == "active"


@pytest.mark.asyncio
async def test_complete_job_transitions_status(orchestrator, test_project, codex_template, db_manager):
    """Test complete_job transitions MCPAgentJob status to complete."""
    from src.giljo_mcp.tools.agent_coordination import register_agent_coordination_tools

    # Spawn and persist job
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.TESTER,
        template=codex_template,
    )

    async with db_manager.get_session_async() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)

    # Register tools and acknowledge job first
    tools = {}
    register_agent_coordination_tools(tools, db_manager)
    tools["acknowledge_job"](
        job_id=job.job_id,
        agent_id="tester",
        tenant_key=test_project.tenant_key,
    )

    # Complete job
    result = tools["complete_job"](
        job_id=job.job_id,
        result={"summary": "All tests passing", "coverage": "95%"},
        tenant_key=test_project.tenant_key,
    )

    assert result["status"] == "success"

    # Verify MCPAgentJob status transitioned to complete
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job.job_id)
        result = await session.execute(stmt)
        updated_job = result.scalar_one()

        assert updated_job.status == "complete"


@pytest.mark.asyncio
async def test_report_error_transitions_status(orchestrator, test_project, codex_template, db_manager):
    """Test report_error transitions MCPAgentJob status to failed."""
    from src.giljo_mcp.tools.agent_coordination import register_agent_coordination_tools

    # Spawn and persist job
    job = await orchestrator._spawn_generic_agent(
        project=test_project,
        role=AgentRole.TESTER,
        template=codex_template,
    )

    async with db_manager.get_session_async() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)

    # Register tools and acknowledge job
    tools = {}
    register_agent_coordination_tools(tools, db_manager)
    tools["acknowledge_job"](
        job_id=job.job_id,
        agent_id="tester",
        tenant_key=test_project.tenant_key,
    )

    # Report error
    result = tools["report_error"](
        job_id=job.job_id,
        error_type="test_failure",
        error_message="Test suite failed",
        context="Running integration tests",
        tenant_key=test_project.tenant_key,
    )

    assert result["status"] == "success"

    # Verify MCPAgentJob status transitioned to failed
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job.job_id)
        result = await session.execute(stmt)
        updated_job = result.scalar_one()

        assert updated_job.status == "failed"


# ========================================================================
# MCP INSTRUCTION GENERATION TESTS
# ========================================================================


def test_generate_mcp_instructions_includes_required_tools(orchestrator):
    """Test MCP instructions include all required tools."""
    instructions = orchestrator._generate_mcp_instructions(
        tenant_key="test-tenant-123",
        agent_role="implementer",
    )

    assert "acknowledge_job" in instructions
    assert "report_progress" in instructions
    assert "complete_job" in instructions
    assert "report_error" in instructions
    assert "get_next_instruction" in instructions


def test_generate_mcp_instructions_includes_tenant_key(orchestrator):
    """Test MCP instructions include tenant_key in examples."""
    tenant_key = "test-tenant-456"
    instructions = orchestrator._generate_mcp_instructions(
        tenant_key=tenant_key,
        agent_role="tester",
    )

    assert tenant_key in instructions
    assert 'tenant_key="test-tenant-456"' in instructions


# ========================================================================
# CLI PROMPT GENERATION TESTS
# ========================================================================


def test_generate_cli_prompt_includes_job_info(orchestrator, test_project, codex_template, db_manager):
    """Test CLI prompt includes job information."""
    # Create mock job
    job = MCPAgentJob(
        tenant_key=test_project.tenant_key,
        agent_type="tester",
        mission="Test mission",
        status="waiting",
    )

    cli_prompt = orchestrator._generate_cli_prompt(
        job=job,
        template=codex_template,
        project=test_project,
        tenant_key=test_project.tenant_key,
    )

    assert job.job_id in cli_prompt
    assert "tester" in cli_prompt
    assert test_project.name in cli_prompt


def test_generate_cli_prompt_copy_paste_ready(orchestrator, test_project, gemini_template, db_manager):
    """Test CLI prompt is copy-paste ready with all sections."""
    job = MCPAgentJob(
        tenant_key=test_project.tenant_key,
        agent_type="reviewer",
        mission="Review code",
        status="waiting",
    )

    cli_prompt = orchestrator._generate_cli_prompt(
        job=job,
        template=gemini_template,
        project=test_project,
        tenant_key=test_project.tenant_key,
    )

    # Verify all required sections
    assert "# " in cli_prompt  # Header
    assert "## Job Information" in cli_prompt
    assert "## Mission" in cli_prompt
    assert "## Getting Started" in cli_prompt
    assert "acknowledge_job" in cli_prompt
    assert "Copy this entire prompt" in cli_prompt


# ========================================================================
# MULTI-TENANT ISOLATION TESTS
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_respects_tenant_isolation(orchestrator, db_manager):
    """Test agent jobs can't access templates from other tenants."""
    async with db_manager.get_session_async() as session:
        # Create project for tenant A
        project_a = Project(
            tenant_key="tenant-a",
            name="Project A",
            mission="Mission A",
            status=ProjectStatus.ACTIVE.value,
        )
        session.add(project_a)

        # Create template for tenant B (different tenant)
        template_b = AgentTemplate(
            tenant_key="tenant-b",
            name="implementer",
            role="implementer",
            category="development",
            template_content="Tenant B template",
            tool="claude",
            is_active=True,
        )
        session.add(template_b)
        await session.commit()
        await session.refresh(project_a)

        # Try to spawn agent for tenant A (should not use tenant B's template)
        job = await orchestrator.spawn_agent(
            project_id=project_a.id,
            role=AgentRole.IMPLEMENTER,
        )

        # Should fall back to legacy logic (no template found)
        assert job is not None
        # Should NOT use tenant B's template
        assert job.job_metadata.get("template_id") != template_b.id


# ========================================================================
# EDGE CASE TESTS
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_handles_missing_project(orchestrator):
    """Test spawn_agent raises ValueError for nonexistent project."""
    with pytest.raises(ValueError, match="Project .* not found"):
        await orchestrator.spawn_agent(
            project_id="nonexistent-project-id",
            role=AgentRole.IMPLEMENTER,
        )


@pytest.mark.asyncio
async def test_spawn_agent_with_custom_mission(orchestrator, test_project, claude_template):
    """Test spawn_agent accepts custom mission override."""
    custom_mission = "Custom mission for agent"

    job = await orchestrator.spawn_agent(
        project_id=test_project.id,
        role=AgentRole.IMPLEMENTER,
        custom_mission=custom_mission,
    )

    assert custom_mission in job.mission


@pytest.mark.asyncio
async def test_template_resolution_inactive_templates_ignored(db_manager, orchestrator):
    """Test inactive templates are not returned."""
    async with db_manager.get_session_async() as session:
        # Create inactive template
        inactive_template = AgentTemplate(
            tenant_key="test-tenant-123",
            name="implementer",
            role="implementer",
            category="development",
            template_content="Inactive template",
            tool="claude",
            is_active=False,  # INACTIVE
        )
        session.add(inactive_template)
        await session.commit()

        # Should not find inactive template
        template = await orchestrator._get_agent_template(
            role="implementer",
            tenant_key="test-tenant-123",
        )

        assert template is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.giljo_mcp.orchestrator", "--cov-report=term-missing"])
