# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for INF-9000i: removal of two vestigial env reads.

GILJO_DEBUG fed server.debug, which had zero downstream consumers (only
re-serialized in get_all_settings). GILJO_DATABASE_TYPE was a dead duplicate
of the live DB_TYPE var -- validate() rejects any database.type value except
"postgresql", so the override never had a legal effect. Both reads, and the
server.debug field/plumbing they fed, are deleted. This locks in the removal:
neither env var may affect config state again.
"""

from giljo_mcp.config_manager import ConfigManager, ServerConfig


class TestDeadEnvReadsRemoved:
    def test_server_config_has_no_debug_field(self):
        """server.debug plumbing (dataclass field) is gone entirely."""
        assert not hasattr(ServerConfig(), "debug")

    def test_giljo_debug_env_var_is_inert(self, monkeypatch):
        """GILJO_DEBUG no longer has any config to write into."""
        monkeypatch.setenv("DB_PASSWORD", "test")  # bypass validation
        monkeypatch.setenv("GILJO_DEBUG", "true")

        config = ConfigManager()

        assert not hasattr(config.server, "debug")

    def test_get_all_settings_has_no_debug_key(self, monkeypatch):
        """The dead field's get_all_settings re-serialization is also gone."""
        monkeypatch.setenv("DB_PASSWORD", "test")

        config = ConfigManager()
        settings = config.get_all_settings()

        assert "debug" not in settings["server"]

    def test_giljo_database_type_env_var_is_inert(self, monkeypatch):
        """GILJO_DATABASE_TYPE no longer overrides database.type; only the
        live DB_TYPE var (untouched by this change) may."""
        monkeypatch.setenv("DB_PASSWORD", "test")
        monkeypatch.delenv("DB_TYPE", raising=False)
        monkeypatch.setenv("GILJO_DATABASE_TYPE", "sqlite")

        config = ConfigManager()

        assert config.database.type == "postgresql"

    def test_db_type_env_var_still_live(self, monkeypatch):
        """DB_TYPE (the real var) still works -- this change must not touch it."""
        monkeypatch.setenv("DB_PASSWORD", "test")
        monkeypatch.setenv("DB_TYPE", "postgresql")

        config = ConfigManager()

        assert config.database.type == "postgresql"
