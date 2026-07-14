# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for BE-9138: removal of ConfigManager.get_tenant_manager() and the
two dead feature flags it gated (features.multi_tenant / features.enable_websockets).

get_tenant_manager() called TenantManager(db_manager=..., multi_tenant_enabled=...),
but TenantManager defines no __init__ that accepts arguments, so the call ALWAYS
raised `TypeError: TenantManager() takes no arguments`. Its sole caller
(scripts/init_config.py test_integration) swallowed the crash in a blanket
try/except. The FeatureFlags dataclass (multi_tenant, enable_websockets) had no
behavioural consumer -- the real websocket switch is server.websocket_enabled and
the real multi-tenant switch is tenant.enable_multi_tenant. Method + flags deleted.

This locks in the removal AND asserts tolerance: existing installs whose config.yaml
carries a legacy `features:` block, or whose environment sets ENABLE_MULTI_TENANT /
ENABLE_WEBSOCKET, must still load without error (legacy values ignored, not crashed on).
"""

import yaml

import giljo_mcp.config_manager as cm
from giljo_mcp.config_manager import ConfigManager


class TestTenantManagerFlagsRemoved:
    def test_config_manager_has_no_get_tenant_manager(self, monkeypatch):
        """The broken get_tenant_manager() method is gone entirely."""
        monkeypatch.setenv("DB_PASSWORD", "test")  # bypass validation
        assert not hasattr(ConfigManager(), "get_tenant_manager")

    def test_featureflags_dataclass_removed(self):
        """The FeatureFlags dataclass no longer exists in the module."""
        assert not hasattr(cm, "FeatureFlags")

    def test_config_has_no_features_attr(self, monkeypatch):
        """config.features (the FeatureFlags instance) is gone."""
        monkeypatch.setenv("DB_PASSWORD", "test")
        assert not hasattr(ConfigManager(), "features")

    def test_get_all_settings_has_no_features_key(self, monkeypatch):
        """The dead flags' get_all_settings re-serialization is also gone."""
        monkeypatch.setenv("DB_PASSWORD", "test")
        settings = ConfigManager().get_all_settings()
        assert "features" not in settings

    def test_env_vars_are_inert(self, monkeypatch):
        """ENABLE_MULTI_TENANT / ENABLE_WEBSOCKET no longer write any config
        state, and setting them does not crash load."""
        monkeypatch.setenv("DB_PASSWORD", "test")
        monkeypatch.setenv("ENABLE_MULTI_TENANT", "false")
        monkeypatch.setenv("ENABLE_WEBSOCKET", "false")

        config = ConfigManager()  # must not raise

        assert not hasattr(config, "features")

    def test_legacy_features_block_in_config_is_tolerated(self, monkeypatch, tmp_path):
        """An existing install whose config.yaml still carries the retired
        `features:` block loads cleanly -- legacy keys are ignored, not rejected."""
        monkeypatch.setenv("DB_PASSWORD", "test")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.safe_dump(
                {
                    "features": {
                        "multi_tenant": True,
                        "websocket_updates": True,
                    }
                }
            )
        )

        config = ConfigManager(config_path=config_file, auto_reload=False)  # must not raise

        assert not hasattr(config, "features")
