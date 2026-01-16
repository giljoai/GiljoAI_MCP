"""
Unit tests for Simplified Git Integration (Handover 013B)

REFACTOR GOAL: Remove over-engineered GitHub API code.
Git integration should ONLY:
1. Store a toggle: "Enable Git + 360 Memory"
2. Store simple config (commit_limit, default_branch)
3. NOT call GitHub API
4. NOT validate repo URLs (CLI agents handle git)

BEHAVIOR TESTS (TDD - WRITE FIRST):
1. Git integration stores simple toggle without repo_url requirement
2. Git integration does NOT call GitHub API
3. Git integration accepts optional config (commit_limit, default_branch)
4. Disabling integration clears config
5. Settings persist across get/update cycles

Target: >80% line coverage

Author: TDD Implementor Agent
Date: 2025-11-16
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
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


class TestSimplifiedGitIntegration:
    """Test simplified git integration without GitHub API"""

    @pytest.mark.asyncio
    async def test_git_integration_stores_simple_toggle(self, mock_db_manager):
        """
        BEHAVIOR: Git integration stores only toggle + config, no GitHub API

        GIVEN: A product exists with initialized product_memory
        WHEN: Git integration is enabled WITHOUT repo_url requirement
        THEN: Settings are stored with simple structure (no repo_url validation)
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act - Enable git integration WITHOUT repo_url
        result = await service.update_git_integration(
            product_id=product.id,
            enabled=True,
            commit_limit=20,
            default_branch="main"
        )

        # Assert
        assert result["success"] is True
        assert product.product_memory["git_integration"]["enabled"] is True
        assert product.product_memory["git_integration"]["commit_limit"] == 20
        assert product.product_memory["git_integration"]["default_branch"] == "main"

        # CRITICAL: No repo_url field should exist
        assert "repo_url" not in product.product_memory["git_integration"]

        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_git_integration_does_not_call_github_api(self, mock_db_manager):
        """
        BEHAVIOR: Git integration does NOT call GitHub API

        GIVEN: Git integration is enabled
        WHEN: Settings are updated or learnings added
        THEN: No external HTTP requests to GitHub API are made
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act - Enable git integration and verify no HTTP calls
        with patch("httpx.AsyncClient") as mock_http_client:
            result = await service.update_git_integration(
                product_id=product.id,
                enabled=True,
                commit_limit=30
            )

            # Assert - No HTTP client should be instantiated
            mock_http_client.assert_not_called()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_git_integration_optional_config_defaults(self, mock_db_manager):
        """
        BEHAVIOR: Git integration accepts optional config with sensible defaults

        GIVEN: A product exists
        WHEN: Git integration is enabled without explicit config
        THEN: Default values are applied (commit_limit=20, default_branch=main)
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act - Enable without explicit config
        result = await service.update_git_integration(
            product_id=product.id,
            enabled=True
        )

        # Assert - Defaults applied
        assert result["success"] is True
        assert product.product_memory["git_integration"]["enabled"] is True
        assert product.product_memory["git_integration"]["commit_limit"] == 20  # Default
        assert product.product_memory["git_integration"]["default_branch"] == "main"  # Default

    @pytest.mark.asyncio
    async def test_disable_git_integration_clears_config(self, mock_db_manager):
        """
        BEHAVIOR: Disabling git integration clears all config

        GIVEN: A product with enabled git integration
        WHEN: Integration is disabled
        THEN: All config fields are cleared (enabled=False only)
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {
            "git_integration": {
                "enabled": True,
                "commit_limit": 20,
                "default_branch": "main"
            },
            "sequential_history": [],
            "context": {}
        }
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act - Disable integration
        result = await service.update_git_integration(
            product_id=product.id,
            enabled=False
        )

        # Assert - Config cleared
        assert result["success"] is True
        assert product.product_memory["git_integration"]["enabled"] is False
        assert "commit_limit" not in product.product_memory["git_integration"]
        assert "default_branch" not in product.product_memory["git_integration"]

    @pytest.mark.asyncio
    async def test_git_integration_no_url_validation(self, mock_db_manager):
        """
        BEHAVIOR: Git integration does NOT validate repo URLs

        GIVEN: A product exists
        WHEN: Git integration is enabled
        THEN: No URL validation occurs (CLI agents handle git)
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act - Enable without any URL (should succeed)
        result = await service.update_git_integration(
            product_id=product.id,
            enabled=True
        )

        # Assert - No validation errors
        assert result["success"] is True
        assert "error" not in result

        # Verify no URL field exists
        assert "repo_url" not in product.product_memory["git_integration"]

    @pytest.mark.asyncio
    async def test_add_learning_does_not_fetch_github_commits(self, mock_db_manager):
        """
        BEHAVIOR: Adding learnings does NOT fetch GitHub commits

        GIVEN: A product with git integration enabled
        WHEN: A learning entry is added to product memory
        THEN: No GitHub API calls are made (commits handled by CLI agents)
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {
            "git_integration": {"enabled": True, "commit_limit": 20},
            "sequential_history": [],
            "context": {}
        }
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        learning_entry = {
            "type": "project_closeout",
            "project_id": str(uuid4()),
            "summary": "Implemented auth feature",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Act - Add learning and verify no HTTP calls
        with patch("httpx.AsyncClient") as mock_http_client:
            updated_product = await service.add_learning_to_product_memory(
                session=session,
                product_id=product.id,
                learning_entry=learning_entry
            )

            # Assert - No HTTP client should be instantiated
            mock_http_client.assert_not_called()

            # Learning should be added without GitHub commits
            assert len(updated_product.product_memory["sequential_history"]) == 1
            assert "git_commits" not in updated_product.product_memory["sequential_history"][0]


class TestGitIntegrationWebSocketEvents:
    """Test WebSocket event emission for git integration changes"""

    @pytest.mark.asyncio
    async def test_update_git_integration_emits_websocket_event(self, mock_db_manager):
        """
        BEHAVIOR: Git integration changes emit WebSocket events

        GIVEN: A product exists
        WHEN: Git integration settings are updated
        THEN: WebSocket event is emitted for real-time UI updates
        """
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.tenant_key = "test-tenant"
        product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}
        product.deleted_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Mock WebSocket emission
        service._emit_websocket_event = AsyncMock()

        # Act
        result = await service.update_git_integration(
            product_id=product.id,
            enabled=True,
            commit_limit=25
        )

        # Assert
        assert result["success"] is True
        service._emit_websocket_event.assert_awaited_once()

        # Verify event structure
        call_args = service._emit_websocket_event.call_args
        assert call_args.kwargs["event_type"] == "product:git:settings:changed"
        assert call_args.kwargs["data"]["product_id"] == product.id
        assert call_args.kwargs["data"]["settings"]["enabled"] is True
        assert call_args.kwargs["data"]["settings"]["commit_limit"] == 25
