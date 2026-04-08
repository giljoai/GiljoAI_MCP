# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ToolAccessor.create_project() — signature and hardcoded behavior.

Test Coverage:
- Method signature: mission is optional, no context_budget, no status param
- Always creates projects with status "inactive"
- Mission parameter default and explicit forwarding
"""

import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


class TestCreateProjectSignature:
    """Test suite for create_project() method signature validation."""

    def test_mission_parameter_is_optional_with_empty_default(self):
        """Verify mission parameter has default empty string."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "mission" in params, "create_project() must accept mission parameter"
        assert params["mission"].default == "", (
            "mission should default to empty string"
        )

    def test_no_context_budget_parameter(self):
        """Verify context_budget parameter has been removed."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "context_budget" not in params, (
            "context_budget parameter should be removed from create_project()"
        )

    def test_no_status_parameter(self):
        """Verify status parameter has been removed (hardcoded to inactive)."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "status" not in params, (
            "status parameter should be removed from create_project()"
        )

    def test_expected_parameters(self):
        """Verify all expected parameters exist with correct defaults."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        expected = {
            "self": inspect.Parameter.empty,
            "name": inspect.Parameter.empty,
            "mission": "",
            "description": "",
            "product_id": None,
            "tenant_key": None,
        }

        for param_name, default in expected.items():
            assert param_name in params, (
                f"Parameter '{param_name}' should be in signature"
            )
            if default is not inspect.Parameter.empty:
                assert params[param_name].default == default, (
                    f"Parameter '{param_name}' should have default {default!r}"
                )

    def test_tenant_key_parameter_present(self):
        """Verify tenant_key parameter exists with None default."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "tenant_key" in params, (
            "create_project() must accept tenant_key parameter"
        )
        assert params["tenant_key"].default is None, (
            "tenant_key should have default value of None"
        )


class TestCreateProjectHardcodedBehavior:
    """Test suite for hardcoded behaviors (status always inactive)."""

    @pytest.mark.asyncio
    async def test_always_creates_with_inactive_status(self):
        """Test that status is always 'inactive' regardless of any other input."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with patch.object(
            tool_accessor._project_service,
            "create_project",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_project = Mock()
            mock_project.id = "proj-status"
            mock_project.alias = "PRJ-STS"
            mock_project.name = "Status Test"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-status"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Status Test",
                product_id="prod-status",
                tenant_key="tenant-abc",
            )

            # Verify ProjectService was called with status="inactive"
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["status"] == "inactive", (
                "Status must always be 'inactive'"
            )

    @pytest.mark.asyncio
    async def test_mission_defaults_to_empty_string(self):
        """Test that mission defaults to empty string when not provided."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with patch.object(
            tool_accessor._project_service,
            "create_project",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_project = Mock()
            mock_project.id = "proj-mission"
            mock_project.alias = "PRJ-MSN"
            mock_project.name = "Mission Default Test"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-mission"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Mission Default Test",
                product_id="prod-mission",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["mission"] == "", (
                "Mission should default to empty string"
            )

    @pytest.mark.asyncio
    async def test_passes_explicit_mission_when_provided(self):
        """Test that an explicitly provided mission is forwarded correctly."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with patch.object(
            tool_accessor._project_service,
            "create_project",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_project = Mock()
            mock_project.id = "proj-expl"
            mock_project.alias = "PRJ-EXP"
            mock_project.name = "Explicit Mission Test"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-expl"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Explicit Mission Test",
                mission="Build the REST API for user management",
                product_id="prod-expl",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["mission"] == "Build the REST API for user management"
