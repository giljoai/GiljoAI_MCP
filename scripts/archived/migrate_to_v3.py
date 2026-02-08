#!/usr/bin/env python3
"""
GiljoAI MCP v2.x → v3.0 Migration Script

This script migrates a v2.x installation to v3.0 architecture:
- Removes deployment mode (LOCAL/LAN/WAN)
- Implements unified authentication with auto-login
- Updates configuration to v3.0 format
- Creates localhost system user
- Preserves all user data

Usage:
    python scripts/migrate_to_v3.py
    python scripts/migrate_to_v3.py --config /path/to/config.yaml
    python scripts/migrate_to_v3.py --dry-run
    python scripts/migrate_to_v3.py --yes  # Skip confirmation
"""

import asyncio
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.config_manager import ConfigManager
from src.giljo_mcp.database import DatabaseManager


class MigrationScript:
    """v2.x → v3.0 migration orchestrator"""

    def __init__(self, config_path: Path, dry_run: bool = False):
        """
        Initialize migration script.

        Args:
            config_path: Path to config.yaml file
            dry_run: If True, preview changes without applying them
        """
        self.config_path = config_path
        self.dry_run = dry_run
        self.backup_dir = config_path.parent / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.old_mode: Optional[str] = None

    def run(self) -> bool:
        """
        Execute complete migration workflow.

        Returns:
            True if migration successful, False otherwise
        """
        click.echo("\n" + "=" * 60)
        click.echo("  GiljoAI MCP v2.x → v3.0 Migration")
        click.echo("=" * 60 + "\n")

        # Step 1: Detect version
        if not self.detect_v2_installation():
            click.echo("❌ No v2.x installation detected")
            return False

        # Step 2: Backup
        if not self.create_backup():
            click.echo("❌ Backup failed - aborting")
            return False

        # Step 3: Migrate config
        if not self.migrate_config():
            click.echo("❌ Config migration failed - aborting")
            return False

        # Step 4: Migrate database
        if not self.migrate_database():
            click.echo("❌ Database migration failed - aborting")
            return False

        # Step 5: Report
        self.print_report()

        return True

    def detect_v2_installation(self) -> bool:
        """
        Detect if this is a v2.x installation.

        Returns:
            True if v2.x detected, False otherwise
        """
        click.echo("🔍 Detecting installation version...")

        if not self.config_path.exists():
            click.echo(f"   Config not found: {self.config_path}")
            return False

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check for mode field (v2.x indicator)
        server_config = config.get("server", {})
        installation_config = config.get("installation", {})

        has_mode = "mode" in server_config or "mode" in installation_config

        # Check version
        version = config.get("version", "2.x")

        if has_mode or not version.startswith("3."):
            click.echo(f"   ✓ Detected v2.x installation (version: {version})")
            self.old_mode = server_config.get("mode") or installation_config.get("mode", "local")
            click.echo(f"   ✓ Current mode: {self.old_mode}")
            return True

        click.echo(f"   Already v3.0 (version: {version})")
        return False

    def create_backup(self) -> bool:
        """
        Create backup of current installation.

        Returns:
            True if backup successful, False otherwise
        """
        click.echo("\n💾 Creating backup...")

        if self.dry_run:
            click.echo("   [DRY RUN] Would create backup")
            return True

        try:
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup config.yaml
            backup_config = self.backup_dir / "config.yaml"
            shutil.copy2(self.config_path, backup_config)
            click.echo(f"   ✓ Config backed up: {backup_config}")

            # Backup .env if exists
            env_path = self.config_path.parent / ".env"
            if env_path.exists():
                backup_env = self.backup_dir / ".env"
                shutil.copy2(env_path, backup_env)
                click.echo(f"   ✓ .env backed up: {backup_env}")

            click.echo(f"\n   📁 Backup location: {self.backup_dir}")
            return True

        except Exception as e:
            click.echo(f"   ❌ Backup failed: {e}")
            return False

    def migrate_config(self) -> bool:
        """
        Migrate configuration to v3.0 format.

        Returns:
            True if migration successful, False otherwise
        """
        click.echo("\n⚙️  Migrating configuration...")

        if self.dry_run:
            click.echo("   [DRY RUN] Would migrate config")
            return True

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            # Remove mode field from both possible locations
            server_mode = config.get("server", {}).pop("mode", None)
            installation_mode = config.get("installation", {}).pop("mode", None)

            # Determine old mode (prefer server, then installation, then default)
            old_mode = server_mode or installation_mode or "local"

            # Store old mode if not already set
            if not self.old_mode:
                self.old_mode = old_mode

            # Add v3.0 fields
            config["version"] = "3.0.0"
            config["deployment_context"] = old_mode  # Informational

            # Ensure server binds to 0.0.0.0
            if "server" not in config:
                config["server"] = {}

            config["server"]["api_host"] = "0.0.0.0"
            config["server"]["dashboard_host"] = "0.0.0.0"
            config["server"]["mcp_host"] = "0.0.0.0"

            # Add features
            if "features" not in config:
                config["features"] = {}

            config["features"]["authentication"] = True
            config["features"]["auto_login_localhost"] = True
            config["features"]["firewall_configured"] = False

            # Save updated config
            with open(self.config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            click.echo(f"   ✓ Removed mode: {old_mode}")
            click.echo("   ✓ Added version: 3.0.0")
            click.echo("   ✓ Updated network binding: 0.0.0.0")
            click.echo("   ✓ Enabled features: authentication, auto_login_localhost")

            return True

        except Exception as e:
            click.echo(f"   ❌ Config migration failed: {e}")
            return False

    def migrate_database(self) -> bool:
        """
        Migrate database schema and create localhost user.

        Returns:
            True if migration successful, False otherwise
        """
        click.echo("\n🗄️  Migrating database...")

        if self.dry_run:
            click.echo("   [DRY RUN] Would migrate database")
            return True

        try:
            # Run Alembic migrations
            click.echo("   Running migrations...")
            result = subprocess.run(["alembic", "upgrade", "head"], check=False, capture_output=True, text=True)

            if result.returncode == 0:
                click.echo("   ✓ Migrations applied")
            else:
                click.echo(f"   ⚠ Migration warning: {result.stderr}")

            # Create localhost user
            click.echo("   Creating localhost user...")
            asyncio.run(self._create_localhost_user())

            return True

        except Exception as e:
            click.echo(f"   ❌ Database migration failed: {e}")
            return False

    async def _create_localhost_user(self) -> None:
        """Create localhost user (async helper)."""
        from src.giljo_mcp.auth.localhost_user import ensure_localhost_user

        config = ConfigManager()
        db_manager = DatabaseManager(database_url=config.database.url, is_async=True)

        try:
            async with db_manager.get_session_async() as session:
                user = await ensure_localhost_user(session)
                click.echo(f"   ✓ Localhost user: {user.username}")
                click.echo(f"   ✓ API Key: {user.api_key[:20]}...")
        finally:
            await db_manager.close_async()

    def print_report(self) -> None:
        """Print migration completion report."""
        click.echo("\n" + "=" * 60)
        click.echo("  ✅ Migration Complete!")
        click.echo("=" * 60)

        click.echo("\n📋 Summary:")
        click.echo(f"   • v2.x mode '{self.old_mode}' → v3.0 unified architecture")
        click.echo("   • Network binding: 0.0.0.0 (firewall controls access)")
        click.echo("   • Authentication: Always enabled")
        click.echo("   • Localhost auto-login: Enabled")

        click.echo("\n📁 Backup location:")
        click.echo(f"   {self.backup_dir}")

        click.echo("\n🔄 Rollback instructions:")
        click.echo(f"   cp {self.backup_dir}/config.yaml {self.config_path}")
        click.echo("   git checkout retired_multi_network_architecture")
        click.echo("   alembic downgrade -1")

        click.echo("\n📚 Documentation:")
        click.echo("   docs/MIGRATION_GUIDE_V3.md")
        click.echo("   docs/sessions/phase1_core_architecture_consolidation.md")

        click.echo("\n⚠️  Manual steps (if needed):")
        click.echo("   1. Configure OS firewall for localhost-only access")
        click.echo("   2. Restart GiljoAI MCP services")
        click.echo("   3. Test localhost access: http://127.0.0.1:7272")

        click.echo("\n" + "=" * 60 + "\n")


@click.command()
@click.option("--config", default="config.yaml", help="Path to config.yaml")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def main(config: str, dry_run: bool, yes: bool) -> None:
    """Migrate GiljoAI MCP from v2.x to v3.0"""
    config_path = Path(config)

    if not dry_run and not yes:
        click.confirm("\n⚠️  This will modify your installation. Continue?", abort=True)

    migration = MigrationScript(config_path, dry_run=dry_run)
    success = migration.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
