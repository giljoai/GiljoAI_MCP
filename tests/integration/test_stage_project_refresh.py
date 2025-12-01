"""
Integration tests for Stage Project refresh mechanism (Handover 0276).

Tests verify that clicking "Stage Project" button:
1. Reuses existing orchestrator (from Handover 0275)
2. Updates orchestrator metadata with current settings (from Handover 0275)
3. **NEW**: Regenerates orchestrator instructions from latest context
4. Returns fresh instructions in response with updated settings

Business Flow:
1. User changes field priorities in settings
2. User clicks "Stage Project" button
3. System updates orchestrator metadata AND regenerates instructions
4. User copies fresh prompt with updated settings
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from passlib.hash import bcrypt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.models import Project, Product, MCPAgentJob, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
async def test_stage_project_updates_existing_orchestrator_metadata(db_session: AsyncSession):
    """
    Test that staging a project updates existing orchestrator metadata.

    Scenario:
    1. Create project with initial orchestrator
    2. Call generate() again (simulating "Stage Project" button click)
    3. Verify orchestrator metadata is updated with new settings
    4. Verify orchestrator_id remains the same (reused, not recreated)
    """
    # ARRANGE: Create tenant, user, product, project
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        password_hash=bcrypt.hash("Test@Pass123"),
        tenant_key=tenant_key,
        field_priority_config={
            "priorities": {
                "product_core": 1,  # CRITICAL
                "vision_documents": 3,  # NICE_TO_HAVE
                "tech_stack": 2,  # IMPORTANT
            }
        },
    )
    db_session.add(user)

    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for staging tests",
    )
    db_session.add(product)

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project for staging tests",
        mission="Initial test mission",
        context_budget=10000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create initial orchestrator with old settings
    generator = ThinClientPromptGenerator(db_session, tenant_key)

    initial_field_priorities = {
        "product_core": 2,  # OLD: IMPORTANT
        "vision_documents": 4,  # OLD: EXCLUDED
    }

    result1 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=initial_field_priorities,
    )

    orchestrator_id_1 = result1["orchestrator_id"]

    # ACT: Update user's field priorities and regenerate
    updated_field_priorities = {
        "product_core": 1,  # NEW: CRITICAL
        "vision_documents": 3,  # NEW: NICE_TO_HAVE
        "tech_stack": 2,  # NEW: IMPORTANT
    }

    result2 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=updated_field_priorities,
    )

    orchestrator_id_2 = result2["orchestrator_id"]

    # ASSERT: Verify orchestrator was reused (same ID)
    assert orchestrator_id_1 == orchestrator_id_2, "Orchestrator should be reused, not recreated"

    # ASSERT: Verify metadata was updated
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == orchestrator_id_2)
    result = await db_session.execute(stmt)
    orchestrator = result.scalar_one()

    assert orchestrator.job_metadata is not None
    assert orchestrator.job_metadata["field_priorities"] == updated_field_priorities
    assert "reused_at" in orchestrator.job_metadata  # Should have reuse timestamp


@pytest.mark.asyncio
async def test_stage_project_regenerates_instructions_with_current_settings(db_session: AsyncSession):
    """
    Test that staging a project regenerates orchestrator instructions with current settings.

    THIS IS THE NEW FEATURE BEING IMPLEMENTED.

    Scenario:
    1. Create project with initial orchestrator
    2. Change user's field priorities
    3. Call generate() again (simulating "Stage Project" button click)
    4. Verify returned prompt includes updated field priorities
    5. Verify instructions can be fetched via get_orchestrator_instructions()

    Expected Behavior:
    - generate() should call get_orchestrator_instructions() internally
    - Response should include fresh instructions with updated settings
    - Instructions should reflect current field_priorities, not old ones
    """
    # ARRANGE: Create tenant, user, product, project
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        password_hash=bcrypt.hash("Test@Pass123"),
        tenant_key=tenant_key,
        field_priority_config={
            "priorities": {
                "product_core": 1,  # CRITICAL
                "vision_documents": 3,  # NICE_TO_HAVE
            }
        },
    )
    db_session.add(user)

    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for instruction regeneration - Core feature set for testing",
    )
    db_session.add(product)

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project for instruction regeneration",
        mission="Initial test mission",
        context_budget=10000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create initial orchestrator with old settings
    generator = ThinClientPromptGenerator(db_session, tenant_key)

    initial_field_priorities = {
        "product_core": 4,  # OLD: EXCLUDED
        "vision_documents": 4,  # OLD: EXCLUDED
    }

    result1 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=initial_field_priorities,
    )

    # ACT: Update field priorities to INCLUDE product_core
    updated_field_priorities = {
        "product_core": 1,  # NEW: CRITICAL (should appear in instructions)
        "vision_documents": 4,  # NEW: EXCLUDED (should NOT appear in instructions)
    }

    result2 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=updated_field_priorities,
    )

    # ASSERT: Verify response includes fresh instructions
    # NOTE: This test will FAIL initially (RED) because generate() doesn't yet
    # regenerate instructions - it only updates metadata
    assert "instructions" in result2 or "mission" in result2, \
        "Response should include regenerated instructions"

    # ASSERT: Verify instructions reflect updated field priorities
    # Since product_core is now CRITICAL (priority 1), it should appear in instructions
    instructions = result2.get("instructions") or result2.get("mission") or ""

    # This will FAIL initially (RED) - we expect the instructions to be regenerated
    assert "Core feature set" in instructions or len(instructions) > 100, \
        "Instructions should be regenerated with updated context (product_core is CRITICAL)"


@pytest.mark.asyncio
async def test_stage_project_returns_fresh_prompt_after_settings_change(db_session: AsyncSession):
    """
    Test that staging returns fresh prompt after user changes settings.

    User Story:
    1. User stages project (creates orchestrator with settings A)
    2. User changes field priorities in settings (settings B)
    3. User clicks "Stage Project" again
    4. User receives UPDATED prompt with settings B (not stale settings A)

    Expected:
    - Response should include fresh instructions
    - Instructions should reflect current user settings, not old settings
    - User can copy and paste updated prompt immediately
    """
    # ARRANGE: Create tenant, user, product, project
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        password_hash=bcrypt.hash("Test@Pass123"),
        tenant_key=tenant_key,
        field_priority_config={
            "priorities": {
                "product_core": 2,  # Initial: IMPORTANT
                "vision_documents": 3,  # Initial: NICE_TO_HAVE
                "tech_stack": 2,  # Initial: IMPORTANT
            }
        },
    )
    db_session.add(user)

    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Product for testing prompt freshness - Product core content included",
    )
    db_session.add(product)

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Project for testing prompt freshness",
        mission="Test mission for prompt refresh",
        context_budget=10000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create initial orchestrator
    generator = ThinClientPromptGenerator(db_session, tenant_key)

    initial_field_priorities = {
        "product_core": 2,  # IMPORTANT
        "vision_documents": 3,  # NICE_TO_HAVE
        "tech_stack": 2,  # IMPORTANT
    }

    result1 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=initial_field_priorities,
    )

    # ACT: User changes settings (promotes product_core to CRITICAL)
    updated_field_priorities = {
        "product_core": 1,  # CRITICAL (upgraded from IMPORTANT)
        "vision_documents": 4,  # EXCLUDED (downgraded from NICE_TO_HAVE)
        "tech_stack": 2,  # IMPORTANT (unchanged)
    }

    result2 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=updated_field_priorities,
    )

    # ASSERT: Response includes fresh prompt
    assert "thin_prompt" in result2, "Response should include thin_prompt"

    # ASSERT: Response includes fresh instructions
    # This will FAIL initially (RED) - we expect instructions to be returned
    assert "instructions" in result2 or "mission" in result2, \
        "Response should include fresh instructions for user to copy"

    # ASSERT: Instructions are not empty
    instructions = result2.get("instructions") or result2.get("mission") or ""
    assert len(instructions) > 50, \
        "Fresh instructions should be non-trivial (>50 chars)"


@pytest.mark.asyncio
async def test_multiple_stage_clicks_keep_same_orchestrator_id(db_session: AsyncSession):
    """
    Test that multiple "Stage Project" clicks reuse the same orchestrator.

    Scenario:
    1. User clicks "Stage Project" (creates orchestrator A)
    2. User clicks "Stage Project" again (reuses orchestrator A)
    3. User clicks "Stage Project" third time (still reuses orchestrator A)

    Expected:
    - All three generate() calls return the same orchestrator_id
    - Metadata is updated each time
    - No duplicate orchestrators created
    """
    # ARRANGE: Create tenant, user, product, project
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        password_hash=bcrypt.hash("Test@Pass123"),
        tenant_key=tenant_key,
        field_priority_config={
            "priorities": {"product_core": 1}
        },
    )
    db_session.add(user)

    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Product for testing multiple stage clicks",
    )
    db_session.add(product)

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Project for testing multiple stage clicks",
        mission="Test mission",
        context_budget=10000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # ACT: Click "Stage Project" three times
    generator = ThinClientPromptGenerator(db_session, tenant_key)

    field_priorities = {"product_core": 1}

    result1 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=field_priorities,
    )

    result2 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=field_priorities,
    )

    result3 = await generator.generate(
        project_id=project.id,
        user_id=str(user.id),
        tool="claude-code",
        instance_number=1,
        field_priorities=field_priorities,
    )

    # ASSERT: All three calls return same orchestrator_id
    assert result1["orchestrator_id"] == result2["orchestrator_id"], \
        "Second stage should reuse orchestrator from first stage"
    assert result2["orchestrator_id"] == result3["orchestrator_id"], \
        "Third stage should reuse orchestrator from previous stages"

    # ASSERT: Only one orchestrator exists in database
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project.id,
        MCPAgentJob.agent_type == "orchestrator",
        MCPAgentJob.tenant_key == tenant_key,
    )
    result = await db_session.execute(stmt)
    orchestrators = result.scalars().all()

    assert len(orchestrators) == 1, \
        "Only one orchestrator should exist (no duplicates created)"
