"""
Example: PostgreSQL Network Configuration for Server Mode

This example demonstrates how to use the DatabaseNetworkConfig module
to enable remote database access for GiljoAI MCP server mode deployment.
"""

import logging
import sys
from pathlib import Path


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from installer.core.database import DatabaseInstaller
from installer.core.database_network import DatabaseNetworkConfig


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def example_localhost_mode():
    """Example: Localhost mode (Phase 1) - no network configuration"""
    print("\n" + "=" * 60)
    print("Example 1: Localhost Mode (Phase 1)")
    print("=" * 60)
    print()

    settings = {
        "pg_host": "localhost",
        "pg_port": 5432,
        "pg_user": "postgres",
        "pg_password": "your_postgres_password",
        "mode": "localhost",  # Localhost mode
        "batch": False,  # Interactive mode
    }

    # Phase 1: Create database locally
    db_installer = DatabaseInstaller(settings)
    result = db_installer.setup()

    if result["success"]:
        print("\nDatabase created successfully!")
        print(f"Credentials saved to: {result.get('credentials_file')}")
        print("\nDatabase is accessible from localhost only.")
    else:
        print("\nDatabase setup failed:")
        for error in result.get("errors", []):
            print(f"  - {error}")

    return result


def example_server_mode_basic():
    """Example: Server mode with basic network access"""
    print("\n" + "=" * 60)
    print("Example 2: Server Mode - Basic Network Access")
    print("=" * 60)
    print()

    settings = {
        "pg_host": "localhost",
        "pg_port": 5432,
        "pg_user": "postgres",
        "pg_password": "your_postgres_password",
        "mode": "server",  # Server mode
        "bind": "0.0.0.0",  # Bind to all interfaces
        "ssl_enabled": False,  # SSL not enabled (not recommended)
        "batch": False,  # Interactive mode
    }

    # Phase 1: Create database locally
    print("Step 1: Creating database...")
    db_installer = DatabaseInstaller(settings)
    db_result = db_installer.setup()

    if not db_result["success"]:
        print("\nDatabase setup failed:")
        for error in db_result.get("errors", []):
            print(f"  - {error}")
        return db_result

    print("\nDatabase created successfully!")

    # Phase 2: Enable remote access
    print("\nStep 2: Enabling remote access...")
    network_config = DatabaseNetworkConfig(settings)
    network_result = network_config.setup_remote_access()

    if network_result["success"]:
        print("\nRemote access configured successfully!")
        print(f"\nBackup directory: {network_result.get('backup_dir')}")
        print(f"Restore scripts: {network_result.get('restore_scripts')}")

        if network_result.get("restart_completed"):
            print("\nPostgreSQL restarted successfully.")
            print("Remote database access is now active.")
        else:
            print("\nWARNING: PostgreSQL restart required!")
            print("Remote access will not work until PostgreSQL is restarted.")

        # Show connection string
        user_password = db_result.get("credentials", {}).get("user_password")
        if user_password:
            conn_string = f"postgresql://giljo_user:{user_password}@YOUR_SERVER_IP:5432/giljo_mcp"
            print("\nRemote connection string:")
            print(f"  {conn_string}")
            print("\nReplace YOUR_SERVER_IP with your server's actual IP address.")

    else:
        print("\nRemote access setup failed:")
        for error in network_result.get("errors", []):
            print(f"  - {error}")

    return network_result


def example_server_mode_ssl():
    """Example: Server mode with SSL enforcement"""
    print("\n" + "=" * 60)
    print("Example 3: Server Mode - SSL Enforced (Recommended)")
    print("=" * 60)
    print()

    settings = {
        "pg_host": "localhost",
        "pg_port": 5432,
        "pg_user": "postgres",
        "pg_password": "your_postgres_password",
        "mode": "server",
        "bind": "0.0.0.0",
        "ssl_enabled": True,  # SSL required
        "batch": False,
    }

    # Phase 1: Create database
    print("Step 1: Creating database...")
    db_installer = DatabaseInstaller(settings)
    db_result = db_installer.setup()

    if not db_result["success"]:
        print("\nDatabase setup failed:")
        for error in db_result.get("errors", []):
            print(f"  - {error}")
        return db_result

    # Phase 2: Enable remote access with SSL
    print("\nStep 2: Enabling remote access with SSL...")
    network_config = DatabaseNetworkConfig(settings)
    network_result = network_config.setup_remote_access()

    if network_result["success"]:
        print("\nRemote access configured with SSL!")
        print("\nSecurity features enabled:")
        print("  - SSL/TLS encryption required")
        print("  - Strong authentication (scram-sha-256)")
        print("  - Private network ranges only")

        # Show SSL connection string
        user_password = db_result.get("credentials", {}).get("user_password")
        if user_password:
            conn_string = f"postgresql://giljo_user:{user_password}@YOUR_SERVER_IP:5432/giljo_mcp?sslmode=require"
            print("\nRemote connection string (SSL):")
            print(f"  {conn_string}")

    return network_result


def example_server_mode_restricted():
    """Example: Server mode with restricted network access"""
    print("\n" + "=" * 60)
    print("Example 4: Server Mode - Restricted Network Access")
    print("=" * 60)
    print()

    settings = {
        "pg_host": "localhost",
        "pg_port": 5432,
        "pg_user": "postgres",
        "pg_password": "your_postgres_password",
        "mode": "server",
        "bind": "192.168.1.10",  # Specific interface
        "ssl_enabled": True,
        "allowed_networks": [
            "192.168.1.0/24",  # Only local subnet
        ],
        "batch": False,
    }

    print("Configuration:")
    print(f"  Bind address: {settings['bind']}")
    print(f"  Allowed networks: {settings['allowed_networks']}")
    print(f"  SSL enabled: {settings['ssl_enabled']}")
    print()

    # Phase 1: Create database
    db_installer = DatabaseInstaller(settings)
    db_result = db_installer.setup()

    if not db_result["success"]:
        return db_result

    # Phase 2: Enable restricted remote access
    network_config = DatabaseNetworkConfig(settings)
    network_result = network_config.setup_remote_access()

    if network_result["success"]:
        print("\nRemote access configured with restrictions!")
        print("\nSecurity posture:")
        print("  - Specific interface binding")
        print("  - Single subnet allowed")
        print("  - SSL required")
        print("  - Strong authentication")

    return network_result


def example_restore_configuration():
    """Example: Restore original PostgreSQL configuration"""
    print("\n" + "=" * 60)
    print("Example 5: Restore Original Configuration")
    print("=" * 60)
    print()

    print("To restore PostgreSQL to localhost-only mode:")
    print()
    print("Windows:")
    print("  1. Open PowerShell as Administrator")
    print("  2. Navigate to installer/scripts/")
    print("  3. Run: .\\restore_pg_config.ps1")
    print()
    print("Linux/macOS:")
    print("  1. Open terminal")
    print("  2. Navigate to installer/scripts/")
    print("  3. Run: sudo bash restore_pg_config.sh")
    print()
    print("The restoration scripts will:")
    print("  - Stop PostgreSQL service")
    print("  - Restore original configuration files")
    print("  - Create pre-restoration backup (safety)")
    print("  - Restart PostgreSQL service")
    print()


def example_batch_mode():
    """Example: Batch mode (non-interactive) deployment"""
    print("\n" + "=" * 60)
    print("Example 6: Batch Mode Deployment")
    print("=" * 60)
    print()

    settings = {
        "pg_host": "localhost",
        "pg_port": 5432,
        "pg_user": "postgres",
        "pg_password": "your_postgres_password",
        "mode": "server",
        "bind": "0.0.0.0",
        "ssl_enabled": True,
        "batch": True,  # Batch mode - no interactive prompts
    }

    print("Batch mode: All confirmations are automatic")
    print()

    # Phase 1: Database creation
    db_installer = DatabaseInstaller(settings)
    db_result = db_installer.setup()

    # Phase 2: Network configuration
    network_config = DatabaseNetworkConfig(settings)
    network_result = network_config.setup_remote_access()

    # Results
    if db_result["success"] and network_result["success"]:
        print("\nBatch deployment completed successfully!")
        print("\nIMPORTANT: PostgreSQL restart may be required manually.")
        print(f"Backup directory: {network_result.get('backup_dir')}")
    else:
        print("\nBatch deployment encountered errors:")
        for error in db_result.get("errors", []) + network_result.get("errors", []):
            print(f"  - {error}")

    return network_result


def example_testing_connectivity():
    """Example: Test remote database connectivity"""
    print("\n" + "=" * 60)
    print("Example 7: Testing Remote Database Connectivity")
    print("=" * 60)
    print()

    print("After configuring remote access, test connectivity:")
    print()
    print("From remote client:")
    print()
    print("  psql -h YOUR_SERVER_IP -U giljo_user -d giljo_mcp")
    print()
    print("Or with Python:")
    print()
    print("  import psycopg2")
    print("  conn = psycopg2.connect(")
    print("      host='YOUR_SERVER_IP',")
    print("      port=5432,")
    print("      database='giljo_mcp',")
    print("      user='giljo_user',")
    print("      password='YOUR_PASSWORD'")
    print("  )")
    print("  print('Connected successfully!')")
    print("  conn.close()")
    print()
    print("Troubleshooting:")
    print("  1. Verify PostgreSQL was restarted")
    print("  2. Check firewall allows port 5432")
    print("  3. Confirm client IP is in allowed networks")
    print("  4. Review PostgreSQL logs for connection attempts")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("GiljoAI MCP - Database Network Configuration Examples")
    print("=" * 60)

    print("\nThese examples demonstrate PostgreSQL network configuration")
    print("for server mode deployment.")
    print()
    print("WARNING: These examples use placeholder passwords.")
    print("         Replace with actual credentials before running.")
    print()

    # Show examples (descriptions only, don't actually run)
    example_localhost_mode()  # Would fail without actual PostgreSQL
    example_server_mode_basic()
    example_server_mode_ssl()
    example_server_mode_restricted()
    example_restore_configuration()
    example_batch_mode()
    example_testing_connectivity()

    print("\n" + "=" * 60)
    print("Examples Complete")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review the examples above")
    print("  2. Update settings with your PostgreSQL credentials")
    print("  3. Choose appropriate mode (localhost or server)")
    print("  4. Run the installer with your configuration")
    print()


if __name__ == "__main__":
    # Note: This is a demonstration script
    # Actual usage would require valid PostgreSQL credentials
    print("=" * 60)
    print("Database Network Configuration - Usage Examples")
    print("=" * 60)
    print()
    print("This script demonstrates how to use the database network module.")
    print("To see the examples, review the code in this file.")
    print()
    print("Available examples:")
    print("  - example_localhost_mode()")
    print("  - example_server_mode_basic()")
    print("  - example_server_mode_ssl()")
    print("  - example_server_mode_restricted()")
    print("  - example_restore_configuration()")
    print("  - example_batch_mode()")
    print("  - example_testing_connectivity()")
    print()
    print("To run an example, uncomment the desired function call below.")
    print()

    # Uncomment to run specific example:
    # example_server_mode_ssl()
