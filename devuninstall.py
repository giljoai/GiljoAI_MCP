#!/usr/bin/env python3
"""
GiljoAI MCP Development Uninstaller
Resets installation to simulate fresh install (keeps Python deps & PostgreSQL server)

Use this for development/testing - it removes:
- All installation files and folders
- giljo_mcp database (but keeps PostgreSQL server)
- User config files from APPDATA
- Generated configs and data

Preserves:
- Python packages (for other projects)
- PostgreSQL server installation
- Source code repository files
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class GiljoDevUninstaller:
    """Development uninstaller - clean slate for testing"""

    def __init__(self):
        self.root_path = Path.cwd()
        self.manifest_path = self.root_path / ".giljo_install_manifest.json"
        self.manifest = self.load_manifest()
        self.platform = sys.platform

    def load_manifest(self):
        """Load installation manifest"""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def log(self, message, level="INFO"):
        """Log with ASCII-only characters for Windows compatibility"""
        print(f"[{level}] {message}")

    def remove_installation_folders(self):
        """Remove all installation folders"""
        self.log("Removing installation folders...")

        folders_to_remove = [
            "venv", "data", "logs", "backups",
            ".giljo_mcp", ".giljo-config", ".giljo_install_manifest.json",
            "config", "giljo_backup", "giljo_export",
            "__pycache__", "node_modules", ".pytest_cache",
            "frontend/node_modules", "frontend/dist", "frontend/build"
        ]

        removed = 0
        for folder_name in folders_to_remove:
            folder_path = self.root_path / folder_name
            if folder_path.exists():
                try:
                    if folder_path.is_dir():
                        shutil.rmtree(folder_path)
                    else:
                        folder_path.unlink()
                    self.log(f"Removed: {folder_name}", "SUCCESS")
                    removed += 1
                except Exception as e:
                    self.log(f"Failed to remove {folder_name}: {e}", "ERROR")

        return removed

    def remove_generated_configs(self):
        """Remove generated configuration files"""
        self.log("Removing generated config files...")

        configs_to_remove = [
            "config.yaml", "config.json", ".env",
            ".env.local", ".env.production",
            "uninstall.log", "uninstall_commands.txt"
        ]

        removed = 0
        for config_name in configs_to_remove:
            config_path = self.root_path / config_name
            if config_path.exists():
                try:
                    config_path.unlink()
                    self.log(f"Removed: {config_name}", "SUCCESS")
                    removed += 1
                except Exception as e:
                    self.log(f"Failed to remove {config_name}: {e}", "ERROR")

        return removed

    def remove_test_artifacts(self):
        """Remove test scripts and artifacts"""
        self.log("Removing test artifacts...")

        test_files = [
            "test_nuclear_uninstall.py",
            "test_selective_uninstall.py",
            "test_repair.py",
            "test_export.py",
            "giltest.bat",
            "GILTEST_README.md"
        ]

        removed = 0
        for test_file in test_files:
            file_path = self.root_path / test_file
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.log(f"Removed: {test_file}", "SUCCESS")
                    removed += 1
                except Exception as e:
                    self.log(f"Failed to remove {test_file}: {e}", "ERROR")

        return removed

    def drop_database(self):
        """Drop the giljo_mcp database only (keep PostgreSQL server)"""
        self.log("Dropping giljo_mcp database...")

        pg_info = self.manifest.get('postgresql', {})
        host = pg_info.get('host', 'localhost')
        port = pg_info.get('port', '5432')
        user = pg_info.get('user', 'postgres')
        password = pg_info.get('password', '')
        database = pg_info.get('database', 'giljo_mcp')

        try:
            # Try with password from manifest
            if password:
                env = os.environ.copy()
                env['PGPASSWORD'] = password
                subprocess.run(
                    ["psql", "-h", host, "-p", port, "-U", user,
                     "-c", f"DROP DATABASE IF EXISTS {database};"],
                    env=env,
                    capture_output=True,
                    timeout=10
                )
                self.log(f"Database '{database}' dropped", "SUCCESS")
            else:
                # Try without password
                subprocess.run(
                    ["psql", "-h", host, "-p", port, "-U", user,
                     "-c", f"DROP DATABASE IF EXISTS {database};"],
                    capture_output=True,
                    timeout=10
                )
                self.log(f"Database '{database}' dropped", "SUCCESS")

        except FileNotFoundError:
            self.log("psql not in PATH - manual database drop required", "WARNING")
            self.log(f"Run: DROP DATABASE IF EXISTS {database};", "INFO")
        except Exception as e:
            self.log(f"Could not drop database: {e}", "WARNING")
            self.log(f"You may need to manually drop database: {database}", "INFO")

    def remove_appdata_configs(self):
        """Remove config files from APPDATA and user directories"""
        self.log("Removing APPDATA configuration files...")

        locations = []
        if self.platform == "win32":
            appdata = Path(os.getenv('APPDATA', ''))
            localappdata = Path(os.getenv('LOCALAPPDATA', ''))
            userprofile = Path(os.getenv('USERPROFILE', ''))

            locations = [
                appdata / "GiljoAI",
                localappdata / "GiljoAI",
                userprofile / ".giljo_mcp",
                userprofile / ".giljo-config",
            ]
        else:
            home = Path.home()
            locations = [
                home / ".giljo_mcp",
                home / ".giljo-config",
                home / ".local" / "share" / "GiljoAI",
                home / ".config" / "GiljoAI",
            ]

        removed = 0
        for loc in locations:
            if loc.exists():
                try:
                    shutil.rmtree(loc)
                    self.log(f"Removed: {loc}", "SUCCESS")
                    removed += 1
                except Exception as e:
                    self.log(f"Failed to remove {loc}: {e}", "ERROR")

        return removed

    def run(self):
        """Run the development uninstall"""
        print("\n" + "="*70)
        print("   GiljoAI MCP Development Uninstaller")
        print("   Simulates Fresh Install Environment")
        print("="*70)

        print("\n[INFO] This will remove:")
        print("  - All installation folders (venv, data, logs, etc.)")
        print("  - Generated config files (config.yaml, .env, etc.)")
        print("  - giljo_mcp database (but keeps PostgreSQL server)")
        print("  - User config files from APPDATA")
        print("  - Test artifacts and scripts")

        print("\n[INFO] This will preserve:")
        print("  - Python packages (for other projects)")
        print("  - PostgreSQL server installation")
        print("  - Source code repository files")

        confirm = input("\nType 'RESET' to confirm: ")
        if confirm != "RESET":
            print("Uninstall cancelled.")
            return

        print("\n" + "="*70)
        print("STARTING DEVELOPMENT RESET")
        print("="*70)

        # Execute uninstall steps
        folders_removed = self.remove_installation_folders()
        configs_removed = self.remove_generated_configs()
        tests_removed = self.remove_test_artifacts()
        appdata_removed = self.remove_appdata_configs()
        self.drop_database()

        print("\n" + "="*70)
        print("DEVELOPMENT RESET COMPLETE")
        print("="*70)
        print(f"\nFolders removed: {folders_removed}")
        print(f"Configs removed: {configs_removed}")
        print(f"Test files removed: {tests_removed}")
        print(f"APPDATA locations removed: {appdata_removed}")

        print("\n[OK] Environment reset for fresh installation!")
        print("[OK] You can now reinstall: python run_cli_install.py")
        print("\n[NOTE] Python packages and PostgreSQL server preserved.")


if __name__ == "__main__":
    uninstaller = GiljoDevUninstaller()
    uninstaller.run()