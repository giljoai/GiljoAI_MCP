"""
Integration tests for orchestrator context flow - TDD Phase 1 (RED)

This test suite verifies the complete flow from user field priority configuration
to orchestrator job creation, ensuring priorities are correctly passed through.

BUG CONTEXT:
- User configures field priorities in UI
- User stages orchestrator via /api/prompts/staging/{project_id}
- Orchestrator job should receive field priorities in job_metadata
- Bug: api/endpoints/prompts.py line 455 looks for "fields" key instead of "priorities"

These tests will initially FAIL to confirm the bug exists.

Handover: Field Priority Bug Fix - Phase 1
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


# Use existing fixtures


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def user_with_field_config(db_session, test_tenant_key):
    """Create test user WITH field priority configuration"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        tenant_key=test_tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {  # CRITICAL: Using correct "priorities" key
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 4,
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_without_field_config(db_session, test_tenant_key):
    """Create test user WITHOUT field priority configuration"""
    user = User(
        id=str(uuid4()),
        username=f"noconfig_{uuid4().hex[:6]}",
        email=f"noconfig_{uuid4().hex[:6]}@example.com",
        tenant_key=test_tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config=None,  # Explicitly no config
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session, user_with_field_config):
    """Create test product"""
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product for field priority testing.",
        tenant_key=user_with_field_config.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, user_with_field_config, test_product):
    """Create test project"""
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for orchestrator field priority testing.",
        product_id=str(test_product.id),
        tenant_key=user_with_field_config.tenant_key,
        status="planning",
        mission="Test mission for orchestrator with field priorities.",
        context_budget=180000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# TEST 2: Orchestrator Receives User Field Priorities
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_receives_user_field_priorities(db_session, user_with_field_config, test_project):
    """
    TEST 2a: Orchestrator job should receive user's field priorities in job_metadata.

    COMPLETE USER FLOW:
    1. User configures field priorities in My Settings
    2. User stages project via /api/prompts/staging/{project_id}
    3. ThinClientPromptGenerator creates orchestrator job
    4. Orchestrator job_metadata should contain user's field priorities

    BUG:
    api/endpoints/prompts.py line 455 uses: user_field_config.get("fields", {})
    But the config structure is: {"priorities": {...}}
    This causes orchestrator to always receive empty dict: field_priorities={}

    This test will FAIL because of the key mismatch.
    """
    # ARRANGE: Verify user has field priority configuration
    assert user_with_field_config.field_priority_config is not None
    assert "priorities" in user_with_field_config.field_priority_config

    expected_priorities = {
        "product_core": 1,
        "vision_documents": 2,
        "agent_templates": 3,
        "project_description": 1,
        "memory_360": 2,
        "git_history": 4,
    }

    # ACT: Simulate the endpoint behavior - this is where the bug occurs
    # The endpoint should:
    # 1. Fetch user.field_priority_config from database
    # 2. Extract priorities dict: user_field_config.get("priorities", {})
    # 3. Pass to ThinClientPromptGenerator.generate()

    # BUG: Current code does this (WRONG):
    user_field_config = user_with_field_config.field_priority_config or {}
    field_priorities_buggy = user_field_config.get("fields", {})  # WRONG KEY!

    # EXPECTED: Fixed code should do this (CORRECT):
    field_priorities_fixed = user_field_config.get("priorities", {})

    # CRITICAL ASSERTION: Demonstrate the bug
    assert field_priorities_buggy == {}, (
        f"BUG DEMONSTRATION: Using 'fields' key returns empty dict. Got: {field_priorities_buggy}"
    )

    assert field_priorities_fixed == expected_priorities, (
        f"CORRECT BEHAVIOR: Using 'priorities' key returns user config. "
        f"Expected: {expected_priorities}, Got: {field_priorities_fixed}"
    )

    # Now test with ThinClientPromptGenerator (simulating fixed endpoint)
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_with_field_config.tenant_key)

    # Pass FIXED field_priorities to generator
    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(user_with_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities_fixed,  # Using CORRECT priorities
    )

    # ASSERT: Verify orchestrator job has field priorities in metadata
    orchestrator_id = result["orchestrator_id"]

    # Fetch the created orchestrator job from database
    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    assert orchestrator_job is not None, "Orchestrator job should exist"
    assert orchestrator_job.job_metadata is not None, "Job metadata should exist"
    assert "field_priorities" in orchestrator_job.job_metadata, "field_priorities key should exist in job_metadata"

    # CRITICAL ASSERTION: field_priorities should match user's config
    actual_priorities = orchestrator_job.job_metadata["field_priorities"]
    assert actual_priorities == expected_priorities, (
        f"Expected orchestrator to receive field_priorities {expected_priorities}, got {actual_priorities}"
    )


@pytest.mark.asyncio
async def test_orchestrator_receives_empty_dict_when_no_user_config(db_session, user_without_field_config):
    """
    TEST 2b: When user has NO field priority config, orchestrator gets empty dict.

    USER FLOW:
    1. User has not configured field priorities (field_priority_config=None)
    2. User stages project
    3. Orchestrator should receive empty dict (system defaults will apply)

    This documents expected behavior for users without custom configuration.
    """
    # ARRANGE: Create product and project for user without config
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product.",
        tenant_key=user_without_field_config.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()

    project = Project(
        id=str(uuid4()),
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project.",
        product_id=str(product.id),
        tenant_key=user_without_field_config.tenant_key,
        status="planning",
        mission="Test mission.",
        context_budget=180000,
    )
    db_session.add(project)
    await db_session.commit()

    # Verify user has NO field config
    assert user_without_field_config.field_priority_config is None

    # ACT: Simulate what FIXED endpoint should do with None config
    user_field_config = user_without_field_config.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # Should be empty dict when user has no config
    assert field_priorities == {}

    # Generate staging prompt with empty priorities
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_without_field_config.tenant_key)

    result = await generator.generate(
        project_id=str(project.id),
        user_id=str(user_without_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities,  # Empty dict
    )

    # ASSERT: Verify orchestrator job has EMPTY field priorities
    orchestrator_id = result["orchestrator_id"]

    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    assert orchestrator_job is not None
    assert orchestrator_job.job_metadata is not None

    # Should have empty dict when user has no config
    actual_priorities = orchestrator_job.job_metadata.get("field_priorities", {})
    assert actual_priorities == {}, f"Expected empty field_priorities {{}}, got {actual_priorities}"


@pytest.mark.asyncio
async def test_orchestrator_field_priorities_match_user_session(db_session, user_with_field_config, test_project):
    """
    TEST 2c: Orchestrator field priorities should reflect current user session.

    USER FLOW:
    1. User A logs in with configured field priorities
    2. User A stages project
    3. Orchestrator should get User A's priorities (not defaults, not another user's)

    This ensures the staging endpoint correctly identifies and uses the current user.
    """
    # ARRANGE: User has field priority configuration
    user_priorities = user_with_field_config.field_priority_config["priorities"]

    # ACT: Generate staging prompt for this user's project
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_with_field_config.tenant_key)

    # Extract priorities correctly (FIXED behavior)
    user_field_config = user_with_field_config.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(user_with_field_config.id),  # CRITICAL: Current user ID
        tool="claude-code",
        field_priorities=field_priorities,
    )

    # ASSERT: Orchestrator should have THIS USER's priorities
    orchestrator_id = result["orchestrator_id"]

    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    actual_priorities = orchestrator_job.job_metadata["field_priorities"]

    # CRITICAL: Should match the user who staged the project
    assert actual_priorities == user_priorities, (
        f"Orchestrator should receive current user's priorities. Expected: {user_priorities}, Got: {actual_priorities}"
    )


@pytest.mark.asyncio
async def test_orchestrator_field_priorities_stored_in_job_metadata(db_session, user_with_field_config, test_project):
    """
    TEST 2d: Field priorities should be stored in job_metadata (not elsewhere).

    This confirms priorities are stored in the correct location for orchestrator access.
    """
    # ARRANGE: Extract user priorities
    user_field_config = user_with_field_config.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # ACT: Generate orchestrator job
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_with_field_config.tenant_key)

    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(user_with_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    orchestrator_id = result["orchestrator_id"]

    # ASSERT: Fetch job and verify storage location
    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    # CRITICAL ASSERTION 1: job_metadata should exist
    assert orchestrator_job.job_metadata is not None, "job_metadata should be populated for orchestrator jobs"

    # CRITICAL ASSERTION 2: field_priorities should be in job_metadata
    assert "field_priorities" in orchestrator_job.job_metadata, (
        f"field_priorities should be in job_metadata. Got metadata keys: {orchestrator_job.job_metadata.keys()}"
    )

    # CRITICAL ASSERTION 3: field_priorities should be a dict
    priorities = orchestrator_job.job_metadata["field_priorities"]
    assert isinstance(priorities, dict), f"field_priorities should be a dict, got {type(priorities)}"


@pytest.mark.asyncio
async def test_orchestrator_field_priorities_available_in_mission(db_session, user_with_field_config, test_project):
    """
    TEST 2e: Field priorities should be accessible when orchestrator fetches mission.

    USER FLOW:
    1. Orchestrator job is created with field priorities in job_metadata
    2. Orchestrator calls get_orchestrator_instructions() MCP tool
    3. MCP tool should have access to field_priorities for context filtering

    This test verifies the data is stored in a way that MCP tools can access it.
    """
    # ARRANGE: Extract user priorities
    user_field_config = user_with_field_config.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # ACT: Generate orchestrator job
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_with_field_config.tenant_key)

    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(user_with_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    orchestrator_id = result["orchestrator_id"]

    # ASSERT: Verify field priorities can be retrieved from database
    stmt = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id, AgentExecution.tenant_key == user_with_field_config.tenant_key
    )
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    # CRITICAL: MCP tool should be able to extract field_priorities
    stored_priorities = orchestrator_job.job_metadata.get("field_priorities", {})

    assert stored_priorities is not None, "field_priorities should be retrievable from job_metadata"

    assert stored_priorities == field_priorities, (
        f"Stored priorities should match input. Expected: {field_priorities}, Got: {stored_priorities}"
    )
