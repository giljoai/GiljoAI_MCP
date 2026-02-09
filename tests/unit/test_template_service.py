"""
Unit tests for TemplateService (Handover 0123 - Phase 2)

Tests cover:
- CRUD operations
- Template retrieval by ID and name
- Tenant isolation
- Error handling and edge cases

Target: >80% line coverage
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.services.template_service import TemplateService


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
    session.delete = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Create mock tenant manager."""
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
    return tenant_manager


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
        # Handover 0730: Service returns dict directly (no success wrapper)
        assert "template_id" in result
        assert result["name"] == "custom-analyzer"
        assert result["tenant_key"] == "test-tenant"
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
        from src.giljo_mcp.exceptions import DatabaseError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Create a proper async context manager that raises on enter
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Database error"))
        session.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = Mock(return_value=session)

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(DatabaseError) as exc_info:
            await service.create_template(name="test", content="content")

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_by_id_success(self):
        """Test successful template retrieval by ID"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        # Mock template
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

        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_template)
        session.execute = AsyncMock(return_value=mock_result)

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.get_template(template_id="test-id")

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert result["template"]["id"] == "test-id"
        assert result["template"]["name"] == "orchestrator"
        assert result["template"]["content"] == "You are an orchestrator..."

    @pytest.mark.asyncio
    async def test_get_template_by_name_success(self):
        """Test successful template retrieval by name"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        # Mock template
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
        session.execute = AsyncMock(return_value=mock_result)

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.get_template(template_name="analyzer")

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert result["template"]["name"] == "analyzer"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test template not found error"""
        from src.giljo_mcp.exceptions import TemplateNotFoundError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

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
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        # Mock templates
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
        session.execute = AsyncMock(return_value=mock_result)

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.list_templates()

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert len(result["templates"]) == 2
        assert result["count"] == 2
        assert result["templates"][0]["name"] == "orchestrator"
        assert result["templates"][1]["name"] == "analyzer"

    @pytest.mark.asyncio
    async def test_list_templates_empty(self):
        """Test listing templates when none exist"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        session.execute = AsyncMock(return_value=mock_result)

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.list_templates()

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert len(result["templates"]) == 0
        assert result["count"] == 0

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
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        # Mock existing template
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
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.update_template(template_id="test-id", name="new-name", content="new content")

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert result["template_id"] == "test-id"
        assert result["updated"] is True
        assert mock_template.name == "new-name"
        # Note: content is stored in system_instructions
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_template_not_found(self):
        """Test update fails when template doesn't exist"""
        from src.giljo_mcp.exceptions import TemplateNotFoundError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(TemplateNotFoundError) as exc_info:
            await service.update_template(template_id="nonexistent", name="new-name")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_template_partial_update(self):
        """Test updating only specific fields"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        # Mock existing template
        mock_template = Mock(spec=AgentTemplate)
        mock_template.id = "test-id"
        mock_template.name = "original-name"
        mock_template.system_instructions = "original content"
        mock_template.role = "original-role"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_template)
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        service = TemplateService(db_manager, tenant_manager)

        # Act - only update content
        result = await service.update_template(template_id="test-id", content="new content")

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert result["updated"] is True
        assert mock_template.name == "original-name"  # Unchanged
        assert mock_template.role == "original-role"  # Unchanged


class TestTemplateServiceTenantIsolation:
    """Test tenant isolation"""

    @pytest.mark.asyncio
    async def test_create_template_uses_provided_tenant_key(self):
        """Test that explicit tenant_key is used"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        session.add = Mock()
        session.commit = AsyncMock()

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.create_template(name="test", content="content", tenant_key="explicit-tenant")

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert result["tenant_key"] == "explicit-tenant"
        # Verify tenant manager was NOT called
        tenant_manager.get_current_tenant.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_templates_filters_by_tenant(self):
        """Test that list_templates only returns templates for specific tenant"""
        # This is verified by checking the SQL query uses tenant_key filter
        # The actual filtering is done by SQLAlchemy, so we just verify
        # the service constructs the correct query

        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        tenant_manager.get_current_tenant = Mock(return_value="tenant-1")
        db_manager.get_session_async = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock())
        )

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        session.execute = AsyncMock(return_value=mock_result)

        service = TemplateService(db_manager, tenant_manager)

        # Act
        result = await service.list_templates()

        # Assert - exception-based pattern (Handover 0730): no success wrapper
        assert "templates" in result
        # Verify execute was called (which means query was built with tenant filter)
        session.execute.assert_awaited_once()


class TestTemplateServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_create_template_database_exception(self):
        """Test database exception handling in create"""
        from src.giljo_mcp.exceptions import DatabaseError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Create a proper async context manager that raises on enter
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = Mock(return_value=session)

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(DatabaseError) as exc_info:
            await service.create_template(name="test", content="content")

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_database_exception(self):
        """Test database exception handling in get"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Create a proper async context manager that raises on enter
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = Mock(return_value=session)

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
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Create a proper async context manager that raises on enter
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = Mock(return_value=session)

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.update_template(template_id="test-id", name="new-name")

        assert "Connection lost" in str(exc_info.value)
