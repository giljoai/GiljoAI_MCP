"""
Tests for the Settings configuration class.

Tests cover:
- Default settings initialization
- Environment variable overrides
- Database URL construction
- Directory creation
- Config file loading/saving
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.config_manager import ConfigManager, get_config


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def test_default_settings(self):
        """Test that default settings are properly initialized."""
        config = get_config()

        assert config.app_name == "GiljoAI MCP Coding Orchestrator"
        assert config.app_version == "0.1.0"
        assert config.debug is False
        assert config.database_type == "sqlite"
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 8000
        assert config.enable_multi_tenant is True
        assert config.vision_chunk_size == 50000
        assert config.vision_overlap == 500

    def test_path_settings(self):
        """Test that path settings use OS-neutral paths."""
        settings = Settings()

        # Verify paths are Path objects
        assert isinstance(settings.data_dir, Path)
        assert isinstance(settings.config_dir, Path)
        assert isinstance(settings.log_dir, Path)

        # Verify paths are under user home
        home = Path.home()
        assert str(settings.data_dir).startswith(str(home))
        assert str(settings.config_dir).startswith(str(home))
        assert str(settings.log_dir).startswith(str(home))

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://user:pass@host:5432/db",
            "DB_TYPE": "postgresql",
            "API_HOST": "0.0.0.0",
            "API_PORT": "9000",
            "API_KEY": "test-key-123",
        },
    )
    def test_environment_variable_override(self):
        """Test that environment variables override default settings."""
        settings = Settings()

        assert config.database_url == "postgresql://user:pass@host:5432/db"
        assert config.database_type == "postgresql"
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 9000
        assert config.api_key == "test-key-123"

    def test_sqlite_database_url(self):
        """Test SQLite database URL generation."""
        settings = Settings()
        db_url = settings.get_database_url()

        assert db_url.startswith("sqlite:///")
        assert "giljo_mcp.db" in db_url

    @patch.dict(
        os.environ,
        {
            "DB_TYPE": "postgresql",
            "DB_HOST": "postgres.example.com",
            "DB_PORT": "5433",
            "DB_NAME": "test_db",
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_pass",
        },
    )
    def test_postgresql_database_url(self):
        """Test PostgreSQL database URL generation from components."""
        settings = Settings()

        # Mock the DatabaseManager import
        with patch("giljo_mcp.config.DatabaseManager") as mock_db_manager:
            mock_db_manager.build_postgresql_url.return_value = (
                "postgresql://test_user:test_pass@postgres.example.com:5433/test_db"
            )

            settings.get_database_url()

            mock_db_manager.build_postgresql_url.assert_called_once_with(
                host="postgres.example.com", port=5433, database="test_db", username="test_user", password="test_pass"
            )

    def test_ensure_directories(self):
        """Test that required directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            settings = Settings(data_dir=tmp_path / "data", config_dir=tmp_path / "config", log_dir=tmp_path / "logs")

            # Directories should not exist initially
            assert not settings.data_dir.exists()
            assert not settings.config_dir.exists()
            assert not settings.log_dir.exists()

            # Create directories
            settings.ensure_directories()

            # Directories should now exist
            assert config.data_dir.exists()
            assert config.config_dir.exists()
            assert config.log_dir.exists()

    def test_load_config_file(self):
        """Test loading configuration from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_file = tmp_path / "config.yaml"

            # Create test config
            test_config = {
                "app_name": "Test App",
                "debug": True,
                "database": {"type": "postgresql", "host": "localhost"},
            }

            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            settings = Settings(config_dir=tmp_path)
            loaded_config = settings.load_config_file(config_file)

            assert loaded_config == test_config

    def test_load_missing_config_file(self):
        """Test loading when config file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            settings = Settings(config_dir=tmp_path)

            # Should return empty dict for missing file
            loaded_config = settings.load_config_file()
            assert loaded_config == {}

    def test_save_config_file(self):
        """Test saving configuration to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_file = tmp_path / "config.yaml"

            settings = Settings(config_dir=tmp_path)

            test_config = {"app_name": "Saved App", "debug": False, "api": {"host": "192.168.1.100", "port": 8080}}

            settings.save_config_file(test_config, config_file)

            # Verify file was created and contains correct data
            assert config_file.exists()

            with open(config_file) as f:
                loaded = yaml.safe_load(f)

            assert loaded == test_config

    def test_save_config_creates_directories(self):
        """Test that save_config_file creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            nested_config = tmp_path / "deep" / "nested" / "config.yaml"

            settings = Settings()
            settings.save_config_file({"test": "data"}, nested_config)

            assert nested_config.exists()
            assert nested_config.parent.exists()


class TestSettingsSingleton:
    """Test the singleton pattern for settings."""

    def test_get_settings_returns_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_set_settings_updates_singleton(self):
        """Test that set_settings updates the singleton instance."""
        original = get_settings()

        new_settings = Settings(app_name="Custom App")
        set_settings(new_settings)

        current = get_settings()
        assert current is new_settings
        assert current.app_name == "Custom App"

        # Restore original for other tests
        set_settings(original)

    @patch.dict(os.environ, {"DEBUG": "true"})
    def test_env_file_loading(self):
        """Test that .env file is loaded if present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            with open(env_file, "w") as f:
                f.write("API_KEY=from-env-file\n")
                f.write("API_PORT=7777\n")

            # Change to temp directory to load .env
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                settings = Settings()

                # Note: pydantic-settings would need to be configured
                # to load from .env file in the current directory
                # This test verifies the structure is in place
                assert hasattr(settings.Config, "env_file")
                assert config.Config.env_file == ".env"
            finally:
                os.chdir(original_cwd)


class TestSettingsValidation:
    """Test settings validation and edge cases."""

    def test_invalid_port_raises_error(self):
        """Test that invalid port numbers raise validation errors."""
        with pytest.raises(ValueError):
            Settings(api_port=-1)

        with pytest.raises(ValueError):
            Settings(api_port=99999)

    def test_database_type_validation(self):
        """Test database type is restricted to valid values."""
        settings = Settings(database_type="sqlite")
        assert config.database_type == "sqlite"

        settings = Settings(database_type="postgresql")
        assert config.database_type == "postgresql"

        # Should accept any string for now, but validation could be added
        settings = Settings(database_type="invalid")
        assert config.database_type == "invalid"

    def test_vision_settings_validation(self):
        """Test vision document settings validation."""
        settings = Settings(vision_chunk_size=100000, vision_overlap=1000)

        assert config.vision_chunk_size == 100000
        assert config.vision_overlap == 1000

        # Test negative values (should be prevented in real implementation)
        with pytest.raises(ValueError):
            Settings(vision_chunk_size=-1)

        with pytest.raises(ValueError):
            Settings(vision_overlap=-100)
