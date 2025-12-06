"""
Final Integration Test for Sub-Agent System
Comprehensive validation of all components post-restart
"""

import json
import time
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import AgentInteraction, Base, Message, Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestFinalIntegration:
    """Complete integration testing for production readiness"""

    @pytest.fixture
    def test_session(self):
        """Create in-memory test database session."""
        engine = create_engine(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def test_project(self, test_session):
        """Create a test project."""
        project = Project(
            id=str(uuid.uuid4()),
            tenant_key="test-tenant",
            name="Integration Test Project",
            mission="Test sub-agent integration",
            status="active",
        )
        test_session.add(project)
        test_session.commit()
        return project

    def test_spawn_sub_agent_creates_interaction(self, test_session, test_project):
        """Test that spawning a sub-agent creates proper interaction record"""
        # Create interaction for spawned sub-agent
        interaction = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="orchestrator",
            sub_agent_name="test_worker",
            interaction_type="spawn",
            mission="Process test data",
            start_time=datetime.now(timezone.utc),
            meta_data=json.dumps({"priority": "high", "test": True}),
        )

        test_session.add(interaction)
        test_session.commit()

        # Verify interaction was created
        result = test_session.query(AgentInteraction).filter_by(id=interaction.id).first()

        assert result is not None
        assert result.sub_agent_name == "test_worker"
        assert result.parent_agent_id == "orchestrator"
        assert result.interaction_type == "spawn"
        assert result.mission == "Process test data"

        meta = json.loads(result.meta_data)
        assert meta["priority"] == "high"
        assert meta["test"]

    def test_complete_sub_agent_updates_interaction(self, test_session, test_project):
        """Test completing a sub-agent updates the interaction properly"""
        # Create initial interaction
        interaction = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="orchestrator",
            sub_agent_name="completion_worker",
            interaction_type="spawn",
            mission="Complete task",
            start_time=datetime.now(timezone.utc),
        )

        test_session.add(interaction)
        test_session.commit()

        # Simulate completion
        time.sleep(0.1)  # Ensure some duration

        # Update to completed
        interaction.interaction_type = "database_initialized"
        interaction.end_time = datetime.now(timezone.utc)
        interaction.duration_seconds = int((interaction.end_time - interaction.start_time).total_seconds())
        interaction.result = "Task completed successfully"
        interaction.tokens_used = 150

        test_session.commit()

        # Verify completion
        result = test_session.query(AgentInteraction).filter_by(id=interaction.id).first()

        assert result.interaction_type == "database_initialized"
        assert result.end_time is not None
        assert result.duration_seconds > 0
        assert result.result == "Task completed successfully"
        assert result.tokens_used == 150

    def test_error_handling_in_sub_agent(self, test_session, test_project):
        """Test error scenarios are properly logged"""
        # Create interaction that will error
        interaction = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="orchestrator",
            sub_agent_name="error_worker",
            interaction_type="spawn",
            mission="Failing task",
            start_time=datetime.now(timezone.utc),
        )

        test_session.add(interaction)
        test_session.commit()

        # Simulate error
        interaction.interaction_type = "error"
        interaction.end_time = datetime.now(timezone.utc)
        interaction.duration_seconds = 1
        interaction.error_message = "Task failed: Resource not found"
        interaction.tokens_used = 50

        test_session.commit()

        # Verify error handling
        result = test_session.query(AgentInteraction).filter_by(id=interaction.id).first()

        assert result.interaction_type == "error"
        assert result.error_message == "Task failed: Resource not found"
        assert result.result is None
        assert result.tokens_used == 50

    def test_concurrent_sub_agents(self, test_session, test_project):
        """Test multiple sub-agents can run concurrently"""
        interactions = []

        # Create 5 concurrent sub-agents
        for i in range(5):
            interaction = AgentInteraction(
                id=str(uuid.uuid4()),
                tenant_key=test_project.tenant_key,
                project_id=test_project.id,
                parent_agent_id="orchestrator",
                sub_agent_name=f"worker_{i}",
                interaction_type="spawn",
                mission=f"Task {i}",
                start_time=datetime.now(timezone.utc),
                meta_data=json.dumps({"index": i}),
            )
            interactions.append(interaction)
            test_session.add(interaction)

        test_session.commit()

        # Verify all were created
        results = test_session.query(AgentInteraction).filter_by(project_id=test_project.id).all()

        assert len(results) == 5

        # Complete all sub-agents
        for interaction in interactions:
            interaction.interaction_type = "database_initialized"
            interaction.end_time = datetime.now(timezone.utc)
            interaction.duration_seconds = 1
            interaction.result = f"Completed {interaction.sub_agent_name}"
            interaction.tokens_used = 100

        test_session.commit()

        # Verify all completed
        completed = (
            test_session.query(AgentInteraction)
            .filter_by(project_id=test_project.id, interaction_type="database_initialized")
            .all()
        )

        assert len(completed) == 5
        for c in completed:
            assert c.result is not None
            assert c.tokens_used == 100

    def test_parent_child_relationships(self, test_session, test_project):
        """Test nested sub-agent relationships"""
        # Create parent -> child -> grandchild hierarchy
        parent = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="orchestrator",
            sub_agent_name="parent_worker",
            interaction_type="spawn",
            mission="Parent task",
            start_time=datetime.now(timezone.utc),
        )

        child = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="parent_worker",
            sub_agent_name="child_worker",
            interaction_type="spawn",
            mission="Child task",
            start_time=datetime.now(timezone.utc),
        )

        grandchild = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="child_worker",
            sub_agent_name="grandchild_worker",
            interaction_type="spawn",
            mission="Grandchild task",
            start_time=datetime.now(timezone.utc),
        )

        test_session.add_all([parent, child, grandchild])
        test_session.commit()

        # Verify relationships
        all_interactions = test_session.query(AgentInteraction).filter_by(project_id=test_project.id).all()

        assert len(all_interactions) == 3

        parent_result = next(i for i in all_interactions if i.sub_agent_name == "parent_worker")
        child_result = next(i for i in all_interactions if i.sub_agent_name == "child_worker")
        grandchild_result = next(i for i in all_interactions if i.sub_agent_name == "grandchild_worker")

        assert parent_result.parent_agent_id == "orchestrator"
        assert child_result.parent_agent_id == "parent_worker"
        assert grandchild_result.parent_agent_id == "child_worker"

    def test_metrics_aggregation(self, test_session, test_project):
        """Test aggregating metrics across sub-agents"""
        # Create completed interactions with metrics
        for i in range(3):
            interaction = AgentInteraction(
                id=str(uuid.uuid4()),
                tenant_key=test_project.tenant_key,
                project_id=test_project.id,
                parent_agent_id="orchestrator",
                sub_agent_name=f"metrics_worker_{i}",
                interaction_type="database_initialized",
                mission=f"Metrics task {i}",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=10 * (i + 1),
                tokens_used=100 * (i + 1),
                result=f"Result {i}",
            )
            test_session.add(interaction)

        test_session.commit()

        # Query and aggregate metrics
        results = (
            test_session.query(AgentInteraction)
            .filter_by(project_id=test_project.id, interaction_type="database_initialized")
            .all()
        )

        total_tokens = sum(r.tokens_used for r in results)
        total_duration = sum(r.duration_seconds for r in results)

        assert total_tokens == 600  # 100 + 200 + 300
        assert total_duration == 60  # 10 + 20 + 30

    def test_backward_compatibility_with_messages(self, test_session, test_project):
        """Ensure agent_interactions doesn't break existing message system"""
        # Create regular message
        message = Message(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            from_agent="orchestrator",
            to_agents=json.dumps(["worker_1"]),
            content="Regular message",
            message_type="direct",
            priority="normal",
            status="waiting",
        )

        # Create agent interaction
        interaction = AgentInteraction(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            parent_agent_id="orchestrator",
            sub_agent_name="sub_worker",
            interaction_type="spawn",
            mission="Sub-agent task",
            start_time=datetime.now(timezone.utc),
        )

        test_session.add_all([message, interaction])
        test_session.commit()

        # Verify both systems work independently
        messages = test_session.query(Message).filter_by(project_id=test_project.id).all()

        interactions = test_session.query(AgentInteraction).filter_by(project_id=test_project.id).all()

        assert len(messages) == 1
        assert len(interactions) == 1
        assert messages[0].content == "Regular message"
        assert interactions[0].mission == "Sub-agent task"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
