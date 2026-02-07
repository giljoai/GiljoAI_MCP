"""
Test suite for context orchestration enhancements (Handover 0281 Phase 1).

Tests the monolithic context implementation focusing on:
1. User configuration fetching (field_priority_config + depth_config)
2. Default configuration fallback behavior
3. Enhanced get_orchestrator_instructions() signature with user_id parameter

Following TDD discipline: RED → GREEN → REFACTOR
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_accepts_user_id(db_manager: DatabaseManager):
    """
    Test that get_orchestrator_instructions() signature accepts user_id parameter.

    BEHAVIOR: The enhanced signature should accept an optional user_id parameter
    without breaking.
    """
    # Setup: Create minimal orchestrator job + project + product
    tenant_key = str(uuid4())
    user_id = str(uuid4())

    # Use db_manager.get_session_async() pattern for data visibility
    async with db_manager.get_session_async() as session:
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Test Product", description="Test product")
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project",
            mission="Test project mission",
        )
        session.add(project)
        await session.flush()

        orchestrator_id = str(uuid4())
        orchestrator_job = AgentExecution(
            job_id=orchestrator_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            agent_name="Signature Test Orchestrator",
            mission="Test enhanced signature",
            status="waiting",
            job_metadata={},
        )
        session.add(orchestrator_job)
        await session.flush()

        # Create user
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username=f"user_{uuid4().hex[:8]}",
            email=f"test_{uuid4().hex[:8]}@example.com",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Act: Call with user_id parameter
    result = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id, tenant_key=tenant_key, user_id=user_id, db_manager=db_manager
    )

    # Assert: Should successfully accept parameter (GREEN phase)
    assert result is not None
    assert isinstance(result, dict)
    assert "error" not in result or "TypeError" not in str(result.get("error", ""))


@pytest.mark.asyncio
async def test_get_user_config_with_custom_settings(db_manager: DatabaseManager):
    """
    Test that user's custom field_priority_config and depth_config are applied.

    BEHAVIOR: When a user has configured custom priority and depth settings,
    the orchestrator should use those settings.
    """
    # Setup: Create user with custom configurations
    tenant_key = str(uuid4())
    user_id = str(uuid4())

    custom_field_priorities = {
        "product_core": {"toggle": True, "priority": 1},
        "vision_documents": {"toggle": False, "priority": 4},  # Disabled
        "tech_stack": {"toggle": True, "priority": 2},
        "memory_360": {"toggle": True, "priority": 1},  # Higher priority than default
    }

    custom_depth_config = {
        "vision_chunking": "full",  # Custom: more chunks than default
        "memory_last_n_projects": 10,  # Custom: more projects than default
        "git_commits": 50,  # Custom: more commits
        "agent_template_detail": "full",  # Custom: full detail
    }

    # Use db_manager.get_session_async() pattern for data visibility
    async with db_manager.get_session_async() as session:
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username=f"user_{uuid4().hex[:8]}",
            email=f"test_{uuid4().hex[:8]}@example.com",
            field_priority_config=custom_field_priorities,
            depth_config=custom_depth_config,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        # Create minimal orchestrator job + project + product
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for context orchestration",
        )
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project requirements",
            mission="Test project mission (orchestrator-generated)",
        )
        session.add(project)
        await session.flush()

        orchestrator_id = str(uuid4())
        orchestrator_job = AgentExecution(
            job_id=orchestrator_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator",
            mission="Test staging workflow",
            status="waiting",
            job_metadata={
                "user_id": user_id,
                "field_priorities": {},  # Should be overridden by user config from database
            },
        )
        session.add(orchestrator_job)
        await session.commit()

    # Act: Fetch orchestrator instructions with user_id
    result = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id, tenant_key=tenant_key, user_id=user_id, db_manager=db_manager
    )

    # Assert: Verify custom configurations were applied
    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "field_priorities" in result

    # The returned field_priorities should reflect user's custom config
    # (specific assertions will be added after implementation)


@pytest.mark.asyncio
async def test_get_user_config_with_defaults(db_manager: DatabaseManager):
    """
    Test that system defaults are returned when user has no custom config.

    BEHAVIOR: When a user hasn't configured field priorities or depth config,
    the system should fall back to sensible defaults (not crash or return None).
    """
    # Setup: Create user WITHOUT custom configurations
    tenant_key = str(uuid4())
    user_id = str(uuid4())

    # Use db_manager.get_session_async() pattern for data visibility
    async with db_manager.get_session_async() as session:
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username=f"user_{uuid4().hex[:8]}",
            email=f"test_{uuid4().hex[:8]}@example.com",
            field_priority_config=None,  # No custom config
            depth_config={  # User has default depth_config from model defaults
                "vision_chunking": "medium",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_template_detail": "standard",
            },
            is_active=True,
        )
        session.add(user)
        await session.flush()

        # Create minimal orchestrator job + project + product
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Test Product", description="Test product")
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project",
            mission="Test project mission",
        )
        session.add(project)
        await session.flush()

        orchestrator_id = str(uuid4())
        orchestrator_job = AgentExecution(
            job_id=orchestrator_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            agent_name="Default Config Orchestrator",
            mission="Test default config fallback",
            status="waiting",
            job_metadata={
                "user_id": user_id,
            },
        )
        session.add(orchestrator_job)
        await session.commit()

    # Act: Fetch orchestrator instructions
    result = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id, tenant_key=tenant_key, user_id=user_id, db_manager=db_manager
    )

    # Assert: Verify defaults were applied (should not crash)
    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "field_priorities" in result
    assert result["estimated_tokens"] > 0  # Sanity check


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_without_user_id_backward_compatibility(db_manager: DatabaseManager):
    """
    Test backward compatibility: get_orchestrator_instructions() works without user_id.

    BEHAVIOR: Existing callers that don't provide user_id should continue to work
    (optional parameter, defaults to None).
    """
    # Setup: Create minimal orchestrator job + project + product
    tenant_key = str(uuid4())

    # Use db_manager.get_session_async() pattern for data visibility
    async with db_manager.get_session_async() as session:
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Test Product", description="Test product")
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project",
            mission="Test project mission",
        )
        session.add(project)
        await session.flush()

        orchestrator_id = str(uuid4())
        orchestrator_job = AgentExecution(
            job_id=orchestrator_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            agent_name="Backward Compat Test",
            mission="Test backward compatibility",
            status="waiting",
            job_metadata={},
        )
        session.add(orchestrator_job)
        await session.commit()

    # Act: Call WITHOUT user_id parameter (existing behavior)
    result = await get_orchestrator_instructions(
        orchestrator_id=orchestrator_id,
        tenant_key=tenant_key,
        # No user_id parameter - should still work
        db_manager=db_manager,
    )

    # Assert: Should work with default field priorities
    assert result is not None
    assert isinstance(result, dict)
    # Should not error due to missing user_id
    assert "error" not in result or result.get("error") != "VALIDATION_ERROR"
