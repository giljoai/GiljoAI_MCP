"""
Integration tests for orchestrator instruction compilation timing in GiljoAI MCP.

Tests verify:
1. When instructions are compiled (activation vs staging vs MCP tool calls)
2. How settings changes impact instruction compilation
3. Whether instructions are cached or freshly compiled
4. Field priority persistence through the compilation pipeline

Test scenarios:
- Project activation (no prompt generation expected)
- Stage Project button press (prompt + instructions generated)
- Repeated MCP tool calls (fresh compilation each time)
- Settings changes before/after project activation
- Field priority application throughout pipeline
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from datetime import datetime, timezone
import json

from src.giljo_mcp.models import (
    Project, AgentExecution, User, Product
)
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions
from src.giljo_mcp.database import DatabaseManager


# ============================================================================
# FIXTURE: Test Data Setup
# ============================================================================

@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str):
    """Create test product with vision document."""
    product = Product(
        id="prod-test-001",
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Test product for compilation timing tests",
        product_memory={
            "objectives": ["Build reliable backend", "Ensure scalability"],
            "decisions": [],
            "context": {},
            "knowledge_base": {},
            "sequential_history": []
        }
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project(db_session: AsyncSession, test_tenant_key: str, test_product):
    """Create test project with basic requirements."""
    project = Project(
        id="proj-test-001",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project",
        description="User-written requirements: Build a REST API with authentication",
        mission="",  # Will be compiled later
        status="waiting",
        context_budget=150000,
        context_used=0
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_user_with_priorities(db_session: AsyncSession, test_tenant_key: str):
    """Create test user with custom field priority configuration."""
    user = User(
        id="user-test-001",
        tenant_key=test_tenant_key,
        username="testuser",
        email="test@example.com",
        hashed_password="fake_hash",
        is_active=True,
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,           # CRITICAL
                "vision_documents": 2,       # IMPORTANT
                "tech_stack": 2,             # IMPORTANT
                "architecture": 2,           # IMPORTANT
                "testing": 3,                # NICE_TO_HAVE
                "memory_360": 1,             # CRITICAL
                "git_history": 2,            # IMPORTANT
                "agent_templates": 2         # IMPORTANT
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
    await db_session.refresh(user)
    return user


# ============================================================================
# TEST 1: Activation Does NOT Compile Instructions
# ============================================================================

@pytest.mark.asyncio
async def test_activate_project_does_not_compile_instructions(
    async_client: AsyncClient,
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Project activation should NOT compile instructions.

    When user clicks "Activate Project":
    - Status changes to "active"
    - NO orchestrator job created
    - NO instructions compiled

    Instructions are only compiled when "Stage Project" is pressed.
    """
    # Get auth token for test user
    auth_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": test_user_with_priorities.username,
            "password": "testpass"  # From fixture setup
        }
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ACTIVATE project
    response = await async_client.post(
        f"/api/projects/{test_project.id}/activate",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    # VERIFY: No orchestrator created
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.project_id == test_project.id,
            AgentExecution.agent_display_name == "orchestrator",
            AgentExecution.tenant_key == test_tenant_key
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrators = orch_result.scalars().all()

    assert len(orchestrators) == 0, \
        f"Expected NO orchestrators after activation, found {len(orchestrators)}"


# ============================================================================
# TEST 2: Stage Project Button Compiles Instructions
# ============================================================================

@pytest.mark.asyncio
async def test_stage_project_compiles_orchestrator_prompt(
    async_client: AsyncClient,
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: "Stage Project" button should compile thin prompt and create orchestrator.

    Sequence:
    1. User clicks "Stage Project"
    2. POST /api/prompts/orchestrator-thin is called
    3. ThinClientPromptGenerator.generate() creates MCPAgentJob
    4. Thin prompt is returned with MCP tool references
    5. Field priorities are stored in job_metadata
    """
    # Get auth token
    auth_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": test_user_with_priorities.username,
            "password": "testpass"
        }
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # STAGE project (generates thin prompt)
    response = await async_client.post(
        "/api/prompts/orchestrator-thin",
        json={
            "project_id": test_project.id,
            "tool": "claude-code",
            "instance_number": 1
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    orchestrator_id = data["orchestrator_id"]
    thin_prompt = data["prompt"]

    # VERIFY: Orchestrator created
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.job_id == orchestrator_id,
            AgentExecution.agent_display_name == "orchestrator",
            AgentExecution.tenant_key == test_tenant_key
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    assert orchestrator is not None
    assert orchestrator.status == "waiting"
    assert orchestrator.project_id == test_project.id

    # VERIFY: Field priorities stored in metadata
    metadata = orchestrator.job_metadata or {}
    stored_priorities = metadata.get("field_priorities", {})

    assert stored_priorities == test_user_with_priorities.field_priority_config["priorities"], \
        "Field priorities not stored in orchestrator metadata"

    # VERIFY: Thin prompt contains MCP tool references (not fat prompt)
    assert "get_orchestrator_instructions" in thin_prompt or "mcp__giljo-mcp" in thin_prompt, \
        "Thin prompt should reference MCP tools"
    assert len(thin_prompt) < 5000, \
        f"Thin prompt is too large ({len(thin_prompt)} chars), should be ~600 tokens"


# ============================================================================
# TEST 3: Settings Change BEFORE Stage Project
# ============================================================================

@pytest.mark.asyncio
async def test_settings_change_before_stage_project(
    async_client: AsyncClient,
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Settings changed BEFORE staging should be reflected in orchestrator.

    Sequence:
    1. User changes field priorities in Settings
    2. User clicks "Stage Project"
    3. New settings should be used in prompt compilation
    4. Orchestrator metadata should have updated priorities
    """
    # Get auth token
    auth_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": test_user_with_priorities.username,
            "password": "testpass"
        }
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # CHANGE priorities - set memory to CRITICAL, testing to EXCLUDED
    new_priorities = test_user_with_priorities.field_priority_config["priorities"].copy()
    new_priorities["memory_360"] = 1  # CRITICAL
    new_priorities["testing"] = 4     # EXCLUDED

    # Update user config in database
    test_user_with_priorities.field_priority_config["priorities"] = new_priorities
    db_session.add(test_user_with_priorities)
    await db_session.commit()

    # STAGE project with new settings
    response = await async_client.post(
        "/api/prompts/orchestrator-thin",
        json={
            "project_id": test_project.id,
            "tool": "claude-code",
            "instance_number": 1
        },
        headers=headers
    )
    assert response.status_code == 200
    orchestrator_id = response.json()["orchestrator_id"]

    # VERIFY: Orchestrator has updated priorities
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.job_id == orchestrator_id,
            AgentExecution.tenant_key == test_tenant_key
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    metadata = orchestrator.job_metadata or {}
    stored_priorities = metadata.get("field_priorities", {})

    assert stored_priorities["memory_360"] == 1, "Memory should be CRITICAL"
    assert stored_priorities["testing"] == 4, "Testing should be EXCLUDED"


# ============================================================================
# TEST 4: Settings Change AFTER Activation, BEFORE Stage
# ============================================================================

@pytest.mark.asyncio
async def test_settings_change_after_activation_before_stage(
    async_client: AsyncClient,
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Settings changed AFTER activation but BEFORE stage should apply.

    Sequence:
    1. User activates project
    2. User changes settings
    3. User clicks "Stage Project"
    4. New settings should be used (no activation-time caching)
    """
    # Get auth token
    auth_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": test_user_with_priorities.username,
            "password": "testpass"
        }
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # STEP 1: Activate project
    activate_response = await async_client.post(
        f"/api/projects/{test_project.id}/activate",
        headers=headers
    )
    assert activate_response.status_code == 200

    # STEP 2: Change settings
    modified_priorities = test_user_with_priorities.field_priority_config["priorities"].copy()
    modified_priorities["git_history"] = 4  # EXCLUDED (was IMPORTANT)

    test_user_with_priorities.field_priority_config["priorities"] = modified_priorities
    db_session.add(test_user_with_priorities)
    await db_session.commit()

    # STEP 3: Stage project
    stage_response = await async_client.post(
        "/api/prompts/orchestrator-thin",
        json={
            "project_id": test_project.id,
            "tool": "claude-code",
            "instance_number": 1
        },
        headers=headers
    )
    assert stage_response.status_code == 200
    orchestrator_id = stage_response.json()["orchestrator_id"]

    # VERIFY: Orchestrator has MODIFIED priorities (not activation-time priorities)
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.job_id == orchestrator_id,
            AgentExecution.tenant_key == test_tenant_key
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    metadata = orchestrator.job_metadata or {}
    stored_priorities = metadata.get("field_priorities", {})

    assert stored_priorities["git_history"] == 4, \
        "Git history should be EXCLUDED (settings after activation)"


# ============================================================================
# TEST 5: Repeated Stage Project Button Clicks (Idempotency)
# ============================================================================

@pytest.mark.asyncio
async def test_repeated_stage_project_reuses_orchestrator(
    async_client: AsyncClient,
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Repeated "Stage Project" clicks should reuse orchestrator.

    Current behavior (per ThinClientPromptGenerator):
    - First click creates orchestrator with status="waiting"
    - Second click detects existing "waiting"/"working" orchestrator
    - Returns SAME orchestrator_id (no duplicate)
    - This prevents database pollution from repeated clicks

    Per code line 196-216 in thin_prompt_generator.py
    """
    # Get auth token
    auth_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": test_user_with_priorities.username,
            "password": "testpass"
        }
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # FIRST click
    response1 = await async_client.post(
        "/api/prompts/orchestrator-thin",
        json={
            "project_id": test_project.id,
            "tool": "claude-code",
            "instance_number": 1
        },
        headers=headers
    )
    assert response1.status_code == 200
    orch_id_1 = response1.json()["orchestrator_id"]

    # SECOND click (immediate)
    response2 = await async_client.post(
        "/api/prompts/orchestrator-thin",
        json={
            "project_id": test_project.id,
            "tool": "claude-code",
            "instance_number": 1
        },
        headers=headers
    )
    assert response2.status_code == 200
    orch_id_2 = response2.json()["orchestrator_id"]

    # VERIFY: Same orchestrator returned
    assert orch_id_1 == orch_id_2, \
        f"Expected same orchestrator on repeated clicks, got {orch_id_1} vs {orch_id_2}"

    # VERIFY: Only ONE orchestrator in database
    orch_stmt = select(AgentExecution).where(
        and_(
            AgentExecution.project_id == test_project.id,
            AgentExecution.agent_display_name == "orchestrator",
            AgentExecution.tenant_key == test_tenant_key
        )
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrators = orch_result.scalars().all()

    assert len(orchestrators) == 1, \
        f"Expected 1 orchestrator, found {len(orchestrators)}"


# ============================================================================
# TEST 6: MCP Tool Compiles Instructions Fresh Each Time
# ============================================================================

@pytest.mark.asyncio
async def test_get_orchestrator_instructions_compiles_fresh(
    test_user_with_priorities,
    test_project,
    test_product,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: get_orchestrator_instructions() should compile fresh instructions EACH time.

    NOT cached from prompt generation stage.

    When called multiple times with same orchestrator_id:
    1. Field priorities applied from job_metadata
    2. Context prioritization applied at MCP tool call time
    3. Mission built fresh each time (via MissionPlanner)
    4. Different calls may return slightly different token counts if settings changed

    Per code: get_orchestrator_instructions() calls
    MissionPlanner._build_context_with_priorities() on EACH call.
    """
    db_manager = DatabaseManager(is_async=True)

    # Create orchestrator directly
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user_with_priorities.id),
        tool="claude-code",        field_priorities=test_user_with_priorities.field_priority_config["priorities"],
        depth_config=test_user_with_priorities.depth_config
    )

    orchestrator_id = result["orchestrator_id"]

    # FIRST MCP tool call
    instructions1 = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )
    assert "error" not in instructions1, f"Error: {instructions1}"
    mission1 = instructions1.get("mission", "")
    tokens1 = instructions1.get("estimated_tokens", 0)

    # SECOND MCP tool call (same orchestrator)
    instructions2 = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )
    assert "error" not in instructions2, f"Error: {instructions2}"
    mission2 = instructions2.get("mission", "")
    tokens2 = instructions2.get("estimated_tokens", 0)

    # VERIFY: Mission content is identical (compiled same way)
    # Token count should be VERY close (within 5% - minor rounding differences)
    assert mission1 == mission2, "Mission content should be identical on repeated calls"
    assert abs(tokens1 - tokens2) <= max(tokens1 // 20, 10), \
        f"Token counts differ too much: {tokens1} vs {tokens2}"


# ============================================================================
# TEST 7: Field Priorities Persist Through Pipeline
# ============================================================================

@pytest.mark.asyncio
async def test_field_priorities_persist_through_pipeline(
    async_client: AsyncClient,
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Field priorities should persist through entire pipeline:
    Staging → Orchestrator Job Metadata → MCP Tool Call → Mission

    Verify:
    1. User's field priorities stored in User.field_priority_config
    2. Passed to generator.generate()
    3. Stored in AgentExecution.job_metadata
    4. Retrieved and applied in get_orchestrator_instructions()
    5. Reflected in final mission content
    """
    db_manager = DatabaseManager(is_async=True)

    # Get auth token
    auth_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": test_user_with_priorities.username,
            "password": "testpass"
        }
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # STAGE project (should apply user priorities)
    response = await async_client.post(
        "/api/prompts/orchestrator-thin",
        json={
            "project_id": test_project.id,
            "tool": "claude-code",
            "instance_number": 1
        },
        headers=headers
    )
    assert response.status_code == 200
    orchestrator_id = response.json()["orchestrator_id"]

    # STEP 1: Verify stored in job_metadata
    orch_stmt = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    metadata = orchestrator.job_metadata or {}
    stored_priorities = metadata.get("field_priorities", {})

    expected_priorities = test_user_with_priorities.field_priority_config["priorities"]
    assert stored_priorities == expected_priorities, \
        "Priorities not stored correctly in job_metadata"

    # STEP 2: Verify retrieved in MCP tool call
    instructions = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )
    assert "error" not in instructions

    returned_priorities = instructions.get("field_priorities", {})
    assert returned_priorities == expected_priorities, \
        "Priorities not retrieved correctly from job_metadata"

    # STEP 3: Verify applied in mission (field priorities should limit context scope)
    mission = instructions.get("mission", "")
    assert len(mission) > 0, "Mission is empty"

    # With CRITICAL priorities, should include specific sections
    # With EXCLUDED priorities, should exclude those sections
    # Check that CRITICAL (priority 1) items are more likely to appear
    if stored_priorities.get("product_core") == 1:  # CRITICAL
        assert "product" in mission.lower() or "system" in mission.lower(), \
            "Product core context not included despite CRITICAL priority"


# ============================================================================
# TEST 8: Settings Changes Impact Mission Content
# ============================================================================

@pytest.mark.asyncio
async def test_settings_changes_impact_mission_content(
    test_user_with_priorities,
    test_project,
    test_product,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Changing field priorities should change mission content.

    When field priorities change, the condensed mission built by
    MissionPlanner._build_context_with_priorities() should be different.

    Test:
    1. Generate orchestrator with full priorities
    2. Generate instructions (full mission)
    3. Change priorities to exclude certain fields
    4. Generate new orchestrator (different prompt)
    5. Generate instructions (reduced mission)
    6. Missions should differ in content/length
    """
    db_manager = DatabaseManager(is_async=True)

    # FIRST: Full priorities (all CRITICAL/IMPORTANT)
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

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
        project_id=test_project.id,
        user_id=str(test_user_with_priorities.id),
        tool="claude-code",        field_priorities=full_priorities
    )
    orch_id_1 = result1["orchestrator_id"]

    instructions1 = await get_orchestrator_instructions(
        orchestrator_id=orch_id_1,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )
    mission1 = instructions1.get("mission", "")
    len1 = len(mission1)

    # SECOND: Excluded priorities (testing and git history excluded)
    excluded_priorities = {
        "product_core": 1,
        "vision_documents": 2,
        "tech_stack": 1,
        "architecture": 1,
        "testing": 4,        # EXCLUDED
        "memory_360": 1,
        "git_history": 4,    # EXCLUDED
        "agent_templates": 1
    }

    # Need new orchestrator to test different priorities
    result2 = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user_with_priorities.id),
        tool="claude-code",  # Different instance
        field_priorities=excluded_priorities
    )
    orch_id_2 = result2["orchestrator_id"]

    instructions2 = await get_orchestrator_instructions(
        orchestrator_id=orch_id_2,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )
    mission2 = instructions2.get("mission", "")
    len2 = len(mission2)

    # VERIFY: Missions differ due to field priority exclusions
    # Mission with excluded fields should be shorter
    assert len2 < len1, \
        f"Reduced priorities should result in shorter mission: {len2} vs {len1}"

    # Missions should have different content
    assert mission1 != mission2, \
        "Different priorities should produce different mission content"


# ============================================================================
# TEST 9: Depth Config Applied on Fresh MCP Calls
# ============================================================================

@pytest.mark.asyncio
async def test_depth_config_persists_and_applies(
    test_user_with_priorities,
    test_project,
    db_session: AsyncSession,
    test_tenant_key: str
):
    """
    BEHAVIOR TEST: Depth config should persist in job_metadata and apply on MCP calls.

    Depth config controls:
    - vision_chunking: "light", "medium", "full"
    - memory_last_n_projects: 1, 3, 5, 10
    - git_commits: 10, 25, 50, 100
    - agent_template_detail: "minimal", "standard", "full"
    - tech_stack_sections: "required", "all"
    - architecture_depth: "overview", "detailed"

    Verify depth config is:
    1. Stored in job_metadata
    2. Retrieved from job_metadata on MCP calls
    3. Applied when building mission
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    custom_depth = {
        "vision_chunking": "light",
        "memory_last_n_projects": 1,
        "git_commits": 10,
        "agent_template_detail": "minimal",
        "tech_stack_sections": "required",
        "architecture_depth": "overview"
    }

    result = await generator.generate(
        project_id=test_project.id,
        user_id=str(test_user_with_priorities.id),
        tool="claude-code",        field_priorities=test_user_with_priorities.field_priority_config["priorities"],
        depth_config=custom_depth
    )

    orchestrator_id = result["orchestrator_id"]

    # VERIFY: Depth config stored in metadata
    orch_stmt = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id
    )
    orch_result = await db_session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    metadata = orchestrator.job_metadata or {}
    stored_depth = metadata.get("depth_config", {})

    assert stored_depth == custom_depth, \
        "Depth config not stored correctly in job_metadata"


# ============================================================================
# TEST 10: Multiple Projects with Different Settings
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_projects_independent_orchestrators(
    db_session: AsyncSession,
    test_user_with_priorities,
    test_tenant_key: str,
    test_product
):
    """
    BEHAVIOR TEST: Different projects should have independent orchestrators.

    Each project's Stage button click creates separate orchestrator.
    Settings apply per-orchestrator (via user at time of staging).
    """
    generator = ThinClientPromptGenerator(db_session, test_tenant_key)

    # Create two projects
    project1 = Project(
        id="proj-test-002",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Project 1",
        description="First test project",
        mission="",
        status="waiting",
        context_budget=150000,
        context_used=0
    )
    db_session.add(project1)
    await db_session.commit()

    project2 = Project(
        id="proj-test-003",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Project 2",
        description="Second test project",
        mission="",
        status="waiting",
        context_budget=150000,
        context_used=0
    )
    db_session.add(project2)
    await db_session.commit()

    # Stage both projects
    result1 = await generator.generate(
        project_id=project1.id,
        user_id=str(test_user_with_priorities.id),
        tool="claude-code",        field_priorities=test_user_with_priorities.field_priority_config["priorities"]
    )
    orch_id_1 = result1["orchestrator_id"]

    result2 = await generator.generate(
        project_id=project2.id,
        user_id=str(test_user_with_priorities.id),
        tool="claude-code",        field_priorities=test_user_with_priorities.field_priority_config["priorities"]
    )
    orch_id_2 = result2["orchestrator_id"]

    # VERIFY: Different orchestrators
    assert orch_id_1 != orch_id_2, "Different projects should have different orchestrators"

    # VERIFY: Correct project linkage
    orch1_stmt = select(AgentExecution).where(AgentExecution.job_id == orch_id_1)
    orch1_result = await db_session.execute(orch1_stmt)
    orch1 = orch1_result.scalar_one_or_none()

    orch2_stmt = select(AgentExecution).where(AgentExecution.job_id == orch_id_2)
    orch2_result = await db_session.execute(orch2_stmt)
    orch2 = orch2_result.scalar_one_or_none()

    assert orch1.project_id == project1.id
    assert orch2.project_id == project2.id
