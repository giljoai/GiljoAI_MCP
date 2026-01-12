"""
Backend Integration Tests for Job Acknowledged Feature - Handover 0297a

Tests the mission_acknowledged_at field tracking in the Jobs dashboard.

Test Coverage:
- Database field exists and is nullable
- API endpoint includes mission_acknowledged_at in responses
- MCP tool sets mission_acknowledged_at on first mission fetch
- Multi-tenant isolation for acknowledged status
- WebSocket event emitted when mission acknowledged
- Idempotent behavior (doesn't overwrite existing timestamp)

TDD Approach: RED Phase
These tests verify that the jobs endpoint correctly exposes the mission_acknowledged_at
field that tracks when an agent first fetches their mission.

Backend Integration Testing - TDD Methodology
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tenant import TenantManager

pytestmark = pytest.mark.asyncio


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
async def test_project_with_jobs_acknowledged(db_session: AsyncSession, tenant_manager: TenantManager):
    """Create a test project with jobs in different acknowledged states."""
    # Use TenantManager to generate a valid tenant key
    tenant_key = tenant_manager.generate_tenant_key("test-tenant-0297a")
    tenant_manager.set_current_tenant(tenant_key)

    # Create project
    project = Project(
        id=f"proj-0297a-{uuid4().hex[:8]}",
        name="Test Project 0297a",
        description="Test project for mission acknowledged tracking",
        mission="Test mission acknowledged implementation",
        tenant_key=tenant_key,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.flush()

    # Create jobs with different acknowledged states
    now = datetime.now(timezone.utc)
    jobs_data = [
        {
            "job_id": "job-unacknowledged-001",
            "agent_name": "Unacknowledged Agent",
            "agent_display_name": "implementer",
            "mission_acknowledged_at": None,  # Not acknowledged yet
        },
        {
            "job_id": "job-acknowledged-002",
            "agent_name": "Acknowledged Agent",
            "agent_display_name": "orchestrator",
            "mission_acknowledged_at": now - timedelta(minutes=5),  # Acknowledged 5 min ago
        },
        {
            "job_id": "job-acknowledged-recent-003",
            "agent_name": "Recently Acknowledged Agent",
            "agent_display_name": "tester",
            "mission_acknowledged_at": now - timedelta(seconds=30),  # Acknowledged 30 sec ago
        },
    ]

    for job_data in jobs_data:
        job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project.id,
            job_id=job_data["job_id"],
            agent_name=job_data["agent_name"],
            agent_display_name=job_data["agent_display_name"],
            mission=f"Mission for {job_data['agent_name']}",
            status="working",
            tool_type="claude-code",
            mission_acknowledged_at=job_data["mission_acknowledged_at"],
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(job)

    await db_session.commit()

    return {
        "project_id": project.id,
        "tenant_key": tenant_key,
        "jobs": jobs_data,
    }


@pytest.fixture
async def test_multi_tenant_acknowledged(db_session: AsyncSession, tenant_manager: TenantManager):
    """Create jobs in multiple tenants for isolation testing."""
    # Tenant A
    tenant_a_key = tenant_manager.generate_tenant_key("tenant-a-0297a")
    project_a = Project(
        id=f"proj-a-0297a-{uuid4().hex[:8]}",
        name="Tenant A Project",
        description="Tenant A test project",
        mission="Tenant A mission",
        tenant_key=tenant_a_key,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project_a)
    await db_session.flush()

    job_a = AgentExecution(
        tenant_key=tenant_a_key,
        project_id=project_a.id,
        job_id=f"job-a-{uuid4().hex[:8]}",
        agent_name="Tenant A Agent",
        agent_display_name="implementer",
        mission="Tenant A mission",
        status="working",
        tool_type="claude-code",
        mission_acknowledged_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job_a)

    # Tenant B
    tenant_b_key = tenant_manager.generate_tenant_key("tenant-b-0297a")
    project_b = Project(
        id=f"proj-b-0297a-{uuid4().hex[:8]}",
        name="Tenant B Project",
        description="Tenant B test project",
        mission="Tenant B mission",
        tenant_key=tenant_b_key,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project_b)
    await db_session.flush()

    job_b = AgentExecution(
        tenant_key=tenant_b_key,
        project_id=project_b.id,
        job_id=f"job-b-{uuid4().hex[:8]}",
        agent_name="Tenant B Agent",
        agent_display_name="implementer",
        mission="Tenant B mission",
        status="working",
        tool_type="claude-code",
        mission_acknowledged_at=None,  # Different acknowledged state
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job_b)

    await db_session.commit()

    return {
        "tenant_a": {
            "tenant_key": tenant_a_key,
            "project_id": project_a.id,
            "job_id": job_a.job_id,
        },
        "tenant_b": {
            "tenant_key": tenant_b_key,
            "project_id": project_b.id,
            "job_id": job_b.job_id,
        },
    }


# ============================================================================
# TEST CASES - API Endpoint Response Structure
# ============================================================================

class TestJobsEndpointMissionAcknowledged:
    """Test jobs endpoint includes mission_acknowledged_at field."""

    async def test_jobs_endpoint_includes_mission_acknowledged_at_field(
        self, db_session: AsyncSession, test_project_with_jobs_acknowledged
    ):
        """Jobs endpoint response MUST include mission_acknowledged_at field for all jobs."""
        from api.endpoints.agent_jobs.table_view import get_agent_jobs_table_view
        from src.giljo_mcp.models import User

        # Create a mock user for authentication with unique email
        unique_id = uuid4().hex[:8]
        user = User(
            id=f"user-test-0297a-{unique_id}",
            username=f"test_user_0297a_{unique_id}",
            email=f"test_{unique_id}@example.com",
            tenant_key=test_project_with_jobs_acknowledged["tenant_key"],
        )
        db_session.add(user)
        await db_session.commit()

        # Call the endpoint
        response = await get_agent_jobs_table_view(
            project_id=test_project_with_jobs_acknowledged["project_id"],
            status=None,
            health_status=None,
            has_unread=None,
            agent_display_name=None,
            sort_by="created_at",
            sort_order="asc",
            limit=50,
            offset=0,
            db=db_session,
            current_user=user,
        )

        assert response.total == 3, "Should have 3 jobs"

        # CRITICAL: Every job MUST have mission_acknowledged_at field
        for row in response.rows:
            assert hasattr(row, "mission_acknowledged_at"), (
                f"Job {row.job_id} missing mission_acknowledged_at field"
            )

    async def test_jobs_endpoint_returns_null_when_not_acknowledged(
        self, db_session: AsyncSession, test_project_with_jobs_acknowledged
    ):
        """Jobs endpoint should return null for mission_acknowledged_at when mission not fetched."""
        from api.endpoints.agent_jobs.table_view import get_agent_jobs_table_view
        from src.giljo_mcp.models import User

        # Create a mock user for authentication with unique email
        unique_id = uuid4().hex[:8]
        user = User(
            id=f"user-test-0297a-null-{unique_id}",
            username=f"test_user_0297a_null_{unique_id}",
            email=f"testnull_{unique_id}@example.com",
            tenant_key=test_project_with_jobs_acknowledged["tenant_key"],
        )
        db_session.add(user)
        await db_session.commit()

        # Call the endpoint
        response = await get_agent_jobs_table_view(
            project_id=test_project_with_jobs_acknowledged["project_id"],
            status=None,
            health_status=None,
            has_unread=None,
            agent_display_name=None,
            sort_by="created_at",
            sort_order="asc",
            limit=50,
            offset=0,
            db=db_session,
            current_user=user,
        )

        # Find the unacknowledged job
        unacknowledged_job = next(
            (row for row in response.rows if row.job_id == "job-unacknowledged-001"),
            None
        )

        assert unacknowledged_job is not None, "Unacknowledged job should exist"
        assert unacknowledged_job.mission_acknowledged_at is None, (
            "Unacknowledged job should have mission_acknowledged_at=None"
        )

    async def test_jobs_endpoint_returns_timestamp_when_acknowledged(
        self, db_session: AsyncSession, test_project_with_jobs_acknowledged
    ):
        """Jobs endpoint should return valid ISO timestamp when mission has been acknowledged."""
        from api.endpoints.agent_jobs.table_view import get_agent_jobs_table_view
        from src.giljo_mcp.models import User

        # Create a mock user for authentication with unique email
        unique_id = uuid4().hex[:8]
        user = User(
            id=f"user-test-0297a-ts-{unique_id}",
            username=f"test_user_0297a_ts_{unique_id}",
            email=f"testts_{unique_id}@example.com",
            tenant_key=test_project_with_jobs_acknowledged["tenant_key"],
        )
        db_session.add(user)
        await db_session.commit()

        # Call the endpoint
        response = await get_agent_jobs_table_view(
            project_id=test_project_with_jobs_acknowledged["project_id"],
            status=None,
            health_status=None,
            has_unread=None,
            agent_display_name=None,
            sort_by="created_at",
            sort_order="asc",
            limit=50,
            offset=0,
            db=db_session,
            current_user=user,
        )

        # Find acknowledged jobs
        acknowledged_jobs = [
            row for row in response.rows
            if row.job_id in ["job-acknowledged-002", "job-acknowledged-recent-003"]
        ]

        assert len(acknowledged_jobs) == 2, "Should have 2 acknowledged jobs"

        for job in acknowledged_jobs:
            assert job.mission_acknowledged_at is not None, (
                f"Job {job.job_id} should have mission_acknowledged_at timestamp"
            )
            assert isinstance(job.mission_acknowledged_at, datetime), (
                f"Job {job.job_id} mission_acknowledged_at should be datetime object"
            )
            # Verify timestamp is in the past (within last hour for test)
            now = datetime.now(timezone.utc)
            assert job.mission_acknowledged_at <= now, (
                f"Job {job.job_id} mission_acknowledged_at should be in the past"
            )
            time_diff = now - job.mission_acknowledged_at
            assert time_diff.total_seconds() < 3600, (
                f"Job {job.job_id} mission_acknowledged_at should be recent (within 1 hour)"
            )

    async def test_jobs_endpoint_distinguishes_acknowledged_vs_unacknowledged(
        self, db_session: AsyncSession, test_project_with_jobs_acknowledged
    ):
        """Jobs endpoint should clearly distinguish acknowledged vs unacknowledged jobs."""
        from api.endpoints.agent_jobs.table_view import get_agent_jobs_table_view
        from src.giljo_mcp.models import User

        # Create a mock user for authentication with unique email
        unique_id = uuid4().hex[:8]
        user = User(
            id=f"user-test-0297a-dist-{unique_id}",
            username=f"test_user_0297a_dist_{unique_id}",
            email=f"testdist_{unique_id}@example.com",
            tenant_key=test_project_with_jobs_acknowledged["tenant_key"],
        )
        db_session.add(user)
        await db_session.commit()

        # Call the endpoint
        response = await get_agent_jobs_table_view(
            project_id=test_project_with_jobs_acknowledged["project_id"],
            status=None,
            health_status=None,
            has_unread=None,
            agent_display_name=None,
            sort_by="created_at",
            sort_order="asc",
            limit=50,
            offset=0,
            db=db_session,
            current_user=user,
        )

        # Categorize jobs by acknowledged status
        acknowledged = []
        unacknowledged = []

        for row in response.rows:
            if row.mission_acknowledged_at is not None:
                acknowledged.append(row.job_id)
            else:
                unacknowledged.append(row.job_id)

        assert len(acknowledged) == 2, "Should have 2 acknowledged jobs"
        assert len(unacknowledged) == 1, "Should have 1 unacknowledged job"

        assert "job-acknowledged-002" in acknowledged
        assert "job-acknowledged-recent-003" in acknowledged
        assert "job-unacknowledged-001" in unacknowledged


# ============================================================================
# TEST CASES - Multi-Tenant Isolation
# ============================================================================

class TestMissionAcknowledgedMultiTenantIsolation:
    """Test multi-tenant isolation for mission acknowledged tracking."""

    async def test_jobs_endpoint_multi_tenant_isolation(
        self, db_session: AsyncSession, test_multi_tenant_acknowledged
    ):
        """Verify each tenant only sees their own jobs' acknowledged status."""
        from api.endpoints.agent_jobs.table_view import get_agent_jobs_table_view
        from src.giljo_mcp.models import User

        tenant_a = test_multi_tenant_acknowledged["tenant_a"]
        tenant_b = test_multi_tenant_acknowledged["tenant_b"]

        # Create user for Tenant A
        unique_id_a = uuid4().hex[:8]
        user_a = User(
            id=f"user-tenant-a-{unique_id_a}",
            username=f"tenant_a_user_{unique_id_a}",
            email=f"tenanta_{unique_id_a}@example.com",
            tenant_key=tenant_a["tenant_key"],
        )
        db_session.add(user_a)

        # Create user for Tenant B
        unique_id_b = uuid4().hex[:8]
        user_b = User(
            id=f"user-tenant-b-{unique_id_b}",
            username=f"tenant_b_user_{unique_id_b}",
            email=f"tenantb_{unique_id_b}@example.com",
            tenant_key=tenant_b["tenant_key"],
        )
        db_session.add(user_b)
        await db_session.commit()

        # Tenant A queries their jobs
        response_a = await get_agent_jobs_table_view(
            project_id=tenant_a["project_id"],
            status=None,
            health_status=None,
            has_unread=None,
            agent_display_name=None,
            sort_by="created_at",
            sort_order="asc",
            limit=50,
            offset=0,
            db=db_session,
            current_user=user_a,
        )

        # Tenant B queries their jobs
        response_b = await get_agent_jobs_table_view(
            project_id=tenant_b["project_id"],
            status=None,
            health_status=None,
            has_unread=None,
            agent_display_name=None,
            sort_by="created_at",
            sort_order="asc",
            limit=50,
            offset=0,
            db=db_session,
            current_user=user_b,
        )

        # Verify Tenant A sees only their job (acknowledged)
        assert response_a.total == 1, "Tenant A should see 1 job"
        assert response_a.rows[0].job_id == tenant_a["job_id"]
        assert response_a.rows[0].mission_acknowledged_at is not None, (
            "Tenant A job should be acknowledged"
        )

        # Verify Tenant B sees only their job (unacknowledged)
        assert response_b.total == 1, "Tenant B should see 1 job"
        assert response_b.rows[0].job_id == tenant_b["job_id"]
        assert response_b.rows[0].mission_acknowledged_at is None, (
            "Tenant B job should be unacknowledged"
        )

        # CRITICAL: Verify no cross-tenant data leakage
        tenant_a_job_ids = {row.job_id for row in response_a.rows}
        tenant_b_job_ids = {row.job_id for row in response_b.rows}

        assert len(tenant_a_job_ids.intersection(tenant_b_job_ids)) == 0, (
            "Cross-tenant job leakage detected in acknowledged status tracking"
        )


# ============================================================================
# TEST CASES - Database Direct Manipulation (MCP Tool Behavior)
# ============================================================================

class TestMissionAcknowledgedDatabaseBehavior:
    """
    Test database-level behavior of mission_acknowledged_at field.

    NOTE: MCP tool tests (get_agent_mission) are in tests/tools/ directory.
    These tests verify database-level behavior that the MCP tool depends on.
    """

    async def test_database_allows_setting_mission_acknowledged_at(
        self, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Database should allow setting mission_acknowledged_at field directly."""
        # Create project and job
        tenant_key = tenant_manager.generate_tenant_key("test-db-0297a")
        project = Project(
            id=f"proj-db-0297a-{uuid4().hex[:8]}",
            name="DB Test Project",
            description="Database behavior test",
            mission="Test database field setting",
            tenant_key=tenant_key,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.flush()

        job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project.id,
            job_id=f"job-db-{uuid4().hex[:8]}",
            agent_name="DB Test Agent",
            agent_display_name="implementer",
            mission="Test database field",
            status="waiting",
            tool_type="claude-code",
            mission_acknowledged_at=None,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        await db_session.commit()

        # Verify initial state
        assert job.mission_acknowledged_at is None

        # Update mission_acknowledged_at directly (simulates MCP tool behavior)
        acknowledged_time = datetime.now(timezone.utc)
        job.mission_acknowledged_at = acknowledged_time
        await db_session.commit()

        # Verify update persisted
        result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job.job_id)
        )
        job_from_db = result.scalar_one()

        assert job_from_db.mission_acknowledged_at is not None
        assert job_from_db.mission_acknowledged_at == acknowledged_time

    async def test_database_preserves_existing_mission_acknowledged_at(
        self, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Database should preserve mission_acknowledged_at when updating other fields."""
        tenant_key = tenant_manager.generate_tenant_key("test-preserve-0297a")
        project = Project(
            id=f"proj-preserve-0297a-{uuid4().hex[:8]}",
            name="Preserve Test Project",
            description="Test field preservation",
            mission="Test database preserves acknowledged timestamp",
            tenant_key=tenant_key,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.flush()

        # Create job with acknowledged timestamp
        original_acknowledged = datetime.now(timezone.utc) - timedelta(hours=1)
        job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project.id,
            job_id=f"job-preserve-{uuid4().hex[:8]}",
            agent_name="Preserve Test Agent",
            agent_display_name="implementer",
            mission="Test preservation",
            status="waiting",
            tool_type="claude-code",
            mission_acknowledged_at=original_acknowledged,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        await db_session.commit()

        # Update other fields (NOT mission_acknowledged_at)
        job.status = "working"
        job.progress = 50
        await db_session.commit()

        # Verify mission_acknowledged_at was NOT changed
        result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job.job_id)
        )
        job_from_db = result.scalar_one()

        assert job_from_db.mission_acknowledged_at == original_acknowledged
        assert job_from_db.status == "working"
        assert job_from_db.progress == 50


# ============================================================================
# TEST CASES - Database Integrity
# ============================================================================

class TestMissionAcknowledgedDatabaseIntegrity:
    """Test database field constraints and integrity."""

    async def test_mission_acknowledged_at_nullable(
        self, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """mission_acknowledged_at field should be nullable in database."""
        # Create job without mission_acknowledged_at
        tenant_key = tenant_manager.generate_tenant_key("test-nullable-0297a")
        project = Project(
            id=f"proj-nullable-0297a-{uuid4().hex[:8]}",
            name="Nullable Test Project",
            description="Test nullable field",
            mission="Test nullable mission_acknowledged_at",
            tenant_key=tenant_key,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.flush()

        job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project.id,
            job_id=f"job-nullable-{uuid4().hex[:8]}",
            agent_name="Nullable Test Agent",
            agent_display_name="implementer",
            mission="Test nullable field",
            status="waiting",
            tool_type="claude-code",
            # Explicitly omit mission_acknowledged_at
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(job)

        # Should commit successfully without mission_acknowledged_at
        await db_session.commit()

        # Verify field is None in database
        result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job.job_id)
        )
        job_from_db = result.scalar_one()

        assert job_from_db.mission_acknowledged_at is None, (
            "mission_acknowledged_at should be nullable"
        )

    async def test_mission_acknowledged_at_timezone_aware(
        self, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """mission_acknowledged_at should be timezone-aware (UTC)."""
        tenant_key = tenant_manager.generate_tenant_key("test-tz-0297a")
        project = Project(
            id=f"proj-tz-0297a-{uuid4().hex[:8]}",
            name="Timezone Test Project",
            description="Test timezone awareness",
            mission="Test timezone-aware timestamps",
            tenant_key=tenant_key,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.flush()

        acknowledged_at = datetime.now(timezone.utc)

        job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project.id,
            job_id=f"job-tz-{uuid4().hex[:8]}",
            agent_name="Timezone Test Agent",
            agent_display_name="implementer",
            mission="Test timezone awareness",
            status="working",
            tool_type="claude-code",
            mission_acknowledged_at=acknowledged_at,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        await db_session.commit()

        # Verify timestamp is timezone-aware
        result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job.job_id)
        )
        job_from_db = result.scalar_one()

        assert job_from_db.mission_acknowledged_at.tzinfo is not None, (
            "mission_acknowledged_at should be timezone-aware"
        )
        assert job_from_db.mission_acknowledged_at.tzinfo == timezone.utc, (
            "mission_acknowledged_at should be in UTC timezone"
        )
