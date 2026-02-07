"""
Simplified test suite for Sub-Agent Integration - runs without MCP server
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import AgentInteraction, Base, Message, Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestAgentInteractionsModel:
    """Test the agent_interactions database model and schema."""

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
    def sample_project(self, test_session):
        """Create a test project."""
        project = Project(
            id="test-project-123",
            tenant_key="test-tenant",
            name="Test Project",
            mission="Test mission",
            status="active",
        )
        test_session.add(project)
        test_session.commit()
        return project

    @pytest.fixture
    def sample_agent(self, test_session, sample_project):
        """Create a test agent."""
        agent = Agent(
            id="test-agent-123",
            tenant_key="test-tenant",
            project_id=sample_project.id,
            name="test_agent",
            role="test",
            status="active",
        )
        test_session.add(agent)
        test_session.commit()
        return agent

    def test_create_agent_interaction(self, test_session, sample_project):
        """Test creating a new agent interaction record."""
        interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            sub_agent_name="code_analyzer",
            interaction_type="SPAWN",
            mission="Analyze the codebase structure",
        )
        test_session.add(interaction)
        test_session.commit()

        assert interaction.id is not None
        assert interaction.interaction_type == "SPAWN"
        assert interaction.start_time is not None
        assert interaction.end_time is None
        assert interaction.duration_seconds is None

    def test_complete_agent_interaction(self, test_session, sample_project):
        """Test completing an agent interaction with results."""
        # Create spawn interaction
        interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            sub_agent_name="worker",
            interaction_type="SPAWN",
            mission="Complete a task",
        )
        test_session.add(interaction)
        test_session.commit()

        # Complete the interaction
        interaction.interaction_type = "COMPLETE"
        interaction.end_time = datetime.now(timezone.utc)
        interaction.duration_seconds = 45
        interaction.result = json.dumps({"files_analyzed": 25, "issues_found": 3})
        interaction.tokens_used = 2500
        test_session.commit()

        # Verify completion
        assert interaction.interaction_type == "COMPLETE"
        assert interaction.end_time is not None
        assert interaction.duration_seconds == 45
        assert interaction.tokens_used == 2500

    def test_error_agent_interaction(self, test_session, sample_project):
        """Test handling error in agent interaction."""
        interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            sub_agent_name="failing_worker",
            interaction_type="ERROR",
            mission="Task that failed",
            error_message="Sub-agent failed: Timeout after 60 seconds",
        )
        test_session.add(interaction)
        test_session.commit()

        assert interaction.interaction_type == "ERROR"
        assert interaction.error_message is not None
        assert "Timeout" in interaction.error_message

    def test_parent_child_relationship(self, test_session, sample_project, sample_agent):
        """Test parent-child agent relationship tracking."""
        interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            parent_agent_id=sample_agent.id,
            sub_agent_name="child_worker",
            interaction_type="SPAWN",
            mission="Perform specific task",
        )
        test_session.add(interaction)
        test_session.commit()

        # Verify relationship
        assert interaction.parent_agent_id == sample_agent.id
        assert interaction.parent_agent is not None

        # Check backref
        test_session.refresh(sample_agent)
        assert len(sample_agent.sub_agent_interactions) > 0

    def test_query_interactions_by_project(self, test_session, sample_project):
        """Test querying interactions by project."""
        # Create multiple interactions
        for i in range(3):
            interaction = AgentInteraction(
                tenant_key="test-tenant",
                project_id=sample_project.id,
                sub_agent_name=f"agent_{i}",
                interaction_type="SPAWN",
                mission=f"Task {i}",
            )
            test_session.add(interaction)
        test_session.commit()

        # Query by project
        stmt = select(AgentInteraction).where(AgentInteraction.project_id == sample_project.id)
        results = test_session.execute(stmt).scalars().all()

        assert len(results) == 3
        for result in results:
            assert result.project_id == sample_project.id


class TestBackwardCompatibility:
    """Test backward compatibility with existing message system."""

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
    def sample_project(self, test_session):
        """Create a test project."""
        project = Project(
            id="test-project-456",
            tenant_key="test-tenant",
            name="Compat Test",
            mission="Test compatibility",
            status="active",
        )
        test_session.add(project)
        test_session.commit()
        return project

    def test_message_system_unaffected(self, test_session, sample_project):
        """Test that existing message system continues to work."""
        message = Message(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            from_agent_id=None,  # Can be None for system messages
            to_agents=["worker1", "worker2"],
            content="Traditional message content",
            message_type="direct",
            priority="normal",
        )
        test_session.add(message)
        test_session.commit()

        assert message.id is not None
        assert message.acknowledged_by == []
        assert message.completed_by == []

    def test_concurrent_messaging_and_interactions(self, test_session, sample_project):
        """Test that messages and interactions can coexist."""
        # Create message
        message = Message(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            to_agents=["analyzer"],
            content="Analyze the system",
            message_type="direct",
            priority="high",
        )

        # Create interaction for same task
        interaction = AgentInteraction(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            sub_agent_name="analyzer",
            interaction_type="SPAWN",
            mission="Analyze the system",
        )

        test_session.add_all([message, interaction])
        test_session.commit()

        # Both should exist independently
        assert message.id is not None
        assert interaction.id is not None
        assert message.project_id == interaction.project_id


class TestMetricsAggregation:
    """Test metrics collection and aggregation."""

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
    def sample_project(self, test_session):
        """Create a test project."""
        project = Project(
            id="test-project-789",
            tenant_key="test-tenant",
            name="Metrics Test",
            mission="Test metrics",
            status="active",
        )
        test_session.add(project)
        test_session.commit()
        return project

    def test_metrics_aggregation(self, test_session, sample_project):
        """Test aggregating metrics across sub-agent interactions."""
        total_tokens = 0
        total_duration = 0

        # Create multiple completed interactions
        for i in range(5):
            interaction = AgentInteraction(
                tenant_key="test-tenant",
                project_id=sample_project.id,
                sub_agent_name=f"metric_agent_{i}",
                interaction_type="COMPLETE",
                mission=f"Task {i}",
                duration_seconds=10 + i,
                tokens_used=100 * (i + 1),
            )
            test_session.add(interaction)
            total_tokens += interaction.tokens_used
            total_duration += interaction.duration_seconds

        test_session.commit()

        # Query and aggregate
        stmt = select(AgentInteraction).where(
            AgentInteraction.project_id == sample_project.id, AgentInteraction.interaction_type == "COMPLETE"
        )
        completed = test_session.execute(stmt).scalars().all()

        calc_tokens = sum(i.tokens_used or 0 for i in completed)
        calc_duration = sum(i.duration_seconds or 0 for i in completed)

        assert len(completed) == 5
        assert calc_tokens == total_tokens
        assert calc_duration == total_duration
        assert calc_tokens == 1500  # 100 + 200 + 300 + 400 + 500
        assert calc_duration == 60  # 10 + 11 + 12 + 13 + 14


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
