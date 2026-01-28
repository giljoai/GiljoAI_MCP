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
from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
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
    def generate_agent_job_data(project_id: str, tenant_key: str, agent_display_name: Optional[str] = None) -> dict[str, Any]:
        """
        Generate test AgentJob data (work order - the WHAT).

        Migration Note (0367d): Replaced MCPAgentJob with AgentJob.
        Returns AgentJob data dictionary.
        """
        return {
            "job_id": str(uuid.uuid4()),
            "tenant_key": tenant_key,
            "project_id": project_id,
            "job_type": agent_display_name or "worker",
            "mission": f"Test mission for {agent_display_name or 'worker'} agent",
            "status": "active",  # AgentJob has 3 statuses: active/completed/cancelled
            "created_at": datetime.now(timezone.utc),
            "job_metadata": {},
        }

    @staticmethod
    def generate_agent_execution_data(
        job_id: str, tenant_key: str, agent_display_name: Optional[str] = None, instance_number: int = 1
    ) -> dict[str, Any]:
        """
        Generate test AgentExecution data (executor - the WHO).

        Migration Note (0367d): Extracted from AgentExecution.
        Returns AgentExecution data dictionary.
        """
        return {
            "agent_id": str(uuid.uuid4()),
            "job_id": job_id,
            "tenant_key": tenant_key,
            "agent_display_name": agent_display_name or "worker",
            "agent_name": f"Test {agent_display_name or 'worker'} Agent",
            "instance_number": instance_number,
            "status": "waiting",  # AgentExecution has 7 statuses
            "progress": 0,
            "messages_sent_count": 0,
            "messages_waiting_count": 0,
            "messages_read_count": 0,
            "health_status": "unknown",
            "tool_type": "universal",
            "context_used": 0,
            "context_budget": 150000,
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

    # Cleanup - ensure proper async disposal
    try:
        if db_mgr and db_mgr.async_engine:
            await db_mgr.close_async()
    except Exception:
        # Ignore cleanup errors - test is done
        pass


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
async def test_agent_jobs(db_session, test_project) -> list[tuple[AgentJob, AgentExecution]]:
    """
    Create multiple test agent jobs with executions.

    Migration Note (0367d): Now creates both AgentJob and AgentExecution.
    Returns list of tuples: [(job1, execution1), (job2, execution2), ...]

    For backward compatibility, tests can unpack: jobs_and_execs = test_agent_jobs
    Or access jobs only: jobs = [job for job, _ in test_agent_jobs]
    """
    jobs_and_executions = []
    agent_display_names = ["orchestrator", "analyzer", "implementer", "tester"]

    for agent_display_name in agent_display_names:
        # Create AgentJob (work order)
        job_data = TestData.generate_agent_job_data(test_project.id, test_project.tenant_key, agent_display_name)
        job = AgentJob(**job_data)
        db_session.add(job)

        # Create AgentExecution (executor)
        execution_data = TestData.generate_agent_execution_data(job.job_id, test_project.tenant_key, agent_display_name)
        execution = AgentExecution(**execution_data)
        db_session.add(execution)

        jobs_and_executions.append((job, execution))

    await db_session.commit()
    for job, execution in jobs_and_executions:
        await db_session.refresh(job)
        await db_session.refresh(execution)

    return jobs_and_executions


@pytest_asyncio.fixture(scope="function")
async def test_messages(db_session, test_agent_jobs, test_project) -> list:
    """
    Create test messages between agents.

    Migration Note (0367d): Messages reference agent_id (from AgentExecution).
    test_agent_jobs now returns list of tuples: [(job, execution), ...]
    """
    messages = []

    # Create messages between agent executions
    for i in range(len(test_agent_jobs) - 1):
        # Extract executions from tuples
        _, from_execution = test_agent_jobs[i]
        _, to_execution = test_agent_jobs[i + 1]

        msg_data = TestData.generate_message_data(
            from_agent=from_execution.agent_id,
            to_agent=to_execution.agent_id,
            project_id=test_project.id,
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
