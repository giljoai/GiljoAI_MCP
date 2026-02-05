"""
Test suite for launch implementation endpoint (Handover 0709).

Tests cover:
- PATCH /projects/{project_id}/launch-implementation sets timestamp
- Endpoint is idempotent (already launched)
- Proper error handling (project not found, tenant isolation)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.auth import User


class TestLaunchImplementationEndpoint:
    """Test suite for PATCH /projects/{project_id}/launch-implementation endpoint."""

    @pytest.mark.asyncio
    async def test_launch_implementation_sets_timestamp(self):
        """Test that launching implementation sets the implementation_launched_at timestamp."""
        project_id = str(uuid4())
        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test description",
            mission="Test mission",
            status="active",
            implementation_launched_at=None,
        )

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=project)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Mock user
        mock_user = User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            tenant_key="tenant-test",
            is_active=True,
        )

        # Import endpoint function directly
        from api.endpoints.agent_jobs.orchestration import launch_implementation

        # Call endpoint
        response = await launch_implementation(
            project_id=project_id,
            current_user=mock_user,
            db=mock_session
        )

        # Verify timestamp was set
        assert project.implementation_launched_at is not None, "implementation_launched_at should be set"
        assert response.success is True, "Response should indicate success"
        assert response.implementation_launched_at is not None, "Response should include timestamp"

        # Verify database operations
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_launch_implementation_idempotent(self):
        """Test that launching implementation again is idempotent."""
        project_id = str(uuid4())
        original_timestamp = datetime.now(timezone.utc)
        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test description",
            mission="Test mission",
            status="active",
            implementation_launched_at=original_timestamp,
        )

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=project)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Mock user
        mock_user = User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            tenant_key="tenant-test",
            is_active=True,
        )

        # Import endpoint function directly
        from api.endpoints.agent_jobs.orchestration import launch_implementation

        # Call endpoint
        response = await launch_implementation(
            project_id=project_id,
            current_user=mock_user,
            db=mock_session
        )

        # Verify timestamp unchanged
        assert project.implementation_launched_at == original_timestamp, "Timestamp should not change on repeat call"
        assert response.already_launched is True, "Response should indicate already launched"
        assert response.launched_at == original_timestamp.isoformat(), "Response should return original timestamp"

        # Verify no database commit (idempotent)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_launch_implementation_project_not_found(self):
        """Test that endpoint returns 404 when project not found."""
        project_id = str(uuid4())

        # Mock database session returning None
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=None)

        # Mock user
        mock_user = User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            tenant_key="tenant-test",
            is_active=True,
        )

        # Import endpoint function directly
        from api.endpoints.agent_jobs.orchestration import launch_implementation

        # Call endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await launch_implementation(
                project_id=project_id,
                current_user=mock_user,
                db=mock_session
            )

        # Verify 404 error
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_launch_implementation_tenant_isolation(self):
        """Test that endpoint enforces tenant isolation."""
        project_id = str(uuid4())
        project = Project(
            id=project_id,
            tenant_key="tenant-other",  # Different tenant
            name="Test Project",
            description="Test description",
            mission="Test mission",
            status="active",
            implementation_launched_at=None,
        )

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=project)

        # Mock user with different tenant
        mock_user = User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            tenant_key="tenant-test",  # Different tenant
            is_active=True,
        )

        # Import endpoint function directly
        from api.endpoints.agent_jobs.orchestration import launch_implementation

        # Call endpoint with different tenant_key
        with pytest.raises(HTTPException) as exc_info:
            await launch_implementation(
                project_id=project_id,
                current_user=mock_user,
                db=mock_session
            )

        # Verify 404 error (tenant isolation)
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()
