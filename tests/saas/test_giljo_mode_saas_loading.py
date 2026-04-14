# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Tests for GILJO_MODE conditional SaaS endpoint/middleware registration (SAAS-001).

These tests reference api.saas_endpoints and api.saas_middleware modules which
are stripped from the CE export. They must live in tests/saas/ to avoid
running in CE CI.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Conditional SaaS endpoint registration
# ---------------------------------------------------------------------------


class TestSaasEndpointRegistration:
    """Verify _register_routers() conditionally loads SaaS endpoints."""

    def test_ce_mode_skips_saas_endpoint_registration(self, monkeypatch):
        """In CE mode, SaaS endpoint registration must NOT be attempted."""
        monkeypatch.setenv("GILJO_MODE", "ce")
        app = MagicMock()

        with patch("api.app.GILJO_MODE", "ce"):
            from api.app import _register_routers

            with patch("api.saas_endpoints.register_saas_routes") as mock_register:
                _register_routers(app)
                mock_register.assert_not_called()

    def test_saas_mode_registers_endpoints_when_dir_exists(self, monkeypatch):
        """In saas mode with saas_endpoints dir present, registration is called."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch("api.app.Path") as mock_path_cls,
            patch("api.saas_endpoints.register_saas_routes") as mock_register,
        ):
            mock_path_instance = MagicMock()
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_path_instance)
            mock_path_instance.is_dir.return_value = True

            from api.app import _register_routers

            _register_routers(app)
            mock_register.assert_called_once_with(app)

    def test_demo_mode_registers_endpoints_when_dir_exists(self, monkeypatch):
        """In demo mode, SaaS endpoints should also be registered."""
        monkeypatch.setenv("GILJO_MODE", "demo")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "demo"),
            patch("api.saas_endpoints.register_saas_routes") as mock_register,
        ):
            from api.app import _register_routers

            _register_routers(app)
            mock_register.assert_called_once_with(app)

    def test_graceful_fallback_when_saas_endpoints_import_fails(self, monkeypatch):
        """In saas mode, if the import fails, no crash occurs."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch(
                "api.saas_endpoints.register_saas_routes",
                side_effect=ImportError("no module"),
            ),
        ):
            from api.app import _register_routers

            _register_routers(app)


# ---------------------------------------------------------------------------
# Conditional SaaS middleware registration
# ---------------------------------------------------------------------------


class TestSaasMiddlewareRegistration:
    """Verify _configure_middleware() conditionally loads SaaS middleware."""

    def test_ce_mode_skips_saas_middleware_registration(self, monkeypatch):
        """In CE mode, SaaS middleware registration must NOT be attempted."""
        monkeypatch.setenv("GILJO_MODE", "ce")
        app = MagicMock()

        with patch("api.app.GILJO_MODE", "ce"):
            from api.app import _configure_middleware

            with patch("api.saas_middleware.register_saas_middleware") as mock_register:
                _configure_middleware(app)
                mock_register.assert_not_called()

    def test_saas_mode_registers_middleware_when_dir_exists(self, monkeypatch):
        """In saas mode with saas_middleware dir present, registration is called."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch("api.saas_middleware.register_saas_middleware") as mock_register,
        ):
            from api.app import _configure_middleware

            _configure_middleware(app)
            mock_register.assert_called_once_with(app)

    def test_graceful_fallback_when_saas_middleware_import_fails(self, monkeypatch):
        """In saas mode, if the middleware import fails, no crash occurs."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch(
                "api.saas_middleware.register_saas_middleware",
                side_effect=ImportError("no module"),
            ),
        ):
            from api.app import _configure_middleware

            _configure_middleware(app)
