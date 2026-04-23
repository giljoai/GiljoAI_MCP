# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition test -- covers CE-tier policy table branches.

"""Unit tests for setup_security policy table (IMP-0011).

Covers the GILJO_MODE x has_admin_user x has_any_user -> route_signal matrix.
Pure function tests -- no DB, no HTTP.
"""

from __future__ import annotations

import pytest

from api.endpoints.setup_security import _compute_setup_signal


class TestComputeSetupSignalCE:
    """CE mode: classic fresh-install detection."""

    def test_ce_no_users_is_fresh_install(self):
        result = _compute_setup_signal(mode="ce", has_admin_user=False, has_any_user=False)
        assert result["is_fresh_install"] is True
        assert result["requires_admin_creation"] is True
        assert result["show_public_landing"] is False
        assert result["route_signal"] == "create_admin"

    def test_ce_with_admin_is_normal_login(self):
        result = _compute_setup_signal(mode="ce", has_admin_user=True, has_any_user=True)
        assert result["is_fresh_install"] is False
        assert result["requires_admin_creation"] is False
        assert result["show_public_landing"] is False
        assert result["route_signal"] == "login"

    def test_ce_any_user_without_admin_is_not_fresh(self):
        # Defensive: should not expose admin-bootstrap once any user exists.
        result = _compute_setup_signal(mode="ce", has_admin_user=False, has_any_user=True)
        assert result["is_fresh_install"] is False
        assert result["requires_admin_creation"] is False
        assert result["route_signal"] == "login"


class TestComputeSetupSignalDemo:
    """Demo mode: never expose admin-bootstrap UI publicly."""

    def test_demo_no_users_shows_public_landing(self):
        result = _compute_setup_signal(mode="demo", has_admin_user=False, has_any_user=False)
        assert result["is_fresh_install"] is False
        assert result["requires_admin_creation"] is False
        assert result["show_public_landing"] is True
        assert result["route_signal"] == "public_landing"

    def test_demo_with_admin_shows_public_landing(self):
        result = _compute_setup_signal(mode="demo", has_admin_user=True, has_any_user=True)
        assert result["is_fresh_install"] is False
        assert result["requires_admin_creation"] is False
        assert result["show_public_landing"] is True
        assert result["route_signal"] == "public_landing"

    def test_demo_non_admin_user_still_public_landing(self):
        result = _compute_setup_signal(mode="demo", has_admin_user=False, has_any_user=True)
        assert result["show_public_landing"] is True
        assert result["requires_admin_creation"] is False
        assert result["route_signal"] == "public_landing"


class TestComputeSetupSignalSaas:
    """SaaS-production mode: identical to demo."""

    def test_saas_no_users_shows_public_landing(self):
        result = _compute_setup_signal(mode="saas", has_admin_user=False, has_any_user=False)
        assert result["show_public_landing"] is True
        assert result["requires_admin_creation"] is False
        assert result["route_signal"] == "public_landing"

    def test_saas_with_admin_shows_public_landing(self):
        result = _compute_setup_signal(mode="saas", has_admin_user=True, has_any_user=True)
        assert result["show_public_landing"] is True
        assert result["requires_admin_creation"] is False
        assert result["route_signal"] == "public_landing"


class TestComputeSetupSignalUnknownMode:
    """Unknown/malformed modes must fail secure -- never expose admin bootstrap."""

    @pytest.mark.parametrize("mode", ["", "production", "dev", "unknown"])
    def test_unknown_mode_fails_secure(self, mode):
        result = _compute_setup_signal(mode=mode, has_admin_user=False, has_any_user=False)
        # Fail-secure: treat as non-CE (no admin creation exposure).
        assert result["requires_admin_creation"] is False
        assert result["show_public_landing"] is True
        assert result["route_signal"] == "public_landing"
