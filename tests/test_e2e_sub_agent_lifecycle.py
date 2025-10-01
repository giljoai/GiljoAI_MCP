"""
End-to-End Test for Sub-Agent Lifecycle
Tests the complete flow from spawn to completion with real-time events
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.database import init_db
from src.giljo_mcp.models import AgentInteraction
from tests.helpers.test_db_helper import PostgreSQLTestHelper

# TODO: AgentTools class doesn't exist yet - commenting out for test collection
# from src.giljo_mcp.tools.agent import AgentTools


class TestSubAgentLifecycle:
    """Test complete sub-agent lifecycle with WebSocket events"""

    @pytest.fixture
    async def db_session(self):
        """Create test database session"""
        engine = create_async_engine(PostgreSQLTestHelper.get_test_db_url())
        async with engine.begin() as conn:
            await conn.run_sync(init_db)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            yield session
            await session.close()

        await engine.dispose()

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager for event testing"""
        manager = Mock()
        manager.broadcast = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_full_sub_agent_lifecycle(self, db_session, mock_websocket_manager):
        """Test complete spawn -> work -> complete cycle"""
        # Setup
        tools = AgentTools()
        tools.session = db_session
        tools.websocket_manager = mock_websocket_manager

        project_id = str(uuid.uuid4())
        parent_agent = "orchestrator"
        sub_agent = "test_worker"
        mission = "Process test data"

        # Step 1: Spawn sub-agent
        spawn_result = await tools.spawn_and_log_sub_agent(
            project_id=project_id,
            parent_agent_name=parent_agent,
            sub_agent_name=sub_agent,
            mission=mission,
            meta_data={"test": True, "priority": "high"},
        )

        # Verify spawn
        assert spawn_result["success"]
        assert "interaction_id" in spawn_result
        assert spawn_result["sub_agent_name"] == sub_agent

        interaction_id = spawn_result["interaction_id"]

        # Verify WebSocket event was sent
        mock_websocket_manager.broadcast.assert_called()
        spawn_event = mock_websocket_manager.broadcast.call_args[0][1]
        assert spawn_event["type"] == "sub_agent_spawned"
        assert spawn_event["data"]["sub_agent_name"] == sub_agent

        # Step 2: Simulate work (wait)
        await asyncio.sleep(0.1)

        # Step 3: Complete sub-agent
        complete_result = await tools.log_sub_agent_completion(
            interaction_id=interaction_id,
            result="Test completed successfully",
            tokens_used=150,
            meta_data={"output": "processed_data.json"},
        )

        # Verify completion
        assert complete_result["success"]
        assert complete_result["status"] == "completed"
        assert "duration_seconds" in complete_result

        # Verify completion WebSocket event
        complete_event = next(
            call[0][1]
            for call in mock_websocket_manager.broadcast.call_args_list
            if call[0][1]["type"] == "sub_agent_completed"
        )
        assert complete_event["data"]["interaction_id"] == interaction_id
        assert complete_event["data"]["result"] == "Test completed successfully"

        # Step 4: Verify database state
        interaction = await db_session.get(AgentInteraction, interaction_id)
        assert interaction is not None
        assert interaction.sub_agent_name == sub_agent
        assert interaction.result == "Test completed successfully"
        assert interaction.tokens_used == 150
        assert interaction.duration_seconds > 0
        assert interaction.end_time is not None

    @pytest.mark.asyncio
    async def test_concurrent_sub_agent_spawns(self, db_session, mock_websocket_manager):
        """Test multiple sub-agents spawned concurrently"""
        tools = AgentTools()
        tools.session = db_session
        tools.websocket_manager = mock_websocket_manager

        project_id = str(uuid.uuid4())
        parent_agent = "orchestrator"

        # Spawn 5 sub-agents concurrently
        spawn_tasks = []
        for i in range(5):
            task = tools.spawn_and_log_sub_agent(
                project_id=project_id,
                parent_agent_name=parent_agent,
                sub_agent_name=f"worker_{i}",
                mission=f"Task {i}",
                meta_data={"index": i},
            )
            spawn_tasks.append(task)

        # Execute all spawns concurrently
        spawn_results = await asyncio.gather(*spawn_tasks)

        # Verify all spawns succeeded
        assert len(spawn_results) == 5
        for i, result in enumerate(spawn_results):
            assert result["success"]
            assert result["sub_agent_name"] == f"worker_{i}"

        # Verify no race conditions - all have unique IDs
        interaction_ids = [r["interaction_id"] for r in spawn_results]
        assert len(set(interaction_ids)) == 5  # All unique

        # Complete all sub-agents
        complete_tasks = []
        for result in spawn_results:
            task = tools.log_sub_agent_completion(
                interaction_id=result["interaction_id"], result=f"Completed {result['sub_agent_name']}", tokens_used=100
            )
            complete_tasks.append(task)

        complete_results = await asyncio.gather(*complete_tasks)

        # Verify all completions
        assert len(complete_results) == 5
        for result in complete_results:
            assert result["success"]
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_sub_agent_error_handling(self, db_session, mock_websocket_manager):
        """Test sub-agent failure scenarios"""
        tools = AgentTools()
        tools.session = db_session
        tools.websocket_manager = mock_websocket_manager

        project_id = str(uuid.uuid4())

        # Spawn sub-agent
        spawn_result = await tools.spawn_and_log_sub_agent(
            project_id=project_id,
            parent_agent_name="orchestrator",
            sub_agent_name="failing_worker",
            mission="Impossible task",
        )

        interaction_id = spawn_result["interaction_id"]

        # Log error completion
        error_result = await tools.log_sub_agent_completion(
            interaction_id=interaction_id, result=None, error="Task failed: Resource not found", tokens_used=50
        )

        # Verify error handling
        assert error_result["success"]
        assert error_result["status"] == "error"
        assert error_result["error"] == "Task failed: Resource not found"

        # Verify error WebSocket event
        error_event = next(
            call[0][1]
            for call in mock_websocket_manager.broadcast.call_args_list
            if call[0][1]["type"] == "sub_agent_error"
        )
        assert error_event["data"]["interaction_id"] == interaction_id
        assert "Resource not found" in error_event["data"]["error"]

        # Verify database state
        interaction = await db_session.get(AgentInteraction, interaction_id)
        assert interaction.error_message == "Task failed: Resource not found"
        assert interaction.result is None

    @pytest.mark.asyncio
    async def test_parent_child_relationships(self, db_session, mock_websocket_manager):
        """Test nested sub-agent relationships"""
        tools = AgentTools()
        tools.session = db_session
        tools.websocket_manager = mock_websocket_manager

        project_id = str(uuid.uuid4())

        # Create parent -> child -> grandchild hierarchy
        parent_result = await tools.spawn_and_log_sub_agent(
            project_id=project_id,
            parent_agent_name="orchestrator",
            sub_agent_name="parent_worker",
            mission="Parent task",
        )

        child_result = await tools.spawn_and_log_sub_agent(
            project_id=project_id,
            parent_agent_name="parent_worker",
            sub_agent_name="child_worker",
            mission="Child task",
        )

        grandchild_result = await tools.spawn_and_log_sub_agent(
            project_id=project_id,
            parent_agent_name="child_worker",
            sub_agent_name="grandchild_worker",
            mission="Grandchild task",
        )

        # Complete in reverse order (grandchild -> child -> parent)
        await tools.log_sub_agent_completion(
            interaction_id=grandchild_result["interaction_id"], result="Grandchild done", tokens_used=25
        )

        await tools.log_sub_agent_completion(
            interaction_id=child_result["interaction_id"], result="Child done", tokens_used=50
        )

        await tools.log_sub_agent_completion(
            interaction_id=parent_result["interaction_id"], result="Parent done", tokens_used=100
        )

        # Verify relationships in database

        # Query all interactions for this project
        stmt = select(AgentInteraction).where(AgentInteraction.project_id == project_id)
        result = await db_session.execute(stmt)
        interactions = result.scalars().all()

        assert len(interactions) == 3

        # Verify parent-child relationships
        parent_int = next(i for i in interactions if i.sub_agent_name == "parent_worker")
        child_int = next(i for i in interactions if i.sub_agent_name == "child_worker")
        grandchild_int = next(i for i in interactions if i.sub_agent_name == "grandchild_worker")

        assert parent_int.parent_agent_id == "orchestrator"
        assert child_int.parent_agent_id == "parent_worker"
        assert grandchild_int.parent_agent_id == "child_worker"

        # Verify all completed successfully
        for interaction in interactions:
            assert interaction.interaction_type == "completed"
            assert interaction.result is not None
            assert interaction.duration_seconds > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
