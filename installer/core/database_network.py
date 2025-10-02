"""
PostgreSQL Network Configuration for Server Mode
Handles remote access setup, pg_hba.conf, and postgresql.conf modifications

This module extends the local database setup to enable network access:
- PostgreSQL remote access configuration
- pg_hba.conf modifications for network clients
- postgresql.conf listen_addresses setup
- Connection pooling optimization
- Backup and restoration capabilities
- Security-first approach with explicit consent
"""

import os
import sys
import platform
import subprocess
import shutil
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class DatabaseNetworkConfig:
    """Configure PostgreSQL for network access in server mode"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.pg_host = settings.get('pg_host', 'localhost')
        self.pg_port = settings.get('pg_port', 5432)
        self.db_name = 'giljo_mcp'
        self.logger = logging.getLogger(self.__class__.__name__)

        # Network configuration
        self.bind_address = settings.get('bind', '0.0.0.0')
        self.allow_ssl_only = settings.get('ssl_enabled', False)
        self.allowed_networks = settings.get('allowed_networks', [
            '192.168.0.0/16',  # Private network range
            '10.0.0.0/8',       # Private network range
            '172.16.0.0/12'     # Private network range
        ])

        # PostgreSQL configuration paths
        self.pg_config_dir = None
        self.postgresql_conf = None
        self.pg_hba_conf = None

        # Backup tracking
        self.backup_dir = None
        self.backups_created = []

    def setup_remote_access(self) -> Dict[str, Any]:
        """Main workflow for enabling remote database access"""
        result = {'success': False, 'errors': [], 'warnings': [], 'backups': []}

        try:
            # Security check - explicit consent required
            if not self._confirm_network_exposure():
                result['errors'].append("User declined network exposure - server mode requires remote database access")
                return result

            # Find PostgreSQL configuration directory
            self.logger.info("Locating PostgreSQL configuration files...")
            config_result = self.find_pg_config_dir()
            if not config_result['success']:
                result['errors'].extend(config_result['errors'])
                return result

            self.pg_config_dir = Path(config_result['config_dir'])
            self.postgresql_conf = self.pg_config_dir / 'postgresql.conf'
            self.pg_hba_conf = self.pg_config_dir / 'pg_hba.conf'

            self.logger.info(f"PostgreSQL config directory: {self.pg_config_dir}")

            # Verify configuration files exist
            if not self.postgresql_conf.exists():
                result['errors'].append(f"postgresql.conf not found at {self.postgresql_conf}")
                return result

            if not self.pg_hba_conf.exists():
                result['errors'].append(f"pg_hba.conf not found at {self.pg_hba_conf}")
                return result

            # Create backup directory
            self.backup_dir = Path("installer/backups/postgresql") / datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Backup directory: {self.backup_dir}")

            # Backup existing configurations
            self.logger.info("Backing up PostgreSQL configuration files...")
            backup_result = self.backup_configs()
            if not backup_result['success']:
                result['errors'].extend(backup_result['errors'])
                return result

            result['backups'] = backup_result['backups']
            self.backups_created = backup_result['backups']

            # Modify postgresql.conf for network listening
            self.logger.info("Configuring postgresql.conf for network access...")
            postgresql_result = self.configure_postgresql_conf()
            if not postgresql_result['success']:
                result['errors'].extend(postgresql_result['errors'])
                # Restore backups on failure
                self.restore_configs()
                return result

            # Modify pg_hba.conf for client authentication
            self.logger.info("Configuring pg_hba.conf for network clients...")
            hba_result = self.configure_pg_hba_conf()
            if not hba_result['success']:
                result['errors'].extend(hba_result['errors'])
                # Restore backups on failure
                self.restore_configs()
                return result

            result['warnings'].extend(hba_result.get('warnings', []))

            # Generate restoration scripts
            self.logger.info("Generating restoration scripts...")
            restore_result = self.generate_restore_scripts()
            if restore_result['success']:
                result['restore_scripts'] = restore_result['scripts']

            # Prompt for PostgreSQL restart
            restart_result = self.prompt_postgresql_restart()
            result['restart_required'] = restart_result['restart_required']
            result['restart_completed'] = restart_result.get('restart_completed', False)

            if not restart_result.get('restart_completed', False):
                result['warnings'].append(
                    "PostgreSQL restart required for changes to take effect. "
                    "Remote database access will not work until PostgreSQL is restarted."
                )

            result['success'] = True
            result['config_dir'] = str(self.pg_config_dir)
            result['backup_dir'] = str(self.backup_dir)

            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Remote access setup failed: {e}", exc_info=True)
            # Attempt to restore backups
            if self.backups_created:
                self.restore_configs()
            return result

    def _confirm_network_exposure(self) -> bool:
        """Require explicit user consent for network exposure"""
        # In batch mode, assume consent if server mode is selected
        if self.settings.get('batch'):
            return True

        print("\n" + "="*60)
        print("SECURITY WARNING: Network Database Access")
        print("="*60)
        print()
        print("You are about to configure PostgreSQL for network access.")
        print("This will allow remote clients to connect to your database.")
        print()
        print("Security implications:")
        print("  - Database will accept connections from network clients")
        print("  - Firewall rules may need adjustment")
        print("  - Strong passwords are essential")
        if self.allow_ssl_only:
            print("  - SSL connections will be required (RECOMMENDED)")
        else:
            print("  - WARNING: SSL not enabled - passwords sent in clear text!")
        print()
        print("The following networks will be allowed:")
        for network in self.allowed_networks:
            print(f"  - {network}")
        print()

        response = input("Do you want to proceed with network access setup? (yes/no): ")
        return response.lower() in ['yes', 'y']

    def find_pg_config_dir(self) -> Dict[str, Any]:
        """Locate PostgreSQL configuration directory"""
        result = {'success': False, 'errors': []}

        try:
            system = platform.system()
            candidate_paths = []

            if system == "Windows":
                # Common Windows PostgreSQL installation paths
                candidate_paths = [
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'PostgreSQL' / '18' / 'data',
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'PostgreSQL' / '17' / 'data',
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'PostgreSQL' / '16' / 'data',
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'PostgreSQL' / '15' / 'data',
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'PostgreSQL' / '14' / 'data',
                    Path('C:\\PostgreSQL\\data'),
                ]
            elif system == "Darwin":  # macOS
                candidate_paths = [
                    Path('/usr/local/var/postgres'),
                    Path('/opt/homebrew/var/postgres'),
                    Path('/Library/PostgreSQL/18/data'),
                    Path('/Library/PostgreSQL/17/data'),
                    Path('/Library/PostgreSQL/16/data'),
                    Path('/Library/PostgreSQL/15/data'),
                    Path('/Library/PostgreSQL/14/data'),
                ]
            else:  # Linux
                candidate_paths = [
                    Path('/etc/postgresql/18/main'),
                    Path('/etc/postgresql/17/main'),
                    Path('/etc/postgresql/16/main'),
                    Path('/etc/postgresql/15/main'),
                    Path('/etc/postgresql/14/main'),
                    Path('/var/lib/pgsql/18/data'),
                    Path('/var/lib/pgsql/17/data'),
                    Path('/var/lib/pgsql/16/data'),
                    Path('/var/lib/pgsql/15/data'),
                    Path('/var/lib/pgsql/14/data'),
                    Path('/var/lib/postgresql/data'),
                ]

            # Try to use pg_config to find the data directory
            try:
                pg_result = subprocess.run(
                    ['psql', '-U', 'postgres', '-t', '-c', 'SHOW data_directory;'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if pg_result.returncode == 0:
                    data_dir = pg_result.stdout.strip()
                    if data_dir:
                        candidate_paths.insert(0, Path(data_dir))
            except Exception:
                pass

            # Check each candidate path
            for path in candidate_paths:
                if path.exists() and (path / 'postgresql.conf').exists():
                    result['success'] = True
                    result['config_dir'] = str(path)
                    return result

            # Not found
            result['errors'].append(
                "PostgreSQL configuration directory not found. "
                "Please provide the path to the PostgreSQL data directory containing postgresql.conf"
            )

            # Suggest manual configuration
            result['manual_config_required'] = True
            result['guide'] = self._get_manual_config_guide()

            return result

        except Exception as e:
            result['errors'].append(f"Error finding PostgreSQL config: {e}")
            return result

    def backup_configs(self) -> Dict[str, Any]:
        """Backup PostgreSQL configuration files"""
        result = {'success': False, 'errors': [], 'backups': []}

        try:
            # Backup postgresql.conf
            postgresql_backup = self.backup_dir / 'postgresql.conf'
            shutil.copy2(self.postgresql_conf, postgresql_backup)
            result['backups'].append({
                'original': str(self.postgresql_conf),
                'backup': str(postgresql_backup)
            })
            self.logger.info(f"Backed up postgresql.conf to {postgresql_backup}")

            # Backup pg_hba.conf
            hba_backup = self.backup_dir / 'pg_hba.conf'
            shutil.copy2(self.pg_hba_conf, hba_backup)
            result['backups'].append({
                'original': str(self.pg_hba_conf),
                'backup': str(hba_backup)
            })
            self.logger.info(f"Backed up pg_hba.conf to {hba_backup}")

            # Create a README in backup directory
            readme = self.backup_dir / 'README.txt'
            readme_content = f"""PostgreSQL Configuration Backup
Created: {datetime.now().isoformat()}

This directory contains backups of PostgreSQL configuration files
before GiljoAI MCP server mode modifications.

Original files:
- {self.postgresql_conf}
- {self.pg_hba_conf}

To restore these configurations:
1. Stop PostgreSQL service
2. Copy backup files to original locations
3. Restart PostgreSQL service

Or use the generated restoration scripts:
- restore_pg_config.ps1 (Windows)
- restore_pg_config.sh (Linux/macOS)
"""
            readme.write_text(readme_content)

            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(f"Backup failed: {e}")
            self.logger.error(f"Configuration backup failed: {e}", exc_info=True)
            return result

    def configure_postgresql_conf(self) -> Dict[str, Any]:
        """Modify postgresql.conf to enable network listening"""
        result = {'success': False, 'errors': []}

        try:
            # Read current configuration
            with open(self.postgresql_conf, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Track if we found and modified listen_addresses
            found_listen_addresses = False
            modified_lines = []

            for line in lines:
                stripped = line.strip()

                # Check for listen_addresses setting
                if stripped.startswith('listen_addresses'):
                    # Comment out the original
                    if not line.startswith('#'):
                        modified_lines.append(f"# {line}")
                    else:
                        modified_lines.append(line)
                    found_listen_addresses = True
                else:
                    modified_lines.append(line)

            # Add GiljoAI MCP configuration section
            modified_lines.append("\n")
            modified_lines.append("# ============================================================\n")
            modified_lines.append("# GiljoAI MCP Server Mode Configuration\n")
            modified_lines.append(f"# Added: {datetime.now().isoformat()}\n")
            modified_lines.append("# ============================================================\n")
            modified_lines.append("\n")

            # Configure listen_addresses
            if self.bind_address == '0.0.0.0':
                modified_lines.append("# Listen on all network interfaces\n")
                modified_lines.append("listen_addresses = '*'\n")
            else:
                modified_lines.append(f"# Listen on specific address: {self.bind_address}\n")
                modified_lines.append(f"listen_addresses = 'localhost,{self.bind_address}'\n")

            modified_lines.append("\n")

            # Connection pooling and performance settings
            modified_lines.append("# Connection settings for server mode\n")
            modified_lines.append("max_connections = 100\n")
            modified_lines.append("shared_buffers = 256MB\n")
            modified_lines.append("effective_cache_size = 1GB\n")
            modified_lines.append("\n")

            # Write modified configuration
            with open(self.postgresql_conf, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

            self.logger.info(f"Modified postgresql.conf - listen_addresses set to network mode")
            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(f"Failed to modify postgresql.conf: {e}")
            self.logger.error(f"postgresql.conf modification failed: {e}", exc_info=True)
            return result

    def configure_pg_hba_conf(self) -> Dict[str, Any]:
        """Modify pg_hba.conf to allow network client authentication"""
        result = {'success': False, 'errors': [], 'warnings': []}

        try:
            # Read current configuration
            with open(self.pg_hba_conf, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Add GiljoAI MCP configuration section at the end
            lines.append("\n")
            lines.append("# ============================================================\n")
            lines.append("# GiljoAI MCP Server Mode - Network Access Rules\n")
            lines.append(f"# Added: {datetime.now().isoformat()}\n")
            lines.append("# ============================================================\n")
            lines.append("\n")

            # Determine authentication method
            auth_method = 'scram-sha-256'  # Most secure for PostgreSQL 14+

            # Add rules for each allowed network
            for network in self.allowed_networks:
                lines.append(f"# Allow connections from {network}\n")

                if self.allow_ssl_only:
                    # SSL-only connections (most secure)
                    lines.append(f"hostssl    {self.db_name}    giljo_user    {network}    {auth_method}\n")
                    lines.append(f"hostssl    {self.db_name}    giljo_owner   {network}    {auth_method}\n")
                else:
                    # Regular TCP connections
                    lines.append(f"host       {self.db_name}    giljo_user    {network}    {auth_method}\n")
                    lines.append(f"host       {self.db_name}    giljo_owner   {network}    {auth_method}\n")
                    result['warnings'].append(
                        f"WARNING: Allowing non-SSL connections from {network}. "
                        "Passwords will be transmitted in clear text unless SSL is used."
                    )

                lines.append("\n")

            # Security notice
            lines.append("# SECURITY NOTES:\n")
            lines.append(f"# - Authentication method: {auth_method}\n")
            if self.allow_ssl_only:
                lines.append("# - SSL required: YES (recommended)\n")
            else:
                lines.append("# - SSL required: NO (consider enabling for production)\n")
            lines.append("# - Ensure strong passwords are used for all roles\n")
            lines.append("# - Adjust network ranges as needed for your environment\n")
            lines.append("# - Firewall rules must allow PostgreSQL port (5432) traffic\n")
            lines.append("\n")

            # Write modified configuration
            with open(self.pg_hba_conf, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            self.logger.info(f"Modified pg_hba.conf - added network access rules for {len(self.allowed_networks)} networks")
            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(f"Failed to modify pg_hba.conf: {e}")
            self.logger.error(f"pg_hba.conf modification failed: {e}", exc_info=True)
            return result

    def restore_configs(self) -> Dict[str, Any]:
        """Restore PostgreSQL configurations from backup"""
        result = {'success': False, 'errors': []}

        try:
            if not self.backups_created:
                result['errors'].append("No backups available to restore")
                return result

            for backup in self.backups_created:
                original = Path(backup['original'])
                backup_file = Path(backup['backup'])

                if backup_file.exists():
                    shutil.copy2(backup_file, original)
                    self.logger.info(f"Restored {original} from backup")
                else:
                    result['errors'].append(f"Backup file not found: {backup_file}")

            if not result['errors']:
                result['success'] = True
                self.logger.info("All configurations restored from backup")

            return result

        except Exception as e:
            result['errors'].append(f"Restore failed: {e}")
            self.logger.error(f"Configuration restore failed: {e}", exc_info=True)
            return result

    def generate_restore_scripts(self) -> Dict[str, Any]:
        """Generate platform-specific restoration scripts"""
        result = {'success': False, 'errors': [], 'scripts': []}

        try:
            scripts_dir = Path("installer/scripts")
            scripts_dir.mkdir(parents=True, exist_ok=True)

            # Generate Windows PowerShell script
            windows_script = self._generate_windows_restore_script(scripts_dir)
            if windows_script:
                result['scripts'].append(str(windows_script))

            # Generate Unix shell script
            unix_script = self._generate_unix_restore_script(scripts_dir)
            if unix_script:
                result['scripts'].append(str(unix_script))

            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(f"Failed to generate restore scripts: {e}")
            return result

    def _generate_windows_restore_script(self, scripts_dir: Path) -> Optional[Path]:
        """Generate Windows PowerShell restoration script"""
        script_path = scripts_dir / "restore_pg_config.ps1"

        script_content = f'''# GiljoAI MCP PostgreSQL Configuration Restoration Script
# Generated: {datetime.now().isoformat()}
#
# This script restores PostgreSQL configuration files to their state
# before GiljoAI MCP server mode modifications.

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "   GiljoAI MCP - PostgreSQL Configuration Restoration" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$BackupDir = "{self.backup_dir.as_posix()}"
$ConfigDir = "{self.pg_config_dir.as_posix()}"

Write-Host "Backup directory: $BackupDir" -ForegroundColor Yellow
Write-Host "Config directory: $ConfigDir" -ForegroundColor Yellow
Write-Host ""

# Check if backup directory exists
if (-not (Test-Path $BackupDir)) {{
    Write-Host "ERROR: Backup directory not found!" -ForegroundColor Red
    Write-Host "Expected: $BackupDir" -ForegroundColor Red
    exit 1
}}

# Confirm restoration
Write-Host "This will restore PostgreSQL configuration files to their original state." -ForegroundColor Yellow
Write-Host "Current server mode settings will be lost." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Do you want to proceed? (yes/no)"

if ($confirm -ne "yes") {{
    Write-Host "Restoration cancelled." -ForegroundColor Yellow
    exit 0
}}

Write-Host ""
Write-Host "Stopping PostgreSQL service..." -ForegroundColor Yellow

try {{
    Stop-Service -Name "postgresql*" -Force -ErrorAction SilentlyContinue
    Write-Host "  Service stopped" -ForegroundColor Green
}} catch {{
    Write-Host "  WARNING: Could not stop PostgreSQL service automatically" -ForegroundColor Yellow
    Write-Host "  Please stop PostgreSQL manually before continuing" -ForegroundColor Yellow
    Read-Host "Press Enter when PostgreSQL is stopped"
}}

Write-Host ""
Write-Host "Restoring configuration files..." -ForegroundColor Yellow

# Restore postgresql.conf
$postgresqlBackup = Join-Path $BackupDir "postgresql.conf"
$postgresqlTarget = Join-Path $ConfigDir "postgresql.conf"

if (Test-Path $postgresqlBackup) {{
    Copy-Item -Path $postgresqlBackup -Destination $postgresqlTarget -Force
    Write-Host "  Restored postgresql.conf" -ForegroundColor Green
}} else {{
    Write-Host "  ERROR: postgresql.conf backup not found!" -ForegroundColor Red
}}

# Restore pg_hba.conf
$hbaBackup = Join-Path $BackupDir "pg_hba.conf"
$hbaTarget = Join-Path $ConfigDir "pg_hba.conf"

if (Test-Path $hbaBackup) {{
    Copy-Item -Path $hbaBackup -Destination $hbaTarget -Force
    Write-Host "  Restored pg_hba.conf" -ForegroundColor Green
}} else {{
    Write-Host "  ERROR: pg_hba.conf backup not found!" -ForegroundColor Red
}}

Write-Host ""
Write-Host "Starting PostgreSQL service..." -ForegroundColor Yellow

try {{
    Start-Service -Name "postgresql*"
    Write-Host "  Service started" -ForegroundColor Green
}} catch {{
    Write-Host "  WARNING: Could not start PostgreSQL service automatically" -ForegroundColor Yellow
    Write-Host "  Please start PostgreSQL manually" -ForegroundColor Yellow
}}

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "   Configuration Restoration Complete!" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
'''

        script_path.write_text(script_content, encoding='utf-8')
        self.logger.info(f"Generated Windows restore script: {script_path}")
        return script_path

    def _generate_unix_restore_script(self, scripts_dir: Path) -> Optional[Path]:
        """Generate Unix/Linux restoration script"""
        script_path = scripts_dir / "restore_pg_config.sh"

        script_content = f'''#!/bin/bash
# GiljoAI MCP PostgreSQL Configuration Restoration Script
# Generated: {datetime.now().isoformat()}
#
# This script restores PostgreSQL configuration files to their state
# before GiljoAI MCP server mode modifications.

set -euo pipefail

echo ""
echo "====================================================================="
echo "   GiljoAI MCP - PostgreSQL Configuration Restoration"
echo "====================================================================="
echo ""

# Configuration
BACKUP_DIR="{self.backup_dir.as_posix()}"
CONFIG_DIR="{self.pg_config_dir.as_posix()}"

echo "Backup directory: $BACKUP_DIR"
echo "Config directory: $CONFIG_DIR"
echo ""

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found!"
    echo "Expected: $BACKUP_DIR"
    exit 1
fi

# Confirm restoration
echo "This will restore PostgreSQL configuration files to their original state."
echo "Current server mode settings will be lost."
echo ""
read -p "Do you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restoration cancelled."
    exit 0
fi

echo ""
echo "Stopping PostgreSQL service..."

# Try different PostgreSQL service names
if systemctl list-units --type=service | grep -q postgresql; then
    sudo systemctl stop postgresql
    echo "  Service stopped"
elif command -v pg_ctl &> /dev/null; then
    sudo -u postgres pg_ctl stop -D "$CONFIG_DIR"
    echo "  Service stopped"
else
    echo "  WARNING: Could not stop PostgreSQL service automatically"
    echo "  Please stop PostgreSQL manually before continuing"
    read -p "Press Enter when PostgreSQL is stopped"
fi

echo ""
echo "Restoring configuration files..."

# Restore postgresql.conf
if [ -f "$BACKUP_DIR/postgresql.conf" ]; then
    sudo cp "$BACKUP_DIR/postgresql.conf" "$CONFIG_DIR/postgresql.conf"
    echo "  Restored postgresql.conf"
else
    echo "  ERROR: postgresql.conf backup not found!"
fi

# Restore pg_hba.conf
if [ -f "$BACKUP_DIR/pg_hba.conf" ]; then
    sudo cp "$BACKUP_DIR/pg_hba.conf" "$CONFIG_DIR/pg_hba.conf"
    echo "  Restored pg_hba.conf"
else
    echo "  ERROR: pg_hba.conf backup not found!"
fi

echo ""
echo "Starting PostgreSQL service..."

# Try different PostgreSQL service names
if systemctl list-units --type=service | grep -q postgresql; then
    sudo systemctl start postgresql
    echo "  Service started"
elif command -v pg_ctl &> /dev/null; then
    sudo -u postgres pg_ctl start -D "$CONFIG_DIR"
    echo "  Service started"
else
    echo "  WARNING: Could not start PostgreSQL service automatically"
    echo "  Please start PostgreSQL manually"
fi

echo ""
echo "====================================================================="
echo "   Configuration Restoration Complete!"
echo "====================================================================="
echo ""
'''

        script_path.write_text(script_content, encoding='utf-8')
        script_path.chmod(0o755)
        self.logger.info(f"Generated Unix restore script: {script_path}")
        return script_path

    def prompt_postgresql_restart(self) -> Dict[str, Any]:
        """Prompt user to restart PostgreSQL or attempt automatic restart"""
        result = {'restart_required': True, 'restart_completed': False}

        # In batch mode, just note that restart is required
        if self.settings.get('batch'):
            return result

        print("\n" + "="*60)
        print("PostgreSQL Restart Required")
        print("="*60)
        print()
        print("The PostgreSQL configuration has been modified.")
        print("PostgreSQL must be restarted for changes to take effect.")
        print()

        response = input("Attempt to restart PostgreSQL now? (yes/no): ")

        if response.lower() not in ['yes', 'y']:
            print()
            print("Please restart PostgreSQL manually:")
            if platform.system() == "Windows":
                print("  - Open Services (services.msc)")
                print("  - Find 'PostgreSQL' service")
                print("  - Click 'Restart'")
            else:
                print("  sudo systemctl restart postgresql")
            print()
            return result

        # Attempt automatic restart
        try:
            success = self._restart_postgresql()
            if success:
                result['restart_completed'] = True
                print()
                print("PostgreSQL restarted successfully!")
                print()
            else:
                print()
                print("WARNING: Could not restart PostgreSQL automatically.")
                print("Please restart PostgreSQL manually.")
                print()
        except Exception as e:
            self.logger.error(f"Failed to restart PostgreSQL: {e}")
            print()
            print(f"WARNING: Restart failed: {e}")
            print("Please restart PostgreSQL manually.")
            print()

        return result

    def _restart_postgresql(self) -> bool:
        """Attempt to restart PostgreSQL service"""
        try:
            system = platform.system()

            if system == "Windows":
                # Try to restart Windows service
                result = subprocess.run(
                    ['net', 'stop', 'postgresql'],
                    capture_output=True,
                    timeout=30
                )
                subprocess.run(
                    ['net', 'start', 'postgresql'],
                    capture_output=True,
                    timeout=30
                )
                return True

            else:  # Linux/macOS
                # Try systemctl first
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', 'postgresql'],
                    capture_output=True,
                    timeout=30
                )
                return result.returncode == 0

        except Exception as e:
            self.logger.error(f"PostgreSQL restart failed: {e}")
            return False

    def _get_manual_config_guide(self) -> str:
        """Return guide for manual PostgreSQL configuration"""
        return """
Manual PostgreSQL Network Configuration Guide:

1. Locate your PostgreSQL configuration directory
   - Look for postgresql.conf and pg_hba.conf
   - Common locations shown in error message above

2. Edit postgresql.conf:
   - Find: #listen_addresses = 'localhost'
   - Change to: listen_addresses = '*'
   - Save the file

3. Edit pg_hba.conf:
   - Add lines like: host    giljo_mcp    giljo_user    192.168.0.0/16    scram-sha-256
   - Adjust network range as needed
   - Save the file

4. Restart PostgreSQL:
   - Windows: Restart PostgreSQL service via services.msc
   - Linux: sudo systemctl restart postgresql
   - macOS: brew services restart postgresql

5. Test connectivity from remote client:
   - psql -h [server-ip] -U giljo_user -d giljo_mcp
"""
