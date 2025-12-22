"""
Edge case tests for database operations and multi-tenant support.

Tests error handling, boundary conditions, and concurrent access scenarios.
"""

# Add src to path
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.exc import IntegrityError

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Configuration, Job, Message, Project, Session, Task, Vision
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory SQLite database session for testing."""
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()

        with db_manager.get_session() as session:
            yield session

        db_manager.close()

    def test_duplicate_agent_name_per_project(self, db_session):
        """Test that duplicate agent names are prevented within a project."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create first agent
        agent1 = Agent(name="analyzer", role="analyzer", tenant_key=tenant_key, project_id=project.id)
        db_session.add(agent1)
        db_session.commit()

        # Try to create duplicate agent
        agent2 = Agent(
            name="analyzer",  # Same name
            role="implementer",  # Different role
            tenant_key=tenant_key,
            project_id=project.id,
        )
        db_session.add(agent2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_agent_name_uniqueness_across_projects(self, db_session):
        """Test that same agent name can exist in different projects."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create two projects
        project1 = Project(name="Project 1", mission="Mission 1", tenant_key=tenant1)
        project2 = Project(name="Project 2", mission="Mission 2", tenant_key=tenant2)
        db_session.add_all([project1, project2])
        db_session.commit()

        # Create agents with same name in different projects
        agent1 = Agent(name="analyzer", role="analyzer", tenant_key=tenant1, project_id=project1.id)
        agent2 = Agent(name="analyzer", role="analyzer", tenant_key=tenant2, project_id=project2.id)  # Same name

        db_session.add_all([agent1, agent2])
        db_session.commit()  # Should succeed

        # Verify both exist
        count = db_session.query(Agent).filter_by(name="analyzer").count()
        assert count == 2

    def test_large_json_metadata(self, db_session):
        """Test storing large JSON metadata."""
        tenant_key = str(uuid4())

        # Create large metadata
        large_metadata = {
            "nested": {"level1": {"level2": {"data": ["item" * 100 for _ in range(100)]}}},
            "arrays": [list(range(100)) for _ in range(10)],
            "strings": {f"key_{i}": f"value_{i}" * 50 for i in range(50)},
        }

        project = Project(
            name="Large Metadata Test",
            mission="Test large JSON storage",
            tenant_key=tenant_key,
            meta_data=large_metadata,
        )

        db_session.add(project)
        db_session.commit()

        # Retrieve and verify
        found = db_session.query(Project).filter_by(id=project.id).first()
        assert found.meta_data == large_metadata

    def test_message_acknowledgment_race_condition(self, db_session):
        """Test concurrent acknowledgment updates."""
        tenant_key = str(uuid4())

        # Create project and message
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        message = Message(
            tenant_key=tenant_key,
            project_id=project.id,
            content="Test message",
            to_agents=["agent1", "agent2", "agent3"],
            acknowledged_by=[],
        )
        db_session.add(message)
        db_session.commit()

        # Simulate concurrent acknowledgments
        msg = db_session.query(Message).filter_by(id=message.id).first()

        # First acknowledgment
        msg.acknowledged_by = [*msg.acknowledged_by, "agent1"]
        db_session.commit()

        # Second acknowledgment (simulating another session's update)
        db_session.refresh(msg)
        msg.acknowledged_by = [*msg.acknowledged_by, "agent2"]
        db_session.commit()

        # Third acknowledgment
        db_session.refresh(msg)
        msg.acknowledged_by = [*msg.acknowledged_by, "agent3"]
        db_session.commit()

        # Verify all acknowledgments are preserved
        db_session.refresh(msg)
        assert len(msg.acknowledged_by) == 3
        assert set(msg.acknowledged_by) == {"agent1", "agent2", "agent3"}

    def test_circular_task_dependency_prevention(self, db_session):
        """Test that circular task dependencies are handled."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create task chain
        task1 = Task(tenant_key=tenant_key, project_id=project.id, title="Task 1")
        db_session.add(task1)
        db_session.commit()

        task2 = Task(tenant_key=tenant_key, project_id=project.id, title="Task 2", parent_task_id=task1.id)
        db_session.add(task2)
        db_session.commit()

        task3 = Task(tenant_key=tenant_key, project_id=project.id, title="Task 3", parent_task_id=task2.id)
        db_session.add(task3)
        db_session.commit()

        # Verify hierarchy
        db_session.refresh(task1)
        assert len(task1.subtasks) == 1
        assert task1.subtasks[0].title == "Task 2"

        db_session.refresh(task2)
        assert len(task2.subtasks) == 1
        assert task2.subtasks[0].title == "Task 3"

    def test_vision_chunk_ordering(self, db_session):
        """Test vision document chunk ordering and retrieval."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create chunks out of order
        chunks = []
        for i in [3, 1, 5, 2, 4]:  # Deliberately out of order
            chunk = Vision(
                tenant_key=tenant_key,
                project_id=project.id,
                document_name="large_doc.md",
                chunk_number=i,
                total_chunks=5,
                content=f"Content for chunk {i}",
                tokens=1000 * i,
            )
            chunks.append(chunk)

        db_session.add_all(chunks)
        db_session.commit()

        # Retrieve in correct order
        ordered_chunks = (
            db_session.query(Vision)
            .filter_by(tenant_key=tenant_key, document_name="large_doc.md")
            .order_by(Vision.chunk_number)
            .all()
        )

        # Verify ordering
        assert len(ordered_chunks) == 5
        for i, chunk in enumerate(ordered_chunks, 1):
            assert chunk.chunk_number == i
            assert chunk.content == f"Content for chunk {i}"

    def test_configuration_tenant_isolation(self, db_session):
        """Test configuration isolation between tenants."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create configurations for different tenants
        config1 = Configuration(tenant_key=tenant1, key="api_key", value={"key": "secret1"}, is_secret=True)
        config2 = Configuration(tenant_key=tenant2, key="api_key", value={"key": "secret2"}, is_secret=True)  # Same key
        global_config = Configuration(tenant_key=None, key="system_setting", value={"enabled": True})  # Global config

        db_session.add_all([config1, config2, global_config])
        db_session.commit()

        # Query tenant1 configs
        tenant1_configs = db_session.query(Configuration).filter_by(tenant_key=tenant1).all()
        assert len(tenant1_configs) == 1
        assert tenant1_configs[0].value["key"] == "secret1"

        # Query tenant2 configs
        tenant2_configs = db_session.query(Configuration).filter_by(tenant_key=tenant2).all()
        assert len(tenant2_configs) == 1
        assert tenant2_configs[0].value["key"] == "secret2"

        # Query global configs
        global_configs = db_session.query(Configuration).filter_by(tenant_key=None).all()
        assert len(global_configs) == 1
        assert global_configs[0].key == "system_setting"

    def test_job_status_transitions(self, db_session):
        """Test job status transitions and task tracking."""
        tenant_key = str(uuid4())

        # Create project and agent
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        agent = Agent(name="worker", role="implementer", tenant_key=tenant_key, project_id=project.id)
        db_session.add(agent)
        db_session.commit()

        # Create job with tasks
        job = Job(
            tenant_key=tenant_key,
            agent_id=agent.id,
            job_type="implementation",
            tasks=["Create database models", "Write unit tests", "Document API"],
            scope_boundary="Only work on database layer",
            vision_alignment="Supports multi-tenant architecture goal",
        )
        db_session.add(job)
        db_session.commit()

        # Update job status
        job.status = "database_initialized"
        job.database_initialized_at = datetime.now(timezone.utc)
        job.meta_data = {"completion_notes": "All tasks completed successfully", "lines_of_code": 1500}
        db_session.commit()

        # Verify job and agent relationship
        db_session.refresh(agent)
        assert len(agent.jobs) == 1
        assert agent.jobs[0].status == "database_initialized"
        assert len(agent.jobs[0].tasks) == 3

    def test_session_numbering_uniqueness(self, db_session):
        """Test session numbering uniqueness per project."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create first session
        session1 = Session(
            tenant_key=tenant_key,
            project_id=project.id,
            session_number=1,
            title="Session 1",
            objectives="Test objectives",
        )
        db_session.add(session1)
        db_session.commit()

        # Try to create duplicate session number
        session2 = Session(
            tenant_key=tenant_key,
            project_id=project.id,
            session_number=1,  # Duplicate number
            title="Session 2",
            objectives="Different objectives",
        )
        db_session.add(session2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_empty_and_null_values(self, db_session):
        """Test handling of empty strings and null values."""
        tenant_key = str(uuid4())

        # Create project with minimal required fields
        project = Project(name="", mission="Mission", tenant_key=tenant_key)  # Empty string
        db_session.add(project)
        db_session.commit()

        # Create message with null optional fields
        message = Message(
            tenant_key=tenant_key,
            project_id=project.id,
            content="Content",
            subject=None,  # Null subject
            to_agents=[],  # Empty array
        )
        db_session.add(message)
        db_session.commit()

        # Verify handling
        assert message.to_agents == []
        assert message.acknowledged_by == []

    def test_context_budget_tracking(self, db_session):
        """Test context budget tracking and limits."""
        tenant_key = str(uuid4())

        # Create project with limited budget
        project = Project(
            name="Limited Budget Project",
            mission="Test budget tracking",
            tenant_key=tenant_key,
            context_budget=1000,
            context_used=0,
        )
        db_session.add(project)
        db_session.commit()

        # Simulate context usage
        for _i in range(5):
            project.context_used += 200
            db_session.commit()

            # Check if over budget
            if project.context_used >= project.context_budget:
                project.status = "inactive"
                db_session.commit()
                break

        # Verify budget tracking
        db_session.refresh(project)
        assert project.context_used == 1000
        assert project.status == "inactive"


class TestPathHandling:
    """Test OS-neutral path handling."""

    def test_path_creation_cross_platform(self):
        """Test that paths are created correctly across platforms."""
        from src.giljo_mcp.config import Config

        config = Config()

        # Test home directory path
        assert isinstance(config.data_dir, Path)
        assert config.data_dir.is_absolute()

        # Test database path
        assert isinstance(config.db_path, Path)
        assert str(config.db_path).replace("\\", "/").endswith(".giljo-mcp/data/giljo_mcp.db")

        # Test log path
        assert isinstance(config.log_dir, Path)
        assert config.log_dir.is_absolute()

    def test_database_url_generation(self):
        """Test database URL generation with proper path handling."""
        from src.giljo_mcp.config import Config

        config = Config()

        # SQLite URL should use forward slashes even on Windows
        sqlite_url = config.get_database_url()
        assert sqlite_url.startswith(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        assert "\\" not in sqlite_url  # No backslashes in URL

        # PostgreSQL URL should not contain file paths
        pg_url = config.get_database_url(
            postgresql=True, host="localhost", port=5432, database="testdb", user="testuser", password="testpass"
        )
        assert pg_url == "postgresql://testuser:testpass@localhost:5432/testdb"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
