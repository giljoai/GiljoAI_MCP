"""
Integration tests for orchestrator job_metadata pipeline (Handover 0275).

Tests the complete flow from user settings to orchestrator job creation:
1. User configures field priorities in My Settings → Context
2. User clicks "Stage Project" button
3. Frontend calls /api/v1/prompts/staging/{project_id}
4. Backend creates/reuses orchestrator with job_metadata populated
5. job_metadata includes field_priorities, depth_config, user_id, tool

Critical for context prioritization and orchestration (v2.0).

Author: Backend Integration Tester Agent
Date: 2025-11-30
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentExecution


@pytest.mark.asyncio
async def test_orchestrator_metadata_new_creation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
    test_product,
    auth_headers,
):
    """
    Test orchestrator metadata is populated on NEW orchestrator creation.

    Flow:
    1. User has field priorities configured
    2. User clicks "Stage Project" for the first time
    3. /api/v1/prompts/staging creates NEW orchestrator
    4. job_metadata contains field_priorities, depth_config, user_id, tool
    """
    # Setup: Create test project
    project = Project(
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        name="Test Orchestrator Metadata",
        description="Integration test for metadata flow",
        mission="Test orchestrator mission",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Setup: Configure user field priorities (simulating My Settings → Context)
    test_user.field_priority_config = {
        "version": "2.0",
        "priorities": {
            "product_core": 1,  # CRITICAL
            "vision_documents": 2,  # IMPORTANT
            "tech_stack": 1,  # CRITICAL
            "architecture": 2,  # IMPORTANT
            "testing": 3,  # NICE_TO_HAVE
            "memory_360": 3,  # NICE_TO_HAVE
            "git_history": 4,  # EXCLUDED
            "agent_templates": 1,  # CRITICAL
            "project_description": 2,  # IMPORTANT
        },
    }
    test_user.depth_config = {
        "vision_chunking": "medium",
        "memory_last_n_projects": 3,
        "git_commits": 25,
        "agent_template_detail": "standard",
        "tech_stack_sections": "all",
        "architecture_depth": "overview",
    }
    await db_session.commit()
    await db_session.refresh(test_user)

    # ACT: Simulate "Stage Project" button click
    response = await async_client.get(
        f"/api/v1/prompts/staging/{project.id}",
        params={"tool": "claude-code"},
        headers=auth_headers,
    )

    # ASSERT: API returns success with orchestrator_id
    assert response.status_code == 200, f"API failed: {response.text}"
    data = response.json()
    assert "orchestrator_id" in data
    assert "prompt" in data

    orchestrator_id = data["orchestrator_id"]

    # ASSERT: Orchestrator exists in database with job_metadata
    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    result = await db_session.execute(stmt)
    orchestrator = result.scalar_one()

    assert orchestrator is not None
    assert orchestrator.agent_display_name == "orchestrator"
    assert orchestrator.status == "waiting"
    assert orchestrator.project_id == project.id
    assert orchestrator.tenant_key == test_user.tenant_key

    # CRITICAL: job_metadata must be populated (NOT empty {})
    assert orchestrator.job_metadata is not None, "job_metadata is None"
    assert orchestrator.job_metadata != {}, "job_metadata is empty dict"

    # CRITICAL: job_metadata contains field priorities from user settings
    assert "field_priorities" in orchestrator.job_metadata
    field_priorities = orchestrator.job_metadata["field_priorities"]
    assert field_priorities == test_user.field_priority_config["priorities"]
    assert field_priorities["product_core"] == 1
    assert field_priorities["git_history"] == 4

    # CRITICAL: job_metadata contains depth config from user settings
    assert "depth_config" in orchestrator.job_metadata
    depth_config = orchestrator.job_metadata["depth_config"]
    assert depth_config["vision_chunking"] == "medium"
    assert depth_config["memory_last_n_projects"] == 3
    assert depth_config["git_commits"] == 25

    # CRITICAL: job_metadata contains user_id for audit trail
    assert "user_id" in orchestrator.job_metadata
    assert orchestrator.job_metadata["user_id"] == str(test_user.id)

    # CRITICAL: job_metadata contains tool type
    assert "tool" in orchestrator.job_metadata
    assert orchestrator.job_metadata["tool"] == "claude-code"

    # CRITICAL: job_metadata tracks creation method
    assert "created_via" in orchestrator.job_metadata
    assert orchestrator.job_metadata["created_via"] == "thin_client_generator"


@pytest.mark.asyncio
async def test_orchestrator_metadata_reuse_updates(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
    test_product,
    auth_headers,
):
    """
    Test orchestrator metadata is UPDATED when reusing existing orchestrator.

    BUG FIX TEST: Before fix, reusing existing orchestrator would NOT update
    job_metadata, leaving it as empty {} from old orchestrator creation.

    Flow:
    1. User creates orchestrator (old version, metadata={})
    2. User updates field priorities in My Settings
    3. User clicks "Stage Project" again
    4. ThinClientPromptGenerator reuses existing orchestrator
    5. BUG FIX: job_metadata is UPDATED with new field priorities
    """
    # Setup: Create test project
    project = Project(
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        name="Test Orchestrator Reuse",
        description="Test metadata update on reuse",
        mission="Test orchestrator mission",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Setup: Create OLD orchestrator with empty metadata (simulating pre-0315 code)
    old_orchestrator = AgentExecution(
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        job_id="f73f6798-5922-4813-bc80-802c68ce1645",  # Use actual UUID from bug report
        agent_name="Orchestrator",
        agent_display_name="orchestrator",
        status="waiting",
        mission="Old orchestrator mission",
        tool_type="claude-code",
        job_metadata={},  # OLD: Empty metadata (the bug we're fixing)
    )
    db_session.add(old_orchestrator)
    await db_session.commit()

    # Setup: User updates field priorities (simulating My Settings → Context)
    test_user.field_priority_config = {
        "version": "2.0",
        "priorities": {
            "product_core": 1,
            "vision_documents": 2,
            "tech_stack": 1,
            "architecture": 2,
            "testing": 3,
            "memory_360": 3,
            "git_history": 4,
            "agent_templates": 1,
            "project_description": 2,
        },
    }
    test_user.depth_config = {
        "vision_chunking": "full",  # Changed from default
        "memory_last_n_projects": 5,  # Changed from default
        "git_commits": 50,  # Changed from default
        "agent_template_detail": "full",  # Changed from default
        "tech_stack_sections": "required",
        "architecture_depth": "detailed",
    }
    await db_session.commit()
    await db_session.refresh(test_user)

    # ACT: User clicks "Stage Project" again (should reuse AND UPDATE metadata)
    response = await async_client.get(
        f"/api/v1/prompts/staging/{project.id}",
        params={"tool": "claude-code"},
        headers=auth_headers,
    )

    # ASSERT: API returns success with same orchestrator_id
    assert response.status_code == 200, f"API failed: {response.text}"
    data = response.json()
    assert data["orchestrator_id"] == old_orchestrator.job_id  # Reused existing

    # ASSERT: Orchestrator metadata is NOW POPULATED (bug fix verification)
    await db_session.refresh(old_orchestrator)

    # CRITICAL BUG FIX: job_metadata must be UPDATED (not left as {})
    assert old_orchestrator.job_metadata is not None
    assert old_orchestrator.job_metadata != {}, "BUG NOT FIXED: job_metadata still empty on reuse"

    # CRITICAL: Updated field priorities match user's current settings
    assert "field_priorities" in old_orchestrator.job_metadata
    field_priorities = old_orchestrator.job_metadata["field_priorities"]
    assert field_priorities == test_user.field_priority_config["priorities"]
    assert field_priorities["memory_360"] == 3

    # CRITICAL: Updated depth config matches user's current settings
    assert "depth_config" in old_orchestrator.job_metadata
    depth_config = old_orchestrator.job_metadata["depth_config"]
    assert depth_config["vision_chunking"] == "full"  # User's updated value
    assert depth_config["memory_last_n_projects"] == 5  # User's updated value
    assert depth_config["git_commits"] == 50  # User's updated value

    # CRITICAL: user_id is populated
    assert old_orchestrator.job_metadata["user_id"] == str(test_user.id)

    # CRITICAL: tool is populated
    assert old_orchestrator.job_metadata["tool"] == "claude-code"

    # CRITICAL: reused_at timestamp is present (new field from fix)
    assert "reused_at" in old_orchestrator.job_metadata


@pytest.mark.asyncio
async def test_orchestrator_metadata_default_values(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
    test_product,
    auth_headers,
):
    """
    Test orchestrator metadata uses defaults when user has no custom settings.

    Flow:
    1. User has NO field_priority_config or depth_config configured
    2. User clicks "Stage Project"
    3. Orchestrator is created with default field_priorities={} and depth_config
    """
    # Setup: Create test project
    project = Project(
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        name="Test Orchestrator Defaults",
        description="Test default metadata values",
        mission="Test orchestrator mission",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Setup: User has NO custom settings (simulating fresh user)
    test_user.field_priority_config = None
    test_user.depth_config = None
    await db_session.commit()
    await db_session.refresh(test_user)

    # ACT: User clicks "Stage Project"
    response = await async_client.get(
        f"/api/v1/prompts/staging/{project.id}",
        params={"tool": "codex"},
        headers=auth_headers,
    )

    # ASSERT: API returns success
    assert response.status_code == 200
    data = response.json()
    orchestrator_id = data["orchestrator_id"]

    # ASSERT: Orchestrator has default metadata values
    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    result = await db_session.execute(stmt)
    orchestrator = result.scalar_one()

    assert orchestrator.job_metadata is not None
    assert "field_priorities" in orchestrator.job_metadata
    assert orchestrator.job_metadata["field_priorities"] == {}  # Default: empty

    # Default depth_config values (from ThinClientPromptGenerator line 179-186)
    assert "depth_config" in orchestrator.job_metadata
    depth_config = orchestrator.job_metadata["depth_config"]
    assert depth_config["vision_chunking"] == "medium"
    assert depth_config["memory_last_n_projects"] == 3
    assert depth_config["git_commits"] == 25
    assert depth_config["agent_template_detail"] == "standard"
    assert depth_config["tech_stack_sections"] == "all"
    assert depth_config["architecture_depth"] == "overview"

    assert orchestrator.job_metadata["tool"] == "codex"
    assert orchestrator.job_metadata["user_id"] == str(test_user.id)
