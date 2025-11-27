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
from src.giljo_mcp.models import MCPAgentJob, Message, Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper, TransactionalTestContext


class TestData:
    """Common test data and utilities"""

    @staticmethod
    def generate_tenant_key() -> str:
        """Generate a test tenant key"""
        from src.giljo_mcp.tenant import TenantManager
        return TenantManager.generate_tenant_key()

    @staticmethod
    def generate_project_data(tenant_key: str) -> dict[str, Any]:
        """Generate test project data"""
        return {
            "id": str(uuid.uuid4()),
            "name": f"Test Project {uuid.uuid4().hex[:8]}",
            "description": "Test project description for automated testing",
            "mission": "Test mission for automated testing",
            "status": ProjectStatus.ACTIVE.value,
            "tenant_key": tenant_key,
            "metadata": {"test": True},
        }

    @staticmethod
    def generate_agent_job_data(project_id: str, tenant_key: str, agent_type: Optional[str] = None) -> dict[str, Any]:
        """Generate test MCPAgentJob data"""
        return {
            "job_id": str(uuid.uuid4()),
            "tenant_key": tenant_key,
            "project_id": project_id,
            "agent_type": agent_type or "worker",
            "mission": f"Test mission for {agent_type or 'worker'} agent",
            "status": "waiting",
            "created_at": datetime.now(timezone.utc),
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
            "status": "waiting",
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
async def test_agent_jobs(db_session, test_project) -> list:
    """Create multiple test agent jobs"""
    jobs = []
    agent_types = ["orchestrator", "analyzer", "implementer", "tester"]

    for agent_type in agent_types:
        job_data = TestData.generate_agent_job_data(test_project.id, test_project.tenant_key, agent_type)
        job = MCPAgentJob(**job_data)
        db_session.add(job)
        jobs.append(job)

    await db_session.commit()
    for job in jobs:
        await db_session.refresh(job)

    return jobs


@pytest_asyncio.fixture(scope="function")
async def test_messages(db_session, test_agent_jobs, test_project) -> list:
    """Create test messages between agents"""
    messages = []

    # Create messages between agent jobs
    for i in range(len(test_agent_jobs) - 1):
        msg_data = TestData.generate_message_data(
            from_agent=test_agent_jobs[i].job_id, to_agent=test_agent_jobs[i + 1].job_id, project_id=test_project.id
        )
        message = Message(**msg_data)
        db_session.add(message)
        messages.append(message)

    await db_session.commit()
    for message in messages:
        await db_session.refresh(message)

    return messages


# E2E Closeout Workflow Fixtures
@pytest_asyncio.fixture(scope="function")
async def e2e_closeout_fixtures(db_session, db_manager):
    """
    Create E2E closeout workflow test fixtures.

    Creates:
    - Test user (test@example.com / testpassword)
    - Test product (active)
    - Test project (Mock Project, active)
    - 3 completed agent jobs

    Returns:
        dict: Fixtures (user, product, project, agents, tenant_key)
    """
    from tests.fixtures.e2e_closeout_fixtures import E2ECloseoutFixtures

    fixture_creator = E2ECloseoutFixtures(db_manager)
    fixtures = await fixture_creator.create_all_fixtures(db_session)

    # Verify fixtures were created
    await fixture_creator.verify_fixtures(db_session, fixtures["tenant_key"])

    return fixtures


# Note: Synchronous database fixtures have been removed.
# All tests should use async PostgreSQL fixtures for consistency with production.
# If you have synchronous tests, they should be migrated to async.
