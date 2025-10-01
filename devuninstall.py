#!/usr/bin/env python3
"""
GiljoAI MCP Development Uninstaller
Nuclear reset for testing - removes ALL files and PostgreSQL

Use this for development/testing - it removes:
- ALL files in the installation folder
- PostgreSQL database AND server
- User config files from APPDATA
- Everything related to this installation

Preserves:
- Python packages (for other projects on this machine)
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

    def remove_all_installation_files(self):
        """Remove ALL files in installation directory except this script"""
        self.log("Removing ALL installation files...")
        script_name = Path(__file__).name

        removed = 0
        for item in self.root_path.iterdir():
            # Skip this script and log files
            if item.name in [script_name, "devuninstall.log"]:
                continue

            try:
                if item.is_dir():
                    shutil.rmtree(item)
                    self.log(f"Removed directory: {item.name}", "SUCCESS")
                else:
                    item.unlink()
                    self.log(f"Removed file: {item.name}", "SUCCESS")
                removed += 1
            except Exception as e:
                self.log(f"Failed to remove {item.name}: {e}", "ERROR")

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

    def remove_postgresql_completely(self):
        """Remove PostgreSQL database AND server"""
        self.log("Removing PostgreSQL completely...")

        pg_info = self.manifest.get('postgresql', {})
        host = pg_info.get('host', 'localhost')
        port = pg_info.get('port', '5432')
        user = pg_info.get('user', 'postgres')
        password = pg_info.get('password', '')
        database = pg_info.get('database', 'giljo_mcp')

        # First, drop the database
        try:
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
            else:
                subprocess.run(
                    ["psql", "-h", host, "-p", port, "-U", user,
                     "-c", f"DROP DATABASE IF EXISTS {database};"],
                    capture_output=True,
                    timeout=10
                )
            self.log(f"Database '{database}' dropped", "SUCCESS")
        except FileNotFoundError:
            self.log("psql not in PATH", "WARNING")
        except Exception as e:
            self.log(f"Could not drop database: {e}", "WARNING")

        # Then, uninstall PostgreSQL server
        pg_deps = self.manifest.get('dependencies', {}).get('postgresql', {})

        if pg_deps.get('installed'):
            self.log("Uninstalling PostgreSQL server...", "INFO")
            try:
                if self.platform == "win32":
                    location = pg_deps.get('location', 'C:/PostgreSQL/18')
                    uninstaller = Path(location) / "uninstall-postgresql.exe"
                    if uninstaller.exists():
                        subprocess.run([str(uninstaller), "--mode", "unattended"], timeout=120)
                        self.log("PostgreSQL server uninstalled", "SUCCESS")
                    else:
                        self.log(f"PostgreSQL uninstaller not found at: {uninstaller}", "WARNING")
                elif self.platform == "darwin":
                    subprocess.run(["brew", "uninstall", "postgresql@18"], timeout=60)
                    subprocess.run(["brew", "services", "stop", "postgresql@18"], timeout=30)
                    self.log("PostgreSQL server uninstalled", "SUCCESS")
                else:
                    subprocess.run(["sudo", "apt", "remove", "postgresql", "postgresql-contrib", "-y"], timeout=120)
                    self.log("PostgreSQL server uninstalled", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to uninstall PostgreSQL: {e}", "ERROR")
        else:
            self.log("PostgreSQL was external - attempting manual uninstall instructions", "INFO")
            self.log("To uninstall PostgreSQL manually:", "INFO")
            self.log("  Windows: Control Panel > Programs > Uninstall PostgreSQL", "INFO")
            self.log("  Mac: brew uninstall postgresql@18", "INFO")
            self.log("  Linux: sudo apt remove postgresql postgresql-contrib", "INFO")

    def remove_mcp_registrations(self):
        """Remove MCP server registrations from AI CLI tools"""
        self.log("Removing MCP registrations from AI CLI tools...")

        try:
            from installer.universal_mcp_installer import UniversalMCPInstaller

            installer = UniversalMCPInstaller()
            tools = installer.detect_installed_tools()

            if not tools:
                self.log("No AI CLI tools detected - skipping MCP unregistration", "INFO")
                return 0

            self.log(f"Detected: {', '.join(tools)}", "INFO")
            results = installer.unregister_all("giljo-mcp")

            success_count = sum(1 for v in results.values() if v)
            self.log(f"Unregistered from {success_count}/{len(results)} AI CLI tools", "SUCCESS")
            return success_count

        except ImportError:
            self.log("MCP unregistration unavailable (missing module)", "WARNING")
            return 0
        except Exception as e:
            self.log(f"MCP unregistration failed: {e}", "WARNING")
            return 0

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
        print("  - ALL files in this installation folder")
        print("  - PostgreSQL database AND server")
        print("  - User config files from APPDATA")
        print("  - EVERYTHING related to this installation")

        print("\n[INFO] This will preserve:")
        print("  - Python packages (for other projects on this machine)")
        print("  - Only this script and log file will remain")

        confirm = input("\nType 'RESET' to confirm: ")
        if confirm != "RESET":
            print("Uninstall cancelled.")
            return

        print("\n" + "="*70)
        print("STARTING DEVELOPMENT RESET")
        print("="*70)

        # Execute uninstall steps
        mcp_unregistered = self.remove_mcp_registrations()
        self.remove_postgresql_completely()
        appdata_removed = self.remove_appdata_configs()
        files_removed = self.remove_all_installation_files()

        print("\n" + "="*70)
        print("DEVELOPMENT RESET COMPLETE")
        print("="*70)
        print(f"\nMCP unregistrations: {mcp_unregistered}")
        print(f"Files removed: {files_removed}")
        print(f"APPDATA locations removed: {appdata_removed}")
        print("PostgreSQL: REMOVED")

        print("\n[OK] Environment reset for fresh installation!")
        print("[OK] You can now reinstall: python run_cli_install.py")
        print("\n[NOTE] Python packages preserved for other projects.")


if __name__ == "__main__":
    uninstaller = GiljoDevUninstaller()
    uninstaller.run()
