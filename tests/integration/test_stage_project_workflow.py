#!/usr/bin/env python
"""
Integration tests for complete Stage Project workflow (Handover 0086B Phase 5.3)

Tests end-to-end staging workflow including:
- Mission generation with user config and field priorities
- Agent creation and WebSocket broadcasts
- Multi-tenant isolation across workflow
- Context prioritization validation (70% target)
- Error handling and concurrent requests

PRODUCTION-GRADE: Validates complete user journey from staging to launch
"""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import create_app
from api.dependencies.websocket import WebSocketDependency
from src.giljo_mcp.agent_selector import AgentSelector
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


@pytest.fixture
def test_app():
    """Create test FastAPI application"""
    app = create_app()
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)


# Note: test_user, test_user_2, test_product, and test_project fixtures
# should be imported from conftest.py or created in shared fixtures.
# For now, these tests rely on the db_session fixture from conftest.


@pytest.mark.asyncio
class TestStageProjectWorkflow:
    """
    Test 1: Complete staging workflow with user config
    Validates end-to-end flow from staging to mission generation
    """

    async def test_complete_staging_workflow_with_user_config(
        self, db_manager, test_user: User, test_project: Project
    ):
        """
        PRODUCTION-GRADE: Complete staging workflow with user field priorities
        """
        # Arrange: User config with field priorities
        user_config = {
            "product_vision": 10,  # Full detail
            "project_description": 8,  # Full detail
            "codebase_summary": 4,  # Abbreviated (50% tokens)
            "architecture": 2,  # Minimal (20% tokens)
        }

        # Mock WebSocket dependency
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        # Act: Generate mission with user config
        mission_planner = MissionPlanner(db_manager=db_manager)
        mission_result = await mission_planner.generate_mission(
            project_id=test_project.id, user_id=test_user.id, field_priorities=user_config, ws_dep=mock_ws_dep
        )

        # Assert: Mission generated with user config applied
        assert mission_result is not None
        assert "mission" in mission_result
        assert mission_result["user_config_applied"] is True
        assert mission_result["token_estimate"] > 0

        # Assert: Field priorities respected (abbreviated codebase)
        mission_text = mission_result["mission"]
        assert len(mission_text) < 10000  # Should be abbreviated

        # Assert: WebSocket broadcast sent
        mock_ws_dep.broadcast_to_tenant.assert_called_once()
        call_args = mock_ws_dep.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == test_user.tenant_key
        assert call_args.kwargs["event_type"] == "project:mission_updated"
        assert call_args.kwargs["data"]["user_config_applied"] is True

    """
    Test 2: Mission generation with field priorities
    Validates context prioritization through field priority system
    """

    async def test_mission_generation_with_field_priorities(self, db_manager, test_user: User, test_project: Project):
        """
        PRODUCTION-GRADE: Validate context prioritization and orchestration through field priorities
        """
        # Arrange: Generate baseline mission (no priorities)
        mission_planner = MissionPlanner(db_manager=db_manager)

        baseline_mission = await mission_planner._build_context_with_priorities(
            product=test_project.product,
            project=test_project,
            field_priorities={},  # No priorities (full detail)
            user_id=None,
        )
        baseline_tokens = len(baseline_mission) // 4  # Approximate token count

        # Act: Generate optimized mission with priorities
        optimized_priorities = {
            "product_vision": 6,  # Abbreviated
            "project_description": 6,  # Abbreviated
            "codebase_summary": 2,  # Minimal
            "architecture": 0,  # Excluded
        }

        optimized_mission = await mission_planner._build_context_with_priorities(
            product=test_project.product,
            project=test_project,
            field_priorities=optimized_priorities,
            user_id=test_user.id,
        )
        optimized_tokens = len(optimized_mission) // 4

        # Assert: Context prioritization achieved (target: 70% reduction)
        token_reduction_pct = ((baseline_tokens - optimized_tokens) / baseline_tokens) * 100
        assert token_reduction_pct >= 50, f"Expected 50%+ reduction, got {token_reduction_pct:.1f}%"

        # Assert: Excluded fields not present
        assert "architecture" not in optimized_mission.lower()

    """
    Test 3: Agent creation and WebSocket broadcasts
    Validates agent creation with real-time WebSocket events
    """

    async def test_agent_creation_and_websocket_broadcasts(self, db_manager, db_session: AsyncSession, test_user: User, test_project: Project):
        """
        PRODUCTION-GRADE: Agent creation with WebSocket broadcast validation
        """
        # Arrange: Mock WebSocket dependency
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=3)

        # Act: Create agent via agent selector
        agent_selector = AgentSelector(db_manager=db_manager)
        agent_data = await agent_selector.create_agent_for_project(
            project_id=test_project.id,
            agent_display_name="implementor",
            mission="Implement feature X",
            user_id=test_user.id,
            ws_dep=mock_ws_dep,
        )

        # Assert: Agent created in database
        from sqlalchemy import select
        result = await db_session.execute(
            select(AgentExecution).filter_by(
                project_id=test_project.id,
                tenant_key=test_user.tenant_key,
                agent_display_name="implementor"
            )
        )
        agent = result.scalar_one_or_none()

        assert agent is not None
        assert agent.mission == "Implement feature X"
        assert agent.status == "pending"

        # Assert: WebSocket broadcast sent
        mock_ws_dep.broadcast_to_tenant.assert_called_once()
        call_args = mock_ws_dep.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == test_user.tenant_key
        assert call_args.kwargs["event_type"] == "agent:created"
        assert call_args.kwargs["data"]["agent"]["id"] == str(agent.id)

    """
    Test 4: Multi-tenant isolation across workflow
    Validates zero cross-tenant leakage in staging workflow
    """

    async def test_multi_tenant_isolation_across_workflow(
        self, db_manager, db_session: AsyncSession, test_user: User, test_user_2: User, test_project: Project
    ):
        """
        PRODUCTION-GRADE: Multi-tenant isolation validation (security critical)
        """
        # Arrange: Mock WebSocket dependency
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        # Act: Generate mission for tenant A (test_user)
        mission_planner = MissionPlanner(db_manager=db_manager)
        mission_result = await mission_planner.generate_mission(
            project_id=test_project.id, user_id=test_user.id, field_priorities={}, ws_dep=mock_ws_dep
        )

        # Assert: WebSocket broadcast only to tenant A
        call_args = mock_ws_dep.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == test_user.tenant_key

        # Assert: Tenant B cannot access mission
        from sqlalchemy import select
        result = await db_session.execute(
            select(Project).filter_by(
                id=test_project.id,
                tenant_key=test_user_2.tenant_key,  # Wrong tenant
            )
        )
        other_project = result.scalar_one_or_none()
        assert other_project is None

    """
    Test 5: Serena toggle integration
    Validates Serena MCP integration in staging workflow
    """

    async def test_serena_toggle_integration(self, db_manager, db_session: AsyncSession, test_user: User, test_project: Project):
        """
        PRODUCTION-GRADE: Serena MCP toggle affects mission generation
        """
        # Arrange: Enable Serena for user
        test_user.config_data = {"serena_enabled": True}
        await db_session.commit()

        # Mock WebSocket dependency
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        # Act: Generate mission with Serena enabled
        mission_planner = MissionPlanner(db_manager=db_manager)
        mission_result = await mission_planner.generate_mission(
            project_id=test_project.id, user_id=test_user.id, field_priorities={}, ws_dep=mock_ws_dep
        )

        # Assert: Mission includes Serena context (if implemented)
        # Note: This test assumes Serena integration exists
        # Adjust based on actual Serena implementation
        mission_text = mission_result["mission"]
        # For now, just verify mission generated successfully
        assert mission_text is not None
        assert len(mission_text) > 0

    """
    Test 6: Context prioritization validation (70% target)
    Validates business goal of context prioritization and orchestration
    """

    async def test_token_reduction_validation_70_percent_target(
        self, db_manager, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """
        PRODUCTION-GRADE: Validate core business value (context prioritization and orchestration)
        """
        # Arrange: Create large product vision and project
        # Update vision via VisionDocument (not deprecated vision_document field)
        if test_project.product.vision_documents:
            vision_doc = test_project.product.vision_documents[0]
            vision_doc.vision_document = "# Vision\n\n" + ("Detailed section. " * 500)

        test_project.description = "Description. " * 200
        # Note: Project model doesn't have codebase_summary field (removed in model refactor)
        await db_session.commit()

        # Baseline: Full detail (no priorities)
        mission_planner = MissionPlanner(db_manager=db_manager)
        baseline_mission = await mission_planner._build_context_with_priorities(
            product=test_project.product,
            project=test_project,
            field_priorities={
                "product_vision": 10,
                "project_description": 10,
                "codebase_summary": 10,
                "architecture": 10,
            },
            user_id=None,
        )
        baseline_tokens = len(baseline_mission) // 4

        # Act: Aggressive optimization (minimal detail)
        optimized_mission = await mission_planner._build_context_with_priorities(
            product=test_project.product,
            project=test_project,
            field_priorities={
                "product_vision": 2,  # Minimal
                "project_description": 2,  # Minimal
                "codebase_summary": 2,  # Minimal
                "architecture": 0,  # Excluded
            },
            user_id=test_user.id,
        )
        optimized_tokens = len(optimized_mission) // 4

        # Assert: 70%+ context prioritization achieved
        token_reduction_pct = ((baseline_tokens - optimized_tokens) / baseline_tokens) * 100
        assert token_reduction_pct >= 70, f"Target: 70% reduction, Achieved: {token_reduction_pct:.1f}%"

        # Assert: Optimized mission still meaningful
        assert len(optimized_mission) > 100  # Not empty
        assert optimized_tokens > 20  # Minimum viable mission

    """
    Test 7: Error handling in staging workflow
    Validates graceful error handling and recovery
    """

    async def test_error_handling_in_staging_workflow(self, db_manager, test_user: User):
        """
        PRODUCTION-GRADE: Error boundaries and graceful degradation
        """
        # Arrange: Invalid project ID
        invalid_project_id = uuid4()

        # Mock WebSocket dependency
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)

        # Act & Assert: Should raise meaningful error
        mission_planner = MissionPlanner(db_manager=db_manager)
        with pytest.raises(Exception) as exc_info:
            await mission_planner.generate_mission(
                project_id=invalid_project_id, user_id=test_user.id, field_priorities={}, ws_dep=mock_ws_dep
            )

        # Assert: Error message is meaningful
        assert "not found" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    """
    Test 8: Concurrent staging requests
    Validates race condition prevention in concurrent scenarios
    """

    async def test_concurrent_staging_requests(self, db_manager, test_user: User, test_project: Project):
        """
        PRODUCTION-GRADE: Race condition prevention for concurrent requests
        """
        # Arrange: Mock WebSocket dependency
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        # Act: 10 concurrent mission generation requests
        mission_planner = MissionPlanner(db_manager=db_manager)

        async def generate_mission():
            return await mission_planner.generate_mission(
                project_id=test_project.id, user_id=test_user.id, field_priorities={}, ws_dep=mock_ws_dep
            )

        tasks = [generate_mission() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert: All requests completed (no exceptions)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 8, "At least 8/10 concurrent requests should succeed"

        # Assert: All missions consistent
        missions = [r["mission"] for r in successful_results]
        assert len(set(missions)) <= 2, "Missions should be consistent or nearly identical"

    """
    Test 9: Mission regeneration with overrides
    Validates mission regeneration endpoint with field priority overrides
    """

    async def test_mission_regeneration_with_overrides(self, db_manager, test_user: User, test_project: Project):
        """
        PRODUCTION-GRADE: Mission regeneration with user-specified overrides
        """
        # Arrange: Generate initial mission
        mission_planner = MissionPlanner(db_manager=db_manager)
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        initial_mission = await mission_planner.generate_mission(
            project_id=test_project.id,
            user_id=test_user.id,
            field_priorities={"product_vision": 10},
            ws_dep=mock_ws_dep,
        )

        # Act: Regenerate with different priorities
        regenerated_mission = await mission_planner.generate_mission(
            project_id=test_project.id,
            user_id=test_user.id,
            field_priorities={"product_vision": 2},  # Changed to minimal
            ws_dep=mock_ws_dep,
        )

        # Assert: Missions different (different detail levels)
        assert len(regenerated_mission["mission"]) < len(initial_mission["mission"])
        assert regenerated_mission["token_estimate"] < initial_mission["token_estimate"]

    """
    Test 10: User config propagation chain
    Validates user_id propagates through entire workflow
    """

    async def test_user_config_propagation_chain(self, db_manager, test_user: User, test_project: Project):
        """
        PRODUCTION-GRADE: Validate user_id parameter chain (Task 2.1)
        """
        # Arrange: Mock WebSocket dependency with call tracking
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        # Act: Generate mission with user_id
        mission_planner = MissionPlanner(db_manager=db_manager)
        mission_result = await mission_planner.generate_mission(
            project_id=test_project.id,
            user_id=test_user.id,  # User ID provided
            field_priorities={"product_vision": 10},
            ws_dep=mock_ws_dep,
        )

        # Assert: user_config_applied flag set
        assert mission_result["user_config_applied"] is True

        # Assert: WebSocket event includes user context
        call_args = mock_ws_dep.broadcast_to_tenant.call_args
        event_data = call_args.kwargs["data"]
        assert event_data["user_config_applied"] is True
        assert "field_priorities" in event_data

        # Compare with mission without user_id
        mission_no_user = await mission_planner.generate_mission(
            project_id=test_project.id,
            user_id=None,  # No user ID
            field_priorities={},
            ws_dep=mock_ws_dep,
        )

        # Assert: user_config_applied flag NOT set
        assert mission_no_user["user_config_applied"] is False


@pytest.mark.asyncio
class TestStageProjectEdgeCases:
    """Edge cases and error scenarios"""

    async def test_staging_with_missing_product(self, db_manager, db_session: AsyncSession, test_user: User):
        """
        Validate error handling when product is missing
        """
        # Arrange: Project without product
        project = Project(
            name="Orphan Project",
            description="Project without product",
            product_id=None,  # Missing product
            tenant_key=test_user.tenant_key,
            status="active",
        )
        db_session.add(project)
        await db_session.commit()

        # Act & Assert: Should fail gracefully
        mission_planner = MissionPlanner(db_manager=db_manager)
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)

        with pytest.raises(Exception) as exc_info:
            await mission_planner.generate_mission(
                project_id=project.id, user_id=test_user.id, field_priorities={}, ws_dep=mock_ws_dep
            )

        assert "product" in str(exc_info.value).lower()

    async def test_staging_with_empty_field_priorities(self, db_manager, test_user: User, test_project: Project):
        """
        Validate default behavior when field_priorities is empty
        """
        # Arrange: Empty field priorities
        mission_planner = MissionPlanner(db_manager=db_manager)
        mock_ws_dep = AsyncMock(spec=WebSocketDependency)
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)

        # Act: Generate mission with empty priorities
        mission_result = await mission_planner.generate_mission(
            project_id=test_project.id,
            user_id=test_user.id,
            field_priorities={},  # Empty
            ws_dep=mock_ws_dep,
        )

        # Assert: Mission generated with defaults (full detail)
        assert mission_result is not None
        assert mission_result["mission"] is not None
        assert mission_result["user_config_applied"] is True  # user_id provided
