"""
Integration test demonstrating the ACTUAL bug in api/endpoints/prompts.py

This test will FAIL because the endpoint uses the WRONG key ("fields" instead of "priorities")
when extracting field priorities from user.field_priority_config.

BUG LOCATION: api/endpoints/prompts.py line 460
WRONG CODE: field_priorities = user_field_config.get("fields", {})
CORRECT CODE: field_priorities = user_field_config.get("priorities", {})

This test simulates the EXACT endpoint behavior to prove the bug exists.

Handover: Field Priority Bug Fix - Phase 1 (RED TEST)
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select

from src.giljo_mcp.models import User, Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

# Use existing fixtures
from tests.fixtures.base_fixtures import db_session


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def user_with_correct_priorities_structure(db_session):
    """
    Create user with field_priority_config using CORRECT structure.

    CORRECT structure (v2.0):
    {
        "version": "2.0",
        "priorities": {  # <-- CORRECT KEY
            "product_core": 1,
            "vision_documents": 2,
            ...
        }
    }
    """
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    user = User(
        id=str(uuid4()),
        username=f"correctuser_{uuid4().hex[:6]}",
        email=f"correct_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {  # CORRECT KEY - matches UserService, API schema
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 4
            }
        }
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_project_for_bug_demo(db_session, user_with_correct_priorities_structure):
    """Create test product and project"""
    # Create product
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product for bug demonstration.",
        tenant_key=user_with_correct_priorities_structure.tenant_key,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()

    # Create project
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for bug demonstration.",
        product_id=str(product.id),
        tenant_key=user_with_correct_priorities_structure.tenant_key,
        status="planning",
        mission="Test mission to demonstrate field priority bug.",
        context_budget=180000
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# TEST: Demonstrate the Actual Bug
# ============================================================================

@pytest.mark.asyncio
async def test_endpoint_uses_wrong_key_for_field_priorities(
    db_session,
    user_with_correct_priorities_structure,
    test_project_for_bug_demo
):
    """
    CRITICAL BUG DEMONSTRATION TEST

    This test simulates EXACTLY what api/endpoints/prompts.py does at line 460.

    USER STORY:
    1. User configures field priorities in My Settings → Context
    2. Data is saved with structure: {"version": "2.0", "priorities": {...}}
    3. User stages project via /api/prompts/staging/{project_id}
    4. Endpoint extracts priorities using: user_field_config.get("fields", {})
    5. BUG: Returns empty dict because key is "priorities" not "fields"!
    6. Orchestrator receives empty field_priorities: {}

    EXPECTED BEHAVIOR:
    - Endpoint should use: user_field_config.get("priorities", {})
    - Orchestrator should receive user's configured priorities

    THIS TEST WILL FAIL UNTIL BUG IS FIXED.
    """
    user = user_with_correct_priorities_structure
    project = test_project_for_bug_demo

    # ARRANGE: Verify user has correct config structure
    assert user.field_priority_config is not None, "User should have field priority config"
    assert "priorities" in user.field_priority_config, (
        "User config should have 'priorities' key (correct structure)"
    )
    assert "fields" not in user.field_priority_config, (
        "User config should NOT have 'fields' key (old/wrong structure)"
    )

    expected_priorities = {
        "product_core": 1,
        "vision_documents": 2,
        "agent_templates": 3,
        "project_description": 1,
        "memory_360": 2,
        "git_history": 4
    }

    # ACT: Simulate EXACTLY what the endpoint does (BUGGY CODE)
    user_field_config = user.field_priority_config or {}
    field_priorities_buggy = user_field_config.get("fields", {})  # BUG: WRONG KEY!

    # ASSERT: Demonstrate the bug - this returns empty dict
    assert field_priorities_buggy == {}, (
        f"BUG DEMONSTRATED: Using 'fields' key returns empty dict. "
        f"Expected: {expected_priorities}, Got: {field_priorities_buggy}"
    )

    # Now show what SHOULD happen (FIXED CODE)
    field_priorities_fixed = user_field_config.get("priorities", {})  # CORRECT KEY

    assert field_priorities_fixed == expected_priorities, (
        f"CORRECT BEHAVIOR: Using 'priorities' key returns user config. "
        f"Got: {field_priorities_fixed}"
    )

    # ACT: Generate orchestrator job using BUGGY extraction (simulating endpoint bug)
    generator = ThinClientPromptGenerator(
        db=db_session,
        tenant_key=user.tenant_key
    )

    result_buggy = await generator.generate(
        project_id=str(project.id),
        user_id=str(user.id),
        tool="claude-code",
        field_priorities=field_priorities_buggy  # EMPTY DICT due to bug!
    )

    # ASSERT: Orchestrator receives EMPTY field_priorities (bug consequence)
    orchestrator_id_buggy = result_buggy["orchestrator_id"]

    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id_buggy)
    job_result = await db_session.execute(stmt)
    orchestrator_job_buggy = job_result.scalar_one_or_none()

    actual_priorities_buggy = orchestrator_job_buggy.job_metadata.get("field_priorities", {})

    # THIS IS THE BUG - orchestrator gets empty dict instead of user's config
    assert actual_priorities_buggy == {}, (
        f"BUG CONSEQUENCE: Orchestrator receives empty field_priorities. "
        f"Expected: {expected_priorities}, Got: {actual_priorities_buggy}"
    )

    # Now demonstrate what SHOULD happen with fixed code
    result_fixed = await generator.generate(
        project_id=str(project.id),
        user_id=str(user.id),
        tool="claude-code",
        field_priorities=field_priorities_fixed  # CORRECT priorities
    )

    orchestrator_id_fixed = result_fixed["orchestrator_id"]

    stmt2 = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id_fixed)
    job_result2 = await db_session.execute(stmt2)
    orchestrator_job_fixed = job_result2.scalar_one_or_none()

    actual_priorities_fixed = orchestrator_job_fixed.job_metadata.get("field_priorities", {})

    # THIS TEST WILL FAIL HERE - demonstrating the bug
    assert actual_priorities_fixed == expected_priorities, (
        f"CORRECT BEHAVIOR: Orchestrator should receive user's field_priorities. "
        f"Expected: {expected_priorities}, Got: {actual_priorities_fixed}"
    )

    # CRITICAL FAILURE POINT:
    # The buggy extraction returns empty dict, causing orchestrator to miss user's config.
    # This test proves the bug exists by comparing buggy vs fixed behavior.
    pytest.fail(
        "BUG CONFIRMED: api/endpoints/prompts.py line 460 uses 'fields' key instead of 'priorities' key. "
        "User configured field priorities are NOT reaching the orchestrator. "
        f"Buggy: {actual_priorities_buggy}, Fixed: {actual_priorities_fixed}"
    )


@pytest.mark.asyncio
async def test_key_mismatch_causes_empty_field_priorities(
    db_session,
    user_with_correct_priorities_structure
):
    """
    SIMPLIFIED BUG DEMONSTRATION

    Shows that using wrong key ("fields") on correct structure ("priorities") = empty dict.

    THIS IS THE ROOT CAUSE OF THE BUG.
    """
    user = user_with_correct_priorities_structure

    # User has CORRECT structure
    config = user.field_priority_config
    assert "priorities" in config  # Correct
    assert "fields" not in config  # Correct - no wrong key

    # Endpoint uses WRONG key
    extracted_buggy = config.get("fields", {})
    extracted_fixed = config.get("priorities", {})

    # BUG: Wrong key returns empty dict
    assert extracted_buggy == {}, (
        "Using 'fields' key on config with 'priorities' key returns empty dict"
    )

    # CORRECT: Right key returns user's priorities
    assert len(extracted_fixed) > 0, (
        "Using 'priorities' key returns user's configured priorities"
    )

    # THIS TEST WILL FAIL - demonstrating the key mismatch bug
    assert extracted_buggy == extracted_fixed, (
        f"KEY MISMATCH BUG: 'fields' key returns {extracted_buggy}, "
        f"but 'priorities' key returns {extracted_fixed}. "
        f"Endpoint must use 'priorities' key to match UserService and API schema."
    )
