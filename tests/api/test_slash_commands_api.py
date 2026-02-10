"""
API tests for slash command endpoints (Handover 0080a)
Tests the /api/slash/execute endpoint functionality

Updated for 0730e compliance:
- UUID fixtures with str(uuid4()) for all IDs
- org_id NOT NULL (0424j) - create Organization before User
- Proper AgentJob/AgentExecution relationship
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from passlib.hash import bcrypt
from sqlalchemy import select

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate test tenant key using proper TenantManager"""
    from src.giljo_mcp.tenant import TenantManager

    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def mock_product(db_session, test_tenant_key):
    """Create test product with UUID-based ID"""
    from src.giljo_mcp.models import Product

    unique_id = str(uuid4())[:8]
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {unique_id}",
        description="Test product for slash command tests",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest_asyncio.fixture
async def mock_project(db_session, test_tenant_key, mock_product):
    """Create test project with UUID-based ID"""
    unique_id = str(uuid4())[:8]
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {unique_id}",
        description="Test project for slash command tests",
        mission="Test mission for slash command tests",
        tenant_key=test_tenant_key,
        product_id=mock_product.id,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest_asyncio.fixture
async def mock_orchestrator(db_session, test_tenant_key, mock_project):
    """Create test orchestrator job with proper AgentJob/AgentExecution relationship.

    Returns AgentExecution with additional attributes for test access:
    - _project_id: The project_id from AgentJob
    - _agent_job: The AgentJob instance
    """
    job_id = str(uuid4())

    # Create AgentJob (work order) first - project_id and mission are on AgentJob
    agent_job = AgentJob(
        job_id=job_id,
        tenant_key=test_tenant_key,
        project_id=mock_project.id,
        job_type="orchestrator",
        mission="Lead the test project",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(agent_job)
    await db_session.flush()

    # Create AgentExecution (executor) linked to job
    # Note: AgentExecution does NOT have project_id or mission - they're on AgentJob
    orchestrator = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job_id,
        agent_display_name="orchestrator",
        status="working",
        tenant_key=test_tenant_key,
        context_used=50000,
        context_budget=200000,
    )
    db_session.add(orchestrator)
    await db_session.commit()

    # Attach project_id for test access (from AgentJob)
    orchestrator._project_id = mock_project.id
    orchestrator._agent_job = agent_job

    return orchestrator


class TestSlashCommandExecute:
    """Tests for /api/slash/execute endpoint"""

    @pytest.mark.asyncio
    async def test_execute_nonexistent_command(self, api_client, auth_headers, test_tenant_key):
        """Test executing nonexistent slash command"""
        response = await api_client.post(
            "/api/slash/execute",
            headers=auth_headers,
            json={
                "command": "gil_nonexistent",
                "tenant_key": test_tenant_key,
                "arguments": {},
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_execute_without_auth(self, api_client):
        """Test executing slash command without authentication"""
        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "gil_handover",
                "tenant_key": "test-tenant",
                "arguments": {},
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_execute_with_invalid_tenant(self, api_client, auth_headers, mock_orchestrator):
        """Test executing slash command with wrong tenant key"""
        response = await api_client.post(
            "/api/slash/execute",
            headers=auth_headers,
            json={
                "command": "gil_handover",
                "tenant_key": "wrong-tenant-key",
                "arguments": {"orchestrator_job_id": mock_orchestrator.job_id},
            },
        )

        # Should return error from handler (not 404, but unsuccessful result)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False


class TestTriggerSuccessionEndpoint:
    """Tests for /api/agent-jobs/{job_id}/trigger_succession endpoint"""

    @pytest.mark.asyncio
    async def test_trigger_succession_nonexistent_job(self, api_client, auth_headers):
        """Test triggering succession for nonexistent job"""
        response = await api_client.post(
            "/api/agent-jobs/nonexistent-job-id/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_trigger_succession_without_auth(self, api_client, mock_orchestrator):
        """Test triggering succession without authentication"""
        response = await api_client.post(f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
