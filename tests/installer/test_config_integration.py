"""
Integration test: Verify complete config.yaml generation includes cookie_domains
Tests the full generate_config_yaml() method to ensure cookie_domains is properly integrated
"""

import pytest
import yaml

from installer.core.config import ConfigManager


class TestConfigIntegration:
    """Integration tests for complete config.yaml generation"""

    def test_full_config_includes_cookie_domains(self, tmp_path):
        """Test that complete config.yaml includes cookie_domains field"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "giljo-test.local",
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        # Generate complete config
        result = manager.generate_config_yaml()

        assert result["success"] is True
        assert manager.config_file.exists()

        # Load and verify structure
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Verify all top-level sections exist
        required_sections = [
            "version",
            "deployment_context",
            "installation",
            "database",
            "server",
            "services",
            "features",
            "paths",
            "logging",
            "agent",
            "session",
            "message_queue",
            "status",
            "security",
        ]

        for section in required_sections:
            assert section in config, f"Missing section: {section}"

        # Verify security section structure
        assert "security" in config
        security = config["security"]

        assert "cors" in security
        assert "cookie_domains" in security  # NEW FIELD
        assert "api_keys" in security
        assert "rate_limiting" in security

        # Verify cookie_domains is a list
        assert isinstance(security["cookie_domains"], list)

        # Verify domain was added
        assert "giljo-test.local" in security["cookie_domains"]

    def test_config_yaml_structure_unchanged(self, tmp_path):
        """Test that adding cookie_domains doesn't break existing config structure"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Verify existing fields are unchanged
        assert config["version"] == "3.0.0"
        assert config["deployment_context"] == "localhost"
        assert config["database"]["host"] == "localhost"
        assert config["server"]["api_host"] == "0.0.0.0"

        # Verify CORS origins still work
        cors_origins = config["security"]["cors"]["allowed_origins"]
        assert "http://127.0.0.1:7274" in cors_origins
        assert "http://localhost:7274" in cors_origins

        # Verify cookie_domains is empty by default
        assert config["security"]["cookie_domains"] == []

    def test_validation_accepts_cookie_domains(self, tmp_path):
        """Test that config validation accepts cookie_domains field"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "test-server.local",
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        # Generate both files
        env_result = manager.generate_env_file()
        config_result = manager.generate_config_yaml()

        assert env_result["success"] is True
        assert config_result["success"] is True

        # Run validation
        validation_result = manager.validate_config()

        # Should validate successfully
        assert validation_result["valid"] is True
        assert len(validation_result["issues"]) == 0

    def test_cookie_domains_yaml_format(self, tmp_path):
        """Test that cookie_domains is properly formatted in YAML output"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "server1.example.com",
            "custom_domain": "server2.example.com",
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Read raw YAML text
        yaml_text = manager.config_file.read_text()

        # Verify cookie_domains appears in YAML
        assert "cookie_domains:" in yaml_text

        # Verify it's a valid YAML list
        assert "- server2.example.com" in yaml_text
        assert "- server1.example.com" in yaml_text

        # Load and verify parsed structure
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        cookie_domains = config["security"]["cookie_domains"]

        # Should contain both domains
        assert len(cookie_domains) == 2
        assert "server1.example.com" in cookie_domains
        assert "server2.example.com" in cookie_domains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
