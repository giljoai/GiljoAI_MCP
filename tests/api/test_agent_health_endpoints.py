"""
API tests for Agent Health Endpoints (Handover 0107).

Tests cancel endpoint, force-fail endpoint, health endpoint,
authentication, and multi-tenant isolation.

Coverage Target: 80%+
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.models import MCPAgentJob, User


@pytest_asyncio.fixture
async def api_client():
    """Create FastAPI test client."""
    from api.app import app
    return TestClient(app)


@pytest_asyncio.fixture
async def test_user():
    """Create test user for authentication."""
    return User(
        id=str(uuid4()),
        username="test_user",
        email="test@example.com",
        tenant_key=f"tk_test_{uuid4().hex[:16]}",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        hashed_password="hashed",
    )


@pytest_asyncio.fixture
async def authenticated_client(api_client, test_user, db_manager):
    """Create API client with authentication mocked."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    # Override authentication
    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    yield api_client, test_user

    # Cleanup
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_job(db_session, test_user):
    """Create test agent job."""
    job = MCPAgentJob(
        tenant_key=test_user.tenant_key,
        project_id=str(uuid4()),
        job_id=str(uuid4()),
        agent_type="implementer",
        mission="Test mission",
        status="active",
        messages=[],
        last_progress_at=datetime.now(timezone.utc),
        last_message_check_at=datetime.now(timezone.utc),
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    return job


class TestCancelEndpoint:
    """Test cancel job endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_endpoint_requires_auth(self, api_client):
        """Test that cancel endpoint returns 401 without authentication."""
        # Attempt to cancel without auth
        response = api_client.post(
            f"/api/jobs/{uuid4()}/cancel",
            json={"reason": "Test"}
        )

        # Verify 401 Unauthorized
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cancel_endpoint_changes_status(self, authenticated_client, test_job, db_session):
        """Test that cancel endpoint changes job status to 'cancelling'."""
        client, user = authenticated_client

        # Cancel job
        response = client.post(
            f"/api/jobs/{test_job.job_id}/cancel",
            json={"reason": "User requested cancellation"}
        )

        # Verify success response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "cancelling"

        # Verify database
        await db_session.refresh(test_job)
        assert test_job.status == "cancelling"

    @pytest.mark.asyncio
    async def test_cancel_endpoint_invalid_job_id(self, authenticated_client):
        """Test cancel endpoint with non-existent job ID."""
        client, user = authenticated_client
        fake_job_id = str(uuid4())

        # Attempt to cancel non-existent job
        response = client.post(
            f"/api/jobs/{fake_job_id}/cancel",
            json={"reason": "Should fail"}
        )

        # Verify 404 Not Found
        assert response.status_code in [404, 400]  # Depending on implementation


class TestForceFailEndpoint:
    """Test force-fail job endpoint."""

    @pytest.mark.asyncio
    async def test_force_fail_endpoint_requires_auth(self, api_client):
        """Test that force-fail endpoint returns 401 without authentication."""
        # Attempt to force-fail without auth
        response = api_client.post(
            f"/api/jobs/{uuid4()}/force-fail",
            json={"reason": "Test"}
        )

        # Verify 401 Unauthorized
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_force_fail_endpoint_marks_failed(self, authenticated_client, test_job, db_session):
        """Test that force-fail endpoint marks job as failed."""
        client, user = authenticated_client

        # Force fail job
        response = client.post(
            f"/api/jobs/{test_job.job_id}/force-fail",
            json={"reason": "Agent unresponsive"}
        )

        # Verify success response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify database
        await db_session.refresh(test_job)
        assert test_job.status == "failed"


class TestHealthEndpoint:
    """Test job health metrics endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_metrics(self, authenticated_client, test_job):
        """Test that health endpoint returns correct response shape."""
        client, user = authenticated_client

        # Get health metrics
        response = client.get(f"/api/jobs/{test_job.job_id}/health")

        # Verify response structure
        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert "status" in data
        assert "last_progress_at" in data
        assert "last_message_check_at" in data
        assert "minutes_since_progress" in data
        assert "is_stale" in data

        assert data["job_id"] == test_job.job_id
        assert data["status"] == test_job.status

    @pytest.mark.asyncio
    async def test_health_endpoint_calculates_stale(self, authenticated_client, db_session, test_user):
        """Test that health endpoint correctly calculates is_stale."""
        client, user = authenticated_client

        # Create job with stale timestamp (11 minutes ago)
        stale_job = MCPAgentJob(
            tenant_key=test_user.tenant_key,
            project_id=str(uuid4()),
            job_id=str(uuid4()),
            agent_type="implementer",
            mission="Stale job",
            status="active",
            last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=11),
            last_message_check_at=datetime.now(timezone.utc),
        )

        db_session.add(stale_job)
        await db_session.commit()

        # Get health metrics
        response = client.get(f"/api/jobs/{stale_job.job_id}/health")

        # Verify stale detection
        assert response.status_code == 200
        data = response.json()
        assert data["is_stale"] is True
        assert data["minutes_since_progress"] >= 10

    @pytest.mark.asyncio
    async def test_health_endpoint_handles_no_timestamps(self, authenticated_client, db_session, test_user):
        """Test that health endpoint handles None timestamp values gracefully."""
        client, user = authenticated_client

        # Create job with no timestamps
        new_job = MCPAgentJob(
            tenant_key=test_user.tenant_key,
            project_id=str(uuid4()),
            job_id=str(uuid4()),
            agent_type="implementer",
            mission="New job",
            status="pending",
            last_progress_at=None,
            last_message_check_at=None,
        )

        db_session.add(new_job)
        await db_session.commit()

        # Get health metrics
        response = client.get(f"/api/jobs/{new_job.job_id}/health")

        # Verify graceful handling
        assert response.status_code == 200
        data = response.json()
        assert data["last_progress_at"] is None
        assert data["minutes_since_progress"] is None
        assert data["is_stale"] is False  # New jobs aren't stale


class TestMultiTenantIsolation:
    """Test multi-tenant isolation across all endpoints."""

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_all_endpoints(self, db_session):
        """Test that all health endpoints respect tenant boundaries."""
        from api.app import app
        from src.giljo_mcp.auth.dependencies import get_current_active_user

        tenant_a = f"tk_test_{uuid4().hex[:16]}"
        tenant_b = f"tk_test_{uuid4().hex[:16]}"

        # Create users for both tenants
        user_a = User(
            id=str(uuid4()),
            username="user_a",
            email="user_a@example.com",
            tenant_key=tenant_a,
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc),
            hashed_password="hashed",
        )

        user_b = User(
            id=str(uuid4()),
            username="user_b",
            email="user_b@example.com",
            tenant_key=tenant_b,
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc),
            hashed_password="hashed",
        )

        # Create job for tenant A
        job_a = MCPAgentJob(
            tenant_key=tenant_a,
            project_id=str(uuid4()),
            job_id=str(uuid4()),
            agent_type="implementer",
            mission="Tenant A job",
            status="active",
            messages=[],
        )

        db_session.add(job_a)
        await db_session.commit()

        # Create client authenticated as user B
        client = TestClient(app)

        async def mock_get_user_b():
            return user_b

        app.dependency_overrides[get_current_active_user] = mock_get_user_b

        # Attempt cancel from tenant B
        response = client.post(
            f"/api/jobs/{job_a.job_id}/cancel",
            json={"reason": "Cross-tenant attack"}
        )
        assert response.status_code in [404, 403]  # Not found or forbidden

        # Attempt force-fail from tenant B
        response = client.post(
            f"/api/jobs/{job_a.job_id}/force-fail",
            json={"reason": "Cross-tenant attack"}
        )
        assert response.status_code in [404, 403]

        # Attempt health check from tenant B
        response = client.get(f"/api/jobs/{job_a.job_id}/health")
        assert response.status_code in [404, 403]

        # Verify job unchanged
        await db_session.refresh(job_a)
        assert job_a.status == "active"

        # Cleanup
        app.dependency_overrides.clear()
