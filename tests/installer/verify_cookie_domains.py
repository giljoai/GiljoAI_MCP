"""
Manual verification script for cookie_domains config generation
"""

import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml

from installer.core.config import ConfigManager


def test_scenario(name: str, settings: dict):
    """Test a specific scenario and print results"""
    print(f"\n{'=' * 70}")
    print(f"Scenario: {name}")
    print(f"{'=' * 70}")

    # Create temp paths
    tmp_path = Path("temp_config_test")
    tmp_path.mkdir(exist_ok=True)

    try:
        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.generate_config_yaml()

        if result["success"]:
            # Load and display cookie_domains
            with open(manager.config_file) as f:
                config = yaml.safe_load(f)

            cookie_domains = config["security"]["cookie_domains"]
            print("Settings:")
            print(f"  external_host: {settings.get('external_host', 'N/A')}")
            print(f"  custom_domain: {settings.get('custom_domain', 'N/A')}")
            print(f"\nGenerated cookie_domains: {cookie_domains}")
            print(f"  Type: {type(cookie_domains)}")
            print(f"  Length: {len(cookie_domains)}")
            print(f"  Empty: {len(cookie_domains) == 0}")

            # Display full security config
            print("\nFull security config:")
            print(yaml.dump(config["security"], default_flow_style=False, indent=2))

        else:
            print(f"FAILED: {result.get('errors', [])}")

    finally:
        # Cleanup
        if (tmp_path / "config.yaml").exists():
            (tmp_path / "config.yaml").unlink()
        if (tmp_path / ".env").exists():
            (tmp_path / ".env").unlink()
        tmp_path.rmdir()


if __name__ == "__main__":
    print("Cookie Domains Configuration Verification")
    print("=" * 70)

    # Scenario 1: Default (localhost only)
    test_scenario(
        "Default localhost installation",
        {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": "F:/GiljoAI_MCP",
            "owner_password": "test_pass",
            "user_password": "test_pass",
            "external_host": "localhost",
        },
    )

    # Scenario 2: LAN IP address
    test_scenario(
        "LAN IP address (should NOT add to cookie_domains)",
        {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": "F:/GiljoAI_MCP",
            "owner_password": "test_pass",
            "user_password": "test_pass",
            "external_host": "192.168.1.100",
        },
    )

    # Scenario 3: Domain name
    test_scenario(
        "Domain name (should add to cookie_domains)",
        {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": "F:/GiljoAI_MCP",
            "owner_password": "test_pass",
            "user_password": "test_pass",
            "external_host": "giljo-server.local",
        },
    )

    # Scenario 4: Custom domain
    test_scenario(
        "Custom domain via installer prompt",
        {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": "F:/GiljoAI_MCP",
            "owner_password": "test_pass",
            "user_password": "test_pass",
            "custom_domain": "my-server.example.com",
        },
    )

    # Scenario 5: Mixed (IP + domain)
    test_scenario(
        "Mixed: IP as external_host + custom domain",
        {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": "F:/GiljoAI_MCP",
            "owner_password": "test_pass",
            "user_password": "test_pass",
            "external_host": "10.1.0.50",  # IP - not added
            "custom_domain": "dev.giljo.local",  # Domain - added
        },
    )

    # Scenario 6: Both are domains
    test_scenario(
        "Both external_host and custom_domain are domain names",
        {
            "api_port": 7272,
            "dashboard_port": 7274,
            "pg_port": 5432,
            "install_dir": "F:/GiljoAI_MCP",
            "owner_password": "test_pass",
            "user_password": "test_pass",
            "external_host": "giljo.local",
            "custom_domain": "giljo-dev.example.com",
        },
    )

    print(f"\n{'=' * 70}")
    print("All scenarios completed successfully")
    print(f"{'=' * 70}\n")
