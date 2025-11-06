"""
Base test fixtures for GiljoAI MCP test suite.
Provides reusable fixtures for database, models, and common test data.

All tests now use PostgreSQL for consistency with production.
Test isolation is achieved through transaction rollback.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any, Optional

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.enums import AgentStatus, ProjectStatus
from src.giljo_mcp.models import Agent, Message, Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper, TransactionalTestContext


class TestData:
    """Common test data and utilities"""

    @staticmethod
    def generate_tenant_key() -> str:
        """Generate a test tenant key"""
        return f"tk_test_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def generate_project_data(tenant_key: str) -> dict[str, Any]:
        """Generate test project data"""
        return {
            "id": str(uuid.uuid4()),
            "name": f"Test Project {uuid.uuid4().hex[:8]}",
            "mission": "Test mission for automated testing",
            "status": ProjectStatus.ACTIVE.value,
            "tenant_key": tenant_key,
            "metadata": {"test": True},
        }

    @staticmethod
    def generate_agent_data(project_id: str, name: Optional[str] = None) -> dict[str, Any]:
        """Generate test agent data"""
        return {
            "id": str(uuid.uuid4()),
            "name": name or f"agent_{uuid.uuid4().hex[:8]}",
            "role": "worker",  # Agent uses 'role' not 'type'
            "status": AgentStatus.ACTIVE.value,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc),
            "metadata": {"test": True},
        }

    @staticmethod
    def generate_message_data(from_agent: str, to_agent: str, project_id: str) -> dict[str, Any]:
        """Generate test message data"""
        return {
            "id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "content": "Test message content",
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc),
            "status": "pending",
        }


@pytest_asyncio.fixture(scope="function")
async def db_manager():
    """
    Function-scoped PostgreSQL database manager.
    Creates a new connection for each test to avoid event loop issues.
    """
    # Ensure test database exists (idempotent)
    await PostgreSQLTestHelper.ensure_test_database_exists()

    connection_string = PostgreSQLTestHelper.get_test_db_url()
    db_mgr = DatabaseManager(connection_string, is_async=True)

    # Tables should already exist from setup script
    # But create them if they don't (idempotent operation)
    try:
        await PostgreSQLTestHelper.create_test_tables(db_mgr)
    except Exception:
        pass  # Tables likely already exist

    yield db_mgr

    # Cleanup
    await db_mgr.close_async()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_manager) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for testing with transaction isolation.

    Each test runs in a transaction that is rolled back at the end,
    ensuring clean state between tests.
    """
    async with TransactionalTestContext(db_manager) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_project(db_session) -> Project:
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
            from_agent=test_agents[i].name, to_agent=test_agents[i + 1].name, project_id=test_project.id
        )
        message = Message(**msg_data)
        db_session.add(message)
        messages.append(message)

    await db_session.commit()
    for message in messages:
        await db_session.refresh(message)

    return messages


# Note: Synchronous database fixtures have been removed.
# All tests should use async PostgreSQL fixtures for consistency with production.
# If you have synchronous tests, they should be migrated to async.
