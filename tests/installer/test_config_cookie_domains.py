"""
Test cookie_domains field in config.yaml generation
Validates installer/core/config.py correctly adds cookie_domains to security config
"""

import pytest
import yaml

from installer.core.config import ConfigManager


class TestCookieDomains:
    """Test cookie_domains field generation in config.yaml"""

    def test_empty_cookie_domains_default(self, tmp_path):
        """Test cookie_domains is empty list by default (no custom domain)"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "localhost",  # localhost - not added
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load generated config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Verify cookie_domains exists and is empty
        assert "security" in config
        assert "cookie_domains" in config["security"]
        assert config["security"]["cookie_domains"] == []

    def test_cookie_domains_with_ip_address(self, tmp_path):
        """Test IPs are NOT added to cookie_domains (auto-allowed)"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "192.168.1.100",  # IP - should NOT be added
            "custom_domain": "10.1.0.50",  # IP - should NOT be added
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load generated config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # IPs should NOT be in cookie_domains
        assert config["security"]["cookie_domains"] == []

    def test_cookie_domains_with_domain_name(self, tmp_path):
        """Test domain names ARE added to cookie_domains"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "giljo.local",  # Domain - should be added
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load generated config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Domain should be in cookie_domains
        assert "giljo.local" in config["security"]["cookie_domains"]

    def test_cookie_domains_with_custom_domain(self, tmp_path):
        """Test custom_domain setting adds domain name"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "custom_domain": "my-server.example.com",  # Custom domain
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load generated config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Custom domain should be in cookie_domains
        assert "my-server.example.com" in config["security"]["cookie_domains"]

    def test_cookie_domains_no_duplicates(self, tmp_path):
        """Test duplicate domains are not added twice"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "giljo.local",  # Same domain
            "custom_domain": "giljo.local",  # Duplicate - should only appear once
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load generated config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Domain should appear only once
        cookie_domains = config["security"]["cookie_domains"]
        assert cookie_domains.count("giljo.local") == 1

    def test_cookie_domains_mixed_scenario(self, tmp_path):
        """Test realistic scenario with IPs and domain names"""
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
            "external_host": "192.168.1.100",  # IP - not added
            "custom_domain": "giljo-dev.local",  # Domain - added
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # Load generated config
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        # Only domain should be in list
        assert config["security"]["cookie_domains"] == ["giljo-dev.local"]

    def test_backwards_compatibility(self, tmp_path):
        """Test old configs without cookie_domains still work"""
        # Simulate old config.yaml without cookie_domains
        old_config = {
            "version": "3.0.0",
            "security": {
                "cors": {"allowed_origins": ["http://localhost:7274"]},
                "api_keys": {"info": "test"},
                "rate_limiting": {"enabled": True},
                # NO cookie_domains field (old config)
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(old_config, f)

        # Load and verify it doesn't crash
        with open(config_file) as f:
            loaded = yaml.safe_load(f)

        # Old config loads fine (no cookie_domains key)
        assert "security" in loaded
        assert "cookie_domains" not in loaded["security"]

        # Now regenerate with ConfigManager
        settings = {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": str(tmp_path),
            "owner_password": "test_owner_pass",
            "user_password": "test_user_pass",
        }

        manager = ConfigManager(settings)
        manager.config_file = config_file
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        assert result["success"] is True

        # New config has cookie_domains
        with open(config_file) as f:
            new_config = yaml.safe_load(f)

        assert "cookie_domains" in new_config["security"]
        assert new_config["security"]["cookie_domains"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
