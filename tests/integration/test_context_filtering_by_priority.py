"""
Integration tests for context filtering by field priority - TDD Phase 1 (RED)

This test suite verifies that context filtering respects field priorities,
specifically that contexts with priority 4 (EXCLUDED) don't appear in
the orchestrator mission.

BUG CONTEXT:
- User sets priority 4 (EXCLUDED) for certain context categories
- Orchestrator should NOT receive these contexts in mission
- Bug: Empty field_priorities dict means filtering doesn't work

These tests will initially FAIL to confirm the bug exists.

Handover: Field Priority Bug Fix - Phase 1
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Product, Project, User
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
async def user_excluding_git_history(db_session, test_tenant_key):
    """Create user who EXCLUDES git_history (priority 4)"""
    user = User(
        id=str(uuid4()),
        username=f"nogit_{uuid4().hex[:6]}",
        email=f"nogit_{uuid4().hex[:6]}@example.com",
        tenant_key=test_tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 4,  # EXCLUDED
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_excluding_vision_and_memory(db_session, test_tenant_key):
    """Create user who EXCLUDES vision_documents and memory_360 (priority 4)"""
    user = User(
        id=str(uuid4()),
        username=f"minimal_{uuid4().hex[:6]}",
        email=f"minimal_{uuid4().hex[:6]}@example.com",
        tenant_key=test_tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 4,  # EXCLUDED
                "agent_templates": 2,
                "project_description": 1,
                "memory_360": 4,  # EXCLUDED
                "git_history": 3,
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_including_everything(db_session, test_tenant_key):
    """Create user who includes ALL contexts (no priority 4)"""
    user = User(
        id=str(uuid4()),
        username=f"allcontext_{uuid4().hex[:6]}",
        email=f"allcontext_{uuid4().hex[:6]}@example.com",
        tenant_key=test_tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 1,
                "agent_templates": 2,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 3,
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product_with_vision(db_session, test_tenant_key):
    """Create product WITH vision documents"""
    product = Product(
        id=str(uuid4()),
        name=f"Product with Vision {uuid4().hex[:8]}",
        description="Test product with vision documents.",
        tenant_key=test_tenant_key,
        is_active=True,
        # Add vision document metadata (simplified)
        product_memory={
            "vision_documents": [
                {"title": "Vision Doc 1", "content": "Vision content 1"},
                {"title": "Vision Doc 2", "content": "Vision content 2"},
            ],
            "sequential_history": [
                {"sequence": 1, "summary": "Project 1 completed"},
                {"sequence": 2, "summary": "Project 2 completed"},
            ],
        },
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project_for_filtering(db_session, test_product_with_vision, test_tenant_key):
    """Create test project for context filtering tests"""
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for context filtering.",
        product_id=str(test_product_with_vision.id),
        tenant_key=test_tenant_key,
        status="planning",
        mission="Test mission for context filtering.",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# TEST 3: Context Filtering Based on Priority 4 (EXCLUDED)
# ============================================================================


@pytest.mark.asyncio
async def test_priority_4_contexts_excluded_from_mission(
    db_session, user_excluding_git_history, test_project_for_filtering
):
    """
    TEST 3a: Contexts with priority 4 (EXCLUDED) should NOT appear in mission.

    USER STORY:
    1. User sets git_history priority to 4 (EXCLUDED) in My Settings
    2. User stages project
    3. Orchestrator mission should NOT contain git history data
    4. Other contexts (priority 1-3) should still appear

    BUG:
    When field_priorities is empty dict (due to "fields" vs "priorities" bug),
    the context filter doesn't work - ALL contexts appear regardless of user settings.

    This test will FAIL because empty field_priorities means no filtering.
    """
    # ARRANGE: Extract user priorities (FIXED behavior)
    user_field_config = user_excluding_git_history.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # Verify user has excluded git_history
    assert field_priorities.get("git_history") == 4, "User should have git_history set to priority 4 (EXCLUDED)"

    # ACT: Generate orchestrator staging prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_excluding_git_history.tenant_key)

    result = await generator.generate(
        project_id=str(test_project_for_filtering.id),
        user_id=str(user_excluding_git_history.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    # Get the generated prompt/mission
    thin_prompt = result.get("thin_prompt", "")

    # ASSERT: Mission should NOT contain git history references
    # (This will fail if filtering isn't working)

    # Git history keywords that should be excluded
    git_keywords = ["git_history", "Git History", "fetch_git_history", "git commits", "commit history"]

    for keyword in git_keywords:
        assert keyword.lower() not in thin_prompt.lower(), (
            f"Mission should NOT contain '{keyword}' when git_history priority is 4 (EXCLUDED). "
            f"BUG: Empty field_priorities dict means filtering didn't work."
        )

    # But other contexts should still be present
    expected_contexts = [
        "product_core",  # Priority 1
        "vision_documents",  # Priority 2
        "project_description",  # Priority 1
    ]

    # At least one expected context should be mentioned
    # (This verifies filtering is selective, not blocking everything)
    has_expected_context = any(ctx.lower() in thin_prompt.lower() for ctx in expected_contexts)

    assert has_expected_context, (
        "Mission should contain other contexts (priority 1-3) even when some are excluded. "
        "Expected at least one of: product_core, vision_documents, project_description"
    )


@pytest.mark.asyncio
async def test_multiple_excluded_contexts_filtered(
    db_session, user_excluding_vision_and_memory, test_project_for_filtering
):
    """
    TEST 3b: Multiple contexts with priority 4 should ALL be excluded.

    USER STORY:
    1. User excludes BOTH vision_documents AND memory_360 (priority 4)
    2. User stages project
    3. Neither vision nor 360 memory should appear in mission
    4. Other contexts should still appear

    This tests that filtering works for multiple exclusions.
    """
    # ARRANGE: Extract user priorities
    user_field_config = user_excluding_vision_and_memory.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # Verify user has excluded both
    assert field_priorities.get("vision_documents") == 4
    assert field_priorities.get("memory_360") == 4

    # ACT: Generate orchestrator prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_excluding_vision_and_memory.tenant_key)

    result = await generator.generate(
        project_id=str(test_project_for_filtering.id),
        user_id=str(user_excluding_vision_and_memory.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    thin_prompt = result.get("thin_prompt", "")

    # ASSERT: Neither vision_documents nor memory_360 should appear
    vision_keywords = ["vision_documents", "Vision Documents", "fetch_vision_document", "product vision"]

    memory_keywords = ["memory_360", "360 Memory", "fetch_360_memory", "project closeout"]

    for keyword in vision_keywords:
        assert keyword.lower() not in thin_prompt.lower(), (
            f"Mission should NOT contain '{keyword}' when vision_documents priority is 4"
        )

    for keyword in memory_keywords:
        assert keyword.lower() not in thin_prompt.lower(), (
            f"Mission should NOT contain '{keyword}' when memory_360 priority is 4"
        )

    # But other contexts should still be present
    assert "product_core" in thin_prompt.lower() or "product" in thin_prompt.lower(), (
        "product_core (priority 1) should still appear"
    )


@pytest.mark.asyncio
async def test_priority_1_2_3_contexts_included(db_session, user_including_everything, test_project_for_filtering):
    """
    TEST 3c: Contexts with priority 1-3 should appear in mission.

    USER STORY:
    1. User includes ALL contexts (no priority 4 exclusions)
    2. User stages project
    3. All context categories should appear in mission

    This confirms that non-excluded contexts are properly included.
    """
    # ARRANGE: Extract user priorities
    user_field_config = user_including_everything.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # Verify user has NO exclusions (no priority 4)
    for category, priority in field_priorities.items():
        assert priority in {1, 2, 3}, f"User should not have priority 4 for any category. Got {category}={priority}"

    # ACT: Generate orchestrator prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_including_everything.tenant_key)

    result = await generator.generate(
        project_id=str(test_project_for_filtering.id),
        user_id=str(user_including_everything.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    thin_prompt = result.get("thin_prompt", "")

    # ASSERT: All context categories should be mentioned or available
    # (Even if not all data is included, the categories should be referenced)

    # At minimum, priority 1 (CRITICAL) contexts must be present
    critical_contexts = [cat for cat, pri in field_priorities.items() if pri == 1]

    for context in critical_contexts:
        # Look for context mention in prompt (flexible matching)
        context_mentioned = (
            context.lower() in thin_prompt.lower() or context.replace("_", " ").lower() in thin_prompt.lower()
        )

        assert context_mentioned, (
            f"Priority 1 (CRITICAL) context '{context}' should appear in mission. "
            f"User included all contexts, none should be filtered out."
        )


@pytest.mark.asyncio
async def test_empty_field_priorities_uses_system_defaults(db_session, test_project_for_filtering):
    """
    TEST 3d: When field_priorities is empty dict, system defaults should apply.

    USER STORY:
    1. User has NOT configured field priorities (field_priority_config=None)
    2. User stages project
    3. System default context filtering should apply

    BUG IMPACT:
    Currently, ALL orchestrators get empty field_priorities dict (even when user
    has configured priorities) due to "fields" vs "priorities" key mismatch.
    This means system defaults apply for EVERYONE, ignoring user preferences.

    This test documents expected behavior for truly unconfigured users.
    """
    # ARRANGE: Create user WITHOUT field priority configuration
    user_no_config = User(
        id=str(uuid4()),
        username=f"noconfig_{uuid4().hex[:6]}",
        email=f"noconfig_{uuid4().hex[:6]}@example.com",
        tenant_key=test_project_for_filtering.tenant_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config=None,  # NO CONFIG
    )
    db_session.add(user_no_config)
    await db_session.commit()

    # ACT: Generate prompt with empty field_priorities
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_no_config.tenant_key)

    result = await generator.generate(
        project_id=str(test_project_for_filtering.id),
        user_id=str(user_no_config.id),
        tool="claude-code",
        field_priorities={},  # Empty dict - use system defaults
    )

    thin_prompt = result.get("thin_prompt", "")

    # ASSERT: With system defaults, certain core contexts should appear
    # (This documents system default behavior)

    # System defaults should include at minimum:
    # - product_core (always critical)
    # - project_description (always critical)

    assert "product" in thin_prompt.lower(), "System defaults should include product_core context"

    assert "project" in thin_prompt.lower(), "System defaults should include project_description"


@pytest.mark.asyncio
async def test_field_priorities_affect_context_detail_level(
    db_session, user_including_everything, test_project_for_filtering
):
    """
    TEST 3e: Priority level (1-3) should affect context DETAIL level.

    USER STORY:
    - Priority 1 (CRITICAL): Full detail, always included
    - Priority 2 (IMPORTANT): Moderate detail, included if budget allows
    - Priority 3 (NICE_TO_HAVE): Minimal detail, included if budget remaining

    This tests that priorities affect not just inclusion, but detail level.
    """
    # ARRANGE: User with varied priorities
    user_field_config = user_including_everything.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # ACT: Generate prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_including_everything.tenant_key)

    result = await generator.generate(
        project_id=str(test_project_for_filtering.id),
        user_id=str(user_including_everything.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    # ASSERT: Verify priorities are stored for MCP tools to use
    # (Detail level filtering happens in MCP tools, not prompt generation)

    orchestrator_id = result["orchestrator_id"]

    from sqlalchemy import select

    from src.giljo_mcp.models.agent_identity import AgentExecution

    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one_or_none()

    stored_priorities = orchestrator_job.job_metadata.get("field_priorities", {})

    # CRITICAL: Priorities should be stored for MCP tools to use
    assert stored_priorities == field_priorities, (
        f"field_priorities should be stored for MCP tools to filter context detail. "
        f"Expected: {field_priorities}, Got: {stored_priorities}"
    )

    # Verify different priority levels are preserved
    priority_levels = set(stored_priorities.values())
    assert len(priority_levels) > 1, "User has varied priorities (1, 2, 3), all should be preserved"
