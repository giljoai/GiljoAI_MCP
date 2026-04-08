# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from src.giljo_mcp.models import Project
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
        import random

        return {
            "id": str(uuid.uuid4()),
            "name": f"Test Project {uuid.uuid4().hex[:8]}",
            "description": "Test project description for automated testing",
            "mission": "Test mission for automated testing",
            "status": "active",
            "tenant_key": tenant_key,
            "metadata": {"test": True},
            "series_number": random.randint(1, 999999),
        }

    @staticmethod
    def generate_agent_job_data(
        project_id: str, tenant_key: str, agent_display_name: Optional[str] = None
    ) -> dict[str, Any]:
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
        job_id: str, tenant_key: str, agent_display_name: Optional[str] = None
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
            "status": "waiting",  # AgentExecution has 7 statuses
            "progress": 0,
            "messages_sent_count": 0,
            "messages_waiting_count": 0,
            "messages_read_count": 0,
            "health_status": "unknown",
            "tool_type": "universal",
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


# Note: Synchronous database fixtures have been removed.
# All tests should use async PostgreSQL fixtures for consistency with production.
# If you have synchronous tests, they should be migrated to async.
