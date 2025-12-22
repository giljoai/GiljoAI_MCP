"""
Test Suite for Sub-Agent Integration Foundation

Tests the hybrid orchestration model that integrates Claude Code's native
sub-agent capabilities with MCP message logging.

Test Coverage:
1. Agent Interactions Database Model
2. spawn_and_log_sub_agent MCP tool
3. log_sub_agent_completion MCP tool
4. WebSocket real-time events
5. Backward compatibility with existing message system
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.giljo_mcp.models import AgentInteraction, Base, Message, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.helpers.test_db_helper import PostgreSQLTestHelper


# We'll mock these since they require MCP server context
spawn_and_log_sub_agent = None
log_sub_agent_completion = None


class TestAgentInteractionsModel:
    """Test the agent_interactions database model and schema."""

    @pytest.fixture
    def sample_interaction_data(self, test_project_id):
        """Sample data for agent interaction testing."""
        return {
            "tenant_key": "test-tenant-123",
            "project_id": test_project_id,
            "parent_agent_id": None,
            "sub_agent_name": "code_analyzer",
            "interaction_type": "SPAWN",
            "mission": "Analyze the codebase structure and provide insights",
            "tokens_used": 1500,
            "meta_data": {"language": "python", "framework": "fastapi"},
        }

    @pytest.mark.asyncio
    async def test_create_agent_interaction(self, db_session, sample_interaction_data):
        """Test creating a new agent interaction record."""
        interaction = AgentInteraction(**sample_interaction_data)
        db_session.add(interaction)
        await db_session.commit()

        assert interaction.id is not None
        assert interaction.interaction_type == "SPAWN"
        assert interaction.start_time is not None
        assert interaction.end_time is None
        assert interaction.duration_seconds is None

    @pytest.mark.asyncio
    async def test_complete_agent_interaction(self, db_session, sample_interaction_data):
        """Test completing an agent interaction with results."""
        # Create spawn interaction
        interaction = AgentInteraction(**sample_interaction_data)
        db_session.add(interaction)
        await db_session.commit()

        # Complete the interaction
        interaction.interaction_type = "COMPLETE"
        interaction.end_time = datetime.now(timezone.utc)
        interaction.duration_seconds = 45
        interaction.result = json.dumps(
            {"files_analyzed": 25, "issues_found": 3, "recommendations": ["Add type hints", "Improve error handling"]}
        )
        interaction.tokens_used = 2500
        await db_session.commit()

        # Verify completion
        assert interaction.interaction_type == "COMPLETE"
        assert interaction.end_time is not None
        assert interaction.duration_seconds == 45
        assert interaction.result is not None
        assert interaction.tokens_used == 2500

    @pytest.mark.asyncio
    async def test_error_agent_interaction(self, db_session, sample_interaction_data):
        """Test handling error in agent interaction."""
        interaction = AgentInteraction(**sample_interaction_data)
        interaction.interaction_type = "ERROR"
        interaction.error_message = "Sub-agent failed: Timeout after 60 seconds"
        interaction.end_time = datetime.now(timezone.utc)

        db_session.add(interaction)
        await db_session.commit()

        assert interaction.interaction_type == "ERROR"
        assert interaction.error_message is not None
        assert "Timeout" in interaction.error_message

    @pytest.mark.asyncio
    async def test_parent_child_relationship(self, db_session, test_project_id, test_agent):
        """Test parent-child agent relationship tracking."""
        # Create parent agent interaction
        parent_interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=test_project_id,
            parent_agent_id=test_agent.id,
            sub_agent_name="child_worker",
            interaction_type="SPAWN",
            mission="Perform specific task",
        )
        db_session.add(parent_interaction)
        await db_session.commit()

        # Verify relationship
        assert parent_interaction.parent_agent_id == test_agent.id
        assert parent_interaction.parent_agent is not None

        # Check backref
        await db_session.refresh(test_agent)
        assert len(test_agent.sub_agent_interactions) > 0

    @pytest.mark.asyncio
    async def test_interaction_type_constraint(self, db_session, sample_interaction_data):
        """Test that only valid interaction types are accepted."""
        sample_interaction_data["interaction_type"] = "INVALID"

        with pytest.raises(Exception):  # Should raise constraint violation
            interaction = AgentInteraction(**sample_interaction_data)
            db_session.add(interaction)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_query_interactions_by_project(self, db_session, test_project_id):
        """Test querying interactions by project."""
        # Create multiple interactions
        for i in range(3):
            interaction = AgentInteraction(
                tenant_key="test-tenant",
                project_id=test_project_id,
                sub_agent_name=f"agent_{i}",
                interaction_type="SPAWN",
                mission=f"Task {i}",
            )
            db_session.add(interaction)
        await db_session.commit()

        # Query by project
        stmt = select(AgentInteraction).where(AgentInteraction.project_id == test_project_id)
        results = await db_session.execute(stmt)
        results = results.scalars().all()

        assert len(results) >= 3
        for result in results:
            assert result.project_id == test_project_id


class TestSubAgentMCPTools:
    """Test the MCP tools for sub-agent integration."""

    @pytest_asyncio.fixture
    async def setup_test_data(self, db_session, test_project_id):
        """Setup test project and agent data."""
        # Create test project
        project = Project(id=test_project_id, tenant_key="test-tenant", name="Test Project", mission="Test mission")

        # Create parent agent
        parent_agent = Agent(
            id="parent-agent-123",
            tenant_key="test-tenant",
            project_id=test_project_id,
            name="parent_agent",
            status="active",
        )

        db_session.add_all([project, parent_agent])
        await db_session.commit()

        return {"project": project, "parent_agent": parent_agent}

    @pytest.mark.asyncio
    async def test_spawn_and_log_sub_agent_success(self, setup_test_data):
        """Test successful spawn_and_log_sub_agent tool execution."""
        test_data = await setup_test_data

        # Call the actual tool function
        result = await spawn_and_log_sub_agent(
            project_id=test_data["project"].id,
            parent_agent_name=test_data["parent_agent"].name,
            sub_agent_name="code_analyzer",
            mission="Analyze codebase structure",
            meta_data={"language": "python", "scope": "backend"},
        )

        # Verify successful response
        assert result["success"] is True
        assert "interaction_id" in result
        assert result["parent_agent"] == "parent_agent"
        assert result["sub_agent"] == "code_analyzer"
        assert result["mission"] == "Analyze codebase structure"
        assert "start_time" in result

    @pytest.mark.asyncio
    async def test_spawn_with_nonexistent_parent(self):
        """Test spawn_and_log_sub_agent creates parent if not exists."""
        # Use a parent that doesn't exist
        result = await spawn_and_log_sub_agent(
            project_id="test-project-id",
            parent_agent_name="new_parent_agent",
            sub_agent_name="analyzer",
            mission="Test with new parent",
            meta_data={"test": True},
        )

        # Should either succeed (if parent created) or fail gracefully
        assert "success" in result
        if not result["success"]:
            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_log_sub_agent_completion_success(self, setup_test_data, db_session):
        """Test successful log_sub_agent_completion tool execution."""
        test_data = await setup_test_data

        # First spawn a sub-agent
        spawn_result = await spawn_and_log_sub_agent(
            project_id=test_data["project"].id,
            parent_agent_name=test_data["parent_agent"].name,
            sub_agent_name="worker",
            mission="Complete a task",
        )

        assert spawn_result["success"] is True
        interaction_id = spawn_result["interaction_id"]

        # Complete the sub-agent task
        completion_result = await log_sub_agent_completion(
            interaction_id=interaction_id,
            result=json.dumps({"status": "success", "output": "Task completed"}),
            tokens_used=1500,
            meta_data={"performance": "optimal"},
        )

        # Verify completion
        assert completion_result["success"] is True
        assert completion_result["interaction_id"] == interaction_id
        assert completion_result["interaction_type"] == "COMPLETE"
        assert completion_result["duration_seconds"] >= 0
        assert completion_result["tokens_used"] == 1500

    @pytest.mark.asyncio
    async def test_log_sub_agent_completion_with_error(self, setup_test_data):
        """Test log_sub_agent_completion with error handling."""
        test_data = await setup_test_data

        # Spawn a sub-agent
        spawn_result = await spawn_and_log_sub_agent(
            project_id=test_data["project"].id,
            parent_agent_name=test_data["parent_agent"].name,
            sub_agent_name="failing_worker",
            mission="Task that will fail",
        )

        interaction_id = spawn_result["interaction_id"]

        # Complete with error
        error_result = await log_sub_agent_completion(
            interaction_id=interaction_id, error_message="Sub-agent crashed: Out of memory", tokens_used=500
        )

        # Verify error handling
        assert error_result["success"] is True
        assert error_result["interaction_type"] == "ERROR"
        assert "error_message" in error_result
        assert "crashed" in error_result["error_message"]

    @pytest.mark.asyncio
    async def test_completion_nonexistent_interaction(self):
        """Test completing a non-existent interaction."""
        result = await log_sub_agent_completion(interaction_id="nonexistent-id-123", result="This should fail")

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_double_completion_prevented(self, setup_test_data):
        """Test that interactions cannot be completed twice."""
        test_data = await setup_test_data

        # Spawn and complete once
        spawn_result = await spawn_and_log_sub_agent(
            project_id=test_data["project"].id,
            parent_agent_name=test_data["parent_agent"].name,
            sub_agent_name="worker",
            mission="Single completion test",
        )

        interaction_id = spawn_result["interaction_id"]

        # First completion
        first_result = await log_sub_agent_completion(interaction_id=interaction_id, result="First completion")
        assert first_result["success"] is True

        # Second completion should fail
        second_result = await log_sub_agent_completion(interaction_id=interaction_id, result="Second completion")
        assert second_result["success"] is False
        assert "already completed" in second_result["error"]


class TestBackwardCompatibility:
    """Test backward compatibility with existing message system."""

    @pytest.mark.asyncio
    async def test_message_system_unaffected(self, db_session, test_project_id):
        """Test that existing message system continues to work."""
        # Create traditional message
        message = Message(
            tenant_key="test-tenant",
            project_id=test_project_id,
            from_agent="orchestrator",
            to_agents=["worker1", "worker2"],
            content="Traditional message content",
            message_type="direct",
            priority="normal",
        )
        db_session.add(message)
        await db_session.commit()

        # Verify message created normally
        assert message.id is not None
        assert message.acknowledged_by == []
        assert message.completed_by == []

    @pytest.mark.asyncio
    async def test_concurrent_messaging_and_interactions(self, db_session, test_project_id):
        """Test that messages and interactions can coexist."""
        # Create message
        message = Message(
            tenant_key="test-tenant",
            project_id=test_project_id,
            from_agent="orchestrator",
            to_agents=["analyzer"],
            content="Analyze the system",
            message_type="direct",
            priority="high",
        )

        # Create interaction for same task
        interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=test_project_id,
            sub_agent_name="analyzer",
            interaction_type="SPAWN",
            mission="Analyze the system",
        )

        db_session.add_all([message, interaction])
        await db_session.commit()

        # Both should exist independently
        assert message.id is not None
        assert interaction.id is not None
        assert message.project_id == interaction.project_id

    @pytest.mark.asyncio
    async def test_agent_model_unchanged(self, db_session, test_agent):
        """Test that Agent model still works as before."""
        # Verify agent has expected attributes
        assert hasattr(test_agent, "id")
        assert hasattr(test_agent, "name")
        assert hasattr(test_agent, "project_id")
        assert hasattr(test_agent, "status")

        # New relationship should exist but be optional
        assert hasattr(test_agent, "sub_agent_interactions")
        assert isinstance(test_agent.sub_agent_interactions, list)


class TestWebSocketEvents:
    """Test WebSocket event streaming for sub-agent interactions."""

    @pytest.mark.asyncio
    async def test_spawn_event_broadcast(self, test_project_id):
        """Test that spawn events are broadcast via WebSocket."""
        with patch("src.giljo_mcp.websocket_client.broadcast_sub_agent_event") as mock_broadcast:
            # Setup
            project = Project(
                id=test_project_id, tenant_key="test-tenant", name="WebSocket Test", mission="Test WebSocket"
            )
            parent = Agent(tenant_key="test-tenant", project_id=test_project_id, name="ws_parent", status="active")

            # Use in-memory session for test
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
            Base.metadata.create_all(engine)
            SessionLocal = sessionmaker(bind=engine)

            with SessionLocal() as session:
                session.add_all([project, parent])
                session.commit()

            # Spawn sub-agent (will trigger broadcast)
            await spawn_and_log_sub_agent(
                project_id=test_project_id,
                parent_agent_name="ws_parent",
                sub_agent_name="ws_worker",
                mission="Test WebSocket broadcast",
            )

            # Verify broadcast was called
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args

            assert call_args[0][0] == "spawned"  # event_type
            assert "interaction_id" in call_args[1]
            assert call_args[1]["sub_agent_name"] == "ws_worker"
            assert call_args[1]["parent_agent_name"] == "ws_parent"

    @pytest.mark.asyncio
    async def test_completion_event_broadcast(self, test_project_id):
        """Test that completion events are broadcast via WebSocket."""
        with patch("src.giljo_mcp.websocket_client.broadcast_sub_agent_event") as mock_broadcast:
            # Setup and spawn first
            project = Project(
                id=test_project_id, tenant_key="test-tenant", name="Completion Test", mission="Test completion"
            )
            parent = Agent(
                tenant_key="test-tenant", project_id=test_project_id, name="complete_parent", status="active"
            )

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
            Base.metadata.create_all(engine)
            SessionLocal = sessionmaker(bind=engine)

            with SessionLocal() as session:
                session.add_all([project, parent])
                session.commit()

            spawn_result = await spawn_and_log_sub_agent(
                project_id=test_project_id,
                parent_agent_name="complete_parent",
                sub_agent_name="complete_worker",
                mission="Will complete",
            )

            # Reset mock for completion call
            mock_broadcast.reset_mock()

            # Complete the sub-agent
            await log_sub_agent_completion(
                interaction_id=spawn_result["interaction_id"], result="Task completed", tokens_used=1000
            )

            # Verify completion broadcast
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args

            assert call_args[0][0] == "database_initialized"  # event_type
            assert "interaction_id" in call_args[1]
            assert call_args[1]["tokens_used"] == 1000

    @pytest.mark.asyncio
    async def test_error_event_broadcast(self, test_project_id):
        """Test that error events are broadcast via WebSocket."""
        with patch("src.giljo_mcp.websocket_client.broadcast_sub_agent_event") as mock_broadcast:
            # Setup similar to above
            project = Project(id=test_project_id, tenant_key="test-tenant", name="Error Test", mission="Test error")
            parent = Agent(tenant_key="test-tenant", project_id=test_project_id, name="error_parent", status="active")

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
            Base.metadata.create_all(engine)
            SessionLocal = sessionmaker(bind=engine)

            with SessionLocal() as session:
                session.add_all([project, parent])
                session.commit()

            spawn_result = await spawn_and_log_sub_agent(
                project_id=test_project_id,
                parent_agent_name="error_parent",
                sub_agent_name="error_worker",
                mission="Will fail",
            )

            # Reset mock for error call
            mock_broadcast.reset_mock()

            # Complete with error
            await log_sub_agent_completion(
                interaction_id=spawn_result["interaction_id"],
                error_message="Worker timeout after 60 seconds",
                tokens_used=100,
            )

            # Verify error broadcast
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args

            assert call_args[0][0] == "error"  # event_type
            assert "error_message" in call_args[1]
            assert "timeout" in call_args[1]["error_message"].lower()


class TestIntegrationScenarios:
    """End-to-end integration scenarios for sub-agent system."""

    @pytest.mark.asyncio
    async def test_full_sub_agent_lifecycle(self, db_session, test_project_id):
        """Test complete lifecycle: spawn -> work -> complete."""
        # Setup project and parent
        project = Project(id=test_project_id, tenant_key="test-tenant", name="Lifecycle Test", mission="Test lifecycle")
        parent = Agent(tenant_key="test-tenant", project_id=test_project_id, name="lifecycle_parent", status="active")
        db_session.add_all([project, parent])
        await db_session.commit()

        # Spawn sub-agent using actual tool
        spawn_result = await spawn_and_log_sub_agent(
            project_id=test_project_id,
            parent_agent_name="lifecycle_parent",
            sub_agent_name="lifecycle_worker",
            mission="Complete full lifecycle test",
            meta_data={"test_type": "lifecycle"},
        )

        assert spawn_result["success"] is True
        interaction_id = spawn_result["interaction_id"]

        # Simulate work being done
        await asyncio.sleep(0.1)

        # Complete the interaction
        complete_result = await log_sub_agent_completion(
            interaction_id=interaction_id,
            result=json.dumps({"status": "database_initialized", "files_processed": 10, "tests_passed": 8}),
            tokens_used=2500,
            meta_data={"performance": "good"},
        )

        assert complete_result["success"] is True
        assert complete_result["interaction_type"] == "COMPLETE"
        assert complete_result["duration_seconds"] > 0
        assert complete_result["tokens_used"] == 2500

        # Verify database state
        stmt = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
        interaction = db_session.execute(stmt).scalar_one()

        assert interaction.interaction_type == "COMPLETE"
        assert interaction.tokens_used == 2500
        assert "files_processed" in interaction.result

    @pytest.mark.asyncio
    async def test_parallel_sub_agents(self, db_session, test_project_id):
        """Test multiple sub-agents running in parallel."""
        # Setup
        project = Project(
            id=test_project_id, tenant_key="test-tenant", name="Parallel Test", mission="Test parallel agents"
        )
        orchestrator = Agent(tenant_key="test-tenant", project_id=test_project_id, name="orchestrator", status="active")
        db_session.add_all([project, orchestrator])
        await db_session.commit()

        # Spawn multiple sub-agents concurrently
        spawn_tasks = []
        for i in range(3):
            task = spawn_and_log_sub_agent(
                project_id=test_project_id,
                parent_agent_name="orchestrator",
                sub_agent_name=f"parallel_worker_{i}",
                mission=f"Parallel task {i}",
            )
            spawn_tasks.append(task)

        spawn_results = await asyncio.gather(*spawn_tasks)

        # Verify all spawned successfully
        interaction_ids = []
        for result in spawn_results:
            assert result["success"] is True
            interaction_ids.append(result["interaction_id"])

        # Complete them in different order with different outcomes
        complete_tasks = [
            log_sub_agent_completion(
                interaction_id=interaction_ids[1], result="Task 1 completed first", tokens_used=1000
            ),
            log_sub_agent_completion(interaction_id=interaction_ids[0], error_message="Task 0 failed", tokens_used=500),
            log_sub_agent_completion(
                interaction_id=interaction_ids[2], result="Task 2 completed last", tokens_used=1500
            ),
        ]

        complete_results = await asyncio.gather(*complete_tasks)

        # Verify different outcomes
        assert complete_results[0]["interaction_type"] == "COMPLETE"
        assert complete_results[1]["interaction_type"] == "ERROR"
        assert complete_results[2]["interaction_type"] == "COMPLETE"

    @pytest.mark.asyncio
    async def test_metrics_aggregation(self, db_session, test_project_id):
        """Test aggregating metrics across sub-agent interactions."""
        # Create multiple completed interactions
        total_tokens = 0
        total_duration = 0

        for i in range(5):
            interaction = AgentInteraction(
                tenant_key="test-tenant",
                project_id=test_project_id,
                sub_agent_name=f"metric_agent_{i}",
                interaction_type="COMPLETE",
                mission=f"Task {i}",
                duration_seconds=10 + i,
                tokens_used=100 * (i + 1),
            )
            db_session.add(interaction)
            total_tokens += interaction.tokens_used
            total_duration += interaction.duration_seconds

        await db_session.commit()

        # Query and aggregate
        stmt = select(AgentInteraction).where(
            AgentInteraction.project_id == test_project_id, AgentInteraction.interaction_type == "COMPLETE"
        )
        result = await db_session.execute(stmt)
        completed = result.scalars().all()

        calc_tokens = sum(i.tokens_used or 0 for i in completed)
        calc_duration = sum(i.duration_seconds or 0 for i in completed)

        assert calc_tokens >= total_tokens
        assert calc_duration >= total_duration


# Test utility functions
def create_test_interaction(session: Session, **kwargs) -> AgentInteraction:
    """Helper to create test interactions."""
    defaults = {
        "tenant_key": "test-tenant",
        "sub_agent_name": "test_agent",
        "interaction_type": "SPAWN",
        "mission": "Test mission",
    }
    defaults.update(kwargs)

    interaction = AgentInteraction(**defaults)
    session.add(interaction)
    session.commit()
    return interaction


def assert_interaction_valid(interaction: AgentInteraction):
    """Helper to validate interaction structure."""
    assert interaction.id is not None
    assert interaction.tenant_key is not None
    assert interaction.sub_agent_name is not None
    assert interaction.interaction_type in ["SPAWN", "COMPLETE", "ERROR"]
    assert interaction.mission is not None
    assert interaction.created_at is not None
