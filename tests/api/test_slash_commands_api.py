"""
API tests for slash command endpoints (Handover 0080a)
Tests the /api/slash/execute endpoint functionality
"""

import pytest
import pytest_asyncio
from fastapi import status
from sqlalchemy import select

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate test tenant key"""
    import uuid
    return f"tk_test_{uuid.uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def mock_product(db_session, test_tenant_key):
    """Create test product"""
    from src.giljo_mcp.models import Product

    product = Product(
        id="test-product-id",
        name="Test Product",
        description="Test product for slash command tests",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest_asyncio.fixture
async def mock_project(db_session, test_tenant_key, mock_product):
    """Create test project"""
    project = Project(
        id="test-project-id",
        name="Test Project",
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
    """Create test orchestrator job"""
    orchestrator = AgentExecution(
        job_id="orch-test-12345",
        agent_display_name="orchestrator",
        status="working",
        tenant_key=test_tenant_key,
        project_id=mock_project.id,        context_used=50000,
        context_budget=200000,
        mission="Lead the test project",
    )
    db_session.add(orchestrator)
    await db_session.commit()
    return orchestrator


class TestSlashCommandExecute:
    """Tests for /api/slash/execute endpoint"""

    @pytest.mark.asyncio
    async def test_execute_gil_handover_success(self, api_client, auth_headers, mock_orchestrator):
        """Test successful /gil_handover execution"""
        response = await api_client.post(
            "/api/slash/execute",
            headers=auth_headers,
            json={
                "command": "gil_handover",
                "tenant_key": mock_orchestrator.tenant_key,
                "project_id": mock_orchestrator.project_id,
                "arguments": {"orchestrator_job_id": mock_orchestrator.job_id},
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "successor_id" in data
        assert "launch_prompt" in data
        assert "handover_summary" in data
        assert "Instance 2" in data["message"]

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
    async def test_trigger_succession_success(self, api_client, auth_headers, mock_orchestrator):
        """Test successful succession trigger via UI endpoint"""
        response = await api_client.post(
            f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "successor_id" in data
        assert "launch_prompt" in data
        assert "handover_summary" in data

    @pytest.mark.asyncio
    async def test_trigger_succession_nonexistent_job(self, api_client, auth_headers):
        """Test triggering succession for nonexistent job"""
        response = await api_client.post(
            "/api/agent-jobs/nonexistent-job-id/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_trigger_succession_non_orchestrator(self, api_client, auth_headers, db_session, test_tenant_key, mock_project):
        """Test triggering succession for non-orchestrator agent"""
        # Create non-orchestrator agent
        frontend_agent = AgentExecution(
            job_id="frontend-test-12345",
            agent_display_name="frontend-dev",
            status="working",
            tenant_key=test_tenant_key,
            project_id=mock_project.id,
        )
        db_session.add(frontend_agent)
        await db_session.commit()

        response = await api_client.post(
            f"/api/agent-jobs/{frontend_agent.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not an orchestrator" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_trigger_succession_already_handed_over(self, api_client, auth_headers, db_session, mock_orchestrator):
        """Test triggering succession for already handed over orchestrator"""
        # Mark orchestrator as handed over
        mock_orchestrator.status = "complete"
        mock_orchestrator.handover_to = "orch-successor-12345"
        await db_session.commit()

        response = await api_client.post(
            f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already been handed over" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_trigger_succession_without_auth(self, api_client, mock_orchestrator):
        """Test triggering succession without authentication"""
        response = await api_client.post(f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_trigger_succession_creates_waiting_successor(self, api_client, auth_headers, db_session, mock_orchestrator):
        """Test that succession creates successor in waiting state"""
        response = await api_client.post(
            f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        successor_id = data["successor_id"]

        # Verify successor exists and is in waiting state
        stmt = select(AgentExecution).where(AgentExecution.job_id == successor_id)
        result = await db_session.execute(stmt)
        successor = result.scalar_one()

        assert successor.status == "waiting"
        assert successor.agent_display_name == "orchestrator"
        assert successor.spawned_by == mock_orchestrator.job_id

    @pytest.mark.asyncio
    async def test_trigger_succession_marks_original_complete(self, api_client, auth_headers, db_session, mock_orchestrator):
        """Test that succession marks original orchestrator as complete"""
        original_job_id = mock_orchestrator.job_id

        response = await api_client.post(
            f"/api/agent-jobs/{original_job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify original orchestrator is complete
        db_session.expire(mock_orchestrator)
        await db_session.refresh(mock_orchestrator)

        assert mock_orchestrator.status == "complete"
        assert mock_orchestrator.handover_to is not None
        assert mock_orchestrator.handover_summary is not None
