"""
Unit tests for database operations and multi-tenant support.

Tests both SQLite and PostgreSQL functionality.
"""

import os

# Add src to path
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob, Message, Project, Task, Vision
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    @pytest.fixture
    def sqlite_db(self):
        """Create a temporary SQLite database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db_url = fPostgreSQLTestHelper.get_test_db_url(async_driver=False)
        db_manager = DatabaseManager(db_url)
        db_manager.create_tables()

        yield db_manager

        db_manager.close()
        os.unlink(db_path)

    def test_sqlite_database_creation(self, sqlite_db):
        """Test SQLite database and table creation."""
        assert sqlite_db.is_sqlite
        assert not sqlite_db.is_postgresql

        # Verify tables exist by creating a session
        with sqlite_db.get_session() as session:
            # Should not raise an error
            session.query(Project).count()

    def test_tenant_filter(self, sqlite_db):
        """Test tenant filter generation."""
        tenant_key = str(uuid4())
        filter_dict = sqlite_db.get_tenant_filter(tenant_key)

        assert filter_dict == {"tenant_key": tenant_key}


class TestMultiTenantModels:
    """Test multi-tenant model functionality."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory SQLite database session for testing."""
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()

        with db_manager.get_session() as session:
            yield session

        db_manager.close()

    def test_project_creation(self, db_session):
        """Test creating a project with tenant isolation."""
        tenant_key = str(uuid4())
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)

        db_session.add(project)
        db_session.commit()

        # Verify project was created
        found = db_session.query(Project).filter_by(tenant_key=tenant_key).first()

        assert found is not None
        assert found.name == "Test Project"
        assert found.mission == "Test mission"
        assert found.status == "active"
        assert found.context_budget == 150000

    def test_tenant_isolation(self, db_session):
        """Test that tenants are properly isolated."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create projects for different tenants
        project1 = Project(name="Tenant 1 Project", mission="Mission 1", tenant_key=tenant1)
        project2 = Project(name="Tenant 2 Project", mission="Mission 2", tenant_key=tenant2)

        db_session.add_all([project1, project2])
        db_session.commit()

        # Query by tenant should only return one project
        tenant1_projects = db_session.query(Project).filter_by(tenant_key=tenant1).all()

        assert len(tenant1_projects) == 1
        assert tenant1_projects[0].name == "Tenant 1 Project"

        tenant2_projects = db_session.query(Project).filter_by(tenant_key=tenant2).all()

        assert len(tenant2_projects) == 1
        assert tenant2_projects[0].name == "Tenant 2 Project"

    def test_agent_project_relationship(self, db_session):
        """Test agent-project relationships with tenant keys."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create agents
        agent1 = Agent(name="analyzer", role="analyzer", tenant_key=tenant_key, project_id=project.id)
        agent2 = Agent(name="implementer", role="implementer", tenant_key=tenant_key, project_id=project.id)

        db_session.add_all([agent1, agent2])
        db_session.commit()

        # Verify relationships
        db_session.refresh(project)
        assert len(project.agents) == 2
        assert {a.name for a in project.agents} == {"analyzer", "implementer"}

        # Verify agent lookup
        found_agent = db_session.query(Agent).filter_by(tenant_key=tenant_key, name="analyzer").first()

        assert found_agent is not None
        assert found_agent.role == "analyzer"
        assert found_agent.project.name == "Test Project"

    def test_message_acknowledgment(self, db_session):
        """Test message acknowledgment arrays."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create message
        message = Message(
            tenant_key=tenant_key,
            project_id=project.id,
            content="Test message",
            to_agents=["agent1", "agent2"],
            acknowledged_by=[],
        )

        db_session.add(message)
        db_session.commit()

        # Simulate acknowledgments
        message.acknowledged_by = ["agent1"]
        db_session.commit()

        # Verify acknowledgment
        found = db_session.query(Message).filter_by(id=message.id).first()

        assert "agent1" in found.acknowledged_by
        assert "agent2" not in found.acknowledged_by

        # Add second acknowledgment
        found.acknowledged_by = [*found.acknowledged_by, "agent2"]
        db_session.commit()

        # Verify both acknowledgments
        db_session.refresh(found)
        assert len(found.acknowledged_by) == 2
        assert set(found.acknowledged_by) == {"agent1", "agent2"}

    def test_task_hierarchy(self, db_session):
        """Test task parent-child relationships."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create parent task
        parent_task = Task(tenant_key=tenant_key, project_id=project.id, title="Parent Task", description="Main task")

        db_session.add(parent_task)
        db_session.commit()

        # Create subtasks
        subtask1 = Task(tenant_key=tenant_key, project_id=project.id, parent_task_id=parent_task.id, title="Subtask 1")
        subtask2 = Task(tenant_key=tenant_key, project_id=project.id, parent_task_id=parent_task.id, title="Subtask 2")

        db_session.add_all([subtask1, subtask2])
        db_session.commit()

        # Verify relationships
        db_session.refresh(parent_task)
        assert len(parent_task.subtasks) == 2
        assert {t.title for t in parent_task.subtasks} == {"Subtask 1", "Subtask 2"}

        # Verify parent reference
        db_session.refresh(subtask1)
        assert subtask1.parent_task.title == "Parent Task"

    def test_vision_chunking(self, db_session):
        """Test vision document chunking support."""
        tenant_key = str(uuid4())

        # Create project
        project = Project(name="Test Project", mission="Test mission", tenant_key=tenant_key)
        db_session.add(project)
        db_session.commit()

        # Create vision chunks
        chunks = []
        for i in range(3):
            chunk = Vision(
                tenant_key=tenant_key,
                project_id=project.id,
                document_name="architecture.md",
                chunk_number=i + 1,
                total_chunks=3,
                content=f"Chunk {i + 1} content",
                tokens=1000,
            )
            chunks.append(chunk)

        db_session.add_all(chunks)
        db_session.commit()

        # Query all chunks for document
        found_chunks = (
            db_session.query(Vision)
            .filter_by(tenant_key=tenant_key, document_name="architecture.md")
            .order_by(Vision.chunk_number)
            .all()
        )

        assert len(found_chunks) == 3
        assert [c.chunk_number for c in found_chunks] == [1, 2, 3]
        assert all(c.total_chunks == 3 for c in found_chunks)


class TestDatabaseOperations:
    """Test CRUD operations with multi-tenant support."""

    @pytest.fixture
    def db_manager(self):
        """Create an in-memory database manager for testing."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        manager.create_tables()
        yield manager
        manager.close()

    def test_project_crud(self, db_manager):
        """Test Create, Read, Update, Delete operations for projects."""
        tenant_key = str(uuid4())

        with db_manager.get_session() as session:
            # Create
            project = Project(name="CRUD Test", mission="Test CRUD operations", tenant_key=tenant_key)
            session.add(project)
            session.commit()
            project_id = project.id

        # Read
        with db_manager.get_session() as session:
            found = session.query(Project).filter_by(id=project_id, tenant_key=tenant_key).first()
            assert found.name == "CRUD Test"

        # Update
        with db_manager.get_session() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            project.status = "database_initialized"
            session.commit()

        # Verify update
        with db_manager.get_session() as session:
            found = session.query(Project).filter_by(id=project_id).first()
            assert found.status == "database_initialized"

        # Delete
        with db_manager.get_session() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            session.delete(project)
            session.commit()

        # Verify deletion
        with db_manager.get_session() as session:
            found = session.query(Project).filter_by(id=project_id).first()
            assert found is None

    def test_cascade_deletion(self, db_manager):
        """Test cascade deletion of related entities."""
        tenant_key = str(uuid4())

        with db_manager.get_session() as session:
            # Create project with related entities
            project = Project(name="Cascade Test", mission="Test cascading", tenant_key=tenant_key)
            session.add(project)
            session.commit()

            # Add agents
            agent = Agent(name="test_agent", role="tester", tenant_key=tenant_key, project_id=project.id)
            session.add(agent)

            # Add message
            message = Message(tenant_key=tenant_key, project_id=project.id, content="Test message")
            session.add(message)

            session.commit()
            project_id = project.id

        # Delete project
        with db_manager.get_session() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            session.delete(project)
            session.commit()

        # Verify cascade deletion
        with db_manager.get_session() as session:
            # Agents should be deleted
            agents = session.query(Agent).filter_by(tenant_key=tenant_key).all()
            assert len(agents) == 0

            # Messages should be deleted
            messages = session.query(Message).filter_by(tenant_key=tenant_key).all()
            assert len(messages) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
