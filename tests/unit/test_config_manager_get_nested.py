"""Tests for ConfigManager.get_nested() accessor.

Covers dot-notation traversal of the raw config dict:
- Simple top-level key
- Nested multi-level key
- Missing key returns default
- Partially missing path returns default
- Empty/None config returns default
- Leaf value of None is returned (not confused with missing key)
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.giljo_mcp.config_manager import ConfigManager


@pytest.fixture
def config_with_data(tmp_path):
    """Create a ConfigManager backed by a temp config.yaml with known values."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "server": {
                    "api": {"host": "0.0.0.0", "port": 7272},
                    "mcp": {"port": 6000},
                },
                "database": {
                    "type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "password": "secret",
                },
                "features": {
                    "serena_mcp": {"use_in_prompts": True},
                    "git_integration": {"enabled": False},
                    "ssl_enabled": False,
                },
                "services": {"external_host": "10.1.0.164"},
                "health_monitoring": {
                    "enabled": True,
                    "timeouts": {"waiting_timeout": 2, "active_no_progress": 5},
                },
                "installation": {"version": "3.3.0"},
                "leaf_null": None,
            }
        ),
        encoding="utf-8",
    )
    # Suppress DB password validation (we're not testing DB connection)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DB_PASSWORD", "test")
        return ConfigManager(config_path=config_file)


@pytest.fixture
def empty_config(tmp_path):
    """ConfigManager with no config file (empty raw config)."""
    missing = tmp_path / "nonexistent.yaml"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DB_PASSWORD", "test")
        return ConfigManager(config_path=missing)


class TestGetNested:
    """Tests for ConfigManager.get_nested()."""

    def test_simple_key(self, config_with_data):
        """Top-level key returns its value."""
        result = config_with_data.get_nested("installation", {})
        assert isinstance(result, dict)
        assert result["version"] == "3.3.0"

    def test_nested_two_levels(self, config_with_data):
        """Two-level dotted key returns correct value."""
        assert config_with_data.get_nested("database.host") == "localhost"
        assert config_with_data.get_nested("database.port") == 5432

    def test_nested_three_levels(self, config_with_data):
        """Three-level dotted key returns correct value."""
        assert config_with_data.get_nested("server.api.port") == 7272
        assert config_with_data.get_nested("features.serena_mcp.use_in_prompts") is True
        assert config_with_data.get_nested("features.git_integration.enabled") is False

    def test_deeply_nested(self, config_with_data):
        """Deep nesting within health_monitoring."""
        assert config_with_data.get_nested("health_monitoring.timeouts.waiting_timeout") == 2
        assert config_with_data.get_nested("health_monitoring.timeouts.active_no_progress") == 5

    def test_missing_key_returns_default(self, config_with_data):
        """Completely missing key returns the provided default."""
        assert config_with_data.get_nested("nonexistent", "fallback") == "fallback"
        assert config_with_data.get_nested("nonexistent.deep.path", 42) == 42

    def test_missing_key_returns_none_by_default(self, config_with_data):
        """Missing key with no explicit default returns None."""
        assert config_with_data.get_nested("nonexistent") is None

    def test_partially_missing_path(self, config_with_data):
        """Path where an intermediate key is missing returns default."""
        assert config_with_data.get_nested("server.nonexistent", None) is None
        assert config_with_data.get_nested("features.serena_mcp.nonexistent_key", "nope") == "nope"

    def test_traversal_into_non_dict(self, config_with_data):
        """Trying to traverse deeper into a scalar value returns default."""
        # database.host is "localhost" (string), can't go deeper
        assert config_with_data.get_nested("database.host.deeper", "default") == "default"

    def test_empty_config_returns_default(self, empty_config):
        """When no config file exists, all keys return their defaults."""
        assert empty_config.get_nested("server.api.port", 7272) == 7272
        assert empty_config.get_nested("features.serena_mcp.use_in_prompts", False) is False
        assert empty_config.get_nested("anything", "fallback") == "fallback"

    def test_leaf_null_value_returned(self, config_with_data):
        """A YAML null value at a leaf is returned as None, not the default."""
        result = config_with_data.get_nested("leaf_null", "NOT_NONE")
        assert result is None

    def test_returns_sub_dict(self, config_with_data):
        """Requesting a non-leaf returns the sub-dict."""
        result = config_with_data.get_nested("health_monitoring.timeouts")
        assert isinstance(result, dict)
        assert result["waiting_timeout"] == 2

    def test_boolean_false_not_confused_with_missing(self, config_with_data):
        """Boolean False values are returned correctly (not treated as missing)."""
        assert config_with_data.get_nested("features.ssl_enabled") is False
        assert config_with_data.get_nested("features.git_integration.enabled") is False

    def test_services_external_host(self, config_with_data):
        """The services.external_host key used by downloads.py works."""
        assert config_with_data.get_nested("services.external_host", "localhost") == "10.1.0.164"

    def test_raw_config_refreshed_on_reload(self, tmp_path):
        """After reload(), get_nested() returns updated values."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.safe_dump({
                "database": {"type": "postgresql", "password": "p1"},
                "features": {"flag": "original"},
            }),
            encoding="utf-8",
        )
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("DB_PASSWORD", "test")
            mgr = ConfigManager(config_path=config_file)

        assert mgr.get_nested("features.flag") == "original"

        # Update file and reload
        config_file.write_text(
            yaml.safe_dump({
                "database": {"type": "postgresql", "password": "p1"},
                "features": {"flag": "updated"},
            }),
            encoding="utf-8",
        )
        mgr.reload()
        assert mgr.get_nested("features.flag") == "updated"
