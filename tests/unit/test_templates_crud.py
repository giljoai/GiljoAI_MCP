"""
Unit tests for templates CRUD endpoints - Handover 0126

Tests create, list, and get endpoints using TemplateService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.endpoints.templates import crud
from api.endpoints.templates.models import TemplateResponse
from src.giljo_mcp.models import AgentTemplate


class TestGetTemplate:
    """Tests for get_template endpoint."""

    @pytest.mark.asyncio
    async def test_get_template_success(self):
        """Test successful template retrieval."""
        # Mock dependencies
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_template = AgentTemplate(
            id="tmpl-123",
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            cli_tool="claude",
            description="Test template",
            system_instructions="Test content",
            model="sonnet",
            is_active=True,
            is_default=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            behavioral_rules=[],
            success_criteria=[],
            tags=[],
            variables=[],
            version="1.0.0",
            usage_count=0,
        )

        mock_service = AsyncMock()
        mock_service.get_template.return_value = {"success": True, "template": mock_template}

        # Call endpoint
        response = await crud.get_template(
            template_id="tmpl-123", current_user=mock_user, template_service=mock_service
        )

        # Assertions
        assert isinstance(response, TemplateResponse)
        assert response.id == "tmpl-123"
        assert response.name == "test-agent"
        mock_service.get_template.assert_called_once_with(template_id="tmpl-123", tenant_key="test_tenant")

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test get template when not found."""
        mock_user = MagicMock()
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.get_template.return_value = {"success": False, "error": "Template not found"}

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_template(template_id="tmpl-123", current_user=mock_user, template_service=mock_service)

        assert exc_info.value.status_code == 404


class TestListTemplates:
    """Tests for list_templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_templates_success(self):
        """Test successful template listing."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_template = AgentTemplate(
            id="tmpl-1",
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            cli_tool="claude",
            description="Test template",
            system_instructions="Test content",
            model="sonnet",
            is_active=True,
            is_default=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            behavioral_rules=[],
            success_criteria=[],
            tags=[],
            variables=[],
            version="1.0.0",
            usage_count=0,
        )

        mock_service = AsyncMock()
        mock_service.list_templates.return_value = {"success": True, "templates": [mock_template]}

        response = await crud.list_templates(
            current_user=mock_user, template_service=mock_service, role=None, is_active=None
        )

        assert len(response) == 1
        assert response[0].id == "tmpl-1"
        mock_service.list_templates.assert_called_once()
