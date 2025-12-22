"""
Direct integration tests for orchestrator instruction compilation timing.

These tests work directly with database and services, not through HTTP client.
They verify the core compilation behavior without HTTP transport complexity.

Key behaviors being tested:
1. ThinClientPromptGenerator.generate() creates orchestrator jobs
2. get_orchestrator_instructions() compiles fresh instructions each time
3. Field priorities persist through the pipeline
4. Depth config is stored and applied
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from datetime import datetime, timezone

from src.giljo_mcp.models import Project, User, Product
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions
from src.giljo_mcp.database import DatabaseManager


# ============================================================================
# FIXTURE: Create Test Data
# ============================================================================

@pytest.fixture
async def setup_test_environment(
    db_session: AsyncSession,
    test_tenant_key: str
):
    """Create test product, projects, and user."""
    # Create product
    product = Product(
        id="prod-comp-test-001",
        tenant_key=test_tenant_key,
        name="Compilation Test Product",
        description="Product for compilation timing tests",
        product_memory={
            "objectives": ["Test orchestrator compilation"],
            "decisions": [],
            "context": {},
            "knowledge_base": {},
            "sequential_history": []
        }
    )
    db_session.add(product)
    await db_session.commit()

    # Create project
    project = Project(
        id="proj-comp-test-001",
        tenant_key=test_tenant_key,
        product_id=product.id,
        name="Compilation Test Project",
        description="User requirements for testing compilation behavior",
        mission="",
        status="waiting",
        context_budget=150000,
        context_used=0
    )
    db_session.add(project)
    await db_session.commit()

    # Create user with custom priorities
    user = User(
        id="user-comp-test-001",
        tenant_key=test_tenant_key,
        username="compilationtest",
        email="compile@test.com",
        hashed_password="fake_hash",
        is_active=True,
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "tech_stack": 1,
                "architecture": 2,
                "testing": 3,
                "memory_360": 1,
                "git_history": 2,
                "agent_templates": 2
            }
        },
        depth_config={
            "vision_chunking": "medium",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_template_detail": "standard",
            "tech_stack_sections": "all",
            "architecture_depth": "overview"
        }
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "product": product,
        "project": project,
        "user": user,
        "tenant_key": test_tenant_key
    }


# ============================================================================
# TEST 1: Orchestrator Creation Stores Field Priorities
# ============================================================================

@pytest.mark.asyncio
async def test_orchestrator_stores_field_priorities(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Field priorities passed to generate() are stored in job_metadata.

    This is critical for the compilation pipeline:
    1. User's priorities from field_priority_config passed to generator.generate()
    2. Generator stores them in AgentExecution.job_metadata
    3. MCP tool retrieves from job_metadata and applies them
    4. Mission is built with those priorities
    """
    env = setup_test_environment
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    # Generate orchestrator with specific priorities
    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"],
        depth_config=env["user"].depth_config
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Priorities stored in database
    orch_stmt = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    assert orchestrator is not None, "Orchestrator not created"
    assert orchestrator.status == "waiting", "Orchestrator status should be 'waiting'"

    metadata = orchestrator.job_metadata or {}
    stored_priorities = metadata.get("field_priorities", {})

    assert stored_priorities == env["user"].field_priority_config["priorities"], \
        "Field priorities not stored in job_metadata"


# ============================================================================
# TEST 2: Orchestrator Stores Depth Config
# ============================================================================

@pytest.mark.asyncio
async def test_orchestrator_stores_depth_config(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Depth config passed to generate() is stored in job_metadata.

    Depth config controls:
    - vision_chunking: controls vision document inclusion
    - memory_last_n_projects: controls how many project summaries to include
    - git_commits: controls how many commits to fetch
    - agent_template_detail: controls agent template verbosity
    - tech_stack_sections: controls tech stack depth
    - architecture_depth: controls architecture detail level
    """
    env = setup_test_environment

    custom_depth = {
        "vision_chunking": "light",
        "memory_last_n_projects": 1,
        "git_commits": 10,
        "agent_template_detail": "minimal",
        "tech_stack_sections": "required",
        "architecture_depth": "overview"
    }

    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"],
        depth_config=custom_depth  # Custom depth config
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Depth config stored
    orch_stmt = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    metadata = orchestrator.job_metadata or {}
    stored_depth = metadata.get("depth_config", {})

    assert stored_depth == custom_depth, \
        f"Depth config mismatch: {stored_depth} vs {custom_depth}"


# ============================================================================
# TEST 3: MCP Tool Retrieves Stored Priorities
# ============================================================================

@pytest.mark.asyncio
async def test_mcp_tool_retrieves_stored_priorities(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: get_orchestrator_instructions() retrieves priorities from job_metadata.

    The MCP tool should:
    1. Fetch orchestrator from database
    2. Extract field_priorities from job_metadata
    3. Return them in the response
    """
    env = setup_test_environment
    db_manager = DatabaseManager(is_async=True)

    # Create orchestrator
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"],
        depth_config=env["user"].depth_config
    )

    orchestrator_id = result["orchestrator_id"]

    # Call MCP tool
    instructions = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=env["tenant_key"],
        db_manager=db_manager
    )

    # VERIFY: Priorities returned
    assert "error" not in instructions, f"Error: {instructions}"
    returned_priorities = instructions.get("field_priorities", {})

    assert returned_priorities == env["user"].field_priority_config["priorities"], \
        "Priorities not retrieved from job_metadata"


# ============================================================================
# TEST 4: MCP Tool Compiles Fresh Mission Each Time
# ============================================================================

@pytest.mark.asyncio
async def test_mcp_tool_compiles_fresh_mission(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: get_orchestrator_instructions() compiles mission fresh on each call.

    The MCP tool calls MissionPlanner._build_context_with_priorities() on EACH
    invocation. It does NOT cache the mission from prompt generation stage.

    When called multiple times with same orchestrator_id:
    - Mission content should be identical (same logic, same data)
    - But compiled fresh from database, not from cache
    """
    env = setup_test_environment
    db_manager = DatabaseManager(is_async=True)

    # Create orchestrator
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"],
        depth_config=env["user"].depth_config
    )

    orchestrator_id = result["orchestrator_id"]

    # FIRST call
    instructions1 = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=env["tenant_key"],
        db_manager=db_manager
    )
    assert "error" not in instructions1
    mission1 = instructions1.get("mission", "")
    tokens1 = instructions1.get("estimated_tokens", 0)

    # SECOND call (immediate)
    instructions2 = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=env["tenant_key"],
        db_manager=db_manager
    )
    assert "error" not in instructions2
    mission2 = instructions2.get("mission", "")
    tokens2 = instructions2.get("estimated_tokens", 0)

    # VERIFY: Content identical
    assert mission1 == mission2, "Mission content should be identical on repeated calls"
    assert tokens1 == tokens2, f"Token counts differ: {tokens1} vs {tokens2}"


# ============================================================================
# TEST 5: Repeated Staging Reuses Orchestrator
# ============================================================================

@pytest.mark.asyncio
async def test_repeated_staging_reuses_orchestrator(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Repeated calls to generate() reuse existing orchestrator.

    Per ThinClientPromptGenerator.generate() lines 196-216:
    - Checks for existing orchestrator with status "waiting" or "working"
    - Returns same orchestrator if found
    - Prevents duplicate creation on repeated "Stage Project" clicks
    """
    env = setup_test_environment
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    # FIRST call
    result1 = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"]
    )
    orch_id_1 = result1["orchestrator_id"]

    # SECOND call (immediate)
    result2 = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"]
    )
    orch_id_2 = result2["orchestrator_id"]

    # VERIFY: Same orchestrator
    assert orch_id_1 == orch_id_2, \
        f"Repeated calls should reuse orchestrator: {orch_id_1} vs {orch_id_2}"

    # VERIFY: Only one orchestrator in database
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.project_id == env["project"].id,
            AgentExecution.agent_type == "orchestrator",
            AgentExecution.tenant_key == env["tenant_key"]
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrators = orch_result.scalars().all()

    assert len(orchestrators) == 1, \
        f"Expected 1 orchestrator, found {len(orchestrators)}"


# ============================================================================
# TEST 6: Different Field Priorities Create Different Missions
# ============================================================================

@pytest.mark.asyncio
async def test_different_priorities_create_different_missions(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Different field priorities result in different mission content.

    The MissionPlanner respects field priorities:
    - Priority 1 (CRITICAL): Always included
    - Priority 2 (IMPORTANT): High priority
    - Priority 3 (NICE_TO_HAVE): Medium priority
    - Priority 4 (EXCLUDED): Never included

    Changing priorities should result in different mission content.
    """
    env = setup_test_environment
    db_manager = DatabaseManager(is_async=True)
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    # FIRST: High priority on all fields
    full_priorities = {
        "product_core": 1,
        "vision_documents": 1,
        "tech_stack": 1,
        "architecture": 1,
        "testing": 1,
        "memory_360": 1,
        "git_history": 1,
        "agent_templates": 1
    }

    result1 = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=full_priorities
    )
    orch_id_1 = result1["orchestrator_id"]

    instructions1 = await get_orchestrator_instructions(
        orchestrator_id=orch_id_1,
        tenant_key=env["tenant_key"],
        db_manager=db_manager
    )
    mission1 = instructions1.get("mission", "")
    len1 = len(mission1)

    # SECOND: Low priority on most fields
    reduced_priorities = {
        "product_core": 1,
        "vision_documents": 4,  # EXCLUDED
        "tech_stack": 4,        # EXCLUDED
        "architecture": 4,      # EXCLUDED
        "testing": 4,           # EXCLUDED
        "memory_360": 1,
        "git_history": 4,       # EXCLUDED
        "agent_templates": 4    # EXCLUDED
    }

    # Need new orchestrator instance to test different priorities
    result2 = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=2,
        field_priorities=reduced_priorities
    )
    orch_id_2 = result2["orchestrator_id"]

    instructions2 = await get_orchestrator_instructions(
        orchestrator_id=orch_id_2,
        tenant_key=env["tenant_key"],
        db_manager=db_manager
    )
    mission2 = instructions2.get("mission", "")
    len2 = len(mission2)

    # VERIFY: Reduced priorities produce shorter mission
    assert len2 < len1, \
        f"Reduced priorities should produce shorter mission: {len2} vs {len1}"

    # VERIFY: Missions are different
    assert mission1 != mission2, \
        "Different priorities should produce different missions"


# ============================================================================
# TEST 7: Thin Prompt References MCP Tools (Not Fat Prompt)
# ============================================================================

@pytest.mark.asyncio
async def test_thin_prompt_references_mcp_tools(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Generated thin prompt references MCP tools, not inline context.

    Thin prompts:
    - ~600 tokens with MCP tool references
    - Include references to: get_orchestrator_instructions, get_available_agents, etc.
    - Much smaller than fat prompts (~3500 tokens with inline context)

    The prompt should tell the orchestrator HOW to fetch context via MCP,
    not provide all context inline.
    """
    env = setup_test_environment
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"]
    )

    thin_prompt = result["thin_prompt"]
    estimated_tokens = result["estimated_prompt_tokens"]

    # VERIFY: Thin prompt is actually thin
    assert estimated_tokens < 2000, \
        f"Thin prompt is too large: {estimated_tokens} tokens (should be ~600)"

    # VERIFY: References MCP tools
    has_mcp_reference = (
        "get_orchestrator_instructions" in thin_prompt or
        "mcp__giljo-mcp" in thin_prompt or
        "get_available_agents" in thin_prompt
    )
    assert has_mcp_reference, \
        "Thin prompt should reference MCP tools for context fetching"

    # VERIFY: Not a fat prompt (should not contain extensive inline context)
    # Fat prompts would have full vision documents, full tech stack, etc.
    # Thin prompts just tell how to fetch
    assert len(thin_prompt) < 5000, \
        f"Thin prompt character length too large: {len(thin_prompt)}"


# ============================================================================
# TEST 8: Orchestrator Status is "waiting" After Creation
# ============================================================================

@pytest.mark.asyncio
async def test_orchestrator_status_waiting_after_creation(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Newly created orchestrator has status "waiting".

    Status lifecycle:
    - "waiting": Created, ready for user to paste prompt
    - "working": Orchestrator is actively executing
    - "completed": Finished successfully
    - "failed": Encountered error
    - "cancelled": User cancelled execution

    When create via generate(), status should be "waiting" until execution begins.
    """
    env = setup_test_environment
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"]
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Status is "waiting"
    orch_stmt = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    assert orchestrator.status == "waiting", \
        f"Expected status 'waiting', got '{orchestrator.status}'"


# ============================================================================
# TEST 9: Thin Prompt Contains Orchestrator ID
# ============================================================================

@pytest.mark.asyncio
async def test_thin_prompt_contains_orchestrator_id(
    db_session: AsyncSession,
    setup_test_environment
):
    """
    VERIFY: Generated thin prompt contains the orchestrator ID.

    The prompt must include:
    - orchestrator_id (so MCP tool knows which orchestrator is calling)
    - tenant_key (for multi-tenant isolation in MCP tool)
    - MCP server connection details

    Without these, the MCP tool cannot retrieve instructions.
    """
    env = setup_test_environment
    generator = ThinClientPromptGenerator(db_session, env["tenant_key"])

    result = await generator.generate(
        project_id=env["project"].id,
        user_id=str(env["user"].id),
        tool="claude-code",
        instance_number=1,
        field_priorities=env["user"].field_priority_config["priorities"]
    )

    orchestrator_id = result["orchestrator_id"]
    thin_prompt = result["thin_prompt"]

    # VERIFY: Orchestrator ID in prompt
    assert orchestrator_id in thin_prompt, \
        "Orchestrator ID should be in thin prompt for MCP tool reference"

    # VERIFY: Tenant key in prompt (for multi-tenant isolation)
    assert env["tenant_key"] in thin_prompt, \
        "Tenant key should be in thin prompt"
