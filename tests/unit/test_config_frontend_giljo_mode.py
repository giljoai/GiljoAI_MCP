# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Tests for giljo_mode field in GET /api/v1/config/frontend (SAAS-005)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestFrontendConfigGiljoMode:
    """Verify that the /frontend config endpoint returns giljo_mode."""

    def _make_request(self) -> MagicMock:
        """Create a fake Request with a client IP."""
        req = MagicMock()
        req.client = MagicMock()
        req.client.host = "127.0.0.1"
        req.headers = {}
        return req

    def _make_config(self) -> MagicMock:
        """Create a fake ConfigManager."""
        cfg = MagicMock()
        cfg.get_nested = MagicMock(
            side_effect=lambda key, default=None: {
                "services.api.port": 7272,
                "features.api_keys_required": False,
                "services.external_host": "localhost",
                "features.ssl_enabled": False,
                "edition": "community",
            }.get(key, default)
        )
        cfg.tenant = MagicMock()
        cfg.tenant.default_tenant_key = "tk_test"
        return cfg

    async def _call_endpoint(self, giljo_mode_value: str) -> dict:
        """Call get_frontend_configuration with mocked state and GILJO_MODE."""
        from api.endpoints.configuration import get_frontend_configuration

        state_mock = MagicMock()
        state_mock.config = self._make_config()

        with (
            patch("api.app.GILJO_MODE", giljo_mode_value),
            patch("api.app.state", state_mock),
        ):
            return await get_frontend_configuration(self._make_request())

    async def test_giljo_mode_default_ce(self):
        """Config endpoint returns giljo_mode='ce' when GILJO_MODE is 'ce'."""
        result = await self._call_endpoint("ce")
        assert "giljo_mode" in result
        assert result["giljo_mode"] == "ce"

    async def test_giljo_mode_demo(self):
        """Config endpoint returns giljo_mode='demo' when GILJO_MODE is 'demo'."""
        result = await self._call_endpoint("demo")
        assert result["giljo_mode"] == "demo"

    async def test_giljo_mode_saas(self):
        """Config endpoint returns giljo_mode='saas' when GILJO_MODE is 'saas'."""
        result = await self._call_endpoint("saas")
        assert result["giljo_mode"] == "saas"

    async def test_existing_fields_still_present(self):
        """Adding giljo_mode does not remove existing response fields."""
        result = await self._call_endpoint("ce")
        assert "api" in result
        assert "websocket" in result
        assert "security" in result
        assert "edition" in result
        assert "giljo_mode" in result

    async def test_giljo_mode_unknown_value_passes_through(self):
        """Unknown GILJO_MODE value is returned as-is (no validation at endpoint level)."""
        result = await self._call_endpoint("unknown_value")
        assert result["giljo_mode"] == "unknown_value"

    async def test_config_unavailable_returns_503(self):
        """Returns 503 when state.config is None (server not ready)."""
        from fastapi import HTTPException

        from api.endpoints.configuration import get_frontend_configuration

        state_mock = MagicMock()
        state_mock.config = None

        with (
            patch("api.app.GILJO_MODE", "ce"),
            patch("api.app.state", state_mock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_frontend_configuration(self._make_request())

        assert exc_info.value.status_code == 503
