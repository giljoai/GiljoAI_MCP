"""
Integration tests for user field priorities in orchestrator staging flow.

Tests that user-configured field priorities from My Settings → Context
are correctly passed through to the orchestrator job metadata.

BUG FIX: api/endpoints/prompts.py was not fetching/passing user's field_priority_config
to ThinClientPromptGenerator, causing orchestrator to always get empty dict.

Handover: Field Priority Bug Fix
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution


@pytest_asyncio.fixture
async def test_user_with_field_config(db_session: AsyncSession):
    """Create test user with field priority configuration."""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "1.0",
            "fields": {"codebase_summary": 8, "product_vision": 10, "architecture": 7, "dependencies": 4},
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_without_field_config(db_session: AsyncSession):
    """Create test user without field priority configuration."""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
        field_priority_config=None,  # Explicitly no config
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_user_with_field_config: User):
    """Create test product."""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product description.",
        tenant_key=test_user_with_field_config.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user_with_field_config: User, test_product: Product):
    """Create test project."""
    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for field priority testing.",
        product_id=str(test_product.id),
        tenant_key=test_user_with_field_config.tenant_key,
        status="planning",
        mission="Test mission for orchestrator.",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_user_field_priorities_passed_to_orchestrator_job(
    db_session: AsyncSession, test_user_with_field_config: User, test_project: Project
):
    """
    CRITICAL TEST: When user has configured field priorities in My Settings,
    those priorities should be stored in the orchestrator job metadata.

    BUG: Current code doesn't fetch user.field_priority_config from database,
    so orchestrator always gets empty dict instead of user's configuration.

    Expected behavior:
    1. User configures field priorities: {"codebase_summary": 8, ...}
    2. User stages project via /api/prompts/staging/{project_id}
    3. Orchestrator job created with job_metadata["field_priorities"] = user's config

    Current behavior (BROKEN):
    1. User configures field priorities
    2. User stages project
    3. Orchestrator job created with job_metadata["field_priorities"] = {} (EMPTY!)
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    # ARRANGE: User already has field_priority_config in fixture
    assert test_user_with_field_config.field_priority_config is not None
    expected_priorities = {"codebase_summary": 8, "product_vision": 10, "architecture": 7, "dependencies": 4}
    assert test_user_with_field_config.field_priority_config["fields"] == expected_priorities

    # ACT: Call the staging prompt generator (simulating endpoint behavior)
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=test_user_with_field_config.tenant_key)

    # THIS IS THE BUG: The endpoint should fetch user.field_priority_config
    # and pass it to generate(), but currently it doesn't
    # For now, we'll simulate what the FIXED endpoint should do:
    user_field_config = test_user_with_field_config.field_priority_config or {}
    field_priorities = user_field_config.get("fields", {})

    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(test_user_with_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities,  # Should be passed by endpoint
    )

    # ASSERT: Verify orchestrator job has field priorities in metadata
    orchestrator_id = result["orchestrator_id"]

    # Fetch the created orchestrator job from database
    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    assert orchestrator_job is not None, "Orchestrator job should exist"
    assert orchestrator_job.job_metadata is not None, "Job metadata should exist"
    assert "field_priorities" in orchestrator_job.job_metadata, "field_priorities key should exist"

    # THIS IS THE KEY ASSERTION - field_priorities should match user's config
    actual_priorities = orchestrator_job.job_metadata["field_priorities"]
    assert actual_priorities == expected_priorities, (
        f"Expected field_priorities {expected_priorities}, got {actual_priorities}"
    )


@pytest.mark.asyncio
async def test_user_without_field_config_uses_empty_dict(
    db_session: AsyncSession, test_user_without_field_config: User
):
    """
    When user has NOT configured field priorities,
    orchestrator should get empty dict (system defaults will apply later).

    Expected behavior:
    - User has field_priority_config = None
    - Orchestrator job created with job_metadata["field_priorities"] = {}
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    # ARRANGE: Create product and project for user without config
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product description.",
        tenant_key=test_user_without_field_config.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project.",
        product_id=str(product.id),
        tenant_key=test_user_without_field_config.tenant_key,
        status="planning",
        mission="Test mission.",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Verify user has NO field config
    assert test_user_without_field_config.field_priority_config is None

    # ACT: Generate staging prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=test_user_without_field_config.tenant_key)

    # Simulate what FIXED endpoint should do with None config
    user_field_config = test_user_without_field_config.field_priority_config or {}
    field_priorities = user_field_config.get("fields", {})

    result = await generator.generate(
        project_id=str(project.id),
        user_id=str(test_user_without_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities,
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
async def test_field_priorities_respect_tenant_isolation(db_session: AsyncSession, test_user_with_field_config: User):
    """
    Field priorities should respect tenant isolation.

    A user in tenant_A should only see their own field priorities,
    not those from users in tenant_B.

    Expected behavior:
    - User in tenant_A has field priorities
    - Different tenant_B user has different priorities
    - When tenant_A user stages project, gets their own priorities
    - Tenant_B cannot access tenant_A's orchestrator job
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    # ARRANGE: Create second user in different tenant with different priorities
    tenant_b_user = User(
        username=f"tenant_b_user_{uuid4().hex[:8]}",
        email=f"tenant_b_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_b_{uuid4().hex[:8]}",  # DIFFERENT tenant
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "1.0",
            "fields": {
                "codebase_summary": 2,  # Different priorities
                "product_vision": 3,
                "architecture": 1,
            },
        },
    )
    db_session.add(tenant_b_user)
    await db_session.commit()
    await db_session.refresh(tenant_b_user)

    # Create product for tenant_A (test_user_with_field_config)
    product_a = Product(
        name=f"Product A {uuid4().hex[:8]}",
        description="Product for tenant A.",
        tenant_key=test_user_with_field_config.tenant_key,
        is_active=True,
    )
    db_session.add(product_a)
    await db_session.commit()
    await db_session.refresh(product_a)

    project_a = Project(
        name=f"Project A {uuid4().hex[:8]}",
        description="Project for tenant A.",
        product_id=str(product_a.id),
        tenant_key=test_user_with_field_config.tenant_key,
        status="planning",
        mission="Mission A.",
    )
    db_session.add(project_a)
    await db_session.commit()
    await db_session.refresh(project_a)

    # ACT: Generate staging prompt for tenant_A user
    generator_a = ThinClientPromptGenerator(db=db_session, tenant_key=test_user_with_field_config.tenant_key)

    user_a_config = test_user_with_field_config.field_priority_config or {}
    field_priorities_a = user_a_config.get("fields", {})

    result_a = await generator_a.generate(
        project_id=str(project_a.id),
        user_id=str(test_user_with_field_config.id),
        tool="claude-code",
        field_priorities=field_priorities_a,
    )

    # ASSERT: Verify tenant_A got their own priorities
    orchestrator_id_a = result_a["orchestrator_id"]

    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id_a)
    job_result = await db_session.execute(stmt)
    orchestrator_job_a = job_result.scalar_one_or_none()

    assert orchestrator_job_a is not None
    assert orchestrator_job_a.tenant_key == test_user_with_field_config.tenant_key

    actual_priorities_a = orchestrator_job_a.job_metadata.get("field_priorities", {})
    expected_priorities_a = {"codebase_summary": 8, "product_vision": 10, "architecture": 7, "dependencies": 4}

    assert actual_priorities_a == expected_priorities_a, (
        f"Tenant A should get their own priorities. Expected {expected_priorities_a}, got {actual_priorities_a}"
    )

    # Verify tenant_B user CANNOT access tenant_A's orchestrator job
    # (by checking tenant_key isolation in database query)
    stmt_b = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id_a,
        AgentExecution.tenant_key == tenant_b_user.tenant_key,  # Different tenant
    )
    job_result_b = await db_session.execute(stmt_b)
    orchestrator_job_b = job_result_b.scalar_one_or_none()

    assert orchestrator_job_b is None, "Tenant B should NOT be able to access Tenant A's orchestrator job"
