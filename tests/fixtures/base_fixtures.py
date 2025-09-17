"""
Base test fixtures for GiljoAI MCP test suite.
Provides reusable fixtures for database, models, and common test data.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
from pathlib import Path
import tempfile
import os

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Agent, Message, Task
from src.giljo_mcp.enums import AgentRole, ProjectType, AgentStatus, ProjectStatus
from src.giljo_mcp.tenant import TenantManager
from sqlalchemy.ext.asyncio import AsyncSession


class TestData:
    """Common test data and utilities"""

    @staticmethod
    def generate_tenant_key() -> str:
        """Generate a test tenant key"""
        return f"tk_test_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def generate_project_data(tenant_key: str) -> Dict[str, Any]:
        """Generate test project data"""
        return {
            "id": str(uuid.uuid4()),
            "name": f"Test Project {uuid.uuid4().hex[:8]}",
            "mission": "Test mission for automated testing",
            "status": ProjectStatus.ACTIVE.value,
            "tenant_key": tenant_key,
            "type": ProjectType.DEVELOPMENT.value,
            "metadata": {"test": True}
        }

    @staticmethod
    def generate_agent_data(project_id: str, name: str = None) -> Dict[str, Any]:
        """Generate test agent data"""
        return {
            "id": str(uuid.uuid4()),
            "name": name or f"agent_{uuid.uuid4().hex[:8]}",
            "type": AgentRole.WORKER.value,
            "status": AgentStatus.ACTIVE.value,
            "project_id": project_id,
            "created_at": datetime.utcnow(),
            "metadata": {"test": True}
        }

    @staticmethod
    def generate_message_data(
        from_agent: str,
        to_agent: str,
        project_id: str
    ) -> Dict[str, Any]:
        """Generate test message data"""
        return {
            "id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "content": "Test message content",
            "project_id": project_id,
            "created_at": datetime.utcnow(),
            "status": "pending"
        }


@pytest_asyncio.fixture(scope="function")
async def sqlite_db_manager():
    """Create SQLite database manager for testing"""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    # Create database manager with test database
    connection_string = f"sqlite+aiosqlite:///{temp_db.name}"
    db_manager = DatabaseManager(connection_string, is_async=True)

    # Initialize database
    await db_manager.create_tables_async()

    yield db_manager

    # Cleanup
    await db_manager.close_async()
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest_asyncio.fixture(scope="function")
async def postgresql_db_manager():
    """Create PostgreSQL database manager for testing"""
    # Use test database configuration
    connection_string = DatabaseManager.build_postgresql_url(
        host="localhost",
        port=5432,
        database="giljo_mcp_test",
        username="postgres",
        password="4010"
    )

    # Convert to async URL
    connection_string = connection_string.replace("postgresql://", "postgresql+asyncpg://")

    db_manager = DatabaseManager(connection_string, is_async=True)

    # Drop and recreate tables for clean test
    try:
        await db_manager.drop_tables_async()
    except:
        pass
    await db_manager.create_tables_async()

    yield db_manager

    # Cleanup
    await db_manager.close_async()


@pytest_asyncio.fixture(scope="function")
async def db_session(sqlite_db_manager) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for testing (defaults to SQLite)"""
    async with sqlite_db_manager.get_session_async() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_project(db_session, sqlite_db_manager) -> Project:
    """Create a test project"""
    tenant_key = TestData.generate_tenant_key()
    project_data = TestData.generate_project_data(tenant_key)

    project = Project(**project_data)
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest_asyncio.fixture(scope="function")
async def test_agents(db_session, test_project) -> list:
    """Create multiple test agents"""
    agents = []
    agent_names = ["orchestrator", "analyzer", "implementer", "tester"]

    for name in agent_names:
        agent_data = TestData.generate_agent_data(test_project.id, name)
        agent = Agent(**agent_data)
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)

    return agents


@pytest_asyncio.fixture(scope="function")
async def test_messages(db_session, test_agents, test_project) -> list:
    """Create test messages between agents"""
    messages = []

    # Create messages between agents
    for i in range(len(test_agents) - 1):
        msg_data = TestData.generate_message_data(
            from_agent=test_agents[i].name,
            to_agent=test_agents[i + 1].name,
            project_id=test_project.id
        )
        message = Message(**msg_data)
        db_session.add(message)
        messages.append(message)

    await db_session.commit()
    for message in messages:
        await db_session.refresh(message)

    return messages


# Synchronous database fixtures for non-async tests
@pytest.fixture(scope="function")
def sync_db_manager():
    """Create synchronous SQLite database manager for testing"""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    # Create database manager with test database
    connection_string = f"sqlite:///{temp_db.name}"
    db_manager = DatabaseManager(connection_string, is_async=False)

    # Initialize database
    db_manager.create_tables()

    yield db_manager

    # Cleanup
    db_manager.close()
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture(scope="function")
def sync_session(sync_db_manager):
    """Get synchronous database session for testing"""
    with sync_db_manager.get_session() as session:
        yield session