"""
Unit tests for GitHub Integration Settings (Handover 0137)

Tests cover:
- Updating GitHub settings in product_memory.github
- Enabling/disabling GitHub integration
- Validating repo URL formats
- Settings persistence across sessions
- Multi-tenant isolation

Target: >80% line coverage

BEHAVIOR TESTS (TDD):
1. GitHub settings are stored in product_memory.github
2. Settings validate repo URL format (HTTPS and SSH)
3. Settings persist across get/update cycles
4. Tenants cannot access other tenants' GitHub settings
5. Disabling integration clears repo_url
6. Invalid repo URLs are rejected
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock
from uuid import uuid4

from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.models import Product


@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


class TestGitHubIntegrationSettings:
    """Test GitHub integration settings management"""

    @pytest.mark.asyncio
    async def test_update_github_settings_stores_in_product_memory(self, mock_db_manager):
        """
        BEHAVIOR: GitHub settings are stored in product_memory.github

        GIVEN: A product exists with initialized product_memory
        WHEN: GitHub settings are updated via update_github_settings()
        THEN: Settings are persisted in product_memory.github field
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"github": {}, "learnings": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=True,
            repo_url="https://github.com/user/repo",
            auto_commit=True
        )

        # Assert
        assert result["success"] is True
        assert product.product_memory["github"]["enabled"] is True
        assert product.product_memory["github"]["repo_url"] == "https://github.com/user/repo"
        assert product.product_memory["github"]["auto_commit"] is True
        assert "last_sync" in product.product_memory["github"]
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enable_github_integration_with_https_url(self, mock_db_manager):
        """
        BEHAVIOR: Enable GitHub integration with HTTPS URL format

        GIVEN: A product with disabled GitHub integration
        WHEN: Integration is enabled with a valid HTTPS GitHub URL
        THEN: Settings are stored and URL is validated
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"github": {"enabled": False}, "learnings": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=True,
            repo_url="https://github.com/patrik-giljoai/GiljoAI_MCP"
        )

        # Assert
        assert result["success"] is True
        assert result["settings"]["enabled"] is True
        assert result["settings"]["repo_url"] == "https://github.com/patrik-giljoai/GiljoAI_MCP"

    @pytest.mark.asyncio
    async def test_enable_github_integration_with_ssh_url(self, mock_db_manager):
        """
        BEHAVIOR: Enable GitHub integration with SSH URL format

        GIVEN: A product with disabled GitHub integration
        WHEN: Integration is enabled with a valid SSH GitHub URL
        THEN: Settings are stored and URL is validated
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"github": {"enabled": False}, "learnings": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=True,
            repo_url="git@github.com:patrik-giljoai/GiljoAI_MCP.git"
        )

        # Assert
        assert result["success"] is True
        assert result["settings"]["enabled"] is True
        assert result["settings"]["repo_url"] == "git@github.com:patrik-giljoai/GiljoAI_MCP.git"

    @pytest.mark.asyncio
    async def test_disable_github_integration_clears_repo_url(self, mock_db_manager):
        """
        BEHAVIOR: Disabling integration clears repo_url

        GIVEN: A product with GitHub integration enabled
        WHEN: Integration is disabled
        THEN: enabled is False and repo_url is set to None
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {
            "github": {
                "enabled": True,
                "repo_url": "https://github.com/user/repo",
                "auto_commit": True
            },
            "learnings": [],
            "context": {}
        }
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=False
        )

        # Assert
        assert result["success"] is True
        assert product.product_memory["github"]["enabled"] is False
        assert product.product_memory["github"]["repo_url"] is None
        assert product.product_memory["github"]["auto_commit"] is False

    @pytest.mark.asyncio
    async def test_invalid_repo_url_rejected(self, mock_db_manager):
        """
        BEHAVIOR: Invalid repo URLs are rejected

        GIVEN: A product with no GitHub integration
        WHEN: Integration is enabled with an invalid repo URL
        THEN: Update fails with validation error
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"github": {}, "learnings": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=True,
            repo_url="not-a-valid-url"
        )

        # Assert
        assert result["success"] is False
        assert "invalid" in result["error"].lower() or "url" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_github_settings_persist_across_get_update_cycles(self, mock_db_manager):
        """
        BEHAVIOR: Settings persist across get/update cycles

        GIVEN: A product with GitHub settings configured
        WHEN: Product is retrieved via get_product()
        THEN: GitHub settings are correctly returned
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.name = "Test Product"
        product.description = "Test"
        product.tenant_key = "test-tenant"
        product.product_memory = {
            "github": {
                "enabled": True,
                "repo_url": "https://github.com/user/repo",
                "auto_commit": False,
                "last_sync": datetime.now(timezone.utc).isoformat()
            },
            "learnings": [],
            "context": {}
        }
        product.primary_vision_path = None
        product.project_path = None
        product.is_active = False
        product.config_data = {}
        product.created_at = datetime.now(timezone.utc)
        product.updated_at = datetime.now(timezone.utc)
        product.deleted_at = None
        product.vision_documents = []

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_product(product.id, include_metrics=False)

        # Assert
        assert result["success"] is True
        assert result["product"]["product_memory"]["github"]["enabled"] is True
        assert result["product"]["product_memory"]["github"]["repo_url"] == "https://github.com/user/repo"

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_github_settings(self, mock_db_manager):
        """
        BEHAVIOR: Tenants cannot access other tenants' GitHub settings

        GIVEN: Product belongs to tenant A
        WHEN: Tenant B tries to update GitHub settings
        THEN: Product not found error is returned
        """
        # Arrange
        db_manager, session = mock_db_manager

        # Product not found for tenant B (different tenant)
        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))

        service = ProductService(db_manager, "tenant-b")

        # Act
        result = await service.update_github_settings(
            product_id="product-owned-by-tenant-a",
            enabled=True,
            repo_url="https://github.com/user/repo"
        )

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_enable_integration_requires_repo_url(self, mock_db_manager):
        """
        BEHAVIOR: Enabling integration requires repo_url

        GIVEN: A product with no GitHub integration
        WHEN: Integration is enabled without repo_url
        THEN: Update fails with validation error
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"github": {}, "learnings": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=True,
            repo_url=None  # Missing repo_url
        )

        # Assert
        assert result["success"] is False
        assert "repo_url" in result["error"].lower() or "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_update_auto_commit_setting(self, mock_db_manager):
        """
        BEHAVIOR: auto_commit setting can be toggled independently

        GIVEN: A product with GitHub integration enabled
        WHEN: auto_commit is toggled without changing other settings
        THEN: Only auto_commit is updated
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {
            "github": {
                "enabled": True,
                "repo_url": "https://github.com/user/repo",
                "auto_commit": False
            },
            "learnings": [],
            "context": {}
        }
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_github_settings(
            product_id=product.id,
            enabled=True,
            repo_url="https://github.com/user/repo",
            auto_commit=True  # Toggle auto_commit
        )

        # Assert
        assert result["success"] is True
        assert product.product_memory["github"]["auto_commit"] is True
        assert product.product_memory["github"]["enabled"] is True
        assert product.product_memory["github"]["repo_url"] == "https://github.com/user/repo"
