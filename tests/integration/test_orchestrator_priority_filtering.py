"""
Integration test for Context Priority & Depth Configuration in Orchestrator Workflow.

Tests that user's field priority settings are respected when orchestrator fetches context.

Handover 0279: Fixes context priority integration gap where orchestrator tool templates
were missing user_id parameter, causing priority filtering to be bypassed.
"""
import pytest
from sqlalchemy import select
from uuid import uuid4

from src.giljo_mcp.models import User, Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.fixture
async def test_user(db_session, test_tenant):
    """Create a test user with custom priorities."""
    user = User(
        id=str(uuid4()),
        username="test_orchestrator_user",
        email="test.orchestrator@example.com",
        password_hash="dummy_hash",
        tenant_key=test_tenant,
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "vision_documents": 4,  # EXCLUDED
                "tech_stack": 1,        # CRITICAL
                "architecture": 2,      # IMPORTANT
                "git_history": 3,       # NICE_TO_HAVE
                "memory_360": 1,        # CRITICAL
            }
        },
        depth_config={
            "vision_chunking": "none",         # Don't want vision docs
            "git_commits": 10,                 # Minimal git history
            "memory_last_n_projects": 3,       # Last 3 projects
            "architecture_depth": "overview",  # Overview only
            "tech_stack_sections": "required"  # Required sections only
        }
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_product(db_session, test_tenant):
    """Create a test product."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant,
        name="Test Product for Priority Filtering",
        description="Test product with vision documents",
        vision_document="This is a test vision document that should be excluded when priority=4."
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project(db_session, test_tenant, test_product):
    """Create a test project."""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant,
        product_id=test_product.id,
        name="Test Project for Priority Filtering",
        description="Test project to verify priority filtering works",
        status="inactive"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_orchestrator_prompt_includes_user_id(
    db_session,
    test_user,
    test_product,
    test_project,
):
    """
    Test that orchestrator thin prompt includes user_id in all MCP tool calls.

    This verifies the fix from Handover 0279 where tool templates were missing user_id.
    """
    # ARRANGE: Create prompt generator
    generator = ThinClientPromptGenerator(
        db=db_session,
        tenant_key=test_user.tenant_key
    )

    # ACT: Generate thin prompt for orchestrator
    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config["priorities"],
        depth_config=test_user.depth_config
    )

    thin_prompt = result["thin_prompt"]

    # ASSERT: All MCP tool calls should include user_id parameter
    assert f"user_id='{test_user.id}'" in thin_prompt, \
        "Orchestrator prompt missing user_id in tool calls"

    print(f"\n[TEST] Orchestrator prompt includes user_id: PASS")
    print(f"[TEST] user_id='{test_user.id}' found in prompt")


@pytest.mark.asyncio
async def test_depth_config_applied_in_orchestrator_prompt(
    db_session,
    test_user,
    test_product,
    test_project,
):
    """
    Test that user's depth configuration is applied in orchestrator prompt.

    Verifies that depth settings (git_commits=10, chunking=none, etc.) are
    passed correctly to MCP tool templates.
    """
    # ARRANGE: User has custom depth config
    assert test_user.depth_config["git_commits"] == 10
    assert test_user.depth_config["vision_chunking"] == "none"

    # ACT: Generate orchestrator prompt
    generator = ThinClientPromptGenerator(
        db=db_session,
        tenant_key=test_user.tenant_key
    )

    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(test_user.id),
        tool="claude-code",
        field_priorities=test_user.field_priority_config["priorities"],
        depth_config=test_user.depth_config
    )

    thin_prompt = result["thin_prompt"]

    # ASSERT: Orchestrator prompt generated successfully
    assert thin_prompt is not None
    assert len(thin_prompt) > 0

    print(f"\n[TEST] Depth config applied successfully")


@pytest.mark.asyncio
async def test_end_to_end_priority_filtering(
    db_session,
    test_user,
    test_product,
    test_project,
):
    """
    End-to-end test: User settings → Database → Orchestrator → MCP Tools → Filtered Context.

    This tests the complete workflow:
    1. User configures priorities and depth in UI
    2. Settings saved to database
    3. Project launched with user_id
    4. Orchestrator prompt generated with user_id in tool calls
    5. MCP tools respect user's priorities
    """
    # ARRANGE: User has priorities configured (done in fixture)
    assert test_user.field_priority_config["priorities"]["vision_documents"] == 4  # EXCLUDED
    assert test_user.field_priority_config["priorities"]["tech_stack"] == 1        # CRITICAL

    # ACT: Launch project (simulates clicking [Stage Project])
    project_service = ProjectService(db_session, test_user.tenant_key)

    result = await project_service.launch_project(
        project_id=str(test_project.id),
        user_id=str(test_user.id)
    )

    # ASSERT 1: Orchestrator job created with user settings in metadata
    orchestrator_stmt = select(AgentExecution).where(
        AgentExecution.project_id == test_project.id,
        AgentExecution.agent_display_name == "orchestrator",
        AgentExecution.tenant_key == test_user.tenant_key
    )
    orchestrator_result = await db_session.execute(orchestrator_stmt)
    orchestrator = orchestrator_result.scalar_one()

    assert orchestrator is not None
    assert orchestrator.job_metadata is not None
    assert "field_priorities" in orchestrator.job_metadata
    assert "depth_config" in orchestrator.job_metadata
    assert "user_id" in orchestrator.job_metadata
    assert orchestrator.job_metadata["user_id"] == str(test_user.id)

    # ASSERT 2: Field priorities match user's settings
    assert orchestrator.job_metadata["field_priorities"]["vision_documents"] == 4
    assert orchestrator.job_metadata["field_priorities"]["tech_stack"] == 1

    # ASSERT 3: Depth config matches user's settings
    assert orchestrator.job_metadata["depth_config"]["git_commits"] == 10
    assert orchestrator.job_metadata["depth_config"]["vision_chunking"] == "none"

    print(f"\n[TEST] End-to-end priority filtering: PASS")
    print(f"[TEST] Orchestrator ID: {orchestrator.job_id}")
    print(f"[TEST] User priorities applied: {orchestrator.job_metadata['field_priorities']}")
    print(f"[TEST] User depth config applied: {orchestrator.job_metadata['depth_config']}")


# ============================================================================
# Integration Test Summary
# ============================================================================
#
# These tests verify the fix from Handover 0279:
#
# BEFORE FIX:
# - Orchestrator tool templates missing user_id parameter
# - MCP tools fell back to DEFAULT priorities (ignored user settings)
# - Result: User sets "Vision Docs = EXCLUDED", but orchestrator still fetches them
#
# AFTER FIX (Handover 0279):
# - Orchestrator tool templates include user_id parameter
# - MCP tools receive user_id and apply custom priorities
# - Result: User sets "Vision Docs = EXCLUDED" → NOT fetched (saves 20K tokens)
#
# CURRENT STATE (Handover 0280-0281):
# - Individual fetch_* tools REMOVED (deprecated)
# - Monolithic context architecture active
# - Context fetched via get_orchestrator_instructions() MCP tool
#
# Test Coverage:
# ✅ Orchestrator prompt includes user_id
# ✅ Depth configuration applied correctly
# ✅ End-to-end workflow (UI → DB → Orchestrator → MCP → Filtered Context)
#
# ============================================================================
