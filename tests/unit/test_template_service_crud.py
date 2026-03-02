"""
Unit tests for TemplateService CRUD operations (Handover 0123 - Phase 2)

Tests cover:
- Template creation (success, missing tenant, error handling)
- Template retrieval by ID and name
- Template listing (success, empty, missing tenant)
- Template update (success, not found, partial)

Split from test_template_service.py.

Updated Handover 0731: Migrated from dict returns to typed
TemplateListResult, TemplateGetResult, TemplateCreateResult, TemplateUpdateResult.
Fixed pre-existing mock setup issues (AsyncMock -> Mock for get_session_async).
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.schemas.service_responses import (
    TemplateCreateResult,
    TemplateGetResult,
    TemplateListResult,
    TemplateUpdateResult,
)
from src.giljo_mcp.services.template_service import TemplateService
from tests.unit.conftest import make_mock_db_manager, make_mock_session


class TestTemplateServiceCRUD:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_template_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful template creation"""
        # Arrange
        db_manager, session = mock_db_manager

        service = TemplateService(db_manager, mock_tenant_manager)

        # Act
        result = await service.create_template(
            name="custom-analyzer", content="You are an analyzer agent...", role="analyzer", category="custom"
        )

        # Assert
        # Handover 0731: Service returns typed TemplateCreateResult
        assert isinstance(result, TemplateCreateResult)
        assert result.template_id  # Non-empty UUID string
        assert result.name == "custom-analyzer"
        assert result.tenant_key == "test-tenant"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_template_no_tenant_context(self):
        """Test template creation fails without tenant context"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(ValidationError) as exc_info:
            await service.create_template(name="test", content="content")

        assert "No tenant context" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_template_error_handling(self):
        """Test error handling in create_template"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        session = make_mock_session()
        session.__aenter__ = AsyncMock(side_effect=Exception("Database error"))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - service wraps all unexpected exceptions as BaseGiljoError
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.create_template(name="test", content="content")

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_by_id_success(self):
        """Test successful template retrieval by ID"""
        # Arrange
        mock_template = Mock(spec=AgentTemplate)
        mock_template.id = "test-id"
        mock_template.name = "orchestrator"
        mock_template.system_instructions = "You are an orchestrator..."
        mock_template.role = "orchestrator"
        mock_template.category = "role"
        mock_template.cli_tool = None
        mock_template.background_color = "#FF5733"
        mock_template.tenant_key = "test-tenant"
        mock_template.product_id = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_template)
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.get_template(template_id="test-id")

        # Assert - Handover 0731: typed TemplateGetResult
        assert isinstance(result, TemplateGetResult)
        assert result.template.id == "test-id"
        assert result.template.name == "orchestrator"
        assert result.template.content == "You are an orchestrator..."

    @pytest.mark.asyncio
    async def test_get_template_by_name_success(self):
        """Test successful template retrieval by name"""
        # Arrange
        mock_template = Mock(spec=AgentTemplate)
        mock_template.id = "test-id"
        mock_template.name = "analyzer"
        mock_template.system_instructions = "You are an analyzer..."
        mock_template.role = "analyzer"
        mock_template.category = "role"
        mock_template.cli_tool = None
        mock_template.background_color = "#00FF00"
        mock_template.tenant_key = "test-tenant"
        mock_template.product_id = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_template)
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.get_template(template_name="analyzer")

        # Assert - Handover 0731: typed TemplateGetResult
        assert isinstance(result, TemplateGetResult)
        assert result.template.name == "analyzer"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test template not found error"""
        from src.giljo_mcp.exceptions import TemplateNotFoundError

        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(TemplateNotFoundError) as exc_info:
            await service.get_template(template_id="nonexistent")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_missing_identifier(self):
        """Test get_template fails without ID or name"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(ValidationError) as exc_info:
            await service.get_template()

        assert "Either template_id or template_name must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_templates_success(self):
        """Test successful template listing"""
        # Arrange
        mock_template1 = Mock(spec=AgentTemplate)
        mock_template1.id = "id-1"
        mock_template1.name = "orchestrator"
        mock_template1.system_instructions = "Content 1"
        mock_template1.role = "orchestrator"
        mock_template1.category = "role"
        mock_template1.cli_tool = None
        mock_template1.background_color = "#FF0000"
        mock_template1.tenant_key = "test-tenant"
        mock_template1.product_id = None

        mock_template2 = Mock(spec=AgentTemplate)
        mock_template2.id = "id-2"
        mock_template2.name = "analyzer"
        mock_template2.system_instructions = "Content 2"
        mock_template2.role = "analyzer"
        mock_template2.category = "role"
        mock_template2.cli_tool = None
        mock_template2.background_color = "#00FF00"
        mock_template2.tenant_key = "test-tenant"
        mock_template2.product_id = None

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_template1, mock_template2])))
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.list_templates()

        # Assert - Handover 0731: typed TemplateListResult
        assert isinstance(result, TemplateListResult)
        assert len(result.templates) == 2
        assert result.count == 2
        assert result.templates[0]["name"] == "orchestrator"
        assert result.templates[1]["name"] == "analyzer"

    @pytest.mark.asyncio
    async def test_list_templates_empty(self):
        """Test listing templates when none exist"""
        # Arrange
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.list_templates()

        # Assert - Handover 0731: typed TemplateListResult
        assert isinstance(result, TemplateListResult)
        assert len(result.templates) == 0
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_list_templates_no_tenant_context(self):
        """Test listing templates fails without tenant context"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(ValidationError) as exc_info:
            await service.list_templates()

        assert "No tenant context" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_template_success(self):
        """Test successful template update"""
        # Arrange
        mock_template = Mock(spec=AgentTemplate)
        mock_template.id = "test-id"
        mock_template.name = "old-name"
        mock_template.system_instructions = "old content"
        mock_template.role = "old-role"
        mock_template.category = "old-category"
        mock_template.cli_tool = None
        mock_template.background_color = "#000000"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_template)
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.update_template(template_id="test-id", name="new-name", content="new content")

        # Assert - Handover 0731: typed TemplateUpdateResult
        assert isinstance(result, TemplateUpdateResult)
        assert result.template_id == "test-id"
        assert result.updated is True
        assert mock_template.name == "new-name"
        # Note: content is stored in system_instructions
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_template_not_found(self):
        """Test update fails when template doesn't exist"""
        from src.giljo_mcp.exceptions import TemplateNotFoundError

        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(TemplateNotFoundError) as exc_info:
            await service.update_template(template_id="nonexistent", name="new-name")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_template_partial_update(self):
        """Test updating only specific fields"""
        # Arrange
        mock_template = Mock(spec=AgentTemplate)
        mock_template.id = "test-id"
        mock_template.name = "original-name"
        mock_template.system_instructions = "original content"
        mock_template.role = "original-role"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_template)
        session = make_mock_session(execute=AsyncMock(return_value=mock_result))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act - only update content
        result = await service.update_template(template_id="test-id", content="new content")

        # Assert - Handover 0731: typed TemplateUpdateResult
        assert isinstance(result, TemplateUpdateResult)
        assert result.updated is True
        assert mock_template.name == "original-name"  # Unchanged
        assert mock_template.role == "original-role"  # Unchanged
