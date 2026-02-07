"""
Test fixtures for service instantiation patterns.

TDD Phase: RED
Tests written BEFORE fixture implementation to verify correct service instantiation.
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def test_user_with_tenant(db_session):
    """Create test user with tenant for service testing"""
    user = User(
        username=f"service_test_{uuid4().hex[:8]}",
        email=f"service_test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestServiceFixtures:
    """Test that service fixtures correctly instantiate services with proper dependencies."""

    async def test_db_manager_fixture_creates_valid_instance(self, db_manager):
        """Test db_manager fixture creates DatabaseManager instance."""
        assert isinstance(db_manager, DatabaseManager), "db_manager fixture must create DatabaseManager instance"
        assert db_manager.is_async is True, "db_manager must be async for integration tests"

    async def test_tenant_manager_fixture_creates_valid_instance(self, tenant_manager):
        """Test tenant_manager fixture creates TenantManager instance."""
        assert isinstance(tenant_manager, TenantManager), "tenant_manager fixture must create TenantManager instance"

    async def test_orchestration_service_instantiation(self, db_manager, tenant_manager):
        """Test OrchestrationService can be instantiated with correct parameters."""
        # Instantiate service with correct signature
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)

        assert isinstance(service, OrchestrationService), "Service must be OrchestrationService instance"
        assert service.db_manager is db_manager, "Service must store db_manager reference"
        assert service.tenant_manager is tenant_manager, "Service must store tenant_manager reference"

    async def test_project_service_instantiation(self, db_manager, tenant_manager):
        """Test ProjectService can be instantiated with correct parameters."""
        # Instantiate service with correct signature
        service = ProjectService(db_manager=db_manager, tenant_manager=tenant_manager)

        assert isinstance(service, ProjectService), "Service must be ProjectService instance"
        assert service.db_manager is db_manager, "Service must store db_manager reference"
        assert service.tenant_manager is tenant_manager, "Service must store tenant_manager reference"

    async def test_orchestration_service_rejects_wrong_signature(self, db_session, test_user_with_tenant):
        """Test OrchestrationService raises error with old (session, tenant_key) signature."""
        with pytest.raises(TypeError) as exc_info:
            # Old signature (WRONG) - should fail
            OrchestrationService(session=db_session, tenant_key=test_user_with_tenant.tenant_key)

        assert "unexpected keyword argument" in str(exc_info.value).lower(), (
            "Service must reject old signature parameters"
        )

    async def test_project_service_rejects_wrong_signature(self, db_session, test_user_with_tenant):
        """Test ProjectService raises error with old (session, tenant_key) signature."""
        with pytest.raises(TypeError) as exc_info:
            # Old signature (WRONG) - should fail
            ProjectService(session=db_session, tenant_key=test_user_with_tenant.tenant_key)

        assert "unexpected keyword argument" in str(exc_info.value).lower(), (
            "Service must reject old signature parameters"
        )

    async def test_service_fixtures_provide_session_access(self, db_manager, tenant_manager):
        """Test services can obtain AsyncSession from db_manager."""
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)

        # Verify service can get session via context manager
        async with db_manager.get_session_async() as session:
            assert session is not None, "db_manager.get_session_async() must return valid AsyncSession"
