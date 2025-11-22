"""
Test mission tracking fields in table-view API endpoint (Handover 0233)
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from uuid import uuid4

from src.giljo_mcp.models.agents import MCPAgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.products import Product


@pytest.fixture
async def test_project_with_jobs(db_manager, admin_user):
    """Create a test project with jobs that have mission tracking fields"""
    async with db_manager.get_session_async() as session:
        # Create product first
        product = Product(
            id=str(uuid4()),
            tenant_key=admin_user.tenant_key,
            name="Test Product",
            description="Test product for mission tracking",
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        
        # Create project
        project = Project(
            id=str(uuid4()),
            product_id=product.id,
            tenant_key=admin_user.tenant_key,
            name="Mission Tracking Test Project",
            description="Test project for mission tracking fields",
            mission="Test mission",
            status="active",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Job 1: With mission_read_at set
        job1_id = str(uuid4())
        read_time = datetime.now(timezone.utc)
        job1 = MCPAgentJob(
            job_id=job1_id,
            tenant_key=admin_user.tenant_key,
            project_id=project.id,
            agent_type="orchestrator",
            agent_name="Test Orchestrator 1",
            tool_type="claude-code",
            mission="Test mission 1",
            status="working",
            mission_read_at=read_time,
            instance_number=1,
        )

        # Job 2: With mission_acknowledged_at set
        job2_id = str(uuid4())
        ack_time = datetime.now(timezone.utc)
        job2 = MCPAgentJob(
            job_id=job2_id,
            tenant_key=admin_user.tenant_key,
            project_id=project.id,
            agent_type="implementer",
            agent_name="Test Implementer",
            tool_type="claude-code",
            mission="Test mission 2",
            status="working",
            mission_acknowledged_at=ack_time,
            instance_number=1,
        )

        # Job 3: With both fields null
        job3_id = str(uuid4())
        job3 = MCPAgentJob(
            job_id=job3_id,
            tenant_key=admin_user.tenant_key,
            project_id=project.id,
            agent_type="tester",
            agent_name="Test Tester",
            tool_type="claude-code",
            mission="Test mission 3",
            status="waiting",
            mission_read_at=None,
            mission_acknowledged_at=None,
            instance_number=1,
        )

        session.add(job1)
        session.add(job2)
        session.add(job3)
        await session.commit()

        return project


@pytest.mark.asyncio
async def test_table_view_returns_mission_read_at_field(
    async_client: AsyncClient, auth_headers, test_project_with_jobs
):
    """Test that /api/agent-jobs/table-view returns mission_read_at"""
    response = await async_client.get(
        f"/api/agent-jobs/table-view?project_id={test_project_with_jobs.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert "rows" in data

    # Find our job in response
    job_row = next((r for r in data["rows"] if r["job_id"] == test_project_with_jobs["job1_id"]), None)
    assert job_row is not None, "Job not found in response"
    assert "mission_read_at" in job_row, "mission_read_at field missing from response"
    assert job_row["mission_read_at"] is not None


@pytest.mark.asyncio
async def test_table_view_returns_mission_acknowledged_at_field(
    async_client: AsyncClient, auth_headers, test_project_with_jobs
):
    """Test that /api/agent-jobs/table-view returns mission_acknowledged_at"""
    response = await async_client.get(
        f"/api/agent-jobs/table-view?project_id={test_project_with_jobs.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    job_row = next((r for r in data["rows"] if r["job_id"] == test_project_with_jobs["job2_id"]), None)
    assert job_row is not None, "Job not found in response"
    assert "mission_acknowledged_at" in job_row, "mission_acknowledged_at field missing from response"
    assert job_row["mission_acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_table_view_mission_fields_null_when_not_set(
    async_client: AsyncClient, auth_headers, test_project_with_jobs
):
    """Test that mission fields are null when not set"""
    response = await async_client.get(
        f"/api/agent-jobs/table-view?project_id={test_project_with_jobs.id}",
        headers=auth_headers,
    )
    data = response.json()

    job_row = next((r for r in data["rows"] if r["job_id"] == test_project_with_jobs["job3_id"]), None)
    assert job_row is not None, "Job not found in response"
    assert job_row["mission_read_at"] is None
    assert job_row["mission_acknowledged_at"] is None
