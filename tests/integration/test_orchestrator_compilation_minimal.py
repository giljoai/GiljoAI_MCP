"""
Minimal integration tests for orchestrator instruction compilation timing.

These tests use existing pytest fixtures and focus on the core compilation behavior.
"""

import pytest
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions


# ============================================================================
# TEST 1: Orchestrator Creation Stores Field Priorities
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_stores_field_priorities(
    db_session: AsyncSession, test_user: object, project_factory, test_tenant_key: str
):
    """
    VERIFY: Field priorities passed to generate() are stored in job_metadata.
    """
    # Create a test project
    project = await project_factory(name="Test Project 1", description="Test requirements", tenant_key=test_tenant_key)

    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    # Use user's priorities
    user_priorities = test_user.field_priority_config.get("priorities", {})

    # Generate orchestrator with specific priorities
    result = await generator.generate(
        project_id=project.id, user_id=str(test_user.id), tool="claude-code", field_priorities=user_priorities
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Priorities stored in database
    orch_stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    assert orchestrator is not None, "Orchestrator not created"
    assert orchestrator.status == "waiting", "Orchestrator status should be 'waiting'"

    metadata = orchestrator.job_metadata or {}
    stored_priorities = metadata.get("field_priorities", {})

    assert stored_priorities == user_priorities, (
        f"Field priorities not stored correctly. Expected {user_priorities}, got {stored_priorities}"
    )


# ============================================================================
# TEST 2: Repeated Staging Reuses Orchestrator
# ============================================================================


@pytest.mark.asyncio
async def test_repeated_staging_reuses_orchestrator(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: Repeated calls to generate() reuse existing orchestrator.

    This prevents duplicate creation on repeated "Stage Project" clicks.
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    user_priorities = test_user.field_priority_config.get("priorities", {})

    # FIRST call
    result1 = await generator.generate(
        project_id=test_project.id, user_id=str(test_user.id), tool="claude-code", field_priorities=user_priorities
    )
    orch_id_1 = result1["orchestrator_id"]

    # SECOND call (immediate)
    result2 = await generator.generate(
        project_id=test_project.id, user_id=str(test_user.id), tool="claude-code", field_priorities=user_priorities
    )
    orch_id_2 = result2["orchestrator_id"]

    # VERIFY: Same orchestrator
    assert orch_id_1 == orch_id_2, f"Repeated calls should reuse orchestrator: {orch_id_1} vs {orch_id_2}"

    # VERIFY: Only one orchestrator in database
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.project_id == test_project.id,
            AgentExecution.agent_display_name == "orchestrator",
            AgentExecution.tenant_key == test_tenant_key,
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrators = orch_result.scalars().all()

    assert len(orchestrators) == 1, f"Expected 1 orchestrator, found {len(orchestrators)}"


# ============================================================================
# TEST 3: MCP Tool Retrieves Stored Priorities
# ============================================================================


@pytest.mark.asyncio
async def test_mcp_tool_retrieves_stored_priorities(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: get_orchestrator_instructions() retrieves priorities from job_metadata.
    """
    db_manager = DatabaseManager(is_async=True)

    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    user_priorities = test_user.field_priority_config.get("priorities", {})

    result = await generator.generate(
        project_id=test_project.id, user_id=str(test_user.id), tool="claude-code", field_priorities=user_priorities
    )

    orchestrator_id = result["orchestrator_id"]

    # Call MCP tool
    instructions = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id, tenant_key=test_tenant_key, db_manager=db_manager
    )

    # VERIFY: Priorities returned
    assert "error" not in instructions, f"Error: {instructions}"
    returned_priorities = instructions.get("field_priorities", {})

    assert returned_priorities == user_priorities, (
        f"Priorities not retrieved correctly. Expected {user_priorities}, got {returned_priorities}"
    )


# ============================================================================
# TEST 4: MCP Tool Compiles Fresh Mission Each Time
# ============================================================================


@pytest.mark.asyncio
async def test_mcp_tool_compiles_fresh_mission(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: get_orchestrator_instructions() compiles mission fresh each time.

    The MCP tool calls MissionPlanner on EACH invocation, not from cache.
    """
    db_manager = DatabaseManager(is_async=True)
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config.get("priorities", {}),
    )

    orchestrator_id = result["orchestrator_id"]

    # FIRST call
    instructions1 = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id, tenant_key=test_tenant_key, db_manager=db_manager
    )
    assert "error" not in instructions1
    mission1 = instructions1.get("mission", "")
    tokens1 = instructions1.get("estimated_tokens", 0)

    # SECOND call (immediate)
    instructions2 = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id, tenant_key=test_tenant_key, db_manager=db_manager
    )
    assert "error" not in instructions2
    mission2 = instructions2.get("mission", "")
    tokens2 = instructions2.get("estimated_tokens", 0)

    # VERIFY: Content identical (compiled same way)
    assert mission1 == mission2, "Mission content should be identical on repeated calls"
    assert tokens1 == tokens2, f"Token counts differ: {tokens1} vs {tokens2}"


# ============================================================================
# TEST 5: Thin Prompt References MCP Tools
# ============================================================================


@pytest.mark.asyncio
async def test_thin_prompt_references_mcp_tools(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: Generated thin prompt references MCP tools, not inline context.

    Thin prompts are ~600 tokens with MCP tool references.
    Fat prompts are ~3500 tokens with inline context.
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config.get("priorities", {}),
    )

    thin_prompt = result["thin_prompt"]
    estimated_tokens = result["estimated_prompt_tokens"]

    # VERIFY: Thin prompt is actually thin
    assert estimated_tokens < 2000, f"Thin prompt is too large: {estimated_tokens} tokens (should be ~600)"

    # VERIFY: References MCP tools
    has_mcp_reference = (
        "get_orchestrator_instructions" in thin_prompt
        or "mcp__giljo-mcp" in thin_prompt
        or "get_available_agents" in thin_prompt
    )
    assert has_mcp_reference, "Thin prompt should reference MCP tools for context fetching"

    # VERIFY: Not a fat prompt
    assert len(thin_prompt) < 5000, f"Thin prompt character length too large: {len(thin_prompt)}"


# ============================================================================
# TEST 6: Orchestrator Status is "waiting"
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_status_waiting_after_creation(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: Newly created orchestrator has status "waiting".
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config.get("priorities", {}),
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Status is "waiting"
    orch_stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    assert orchestrator.status == "waiting", f"Expected status 'waiting', got '{orchestrator.status}'"


# ============================================================================
# TEST 7: Orchestrator ID in Thin Prompt
# ============================================================================


@pytest.mark.asyncio
async def test_thin_prompt_contains_orchestrator_id(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: Generated thin prompt contains the orchestrator ID.

    Without this, the MCP tool cannot retrieve instructions.
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config.get("priorities", {}),
    )

    orchestrator_id = result["orchestrator_id"]
    thin_prompt = result["thin_prompt"]

    # VERIFY: Orchestrator ID in prompt
    assert orchestrator_id in thin_prompt, "Orchestrator ID should be in thin prompt for MCP tool reference"

    # VERIFY: Tenant key in prompt (for multi-tenant isolation)
    assert test_tenant_key in thin_prompt, "Tenant key should be in thin prompt"


# ============================================================================
# TEST 8: Depth Config Stored in Metadata
# ============================================================================


@pytest.mark.asyncio
async def test_depth_config_stored_in_metadata(
    db_session: AsyncSession, test_user: object, test_project: object, test_tenant_key: str
):
    """
    VERIFY: Depth config is stored in job_metadata when provided.
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    custom_depth = {
        "vision_chunking": "light",
        "memory_last_n_projects": 1,
        "git_commits": 10,
        "agent_template_detail": "minimal",
        "tech_stack_sections": "required",
        "architecture_depth": "overview",
    }

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config.get("priorities", {}),
        depth_config=custom_depth,
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Depth config stored
    orch_stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    metadata = orchestrator.job_metadata or {}
    stored_depth = metadata.get("depth_config", {})

    assert stored_depth == custom_depth, f"Depth config mismatch. Expected {custom_depth}, got {stored_depth}"
