"""
Unit tests for Configuration Manager
"""

# Import the configuration system
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from tests.helpers.test_db_helper import PostgreSQLTestHelper


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.config.config_manager import (
        ConfigFormat,
        Configuration,
        ConfigurationManager,
        ConfigurationValue,
        generate_config_for_profile,
        validate_env_file,
    )

    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    pytest.skip("Configuration Manager not available", allow_module_level=True)


class TestConfigFormat:
    """Test ConfigFormat enum"""

    def test_config_format_values(self):
        """Test config format values"""
        assert ConfigFormat.ENV.value == ".env"
        assert ConfigFormat.YAML.value == "yaml"
        assert ConfigFormat.JSON.value == "json"
        assert ConfigFormat.INI.value == "ini"
        assert ConfigFormat.TOML.value == "toml"


class TestConfigurationValue:
    """Test ConfigurationValue dataclass"""

    def test_configuration_value_creation(self):
        """Test creating configuration value"""
        value = ConfigurationValue(
            key="DATABASE_URL",
            value="postgresql://user:pass@localhost/db",
            description="Database connection string",
            required=True,
            secret=True,
        )

        assert value.key == "DATABASE_URL"
        assert value.value == "postgresql://user:pass@localhost/db"
        assert value.description == "Database connection string"
        assert value.required
        assert value.secret

    def test_configuration_value_to_env_line(self):
        """Test converting value to .env line"""
        # Simple value
        value = ConfigurationValue(key="APP_NAME", value="GiljoAI_MCP", description="Application name")

        env_line = value.to_env_line()
        assert "# Application name" in env_line
        assert "APP_NAME=GiljoAI_MCP" in env_line

        # Boolean value
        bool_value = ConfigurationValue(key="DEBUG", value=True, description="Debug mode")

        bool_env_line = bool_value.to_env_line()
        assert "DEBUG=true" in bool_env_line

        # Secret value
        secret_value = ConfigurationValue(
            key="SECRET_KEY", value="supersecret123", description="Secret key", secret=True
        )

        secret_env_line = secret_value.to_env_line()
        assert "# Secret value (masked)" in secret_env_line
        assert "SECRET_KEY=supersecret123" in secret_env_line

    def test_configuration_value_with_spaces(self):
        """Test value with spaces gets quoted"""
        value = ConfigurationValue(key="DESCRIPTION", value="This has spaces", description="Description with spaces")

        env_line = value.to_env_line()
        assert 'DESCRIPTION="This has spaces"' in env_line

    def test_configuration_value_json_list(self):
        """Test JSON list value"""
        value = ConfigurationValue(
            key="CORS_ORIGINS", value=["http://localhost:3000", "http://localhost:8000"], description="CORS origins"
        )

        env_line = value.to_env_line()
        assert "CORS_ORIGINS=" in env_line
        assert "http://localhost:3000" in env_line


class TestConfiguration:
    """Test Configuration dataclass"""

    def test_configuration_creation(self):
        """Test creating configuration"""
        config = Configuration(profile_type="developer")

        assert config.profile_type == "developer"
        assert len(config.values) == 0
        assert config.version == "1.0.0"
        assert isinstance(config.created_at, datetime)

    def test_configuration_add_value(self):
        """Test adding configuration value"""
        config = Configuration(profile_type="team")

        config.add_value("APP_NAME", "GiljoAI_MCP", description="App name")
        config.add_value("DEBUG", False, description="Debug mode")

        assert len(config.values) == 2
        assert config.get_value("APP_NAME") == "GiljoAI_MCP"
        assert not config.get_value("DEBUG")

    def test_configuration_get_value_default(self):
        """Test getting value with default"""
        config = Configuration(profile_type="developer")

        # Non-existent key should return default
        assert config.get_value("MISSING_KEY", "default") == "default"
        assert config.get_value("MISSING_KEY") is None

    def test_configuration_to_dict(self):
        """Test converting configuration to dict"""
        config = Configuration(profile_type="enterprise")
        config.add_value("API_PORT", 8000)
        config.add_value("DEBUG", False)

        config_dict = config.to_dict()

        assert config_dict["profile_type"] == "enterprise"
        assert config_dict["values"]["API_PORT"] == 8000
        assert not config_dict["values"]["DEBUG"]
        assert "created_at" in config_dict

    def test_configuration_to_env(self):
        """Test converting configuration to .env format"""
        config = Configuration(profile_type="developer")
        config.add_value("APP_NAME", "GiljoAI_MCP", description="Application name")
        config.add_value("DEBUG", True, description="Debug mode")
        config.add_value("API_PORT", 8000, description="API port")

        env_content = config.to_env()

        assert "# GiljoAI MCP Configuration" in env_content
        assert "# Profile: developer" in env_content
        assert "APP_NAME=GiljoAI_MCP" in env_content
        assert "DEBUG=true" in env_content
        assert "API_PORT=8000" in env_content

    def test_configuration_categorization(self):
        """Test configuration categorization in .env output"""
        config = Configuration(profile_type="team")
        config.add_value("APP_NAME", "GiljoAI")
        config.add_value("DATABASE_URL", "postgresql://localhost/db")
        config.add_value("REDIS_URL", "redis://localhost:6379")
        config.add_value("API_PORT", 8000)

        env_content = config.to_env()

        # Should have category headers
        assert "============= APP Configuration =============" in env_content
        assert "============= DATABASE Configuration =============" in env_content
        assert "============= REDIS Configuration =============" in env_content
        assert "============= API Configuration =============" in env_content


class TestConfigurationManager:
    """Test ConfigurationManager class"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = ConfigurationManager(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_configuration_manager_initialization(self):
        """Test ConfigurationManager initialization"""
        manager = ConfigurationManager()
        assert manager is not None
        assert manager.config_dir.name == "config"

        # Test with custom path
        temp_dir = Path(tempfile.mkdtemp())
        manager = ConfigurationManager(temp_dir)
        assert manager.base_path == temp_dir
        assert manager.config_dir == temp_dir / "installer" / "config"

    def test_generate_developer_configuration(self):
        """Test generating developer configuration"""
        manager = ConfigurationManager()

        config = manager.generate_configuration("developer")

        assert config.profile_type == "developer"
        assert config.get_value("APP_ENV") == "development"
        assert config.get_value("DEBUG")
        assert config.get_value("DATABASE_TYPE") == "postgresql"  # Project standardized on PostgreSQL
        assert not config.get_value("AUTH_ENABLED")
        assert config.get_value("LOG_LEVEL") == "DEBUG"

    def test_generate_team_configuration(self):
        """Test generating team configuration"""
        manager = ConfigurationManager()

        user_inputs = {"team_name": "Alpha Team", "team_size": 10}

        connection_strings = {"postgresql": "postgresql://team_user:pass@localhost:5432/team_db"}

        config = manager.generate_configuration("team", user_inputs=user_inputs, connection_strings=connection_strings)

        assert config.profile_type == "team"
        assert config.get_value("APP_ENV") == "staging"
        assert not config.get_value("DEBUG")
        assert config.get_value("DATABASE_TYPE") == "postgresql"
        assert "postgresql://team_user" in config.get_value("DATABASE_URL")
        assert config.get_value("TEAM_NAME") == "Alpha Team"
        assert config.get_value("TEAM_SIZE") == 10
        assert config.get_value("AUTH_ENABLED")

    def test_generate_enterprise_configuration(self):
        """Test generating enterprise configuration"""
        manager = ConfigurationManager()

        user_inputs = {"enterprise_name": "MegaCorp", "compliance_mode": "HIPAA"}

        config = manager.generate_configuration("enterprise", user_inputs=user_inputs)

        assert config.profile_type == "enterprise"
        assert config.get_value("APP_ENV") == "production"
        assert config.get_value("SECURE_COOKIES")
        assert config.get_value("AUTH_METHOD") == "oauth"
        assert config.get_value("ENTERPRISE_NAME") == "MegaCorp"
        assert config.get_value("COMPLIANCE_MODE") == "HIPAA"
        assert config.get_value("AUDIT_LOGGING")

    def test_generate_research_configuration(self):
        """Test generating research configuration"""
        manager = ConfigurationManager()

        config = manager.generate_configuration("research")

        assert config.profile_type == "research"
        assert config.get_value("APP_ENV") == "research"
        assert config.get_value("EXPERIMENT_MODE")
        assert config.get_value("DATA_COLLECTION")
        assert not config.get_value("GPU_ENABLED")  # Default

    def test_configuration_with_connection_strings(self):
        """Test configuration with provided connection strings"""
        manager = ConfigurationManager()

        connection_strings = {
            "postgresql": "postgresql://user:pass@db.example.com:5432/proddb",
            "redis": "redis://:password@redis.example.com:6379/0",
        }

        config = manager.generate_configuration("team", connection_strings=connection_strings)

        assert config.get_value("DATABASE_URL") == connection_strings["postgresql"]
        assert config.get_value("REDIS_URL") == connection_strings["redis"]

    def test_secret_key_generation(self):
        """Test secret key generation"""
        manager = ConfigurationManager()

        key1 = manager._generate_secret_key()
        key2 = manager._generate_secret_key()

        # Should be different each time
        assert key1 != key2
        assert len(key1) > 20  # Should be reasonably long

        # Test custom length
        short_key = manager._generate_secret_key(16)
        assert len(short_key) >= 16

    def test_api_key_generation(self):
        """Test API key generation"""
        manager = ConfigurationManager()

        api_key = manager._generate_api_key()

        assert api_key.startswith("gjai_")
        assert len(api_key) > 20

    @patch("pathlib.Path.write_text")
    def test_save_configuration_env(self, mock_write):
        """Test saving configuration as .env"""
        manager = ConfigurationManager()

        config = Configuration(profile_type="developer")
        config.add_value("APP_NAME", "GiljoAI_MCP")
        config.add_value("DEBUG", True)

        manager.save_configuration(config, format=ConfigFormat.ENV)

        # Should have written the file
        mock_write.assert_called_once()
        written_content = mock_write.call_args[0][0]
        assert "APP_NAME=GiljoAI_MCP" in written_content
        assert "DEBUG=true" in written_content

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_dump")
    def test_save_configuration_yaml(self, mock_yaml_dump, mock_file):
        """Test saving configuration as YAML"""
        manager = ConfigurationManager()

        config = Configuration(profile_type="team")
        config.add_value("APP_NAME", "GiljoAI_MCP")

        manager.save_configuration(config, format=ConfigFormat.YAML)

        # Should have called yaml.safe_dump
        mock_yaml_dump.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_configuration_json(self, mock_json_dump, mock_file):
        """Test saving configuration as JSON"""
        manager = ConfigurationManager()

        config = Configuration(profile_type="enterprise")
        config.add_value("APP_NAME", "GiljoAI_MCP")

        manager.save_configuration(config, format=ConfigFormat.JSON)

        # Should have called json.dump
        mock_json_dump.assert_called_once()

    @patch("pathlib.Path.read_text")
    def test_load_env_configuration(self, mock_read):
        """Test loading .env configuration"""
        mock_read.return_value = """
# Test configuration
APP_NAME=GiljoAI_MCP
DEBUG=true
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
"""

        manager = ConfigurationManager()
        config = manager.load_configuration(Path("test.env"))

        assert config.get_value("APP_NAME") == "GiljoAI_MCP"
        assert config.get_value("DEBUG")
        assert config.get_value("API_PORT") == 8000

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_load_yaml_configuration(self, mock_yaml_load, mock_file):
        """Test loading YAML configuration"""
        mock_yaml_load.return_value = {"profile_type": "team", "values": {"APP_NAME": "GiljoAI_MCP", "DEBUG": False}}

        manager = ConfigurationManager()
        config = manager.load_configuration(Path("test.yaml"))

        assert config.profile_type == "team"
        assert config.get_value("APP_NAME") == "GiljoAI_MCP"
        assert not config.get_value("DEBUG")

    def test_validate_valid_configuration(self):
        """Test validating valid configuration"""
        manager = ConfigurationManager()

        config = Configuration(profile_type="developer")
        config.add_value("API_PORT", 8000)
        config.add_value("FRONTEND_PORT", 3000)
        config.add_value("DATABASE_URL", PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        config.add_value("LOG_LEVEL", "INFO")

        is_valid, errors = manager.validate_configuration(config)

        assert is_valid
        assert len(errors) == 0

    def test_validate_invalid_configuration(self):
        """Test validating invalid configuration"""
        manager = ConfigurationManager()

        config = Configuration(profile_type="test")
        config.add_value("API_PORT", 99999)  # Invalid port
        config.add_value("DATABASE_URL", "invalid://url")  # Invalid URL
        config.add_value("LOG_LEVEL", "INVALID")  # Invalid log level
        config.add_value("AUTH_ENABLED", True)
        config.add_value("AUTH_METHOD", "api_key")
        # Missing required API_KEY

        is_valid, errors = manager.validate_configuration(config)

        assert not is_valid
        assert len(errors) > 0

        # Check specific errors
        error_text = " ".join(errors)
        assert "API_PORT" in error_text
        assert "DATABASE_URL" in error_text
        assert "LOG_LEVEL" in error_text
        assert "API_KEY" in error_text

    def test_validate_auth_configuration(self):
        """Test validating authentication configuration"""
        manager = ConfigurationManager()

        # OAuth without required fields
        config = Configuration(profile_type="enterprise")
        config.add_value("AUTH_ENABLED", True)
        config.add_value("AUTH_METHOD", "oauth")
        # Missing OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET

        is_valid, errors = manager.validate_configuration(config)

        assert not is_valid
        assert any("OAUTH_CLIENT_ID" in error for error in errors)
        assert any("OAUTH_CLIENT_SECRET" in error for error in errors)

    @patch("shutil.copy2")
    @patch("pathlib.Path.exists", return_value=True)
    def test_backup_configuration(self, mock_exists, mock_copy):
        """Test configuration backup"""
        manager = ConfigurationManager()

        config_path = Path("test.env")
        backup_path = manager.backup_configuration(config_path)

        assert backup_path is not None
        assert "test_" in str(backup_path)
        mock_copy.assert_called_once()

    def test_diff_configurations(self):
        """Test comparing configurations"""
        manager = ConfigurationManager()

        # Create two configurations
        config1 = Configuration(profile_type="developer")
        config1.add_value("APP_NAME", "GiljoAI_MCP")
        config1.add_value("DEBUG", True)
        config1.add_value("API_PORT", 8000)

        config2 = Configuration(profile_type="team")
        config2.add_value("APP_NAME", "GiljoAI_MCP")  # Same
        config2.add_value("DEBUG", False)  # Changed
        config2.add_value("TEAM_NAME", "Alpha")  # Added
        # API_PORT removed

        diff = manager.diff_configurations(config1, config2)

        assert "TEAM_NAME" in diff["added"]
        assert "API_PORT" in diff["removed"]
        assert "DEBUG" in diff["modified"]
        assert diff["modified"]["DEBUG"]["old"]
        assert not diff["modified"]["DEBUG"]["new"]
        assert "APP_NAME" in diff["unchanged"]

    def test_migration_configuration(self):
        """Test configuration migration"""
        manager = ConfigurationManager()

        # Create old configuration
        old_config = Configuration(profile_type="developer")
        old_config.add_value("OLD_SETTING", "value")
        old_config.add_value("API_PORT", 9000)

        with patch.object(manager, "load_configuration", return_value=old_config):
            migrated = manager.migrate_configuration(Path("old_config.env"), new_profile="team")

        # Should be team profile but preserve custom port
        assert migrated.profile_type == "team"
        assert migrated.get_value("API_PORT") == 9000  # Preserved
        assert "migrated_from" in migrated.metadata

    def test_profile_defaults(self):
        """Test profile default values"""
        manager = ConfigurationManager()

        # Developer defaults (project standardized on PostgreSQL)
        dev_defaults = manager._get_profile_defaults("developer")
        assert dev_defaults["debug"]
        assert dev_defaults["database"] == "postgresql"  # Project standardized on PostgreSQL
        assert not dev_defaults["auth_enabled"]

        # Enterprise defaults
        ent_defaults = manager._get_profile_defaults("enterprise")
        assert not ent_defaults["debug"]
        assert ent_defaults["database"] == "postgresql"
        assert ent_defaults["auth_enabled"]
        assert ent_defaults["secure_cookies"]


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_generate_config_for_profile(self):
        """Test generate_config_for_profile function"""
        config = generate_config_for_profile("developer")

        assert config.profile_type == "developer"
        assert config.get_value("DEBUG")

        # With user inputs
        config_with_inputs = generate_config_for_profile("team", user_inputs={"team_name": "Test Team"})

        assert config_with_inputs.get_value("TEAM_NAME") == "Test Team"

    @patch("installer.config.config_manager.ConfigurationManager.load_configuration")
    @patch("installer.config.config_manager.ConfigurationManager.validate_configuration")
    def test_validate_env_file(self, mock_validate, mock_load):
        """Test validate_env_file function"""
        # Mock loading and validation
        mock_config = Configuration(profile_type="test")
        mock_load.return_value = mock_config
        mock_validate.return_value = (True, [])

        is_valid, errors = validate_env_file("test.env")

        assert is_valid
        assert len(errors) == 0
        mock_load.assert_called_once()
        mock_validate.assert_called_once()


# Pytest fixtures
@pytest.fixture
def config_manager():
    """Create ConfigurationManager for testing"""
    return ConfigurationManager()


@pytest.fixture
def sample_configuration():
    """Create sample configuration"""
    config = Configuration(profile_type="developer")
    config.add_value("APP_NAME", "GiljoAI_MCP")
    config.add_value("DEBUG", True)
    config.add_value("API_PORT", 8000)
    return config


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    import shutil

    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# Parameterized tests
@pytest.mark.parametrize(
    ("profile", "expected_debug"), [("developer", True), ("team", False), ("enterprise", False), ("research", True)]
)
def test_profile_debug_settings(config_manager, profile, expected_debug):
    """Test debug settings for different profiles"""
    config = config_manager.generate_configuration(profile)
    assert config.get_value("DEBUG") == expected_debug


@pytest.mark.parametrize(
    ("profile", "expected_db"),
    [("developer", "postgresql"), ("team", "postgresql"), ("enterprise", "postgresql"), ("research", "postgresql")],
)
def test_profile_database_settings(config_manager, profile, expected_db):
    """Test database settings for different profiles (project standardized on PostgreSQL)"""
    config = config_manager.generate_configuration(profile)
    assert config.get_value("DATABASE_TYPE") == expected_db


@pytest.mark.parametrize("port", [80, 443, 8000, 8080, 3000])
def test_valid_port_validation(config_manager, port):
    """Test valid port validation"""
    config = Configuration(profile_type="test")
    config.add_value("API_PORT", port)

    _is_valid, errors = config_manager.validate_configuration(config)
    # Should not have port-related errors
    port_errors = [e for e in errors if "API_PORT" in e]
    assert len(port_errors) == 0


@pytest.mark.parametrize("invalid_port", [-1, 0, 99999, "not_a_port"])
def test_invalid_port_validation(config_manager, invalid_port):
    """Test invalid port validation"""
    config = Configuration(profile_type="test")
    config.add_value("API_PORT", invalid_port)

    _is_valid, errors = config_manager.validate_configuration(config)
    # Should have port-related error
    port_errors = [e for e in errors if "API_PORT" in e]
    assert len(port_errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
