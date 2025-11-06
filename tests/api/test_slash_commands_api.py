"""
API tests for slash command endpoints (Handover 0080a)
Tests the /api/slash/execute endpoint functionality
"""

import pytest
from fastapi import status
from sqlalchemy import select

from src.giljo_mcp.models import MCPAgentJob, Project


@pytest.fixture
def mock_project(db_session, test_tenant):
    """Create test project"""
    project = Project(
        id="test-project-id",
        name="Test Project",
        tenant_key=test_tenant.tenant_key,
        product_id="test-product-id",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def mock_orchestrator(db_session, test_tenant, mock_project):
    """Create test orchestrator job"""
    orchestrator = MCPAgentJob(
        job_id="orch-test-12345",
        agent_type="orchestrator",
        status="working",
        tenant_key=test_tenant.tenant_key,
        project_id=mock_project.id,
        instance_number=1,
        context_used=50000,
        context_budget=200000,
        mission="Lead the test project",
    )
    db_session.add(orchestrator)
    db_session.commit()
    return orchestrator


class TestSlashCommandExecute:
    """Tests for /api/slash/execute endpoint"""

    def test_execute_gil_handover_success(self, client, auth_headers, mock_orchestrator):
        """Test successful /gil_handover execution"""
        response = client.post(
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

    def test_execute_nonexistent_command(self, client, auth_headers, test_tenant):
        """Test executing nonexistent slash command"""
        response = client.post(
            "/api/slash/execute",
            headers=auth_headers,
            json={
                "command": "gil_nonexistent",
                "tenant_key": test_tenant.tenant_key,
                "arguments": {},
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_execute_without_auth(self, client):
        """Test executing slash command without authentication"""
        response = client.post(
            "/api/slash/execute",
            json={
                "command": "gil_handover",
                "tenant_key": "test-tenant",
                "arguments": {},
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_execute_with_invalid_tenant(self, client, auth_headers, mock_orchestrator):
        """Test executing slash command with wrong tenant key"""
        response = client.post(
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

    def test_trigger_succession_success(self, client, auth_headers, mock_orchestrator):
        """Test successful succession trigger via UI endpoint"""
        response = client.post(
            f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "successor_id" in data
        assert "launch_prompt" in data
        assert "handover_summary" in data

    def test_trigger_succession_nonexistent_job(self, client, auth_headers):
        """Test triggering succession for nonexistent job"""
        response = client.post(
            "/api/agent-jobs/nonexistent-job-id/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_trigger_succession_non_orchestrator(self, client, auth_headers, db_session, test_tenant, mock_project):
        """Test triggering succession for non-orchestrator agent"""
        # Create non-orchestrator agent
        frontend_agent = MCPAgentJob(
            job_id="frontend-test-12345",
            agent_type="frontend-dev",
            status="working",
            tenant_key=test_tenant.tenant_key,
            project_id=mock_project.id,
        )
        db_session.add(frontend_agent)
        db_session.commit()

        response = client.post(
            f"/api/agent-jobs/{frontend_agent.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not an orchestrator" in response.json()["detail"]

    def test_trigger_succession_already_handed_over(self, client, auth_headers, db_session, mock_orchestrator):
        """Test triggering succession for already handed over orchestrator"""
        # Mark orchestrator as handed over
        mock_orchestrator.status = "complete"
        mock_orchestrator.handover_to = "orch-successor-12345"
        db_session.commit()

        response = client.post(
            f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already been handed over" in response.json()["detail"]

    def test_trigger_succession_without_auth(self, client, mock_orchestrator):
        """Test triggering succession without authentication"""
        response = client.post(f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_trigger_succession_creates_waiting_successor(self, client, auth_headers, db_session, mock_orchestrator):
        """Test that succession creates successor in waiting state"""
        response = client.post(
            f"/api/agent-jobs/{mock_orchestrator.job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        successor_id = data["successor_id"]

        # Verify successor exists and is in waiting state
        stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == successor_id)
        result = db_session.execute(stmt)
        successor = result.scalar_one()

        assert successor.status == "waiting"
        assert successor.agent_type == "orchestrator"
        assert successor.instance_number == 2
        assert successor.spawned_by == mock_orchestrator.job_id

    def test_trigger_succession_marks_original_complete(self, client, auth_headers, db_session, mock_orchestrator):
        """Test that succession marks original orchestrator as complete"""
        original_job_id = mock_orchestrator.job_id

        response = client.post(
            f"/api/agent-jobs/{original_job_id}/trigger_succession",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify original orchestrator is complete
        db_session.expire(mock_orchestrator)
        db_session.refresh(mock_orchestrator)

        assert mock_orchestrator.status == "complete"
        assert mock_orchestrator.handover_to is not None
        assert mock_orchestrator.handover_summary is not None
