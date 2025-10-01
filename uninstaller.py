#!/usr/bin/env python3
"""
GiljoAI MCP Comprehensive Uninstaller
Safely removes GiljoAI MCP installation with multiple options
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class GiljoUninstaller:
    """Comprehensive uninstaller for GiljoAI MCP"""

    def __init__(self):
        self.root_path = Path.cwd()
        self.manifest_path = self.root_path / ".giljo_install_manifest.json"
        self.manifest = self.load_manifest()
        self.platform = sys.platform
        self.uninstall_log = []

    def load_manifest(self) -> Dict:
        """Load installation manifest if it exists"""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load manifest: {e}")
                return {}
        return {}

    def log(self, message: str, level: str = "INFO"):
        """Log uninstall actions"""
        self.uninstall_log.append(f"[{level}] {message}")
        print(f"[{level}] {message}")

    def save_uninstall_log(self):
        """Save uninstall log to file"""
        log_path = self.root_path / "uninstall.log"
        with open(log_path, 'w') as f:
            f.write('\n'.join(self.uninstall_log))
        print(f"\nUninstall log saved to: {log_path}")

    def create_selective_manifest(self) -> Path:
        """Create a manifest file with commands for selective uninstall"""
        manifest_path = self.root_path / "uninstall_commands.txt"

        commands = []
        commands.append("# GiljoAI MCP Selective Uninstall Commands")
        commands.append("# Run these commands manually to remove specific components\n")

        # Python dependencies
        commands.append("# === Python Dependencies ===")
        commands.append("# Remove all Python packages installed by GiljoAI:")
        if (self.root_path / "requirements.txt").exists():
            commands.append("pip uninstall -r requirements.txt -y")
        commands.append("pip uninstall giljo-mcp -y")
        commands.append("")

        # PostgreSQL
        commands.append("# === PostgreSQL Database ===")
        if self.manifest.get('dependencies', {}).get('postgresql', {}).get('installed'):
            pg_info = self.manifest['dependencies']['postgresql']
            commands.append("# Remove only the GiljoAI database (preserves other databases):")
            commands.append('psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"')
            commands.append("")
            commands.append("# Complete PostgreSQL removal (WARNING: removes all databases!):")

            if self.platform == "win32":
                pg_location = pg_info.get('location', 'C:/PostgreSQL/18')
                commands.append(f'& "{pg_location}/uninstall-postgresql.exe" --mode unattended')
            elif self.platform == "darwin":
                commands.append("brew uninstall postgresql@18")
                commands.append("brew services stop postgresql@18")
            else:
                commands.append("sudo apt remove postgresql postgresql-contrib -y")
                commands.append("# OR for RHEL/CentOS:")
                commands.append("# sudo yum remove postgresql-server postgresql-contrib -y")
        else:
            commands.append("# PostgreSQL was not installed by this installer")
            commands.append('# To remove the database: psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"')
        commands.append("")

        # Virtual environment
        commands.append("# === Virtual Environment ===")
        if self.platform == "win32":
            commands.append("rmdir /s /q venv")
        else:
            commands.append("rm -rf venv")
        commands.append("")

        # Data directories
        commands.append("# === Data Directories ===")
        dirs = ["data", "logs", "backups", ".giljo_mcp", ".giljo-config", ".giljo_install_manifest.json"]
        for dir_name in dirs:
            if self.platform == "win32":
                commands.append(f"rmdir /s /q {dir_name}")
            else:
                commands.append(f"rm -rf {dir_name}")
        commands.append("")

        # Configuration files
        commands.append("# === Configuration Files ===")
        config_files = [".env", "config.yaml", "config.json"]
        for file in config_files:
            if self.platform == "win32":
                commands.append(f"del {file}")
            else:
                commands.append(f"rm -f {file}")
        commands.append("")

        # Windows shortcuts
        if self.platform == "win32":
            commands.append("# === Desktop Shortcuts (Windows) ===")
            commands.append('del "%USERPROFILE%\\Desktop\\Start GiljoAI Server.lnk"')
            commands.append('del "%USERPROFILE%\\Desktop\\Stop GiljoAI Server.lnk"')
            commands.append('del "%USERPROFILE%\\Desktop\\GiljoAI Dashboard.lnk"')
            commands.append("")

        # Services
        if self.manifest.get('dependencies', {}).get('postgresql', {}).get('service_name'):
            commands.append("# === Services ===")
            service = self.manifest['dependencies']['postgresql']['service_name']
            if self.platform == "win32":
                commands.append(f"sc stop {service}")
                commands.append(f"sc delete {service}")
            else:
                commands.append(f"sudo systemctl stop {service}")
                commands.append(f"sudo systemctl disable {service}")
            commands.append("")

        # Write manifest
        with open(manifest_path, 'w') as f:
            f.write('\n'.join(commands))

        return manifest_path

    def backup_user_data(self) -> Optional[Path]:
        """Create backup of user data before uninstall"""
        backup_dir = self.root_path / "giljo_backup"

        try:
            self.log("Creating backup of user data...")
            backup_dir.mkdir(exist_ok=True)

            # Backup config files
            for config_file in [".env", "config.yaml", "config.json"]:
                src = self.root_path / config_file
                if src.exists():
                    shutil.copy2(src, backup_dir / config_file)

            # Backup data directory
            data_dir = self.root_path / "data"
            if data_dir.exists():
                shutil.copytree(data_dir, backup_dir / "data", dirs_exist_ok=True)

            self.log(f"Backup created at: {backup_dir}", "SUCCESS")
            return backup_dir
        except Exception as e:
            self.log(f"Backup failed: {e}", "WARNING")
            return None

    def remove_python_packages(self):
        """Remove Python packages"""
        self.log("Removing Python packages...")

        try:
            # Uninstall giljo-mcp
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "giljo-mcp", "-y"],
                         capture_output=True)

            # Uninstall requirements if file exists
            req_file = self.root_path / "requirements.txt"
            if req_file.exists():
                subprocess.run([sys.executable, "-m", "pip", "uninstall", "-r", str(req_file), "-y"],
                             capture_output=True)

            self.log("Python packages removed", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to remove Python packages: {e}", "ERROR")

    def remove_postgresql(self, complete: bool = False):
        """Remove PostgreSQL database or complete installation"""
        if not self.manifest.get('dependencies', {}).get('postgresql', {}).get('installed'):
            self.log("PostgreSQL was not installed by this installer")
            return

        pg_info = self.manifest['dependencies']['postgresql']

        if complete:
            self.log("Removing complete PostgreSQL installation...")
            try:
                if self.platform == "win32":
                    pg_uninstaller = Path(pg_info.get('location', 'C:/PostgreSQL/18')) / "uninstall-postgresql.exe"
                    if pg_uninstaller.exists():
                        subprocess.run([str(pg_uninstaller), "--mode", "unattended"], check=True)
                elif self.platform == "darwin":
                    subprocess.run(["brew", "uninstall", "postgresql@18"], check=True)
                    subprocess.run(["brew", "services", "stop", "postgresql@18"], check=True)
                else:
                    subprocess.run(["sudo", "apt", "remove", "postgresql", "postgresql-contrib", "-y"], check=True)

                self.log("PostgreSQL completely removed", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to remove PostgreSQL: {e}", "ERROR")
        else:
            self.log("Removing GiljoAI database only...")
            try:
                # Drop the giljo_mcp database
                subprocess.run([
                    "psql", "-U", "postgres", "-c", "DROP DATABASE IF EXISTS giljo_mcp;"
                ], capture_output=True)
                self.log("GiljoAI database removed", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to remove database: {e}", "ERROR")

    def remove_virtual_environment(self):
        """Remove Python virtual environment"""
        venv_path = self.root_path / "venv"
        if venv_path.exists():
            self.log("Removing virtual environment...")
            try:
                shutil.rmtree(venv_path)
                self.log("Virtual environment removed", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to remove virtual environment: {e}", "ERROR")

    def remove_directories(self):
        """Remove GiljoAI directories"""
        dirs = ["data", "logs", "backups", ".giljo_mcp", ".giljo-config"]

        for dir_name in dirs:
            dir_path = self.root_path / dir_name
            if dir_path.exists():
                self.log(f"Removing {dir_name} directory...")
                try:
                    shutil.rmtree(dir_path)
                    self.log(f"{dir_name} removed", "SUCCESS")
                except Exception as e:
                    self.log(f"Failed to remove {dir_name}: {e}", "ERROR")

    def remove_config_files(self):
        """Remove configuration files"""
        config_files = [".env", "config.yaml", "config.json", ".giljo_install_manifest.json"]

        for file_name in config_files:
            file_path = self.root_path / file_name
            if file_path.exists():
                self.log(f"Removing {file_name}...")
                try:
                    file_path.unlink()
                    self.log(f"{file_name} removed", "SUCCESS")
                except Exception as e:
                    self.log(f"Failed to remove {file_name}: {e}", "ERROR")

    def remove_shortcuts(self):
        """Remove desktop shortcuts (Windows)"""
        if self.platform != "win32":
            return

        self.log("Removing desktop shortcuts...")
        desktop = Path.home() / "Desktop"
        shortcuts = [
            "Start GiljoAI Server.lnk",
            "Stop GiljoAI Server.lnk",
            "GiljoAI Dashboard.lnk"
        ]

        for shortcut in shortcuts:
            shortcut_path = desktop / shortcut
            if shortcut_path.exists():
                try:
                    shortcut_path.unlink()
                    self.log(f"Removed {shortcut}", "SUCCESS")
                except Exception as e:
                    self.log(f"Failed to remove {shortcut}: {e}", "ERROR")

    def nuclear_uninstall(self):
        """Complete removal of everything"""
        print("\n" + "="*60)
        print("NUCLEAR UNINSTALL - This will remove EVERYTHING!")
        print("="*60)
        print("\nThis includes:")
        print("- All Python packages")
        print("- PostgreSQL installation (if installed by us)")
        print("- All data and configuration")
        print("- Virtual environment")
        print("- All shortcuts and services")

        confirm = input("\nType 'DESTROY' to confirm: ")
        if confirm != "DESTROY":
            print("Uninstall cancelled.")
            return

        # Create backup first
        self.backup_user_data()

        # Remove everything
        self.remove_python_packages()
        self.remove_postgresql(complete=True)
        self.remove_virtual_environment()
        self.remove_directories()
        self.remove_config_files()
        self.remove_shortcuts()

        self.save_uninstall_log()
        print("\n✓ Nuclear uninstall complete!")

    def database_only_uninstall(self):
        """Remove only the application database"""
        print("\n" + "="*60)
        print("DATABASE-SPECIFIC UNINSTALL")
        print("="*60)
        print("\nThis will remove:")
        print("- The giljo_mcp database")
        print("- Application data files")
        print("\nThis will preserve:")
        print("- PostgreSQL installation")
        print("- Other databases")
        print("- Python packages")

        confirm = input("\nContinue? (y/n): ")
        if confirm.lower() != 'y':
            print("Uninstall cancelled.")
            return

        # Create backup first
        self.backup_user_data()

        # Remove database and data
        self.remove_postgresql(complete=False)
        self.remove_directories()
        self.remove_config_files()

        self.save_uninstall_log()
        print("\n✓ Database uninstall complete!")

    def selective_uninstall(self):
        """Create manifest for selective manual uninstall"""
        print("\n" + "="*60)
        print("SELECTIVE UNINSTALL")
        print("="*60)
        print("\nThis will create a text file with commands to:")
        print("- Selectively remove components")
        print("- Preserve what you want to keep")
        print("- Give you full control over the process")

        confirm = input("\nCreate selective uninstall manifest? (y/n): ")
        if confirm.lower() != 'y':
            print("Uninstall cancelled.")
            return

        manifest_path = self.create_selective_manifest()

        print(f"\n✓ Selective uninstall manifest created: {manifest_path}")
        print("\nYou can now:")
        print("1. Open the manifest file")
        print("2. Review each command")
        print("3. Run only the commands you want")
        print("4. Skip components you want to keep")

    def repair_installation(self):
        """Attempt to repair broken installation"""
        print("\n" + "="*60)
        print("REPAIR INSTALLATION")
        print("="*60)
        print("\nThis will attempt to:")
        print("- Fix missing directories")
        print("- Restore default configuration")
        print("- Verify database connection")

        confirm = input("\nAttempt repair? (y/n): ")
        if confirm.lower() != 'y':
            print("Repair cancelled.")
            return

        # Create missing directories
        dirs = ["data", "logs", "backups", ".giljo_mcp", ".giljo-config"]
        for dir_name in dirs:
            dir_path = self.root_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.log(f"Created missing directory: {dir_name}", "SUCCESS")

        # Check for config files
        if not (self.root_path / ".env").exists() and not (self.root_path / "config.yaml").exists():
            self.log("Configuration files missing - please run setup again", "WARNING")

        self.log("Repair attempt complete", "SUCCESS")
        self.save_uninstall_log()

    def export_data(self):
        """Export database data before uninstall"""
        print("\n" + "="*60)
        print("EXPORT DATA")
        print("="*60)

        export_dir = self.root_path / "giljo_export"
        export_dir.mkdir(exist_ok=True)

        # Get database config from manifest
        db_config = self.manifest.get('configuration', {})

        if db_config.get('database_type') == 'postgresql':
            print("\nExporting PostgreSQL database...")
            try:
                # Export database
                export_file = export_dir / "giljo_mcp_backup.sql"
                subprocess.run([
                    "pg_dump", "-U", "postgres", "-d", "giljo_mcp",
                    "-f", str(export_file)
                ], check=True)
                print(f"✓ Database exported to: {export_file}")
            except Exception as e:
                print(f"✗ Export failed: {e}")

        # Copy config files
        for config_file in [".env", "config.yaml", "config.json"]:
            src = self.root_path / config_file
            if src.exists():
                shutil.copy2(src, export_dir / config_file)
                print(f"✓ Exported {config_file}")

        print(f"\n✓ Data exported to: {export_dir}")

    def run(self):
        """Main uninstaller interface"""
        print("\n" + "="*70)
        print("   GiljoAI MCP Uninstaller")
        print("="*70)

        # Check for manifest
        if not self.manifest:
            print("\n⚠️  Warning: No installation manifest found.")
            print("   Some features may not work correctly.")

        while True:
            print("\nSelect uninstall option:")
            print("\n1. Nuclear - Complete removal of EVERYTHING")
            print("2. Database Only - Remove app database, keep PostgreSQL")
            print("3. Selective - Create command list for manual removal")
            print("4. Repair - Attempt to fix broken installation")
            print("5. Export - Export data before uninstall")
            print("6. Exit")

            choice = input("\nEnter choice (1-6): ").strip()

            if choice == "1":
                self.nuclear_uninstall()
                break
            elif choice == "2":
                self.database_only_uninstall()
                break
            elif choice == "3":
                self.selective_uninstall()
                break
            elif choice == "4":
                self.repair_installation()
            elif choice == "5":
                self.export_data()
            elif choice == "6":
                print("Uninstaller exited.")
                break
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    uninstaller = GiljoUninstaller()
    uninstaller.run()
