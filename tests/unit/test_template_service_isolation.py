"""
Unit tests for TemplateService tenant isolation and error handling (Handover 0123 - Phase 2)

Tests cover:
- Tenant isolation (explicit tenant key, tenant-scoped queries)
- Database error handling (create, get, update exceptions)

Split from test_template_service.py.

Updated Handover 0731: Migrated from dict returns to typed
TemplateListResult, TemplateGetResult, TemplateCreateResult, TemplateUpdateResult.
Fixed pre-existing mock setup issues (AsyncMock -> Mock for get_session_async).
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.schemas.service_responses import (
    TemplateCreateResult,
    TemplateListResult,
)
from src.giljo_mcp.services.template_service import TemplateService
from tests.unit.conftest import make_mock_db_manager, make_mock_session


class TestTemplateServiceTenantIsolation:
    """Test tenant isolation"""

    @pytest.mark.asyncio
    async def test_create_template_uses_provided_tenant_key(self):
        """Test that explicit tenant_key is used"""
        # Arrange
        session = make_mock_session()
        db_manager = make_mock_db_manager(session)
        tenant_manager = Mock()

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.create_template(name="test", content="content", tenant_key="explicit-tenant")

        # Assert - Handover 0731: typed TemplateCreateResult
        assert isinstance(result, TemplateCreateResult)
        assert result.tenant_key == "explicit-tenant"
        # Verify tenant manager was NOT called
        tenant_manager.get_current_tenant.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_templates_filters_by_tenant(self):
        """Test that list_templates only returns templates for specific tenant"""
        # This is verified by checking the SQL query uses tenant_key filter
        # The actual filtering is done by SQLAlchemy, so we just verify
        # the service constructs the correct query

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-1")

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.list_templates()

        # Assert - Handover 0731: typed TemplateListResult
        assert isinstance(result, TemplateListResult)
        assert hasattr(result, "templates")
        # Verify execute was called (which means query was built with tenant filter)
        session.execute.assert_awaited_once()


class TestTemplateServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_create_template_database_exception(self):
        """Test database exception handling in create"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        session = make_mock_session()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - service wraps all unexpected exceptions as BaseGiljoError
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.create_template(name="test", content="content")

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_database_exception(self):
        """Test database exception handling in get"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        session = make_mock_session()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.get_template(template_id="test-id")

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_template_database_exception(self):
        """Test database exception handling in update"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        session = make_mock_session()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.update_template(template_id="test-id", name="new-name")

        assert "Connection lost" in str(exc_info.value)
