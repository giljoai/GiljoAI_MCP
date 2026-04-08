# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test suite for AgentJobManager exception-based error handling.

This test suite verifies that AgentJobManager raises appropriate exceptions
instead of returning error dicts (0480 migration).

Tests cover:
- spawn_agent() - Generic exceptions
- complete_job() - ResourceNotFoundError and generic exceptions
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import BaseGiljoError, ResourceNotFoundError
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
def mock_db_manager():
    """Create a mock DatabaseManager."""
    return AsyncMock(spec=DatabaseManager)


@pytest.fixture
def mock_tenant_manager():
    """Create a mock TenantManager."""
    manager = AsyncMock(spec=TenantManager)
    manager.get_current_tenant.return_value = "test-tenant"
    return manager


@pytest.fixture
def agent_job_manager(mock_db_manager, mock_tenant_manager):
    """Create an AgentJobManager instance with mocked dependencies."""
    return AgentJobManager(db_manager=mock_db_manager, tenant_manager=mock_tenant_manager)


class TestSpawnAgentExceptions:
    """Test spawn_agent() exception handling."""

    @pytest.mark.asyncio
    async def test_spawn_agent_raises_exception_on_database_error(self, agent_job_manager, mock_db_manager):
        """Test that spawn_agent raises BaseGiljoError on database errors."""
        # Mock session to raise an exception during commit
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit.side_effect = Exception("Database connection lost")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_db_manager.get_session_async.return_value = mock_session

        # Verify exception is raised (not error dict returned)
        with pytest.raises(BaseGiljoError) as exc_info:
            await agent_job_manager.spawn_agent(
                project_id="test-project",
                agent_display_name="Test Agent",
                mission="Test mission",
                tenant_key="test-tenant",
            )

        # Verify exception details
        assert "Database connection lost" in str(exc_info.value)
        assert exc_info.value.context.get("operation") == "spawn_agent"


class TestCompleteJobExceptions:
    """Test complete_job() exception handling."""

    @pytest.mark.asyncio
    async def test_complete_job_raises_not_found_error(self, agent_job_manager, mock_db_manager):
        """Test that complete_job raises ResourceNotFoundError when job not found."""
        # Mock session that returns no job
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_db_manager.get_session_async.return_value = mock_session

        # Verify ResourceNotFoundError is raised
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_job_manager.complete_job(job_id="nonexistent-job", tenant_key="test-tenant")

        # Verify exception details
        assert "Job" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
        assert exc_info.value.context.get("job_id") == "nonexistent-job"

    @pytest.mark.asyncio
    async def test_complete_job_raises_exception_on_database_error(self, agent_job_manager, mock_db_manager):
        """Test that complete_job raises BaseGiljoError on database errors."""
        # Mock session that raises an exception
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database error during job completion")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_db_manager.get_session_async.return_value = mock_session

        # Verify exception is raised
        with pytest.raises(BaseGiljoError) as exc_info:
            await agent_job_manager.complete_job(job_id="test-job", tenant_key="test-tenant")

        # Verify exception details
        assert "Database error during job completion" in str(exc_info.value)
        assert exc_info.value.context.get("operation") == "complete_job"
