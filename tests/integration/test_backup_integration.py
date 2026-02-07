"""
Integration tests for database backup functionality
Handover: Database Backup Integration Testing

Tests cover:
- MCP Tool Integration (backup_database tool)
- API Endpoint Integration (POST /api/backup/database)
- Multi-tenant isolation (backups filtered by tenant)
- Authentication and authorization
- Error handling (database errors, filesystem errors)
- Performance characteristics (backup completion time)
- Backup metadata validation
- Concurrent backup handling

Following TDD methodology - these tests define expected behavior.
"""

import pytest


pytest.skip("TODO(0127a-2): Comprehensive refactoring needed for MCPAgentJob model", allow_module_level=True)
import asyncio
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# TODO(0127a): from src.giljo_mcp.models import Agent, Project, User
# from src.giljo_mcp.models import MCPAgentJob  # Use this instead


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user with unique tenant for backup testing"""
    user = User(
        id=str(uuid4()),
        username=f"backup_testuser_{uuid4().hex[:8]}",
        email=f"backup_test_{uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$test_hash_for_backup_testing",
        tenant_key=f"tenant_backup_{uuid4().hex[:8]}",
        is_active=True,
        role="developer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for backup testing"""
    user = User(
        id=str(uuid4()),
        username=f"admin_backup_{uuid4().hex[:8]}",
        email=f"admin_backup_{uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$test_hash_for_admin_backup",
        tenant_key=f"tenant_admin_{uuid4().hex[:8]}",
        is_active=True,
        role="admin",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    """Create test project for backup testing"""
    project = Project(
        id=str(uuid4()),
        name=f"Backup Test Project {uuid4().hex[:8]}",
        description="Test project description for backup testing",
        mission="Test project for database backup testing",
        status="active",
        tenant_key=test_user.tenant_key,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_agents(db_session: AsyncSession, test_project: Project) -> list[Agent]:
    """Create test agents for backup testing"""
    agents = []
    for i in range(3):
        agent = Agent(
            id=str(uuid4()),
            name=f"backup_test_agent_{i}",
            role="worker",
            status="active",
            project_id=test_project.id,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)

    return agents


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate JWT authentication headers for test user"""
    # Mock JWT token for testing
    return {"Authorization": f"Bearer test_token_{test_user.id}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict:
    """Generate JWT authentication headers for admin user"""
    return {"Authorization": f"Bearer test_token_{admin_user.id}"}


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing"""
    from api.app import app

    # Override database dependency to use test database
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


def get_db_session():
    """Placeholder for dependency injection - will be overridden"""


# ============================================================================
# MCP Tool Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestBackupDatabaseMCPTool:
    """Tests for backup_database MCP tool"""

    async def test_backup_database_tool_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
        test_agents: list[Agent],
    ):
        """Test backup_database MCP tool creates backup successfully"""
        from src.giljo_mcp.tools.backup import backup_database

        # Execute backup tool
        result = await backup_database(
            tenant_key=test_user.tenant_key,
        )

        # Verify success response
        assert result["success"] is True
        assert "backup_path" in result
        assert "metadata" in result
        assert "message" in result

        # Verify backup path follows expected format
        backup_path = Path(result["backup_path"])
        assert backup_path.parent == Path("docs/archive/database_backups")

        # Verify backup path contains timestamp
        assert datetime.now().strftime("%Y-%m-%d") in str(backup_path)

        # Verify metadata contains expected fields
        metadata = result["metadata"]
        assert "timestamp" in metadata
        assert "tenant_key" in metadata
        assert metadata["tenant_key"] == test_user.tenant_key
        assert "tables_backed_up" in metadata
        assert "record_counts" in metadata

        # Verify record counts reflect test data
        record_counts = metadata["record_counts"]
        assert "projects" in record_counts
        assert record_counts["projects"] >= 1  # At least our test project
        assert "agents" in record_counts
        assert record_counts["agents"] >= 3  # Our 3 test agents

    async def test_backup_database_tool_multi_tenant_isolation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
    ):
        """Test backup only includes data for specified tenant"""
        # Create another tenant's data
        other_tenant = f"tenant_other_{uuid4().hex[:8]}"
        other_project = Project(
            id=str(uuid4()),
            name="Other Tenant Project",
            description="Other tenant project description",
            mission="Should not be in backup",
            status="active",
            tenant_key=other_tenant,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_project)
        await db_session.commit()

        # Execute backup for test_user's tenant
        from src.giljo_mcp.tools.backup import backup_database

        result = await backup_database(tenant_key=test_user.tenant_key)

        # Verify success
        assert result["success"] is True

        # Verify metadata shows correct tenant isolation
        metadata = result["metadata"]
        assert metadata["tenant_key"] == test_user.tenant_key

        # TODO: When implementation exists, verify backup file content
        # only contains test_user's tenant data, not other_tenant data

    async def test_backup_database_tool_handles_empty_database(
        self,
        db_session: AsyncSession,
    ):
        """Test backup handles tenant with no data gracefully"""
        empty_tenant = f"tenant_empty_{uuid4().hex[:8]}"

        from src.giljo_mcp.tools.backup import backup_database

        result = await backup_database(tenant_key=empty_tenant)

        # Should succeed even with no data
        assert result["success"] is True
        assert "backup_path" in result

        # Metadata should show zero records
        metadata = result["metadata"]
        record_counts = metadata.get("record_counts", {})
        # All counts should be 0 for empty tenant
        for count in record_counts.values():
            assert count == 0

    async def test_backup_database_tool_handles_database_error(
        self,
        test_user: User,
    ):
        """Test backup handles database connection errors gracefully"""
        from src.giljo_mcp.tools.backup import backup_database

        # Mock database manager to raise error
        with patch("src.giljo_mcp.tools.backup.get_database_manager") as mock_db:
            mock_db.side_effect = ConnectionError("Database connection failed")

            result = await backup_database(tenant_key=test_user.tenant_key)

            # Should return failure with error message
            assert result["success"] is False
            assert "error" in result
            assert "Database connection failed" in result["error"]

    async def test_backup_database_tool_handles_filesystem_error(
        self,
        test_user: User,
    ):
        """Test backup handles filesystem errors gracefully"""
        from src.giljo_mcp.tools.backup import backup_database

        # Mock filesystem operations to raise error
        with patch("src.giljo_mcp.database_backup.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Cannot create backup directory")

            result = await backup_database(tenant_key=test_user.tenant_key)

            # Should return failure with error message
            assert result["success"] is False
            assert "error" in result
            assert "Permission" in result["error"] or "filesystem" in result["error"].lower()

    async def test_backup_database_tool_performance(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
        test_agents: list[Agent],
    ):
        """Test backup completes within reasonable time"""
        from src.giljo_mcp.tools.backup import backup_database

        start_time = time.time()
        result = await backup_database(tenant_key=test_user.tenant_key)
        duration = time.time() - start_time

        # Backup should succeed
        assert result["success"] is True

        # Should complete within 5 seconds for small test dataset
        assert duration < 5.0, f"Backup took {duration:.2f}s, expected < 5s"

        # Metadata should include timing information
        if "duration_seconds" in result["metadata"]:
            assert result["metadata"]["duration_seconds"] < 5.0


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestBackupDatabaseAPIEndpoint:
    """Tests for POST /api/backup/database endpoint"""

    async def test_backup_endpoint_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_project: Project,
        test_agents: list[Agent],
    ):
        """Test successful database backup via API endpoint"""
        response = await async_client.post(
            "/api/backup/database",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "backup_path" in data
        assert "metadata" in data
        assert "message" in data
        assert "Database backup completed successfully" in data["message"]

        # Verify backup path format
        backup_path = data["backup_path"]
        assert "docs/archive/database_backups/" in backup_path
        assert datetime.now().strftime("%Y-%m-%d") in backup_path

        # Verify metadata
        metadata = data["metadata"]
        assert metadata["tenant_key"] == test_user.tenant_key
        assert "timestamp" in metadata
        assert "tables_backed_up" in metadata
        assert "record_counts" in metadata

    async def test_backup_endpoint_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
        """Test backup endpoint requires authentication"""
        response = await async_client.post(
            "/api/backup/database",
            # No auth headers
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_backup_endpoint_uses_authenticated_user_tenant(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test backup uses tenant from authenticated user"""
        response = await async_client.post(
            "/api/backup/database",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should use test_user's tenant_key
        assert data["metadata"]["tenant_key"] == test_user.tenant_key

    async def test_backup_endpoint_multi_tenant_isolation(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test backup only includes authenticated user's tenant data"""
        # Create project for different tenant
        other_tenant = f"tenant_other_{uuid4().hex[:8]}"
        other_project = Project(
            id=str(uuid4()),
            name="Other Tenant Project",
            description="Other tenant project description",
            mission="Should not appear in backup",
            status="active",
            tenant_key=other_tenant,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_project)
        await db_session.commit()

        # Request backup as test_user
        response = await async_client.post(
            "/api/backup/database",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify tenant isolation in metadata
        assert data["metadata"]["tenant_key"] == test_user.tenant_key
        assert data["metadata"]["tenant_key"] != other_tenant

    async def test_backup_endpoint_handles_database_error(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test backup endpoint handles database errors gracefully"""
        # Mock database backup to raise error
        with patch("api.endpoints.backup.backup_database_utility") as mock_backup:
            mock_backup.side_effect = ConnectionError("Database unavailable")

            response = await async_client.post(
                "/api/backup/database",
                headers=auth_headers,
            )

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Database" in data["detail"] or "error" in data["detail"].lower()

    async def test_backup_endpoint_handles_filesystem_error(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test backup endpoint handles filesystem errors gracefully"""
        with patch("src.giljo_mcp.database_backup.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Cannot write to backup directory")

            response = await async_client.post(
                "/api/backup/database",
                headers=auth_headers,
            )

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Permission" in data["detail"] or "filesystem" in data["detail"].lower()

    async def test_backup_endpoint_returns_proper_json_structure(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test backup endpoint returns properly structured JSON"""
        response = await async_client.post(
            "/api/backup/database",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        required_fields = ["success", "backup_path", "metadata", "message"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify metadata structure
        metadata = data["metadata"]
        required_metadata_fields = [
            "timestamp",
            "tenant_key",
            "tables_backed_up",
            "record_counts",
        ]
        for field in required_metadata_fields:
            assert field in metadata, f"Missing required metadata field: {field}"

        # Verify record_counts structure
        record_counts = metadata["record_counts"]
        assert isinstance(record_counts, dict)
        expected_tables = ["users", "projects", "agents", "messages"]
        for table in expected_tables:
            assert table in record_counts
            assert isinstance(record_counts[table], int)

    async def test_backup_endpoint_performance(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_project: Project,
        test_agents: list[Agent],
    ):
        """Test backup endpoint responds within reasonable time"""
        start_time = time.time()

        response = await async_client.post(
            "/api/backup/database",
            headers=auth_headers,
        )

        duration = time.time() - start_time

        assert response.status_code == 200

        # API response should be within 10 seconds for small dataset
        assert duration < 10.0, f"Backup API took {duration:.2f}s, expected < 10s"

    async def test_backup_endpoint_concurrent_requests(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test backup endpoint handles concurrent requests gracefully"""
        # Create 3 concurrent backup requests
        tasks = [async_client.post("/api/backup/database", headers=auth_headers) for _ in range(3)]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All requests should complete
        assert len(responses) == 3

        # At least some should succeed (may have rate limiting)
        successful = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]
        assert len(successful) >= 1, "At least one concurrent backup should succeed"

        # Verify successful responses have unique backup paths
        backup_paths = [r.json()["backup_path"] for r in successful]
        assert len(backup_paths) == len(set(backup_paths)), "Backup paths should be unique"

    async def test_backup_endpoint_inactive_user_denied(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test backup endpoint denies inactive users"""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()

        response = await async_client.post(
            "/api/backup/database",
            headers=auth_headers,
        )

        # Should be denied (401 or 403)
        assert response.status_code in [401, 403]


# ============================================================================
# Edge Cases and Error Conditions
# ============================================================================


@pytest.mark.asyncio
class TestBackupEdgeCases:
    """Tests for edge cases and unusual conditions"""

    async def test_backup_with_special_characters_in_tenant(
        self,
        db_session: AsyncSession,
    ):
        """Test backup handles tenant keys with special characters"""
        special_tenant = "tenant_特殊文字_émojis_😀"

        from src.giljo_mcp.tools.backup import backup_database

        result = await backup_database(tenant_key=special_tenant)

        # Should handle gracefully (success or proper error)
        assert "success" in result
        if result["success"]:
            assert "backup_path" in result
            # Backup path should be filesystem-safe
            backup_path = Path(result["backup_path"])
            assert backup_path.name.replace("-", "").replace("_", "").isascii()

    async def test_backup_with_very_long_tenant_key(
        self,
        db_session: AsyncSession,
    ):
        """Test backup handles very long tenant keys"""
        long_tenant = "tenant_" + "x" * 500

        from src.giljo_mcp.tools.backup import backup_database

        result = await backup_database(tenant_key=long_tenant)

        # Should handle gracefully
        assert "success" in result

    async def test_backup_creates_directory_structure(
        self,
        test_user: User,
    ):
        """Test backup creates necessary directory structure"""
        from src.giljo_mcp.tools.backup import backup_database

        # Clear any existing backup directory
        backup_base = Path("docs/archive/database_backups")

        result = await backup_database(tenant_key=test_user.tenant_key)

        if result["success"]:
            backup_path = Path(result["backup_path"])
            assert backup_path.parent.exists()
            assert backup_path.parent == backup_base


# ============================================================================
# Performance and Reliability Tests
# ============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestBackupPerformance:
    """Performance tests for backup functionality"""

    async def test_backup_with_large_dataset(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test backup performance with larger dataset"""
        # Create 50 projects and 150 agents
        projects = []
        agents = []

        for i in range(50):
            project = Project(
                id=str(uuid4()),
                name=f"Performance Test Project {i}",
                description=f"Test description {i}",
                mission=f"Test mission {i}",
                status="active",
                tenant_key=test_user.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            projects.append(project)
            db_session.add(project)

        await db_session.commit()

        for project in projects[:30]:  # Add agents to first 30 projects
            for j in range(5):
                agent = Agent(
                    id=str(uuid4()),
                    name=f"perf_agent_{project.name}_{j}",
                    role="worker",
                    status="active",
                    project_id=project.id,
                    created_at=datetime.now(timezone.utc),
                )
                agents.append(agent)
                db_session.add(agent)

        await db_session.commit()

        # Measure backup time
        from src.giljo_mcp.tools.backup import backup_database

        start_time = time.time()
        result = await backup_database(tenant_key=test_user.tenant_key)
        duration = time.time() - start_time

        assert result["success"] is True

        # Should complete within 30 seconds even with larger dataset
        assert duration < 30.0, f"Large backup took {duration:.2f}s, expected < 30s"

        # Verify record counts
        record_counts = result["metadata"]["record_counts"]
        assert record_counts.get("projects", 0) >= 50
        assert record_counts.get("agents", 0) >= 150

    async def test_backup_does_not_lock_database(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
    ):
        """Test backup does not block other database operations"""
        from src.giljo_mcp.tools.backup import backup_database

        # Start backup in background
        backup_task = asyncio.create_task(backup_database(tenant_key=test_user.tenant_key))

        # Attempt concurrent database operation
        await asyncio.sleep(0.1)  # Let backup start

        new_project = Project(
            id=str(uuid4()),
            name="Concurrent Test Project",
            description="Concurrent test project description",
            mission="Should not be blocked",
            status="active",
            tenant_key=test_user.tenant_key,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(new_project)
        await db_session.commit()  # Should not hang

        # Wait for backup to complete
        result = await backup_task
        assert result["success"] is True
