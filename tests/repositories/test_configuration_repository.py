"""
Tests for ConfigurationRepository (Handover 1011 Phase 3).

Test-driven development: Comprehensive coverage of all configuration repository methods
with CRITICAL tenant isolation testing.
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Configuration
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.repositories.configuration_repository import ConfigurationRepository



@pytest.fixture
def config_repo(db_manager):
    """Create ConfigurationRepository instance"""
    return ConfigurationRepository(db_manager)


@pytest_asyncio.fixture
async def test_configurations(db_session, test_tenant_key):
    """Create test configurations for a tenant"""
    configurations = []
    for i in range(3):
        config = Configuration(
            tenant_key=test_tenant_key,
            key=f"test.key.{i}",
            value=f"test_value_{i}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(config)
        configurations.append(config)
    await db_session.commit()
    return configurations


@pytest_asyncio.fixture
async def other_tenant_configurations(db_session):
    """Create configurations for a different tenant"""
    other_tenant_key = "other_tenant"
    configurations = []
    for i in range(2):
        config = Configuration(
            tenant_key=other_tenant_key,
            key=f"other.key.{i}",
            value=f"other_value_{i}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(config)
        configurations.append(config)
    await db_session.commit()
    return configurations


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create an admin user for first-run detection tests"""
    user = User(
        id="admin_001",
        tenant_key="default",
        username="admin",
        email="admin@test.com",
        password_hash="hashed_password",
        role="admin",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    return user


# ============================================================================
# TENANT CONFIGURATION DOMAIN TESTS
# ============================================================================


class TestTenantConfigurationDomain:
    """Test tenant configuration retrieval and management"""

    @pytest.mark.asyncio
    async def test_list_tenant_keys(
        self, config_repo, db_session, test_tenant_key, test_configurations, other_tenant_configurations
    ):
        """Test listing all tenant keys with configurations"""
        tenant_keys = await config_repo.list_tenant_keys(db_session)

        assert len(tenant_keys) >= 2  # At least our two test tenants
        assert test_tenant_key in tenant_keys  # Use the fixture-provided tenant key
        assert "other_tenant" in tenant_keys

    @pytest.mark.asyncio
    async def test_list_tenant_keys_empty(self, config_repo, db_session):
        """Test listing tenant keys when no configurations exist"""
        tenant_keys = await config_repo.list_tenant_keys(db_session)

        # Should return empty list if no configurations
        assert isinstance(tenant_keys, list)

    @pytest.mark.asyncio
    async def test_get_tenant_configurations(self, config_repo, db_session, test_tenant_key, test_configurations):
        """Test retrieving all configurations for a tenant"""
        configs = await config_repo.get_tenant_configurations(db_session, test_tenant_key)

        assert len(configs) == 3
        assert all(c.tenant_key == test_tenant_key for c in configs)
        assert all(isinstance(c, Configuration) for c in configs)

    @pytest.mark.asyncio
    async def test_get_tenant_configurations_isolation(
        self, config_repo, db_session, test_tenant_key, test_configurations, other_tenant_configurations
    ):
        """CRITICAL: Test tenant isolation - should not see other tenant's configs"""
        configs = await config_repo.get_tenant_configurations(db_session, test_tenant_key)

        # Should only see our tenant's configs, not other tenant's
        assert len(configs) == 3
        assert all(c.tenant_key == test_tenant_key for c in configs)
        assert not any(c.tenant_key == "other_tenant" for c in configs)

    @pytest.mark.asyncio
    async def test_get_tenant_configurations_empty(self, config_repo, db_session):
        """Test retrieving configurations for tenant with no configs"""
        configs = await config_repo.get_tenant_configurations(db_session, "nonexistent_tenant")

        assert configs == []

    @pytest.mark.asyncio
    async def test_get_configuration_by_key(self, config_repo, db_session, test_tenant_key, test_configurations):
        """Test retrieving specific configuration by key"""
        config = await config_repo.get_configuration_by_key(db_session, test_tenant_key, "test.key.0")

        assert config is not None
        assert config.tenant_key == test_tenant_key
        assert config.key == "test.key.0"
        assert config.value == "test_value_0"

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_isolation(
        self, config_repo, db_session, test_tenant_key, test_configurations, other_tenant_configurations
    ):
        """CRITICAL: Test tenant isolation - cannot access other tenant's config by key"""
        # Try to access other tenant's key using our tenant_key
        config = await config_repo.get_configuration_by_key(db_session, test_tenant_key, "other.key.0")

        assert config is None  # Should not find it (different tenant)

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_not_found(self, config_repo, db_session, test_tenant_key):
        """Test retrieving non-existent configuration"""
        config = await config_repo.get_configuration_by_key(db_session, test_tenant_key, "nonexistent.key")

        assert config is None

    @pytest.mark.asyncio
    async def test_delete_tenant_configurations(self, config_repo, db_session, test_tenant_key, test_configurations):
        """Test deleting all configurations for a tenant"""
        # Delete all configurations
        deleted_count = await config_repo.delete_tenant_configurations(db_session, test_tenant_key)
        await db_session.commit()

        # Verify deletion
        assert deleted_count == 3
        configs = await config_repo.get_tenant_configurations(db_session, test_tenant_key)
        assert configs == []

    @pytest.mark.asyncio
    async def test_delete_tenant_configurations_isolation(
        self, config_repo, db_session, test_tenant_key, test_configurations, other_tenant_configurations
    ):
        """CRITICAL: Test tenant isolation - deletion only affects target tenant"""
        # Delete only our tenant's configurations
        deleted_count = await config_repo.delete_tenant_configurations(db_session, test_tenant_key)
        await db_session.commit()

        # Verify our configs deleted
        assert deleted_count == 3
        our_configs = await config_repo.get_tenant_configurations(db_session, test_tenant_key)
        assert our_configs == []

        # Verify other tenant's configs still exist
        other_configs = await config_repo.get_tenant_configurations(db_session, "other_tenant")
        assert len(other_configs) == 2

    @pytest.mark.asyncio
    async def test_delete_tenant_configurations_not_found(self, config_repo, db_session):
        """Test deleting configurations for tenant with none"""
        deleted_count = await config_repo.delete_tenant_configurations(db_session, "nonexistent_tenant")

        assert deleted_count == 0


# ============================================================================
# SETUP / FIRST-RUN DOMAIN TESTS
# ============================================================================


class TestSetupDomain:
    """Test setup and first-run detection"""

    @pytest.mark.asyncio
    async def test_check_admin_user_exists_true(self, config_repo, db_session, admin_user):
        """Test admin user existence check when admin exists"""
        exists = await config_repo.check_admin_user_exists(db_session)

        assert exists is True

    @pytest.mark.asyncio
    async def test_check_admin_user_exists_false(self, config_repo, db_manager):
        """Test admin user existence check when no admin exists"""
        # Create a fresh session with no admin users
        async with db_manager.get_session_async() as fresh_session:
            # First verify no admin exists by not creating one
            from sqlalchemy import delete

            from src.giljo_mcp.models.auth import User

            # Delete any admin users that might exist from other tests
            await fresh_session.execute(delete(User).where(User.role == "admin"))
            await fresh_session.commit()

            # Now check - should be False
            exists = await config_repo.check_admin_user_exists(fresh_session)

            assert exists is False


# ============================================================================
# HEALTH CHECK DOMAIN TESTS
# ============================================================================


class TestHealthCheckDomain:
    """Test database health checks"""

    @pytest.mark.asyncio
    async def test_execute_health_check_success(self, config_repo, db_session):
        """Test successful database health check"""
        is_healthy = await config_repo.execute_health_check(db_session)

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_execute_health_check_failure(self, config_repo, db_manager, monkeypatch):
        """Test health check when database fails — only RuntimeError/OSError are caught."""

        # Create a mock session that raises RuntimeError (caught by health check)
        class FailingSession:
            async def execute(self, stmt):
                raise RuntimeError("Database connection failed")

        is_healthy = await config_repo.execute_health_check(FailingSession())

        assert is_healthy is False
