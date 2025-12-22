"""
Unit tests for ProjectOrchestrator class.
Tests project lifecycle, agent management, handoffs, and context tracking.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.enums import AgentRole, AgentStatus, ContextStatus, ProjectType
from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from tests.fixtures.base_fixtures import TestData
from tests.fixtures.base_test import BaseAsyncTest


class TestProjectOrchestrator(BaseAsyncTest):
    """Test suite for ProjectOrchestrator"""

    def setup_method(self, method):
        """Setup test method"""
        super().setup_method(method)
        self.orchestrator = ProjectOrchestrator()
        self.tenant_key = TestData.generate_tenant_key()

    # ==================== Project Lifecycle Tests ====================

    @pytest.mark.asyncio
    async def test_create_project_success(self):
        """Test successful project creation"""
        # Mock database session
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Create project
        result = await self.orchestrator.create_project(
            name="Test Project",
            mission="Test mission",
            tenant_key=self.tenant_key,
            project_type=ProjectType.DEVELOPMENT,
            db_session=mock_session,
        )

        # Assertions
        assert result["status"] == "success"
        assert result["project"] is not None
        assert result["project"].name == "Test Project"
        assert result["project"].mission == "Test mission"
        assert result["project"].tenant_key == self.tenant_key
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_with_metadata(self):
        """Test project creation with metadata"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        metadata = {"priority": "high", "team": "alpha"}

        result = await self.orchestrator.create_project(
            name="Test Project",
            mission="Test mission",
            tenant_key=self.tenant_key,
            project_type=ProjectType.RESEARCH,
            metadata=metadata,
            db_session=mock_session,
        )

        assert result["project"].metadata == metadata
        assert result["project"].type == ProjectType.RESEARCH.value

    @pytest.mark.asyncio
    async def test_create_project_handles_exception(self):
        """Test project creation handles database exceptions"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()

        result = await self.orchestrator.create_project(
            name="Test Project", mission="Test mission", tenant_key=self.tenant_key, db_session=mock_session
        )

        assert result["status"] == "error"
        assert "Database error" in result["error"]
        mock_session.rollback.assert_called_once()

    # ==================== Agent Management Tests ====================

    @pytest.mark.asyncio
    async def test_spawn_agent_success(self):
        """Test successful agent spawning"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        project_id = str(uuid.uuid4())

        result = await self.orchestrator.spawn_agent(
            project_id=project_id, role=AgentRole.ANALYZER, name="test_analyzer", db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["agent"] is not None
        assert result["agent"].name == "test_analyzer"
        assert result["agent"].type == AgentRole.ANALYZER.value
        assert result["agent"].project_id == project_id
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_agent_with_custom_mission(self):
        """Test agent spawning with custom mission"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        custom_mission = "Custom analyzer mission"

        result = await self.orchestrator.spawn_agent(
            project_id=str(uuid.uuid4()),
            role=AgentRole.ANALYZER,
            name="custom_analyzer",
            mission=custom_mission,
            db_session=mock_session,
        )

        assert result["agent"].mission == custom_mission

    @pytest.mark.asyncio
    async def test_spawn_agent_generates_default_mission(self):
        """Test agent spawning generates default mission from role"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await self.orchestrator.spawn_agent(
            project_id=str(uuid.uuid4()), role=AgentRole.IMPLEMENTER, name="implementer", db_session=mock_session
        )

        # Should use the default mission template for IMPLEMENTER role
        assert "implementer responsible for" in result["agent"].mission
        assert "Writing clean, maintainable code" in result["agent"].mission

    @pytest.mark.asyncio
    async def test_deactivate_agent(self):
        """Test agent deactivation"""
        mock_session = self.create_async_mock("session")

        # Create mock agent
        mock_agent = Mock(spec=Agent)
        mock_agent.id = str(uuid.uuid4())
        mock_agent.status = AgentStatus.ACTIVE.value

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_agent
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await self.orchestrator.deactivate_agent(
            agent_id=mock_agent.id, reason="Task completed", db_session=mock_session
        )

        assert result["status"] == "success"
        assert mock_agent.status == AgentStatus.INACTIVE.value
        assert mock_agent.metadata["deactivation_reason"] == "Task completed"
        mock_session.commit.assert_called_once()

    # ==================== Handoff Tests ====================

    @pytest.mark.asyncio
    async def test_handoff_success(self):
        """Test successful handoff between agents"""
        mock_session = self.create_async_mock("session")

        # Create mock agents
        from_agent = Mock(spec=Agent)
        from_agent.id = str(uuid.uuid4())
        from_agent.name = "analyzer"
        from_agent.status = AgentStatus.ACTIVE.value

        to_agent = Mock(spec=Agent)
        to_agent.id = str(uuid.uuid4())
        to_agent.name = "implementer"
        to_agent.status = AgentStatus.ACTIVE.value

        # Mock queries
        mock_query = Mock()
        mock_query.filter_by.return_value.first.side_effect = [from_agent, to_agent]
        mock_session.query.return_value = mock_query
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()

        context = {"analysis_complete": True, "next_steps": ["implement", "test"]}

        result = await self.orchestrator.handoff(
            from_agent_id=from_agent.id, to_agent_id=to_agent.id, context=context, db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["handoff"] is not None
        assert from_agent.status == AgentStatus.HANDOFF.value
        assert to_agent.status == AgentStatus.ACTIVE.value
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handoff_invalid_agent(self):
        """Test handoff with invalid agent ID"""
        mock_session = self.create_async_mock("session")

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        result = await self.orchestrator.handoff(
            from_agent_id="invalid_id", to_agent_id="another_invalid", context={}, db_session=mock_session
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    # ==================== Context Tracking Tests ====================

    @pytest.mark.asyncio
    async def test_update_context_usage(self):
        """Test context usage update"""
        mock_session = self.create_async_mock("session")

        # Create mock project with context tracking
        mock_project = Mock(spec=Project)
        mock_project.id = str(uuid.uuid4())
        mock_project.metadata = {"context_used": 5000, "context_budget": 150000}

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await self.orchestrator.update_context_usage(
            project_id=mock_project.id, tokens_used=10000, db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["context_used"] == 15000
        assert result["context_remaining"] == 135000
        assert mock_project.metadata["context_used"] == 15000
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_context_status(self):
        """Test getting context status"""
        mock_session = self.create_async_mock("session")

        mock_project = Mock(spec=Project)
        mock_project.id = str(uuid.uuid4())
        mock_project.metadata = {"context_used": 120000, "context_budget": 150000}

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query

        status = await self.orchestrator.get_context_status(project_id=mock_project.id, db_session=mock_session)

        assert status == ContextStatus.CRITICAL
        assert mock_project.metadata["context_status"] == ContextStatus.CRITICAL.value

    @pytest.mark.asyncio
    async def test_context_status_levels(self):
        """Test different context status levels"""
        test_cases = [
            (10000, 150000, ContextStatus.HEALTHY),  # < 50%
            (90000, 150000, ContextStatus.WARNING),  # 60%
            (120000, 150000, ContextStatus.CRITICAL),  # 80%
            (145000, 150000, ContextStatus.EXHAUSTED),  # > 95%
        ]

        for used, budget, expected_status in test_cases:
            mock_session = self.create_async_mock("session")

            mock_project = Mock(spec=Project)
            mock_project.metadata = {"context_used": used, "context_budget": budget}

            mock_query = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_project
            mock_session.query.return_value = mock_query

            status = await self.orchestrator.get_context_status(project_id=str(uuid.uuid4()), db_session=mock_session)

            assert status == expected_status

    # ==================== State Machine Tests ====================

    @pytest.mark.asyncio
    async def test_transition_project_state(self):
        """Test project state transitions"""
        mock_session = self.create_async_mock("session")

        mock_project = Mock(spec=Project)
        mock_project.id = str(uuid.uuid4())
        mock_project.status = "planning"
        mock_project.metadata = {}

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        # Valid transition from planning to active
        result = await self.orchestrator.transition_project_state(
            project_id=mock_project.id, new_state="active", db_session=mock_session
        )

        assert result["status"] == "success"
        assert mock_project.status == "active"
        assert "planning" in mock_project.metadata.get("state_history", [])[0]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_state_transition(self):
        """Test invalid project state transition"""
        mock_session = self.create_async_mock("session")

        mock_project = Mock(spec=Project)
        mock_project.id = str(uuid.uuid4())
        mock_project.status = "database_initialized"

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query

        # Cannot transition from completed to planning
        result = await self.orchestrator.transition_project_state(
            project_id=mock_project.id, new_state="planning", db_session=mock_session
        )

        assert result["status"] == "error"
        assert "Invalid state transition" in result["error"]

    # ==================== Multi-Project Tests ====================

    @pytest.mark.asyncio
    async def test_get_active_projects_by_tenant(self):
        """Test retrieving active projects for a tenant"""
        mock_session = self.create_async_mock("session")

        # Create mock projects
        project1 = Mock(spec=Project)
        project1.id = str(uuid.uuid4())
        project1.name = "Project 1"
        project1.status = "active"

        project2 = Mock(spec=Project)
        project2.id = str(uuid.uuid4())
        project2.name = "Project 2"
        project2.status = "active"

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.all.return_value = [project1, project2]
        mock_session.query.return_value = mock_query

        result = await self.orchestrator.get_active_projects(tenant_key=self.tenant_key, db_session=mock_session)

        assert len(result) == 2
        assert all(p.status == "active" for p in result)
        mock_query.filter_by.assert_called_with(tenant_key=self.tenant_key)

    @pytest.mark.asyncio
    async def test_concurrent_project_limit(self):
        """Test concurrent project limit enforcement"""
        mock_session = self.create_async_mock("session")

        # Mock 5 active projects (at the limit)
        [Mock(spec=Project) for _ in range(5)]

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.count.return_value = 5
        mock_session.query.return_value = mock_query

        result = await self.orchestrator.check_project_limit(tenant_key=self.tenant_key, db_session=mock_session)

        assert result["can_create"] is False
        assert result["active_count"] == 5
        assert result["limit"] == 5
