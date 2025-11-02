"""
Unit tests for agent import slash command handlers (Handover 0084b)
Tests the /gil_import_productagents and /gil_import_personalagents slash commands
"""
import pytest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from dataclasses import dataclass

from src.giljo_mcp.models import Product, User, AgentTemplate
from src.giljo_mcp.slash_commands.import_agents import (
    handle_import_productagents,
    handle_import_personalagents,
)


@dataclass
class TestTenant:
    """Simple test tenant object"""
    tenant_key: str


@pytest.fixture
def test_tenant():
    """Create test tenant"""
    return TestTenant(tenant_key=f"tk_test_{uuid.uuid4().hex[:16]}")


@pytest.fixture
def sync_db_manager():
    """
    Create synchronous database manager for slash command testing.
    Slash command handlers use sync sessions, not async.
    """
    from tests.helpers.test_db_helper import PostgreSQLTestHelper
    import asyncio

    # Ensure test database exists
    asyncio.run(PostgreSQLTestHelper.ensure_test_database_exists())

    connection_string = PostgreSQLTestHelper.get_test_db_url()
    from src.giljo_mcp.database import DatabaseManager

    db_mgr = DatabaseManager(connection_string, is_async=False)  # SYNC mode

    yield db_mgr

    # Cleanup
    db_mgr.close()


@pytest.fixture
def sync_db_session(sync_db_manager):
    """Get synchronous database session for slash command testing"""
    with sync_db_manager.get_session() as session:
        yield session
        session.rollback()  # Rollback to keep tests isolated


@pytest.fixture
def test_user(sync_db_session, test_tenant):
    """Create test user"""
    user = User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        tenant_key=test_tenant.tenant_key,
        hashed_password="hashed_password_here",
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    return user


@pytest.fixture
def active_product(sync_db_session, test_tenant, tmp_path):
    """Create active product with project_path"""
    # Create test project directory
    project_dir = tmp_path / "test_product"
    project_dir.mkdir(parents=True, exist_ok=True)

    product = Product(
        id="test-product-id",
        name="Test Product",
        tenant_key=test_tenant.tenant_key,
        is_active=True,
        project_path=str(project_dir),
    )
    sync_db_session.add(product)
    sync_db_session.commit()
    return product


@pytest.fixture
def inactive_product(sync_db_session, test_tenant):
    """Create inactive product"""
    product = Product(
        id="inactive-product-id",
        name="Inactive Product",
        tenant_key=test_tenant.tenant_key,
        is_active=False,
    )
    sync_db_session.add(product)
    sync_db_session.commit()
    return product


@pytest.fixture
def product_without_path(sync_db_session, test_tenant):
    """Create active product without project_path"""
    product = Product(
        id="no-path-product-id",
        name="No Path Product",
        tenant_key=test_tenant.tenant_key,
        is_active=True,
        project_path=None,
    )
    sync_db_session.add(product)
    sync_db_session.commit()
    return product


@pytest.fixture
def test_templates(sync_db_session, test_tenant):
    """Create test agent templates"""
    templates = [
        AgentTemplate(
            id="template-1",
            name="orchestrator",
            role="orchestrator",
            tenant_key=test_tenant.tenant_key,
            is_active=True,
            template_content="You are the orchestrator agent",
            tool="claude",
        ),
        AgentTemplate(
            id="template-2",
            name="implementer",
            role="implementer",
            tenant_key=test_tenant.tenant_key,
            is_active=True,
            template_content="You are the implementer agent",
            tool="claude",
        ),
        AgentTemplate(
            id="template-3",
            name="inactive_agent",
            role="inactive",
            tenant_key=test_tenant.tenant_key,
            is_active=False,
            template_content="You are inactive",
            tool="claude",
        ),
    ]

    for template in templates:
        sync_db_session.add(template)
    sync_db_session.commit()
    return templates


class TestHandleImportProductAgents:
    """Tests for handle_import_productagents slash command handler"""

    @pytest.mark.asyncio
    async def test_imports_to_product_path(
        self, db_session, test_tenant, test_user, active_product, test_templates
    ):
        """Test /gil_import_productagents imports to product's .claude/agents"""
        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )

        assert result["success"] is True
        assert result["exported_count"] == 2  # 2 active templates
        assert "Test Product" in result["message"]
        assert "files" in result
        assert len(result["files"]) == 2

        # Verify files were exported to correct path
        export_path = Path(active_product.project_path) / ".claude" / "agents"
        assert export_path.exists()
        assert (export_path / "orchestrator.md").exists()
        assert (export_path / "implementer.md").exists()

    @pytest.mark.asyncio
    async def test_creates_claude_agents_directory(
        self, db_session, test_tenant, test_user, active_product, test_templates
    ):
        """Test creates .claude/agents directory if it doesn't exist"""
        export_path = Path(active_product.project_path) / ".claude" / "agents"

        # Ensure directory doesn't exist
        if export_path.exists():
            import shutil
            shutil.rmtree(export_path.parent)

        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )

        assert result["success"] is True
        assert export_path.exists()
        assert export_path.is_dir()

    @pytest.mark.asyncio
    async def test_error_no_active_product(
        self, db_session, test_tenant, test_user, inactive_product
    ):
        """Test error when no active product exists"""
        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )

        assert result["success"] is False
        assert result["error"] == "NO_ACTIVE_PRODUCT"
        assert "No active product found" in result["message"]

    @pytest.mark.asyncio
    async def test_error_product_without_project_path(
        self, db_session, test_tenant, test_user, product_without_path
    ):
        """Test error when product doesn't have project_path configured"""
        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )

        assert result["success"] is False
        assert result["error"] == "NO_PROJECT_PATH"
        assert "does not have a project path configured" in result["message"]
        assert product_without_path.name in result["message"]

    @pytest.mark.asyncio
    async def test_error_invalid_project_path(
        self, db_session, test_tenant, test_user
    ):
        """Test error when product's project_path doesn't exist"""
        # Create product with non-existent path
        product = Product(
            id="invalid-path-product",
            name="Invalid Path Product",
            tenant_key=test_tenant.tenant_key,
            is_active=True,
            project_path="/nonexistent/path/to/project",
        )
        db_session.add(product)
        db_session.commit()

        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_PROJECT_PATH"
        assert "does not exist" in result["message"]

    @pytest.mark.asyncio
    async def test_error_user_not_found(self, db_session):
        """Test error when user not found for tenant"""
        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key="nonexistent-tenant-key",
        )

        assert result["success"] is False
        assert result["error"] == "USER_NOT_FOUND"
        assert "User not found" in result["message"]

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self, db_session, test_tenant, test_user, active_product
    ):
        """Test tenant isolation enforced"""
        # Create product for different tenant
        other_product = Product(
            id="other-product-id",
            name="Other Product",
            tenant_key="other-tenant-key",
            is_active=True,
            project_path="/other/path",
        )
        db_session.add(other_product)
        db_session.commit()

        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,  # Different tenant
        )

        # Should use test_tenant's active product, not other tenant's
        assert result["success"] is True
        assert active_product.name in result["message"]

    @pytest.mark.asyncio
    async def test_backup_creation(
        self, db_session, test_tenant, test_user, active_product, test_templates
    ):
        """Test backup is created when overwriting existing files"""
        # First export
        result1 = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )
        assert result1["success"] is True

        # Second export (should create backup)
        result2 = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )
        assert result2["success"] is True
        assert "Backup created" in result2["message"]


class TestHandleImportPersonalAgents:
    """Tests for handle_import_personalagents slash command handler"""

    @pytest.mark.asyncio
    async def test_imports_to_personal_directory(
        self, db_session, test_tenant, test_user, test_templates, tmp_path
    ):
        """Test /gil_import_personalagents imports to ~/.claude/agents"""
        # Mock Path.home() to use tmp_path
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            result = await handle_import_personalagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )

            assert result["success"] is True
            assert result["exported_count"] == 2  # 2 active templates
            assert "personal agents" in result["message"]
            assert "files" in result
            assert len(result["files"]) == 2

            # Verify files were exported to correct path
            export_path = mock_home / ".claude" / "agents"
            assert export_path.exists()
            assert (export_path / "orchestrator.md").exists()
            assert (export_path / "implementer.md").exists()

    @pytest.mark.asyncio
    async def test_creates_personal_directory(
        self, db_session, test_tenant, test_user, test_templates, tmp_path
    ):
        """Test creates ~/.claude/agents directory if it doesn't exist"""
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            export_path = mock_home / ".claude" / "agents"

            # Ensure directory doesn't exist
            assert not export_path.exists()

            result = await handle_import_personalagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )

            assert result["success"] is True
            assert export_path.exists()
            assert export_path.is_dir()

    @pytest.mark.asyncio
    async def test_error_user_not_found(self, db_session):
        """Test error when user not found for tenant"""
        result = await handle_import_personalagents(
            db_session=db_session,
            tenant_key="nonexistent-tenant-key",
        )

        assert result["success"] is False
        assert result["error"] == "USER_NOT_FOUND"
        assert "User not found" in result["message"]

    @pytest.mark.asyncio
    async def test_no_active_product_required(
        self, db_session, test_tenant, test_user, test_templates, tmp_path
    ):
        """Test personal import works without active product"""
        # No active product created
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            result = await handle_import_personalagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )

            # Should succeed even without active product
            assert result["success"] is True
            assert result["exported_count"] == 2

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self, db_session, test_tenant, test_user, tmp_path
    ):
        """Test tenant isolation enforced"""
        # Create templates for different tenant
        other_template = AgentTemplate(
            id="other-template-1",
            name="other_agent",
            role="other",
            tenant_key="other-tenant-key",
            is_active=True,
            template_content="Other tenant template",
            tool="claude",
        )
        db_session.add(other_template)
        db_session.commit()

        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            result = await handle_import_personalagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )

            # Should not export other tenant's templates
            export_path = mock_home / ".claude" / "agents"
            assert not (export_path / "other_agent.md").exists()

    @pytest.mark.asyncio
    async def test_backup_creation(
        self, db_session, test_tenant, test_user, test_templates, tmp_path
    ):
        """Test backup is created when overwriting existing files"""
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            # First export
            result1 = await handle_import_personalagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )
            assert result1["success"] is True

            # Second export (should create backup)
            result2 = await handle_import_personalagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )
            assert result2["success"] is True
            assert "Backup created" in result2["message"]


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_no_active_templates(
        self, db_session, test_tenant, test_user, active_product
    ):
        """Test when tenant has no active templates"""
        result = await handle_import_productagents(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
        )

        assert result["success"] is True
        assert result["exported_count"] == 0
        assert "No active templates found" in result["message"]

    @pytest.mark.asyncio
    async def test_handles_export_exception(
        self, db_session, test_tenant, test_user, active_product, test_templates
    ):
        """Test exception handling during export"""
        # Mock export function to raise exception
        with patch(
            "src.giljo_mcp.slash_commands.import_agents.export_templates_to_claude_code",
            side_effect=Exception("Simulated export failure"),
        ):
            result = await handle_import_productagents(
                db_session=db_session,
                tenant_key=test_tenant.tenant_key,
            )

            assert result["success"] is False
            assert result["error"] == "UNEXPECTED_ERROR"
            assert "Failed to import agents" in result["message"]
