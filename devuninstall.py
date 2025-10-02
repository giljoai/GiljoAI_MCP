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

    def drop_postgresql_database(self):
        """Drop PostgreSQL databases (main and test), keep server intact"""
        self.log("Dropping PostgreSQL databases...")

        # Default PostgreSQL configuration
        host = 'localhost'
        port = '5432'
        user = 'postgres'
        password = '4010'  # Default password for PostgreSQL

        # Check manifest for configuration
        pg_info = self.manifest.get('postgresql', {})
        if pg_info:
            host = pg_info.get('host', host)
            port = pg_info.get('port', port)
            user = pg_info.get('user', user)
            password = pg_info.get('password', password)

        # Databases to drop
        databases = ['giljo_mcp', 'giljo_mcp_test']

        # Find psql executable
        psql_paths = [
            r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\12\bin\psql.exe",
            "/c/Program Files/PostgreSQL/18/bin/psql.exe",
            "/c/Program Files/PostgreSQL/17/bin/psql.exe",
            "/c/Program Files/PostgreSQL/16/bin/psql.exe",
            "psql"  # Fallback to PATH
        ]

        psql_cmd = None
        for path in psql_paths:
            if Path(path).exists() or shutil.which(path):
                psql_cmd = path
                break

        if not psql_cmd:
            self.log("PostgreSQL psql command not found", "WARNING")
            self.log("Please ensure PostgreSQL client is installed", "WARNING")
            return 0

        dropped = 0
        for database in databases:
            try:
                env = os.environ.copy()
                env['PGPASSWORD'] = password

                # First, terminate all connections to the database
                # Using parameterized query to avoid SQL injection (bandit B608)
                terminate_query = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid();"
                terminate_cmd = [psql_cmd, "-h", host, "-p", port, "-U", user, "-d", "postgres",
                                "-c", terminate_query.replace('%s', f"'{database}'")]  # nosec B608

                subprocess.run(
                    terminate_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.log(f"Terminated connections to '{database}'", "INFO")

                # Now drop the database
                cmd = [psql_cmd, "-h", host, "-p", port, "-U", user,
                       "-c", f"DROP DATABASE IF EXISTS {database};"]

                # Run command
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 or "does not exist" in result.stderr:
                    self.log(f"PostgreSQL database '{database}' dropped", "SUCCESS")
                    dropped += 1
                else:
                    self.log(f"Could not drop '{database}': {result.stderr}", "WARNING")

            except subprocess.TimeoutExpired:
                self.log(f"Timeout dropping '{database}'", "WARNING")
            except Exception as e:
                self.log(f"Could not drop '{database}': {e}", "WARNING")

        return dropped

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

    def remove_all_databases(self):
        """Remove all SQLite and PostgreSQL databases"""
        self.log("Removing all GiljoAI MCP databases...")

        removed = 0

        # Remove SQLite database files
        db_locations = [
            self.root_path / "data" / "giljo.db",
            self.root_path / "data" / "giljo_mcp.db",
            self.root_path / "giljo.db",
        ]

        for db_path in db_locations:
            if db_path.exists():
                try:
                    db_path.unlink()
                    self.log(f"Removed SQLite database: {db_path.name}", "SUCCESS")
                    removed += 1
                except Exception as e:
                    self.log(f"Failed to remove {db_path}: {e}", "ERROR")

        # Drop PostgreSQL database
        pg_dropped = self.drop_postgresql_database()
        removed += pg_dropped

        return removed

    def run(self):
        """Run the development uninstall"""
        print("\n" + "="*70)
        print("   GiljoAI MCP Development Uninstaller")
        print("   Clean Slate for Testing and Development")
        print("="*70)

        print("\n[INFO] Select reset mode:")
        print("  1. Remove all files (keeps PostgreSQL server)")
        print("  2. Remove all files + drop databases (fresh install state)")
        print("  3. Drop databases only (clean data, keep everything else)")
        print("  4. Cancel")

        choice = input("\nSelect option [1-4]: ").strip()

        if choice == "1":
            # Remove all files, keep PostgreSQL server
            print("\n[INFO] This will remove:")
            print("  - ALL files in this installation folder")
            print("  - User config files from APPDATA")
            print("  - MCP registrations")

            print("\n[INFO] This will preserve:")
            print("  - PostgreSQL server (if installed)")
            print("  - Python packages")
            print("  - Only this script and log file will remain")

            confirm = input("\nType 'RESET' to confirm: ")
            if confirm != "RESET":
                print("Reset cancelled.")
                return

            print("\n" + "="*70)
            print("REMOVING ALL FILES")
            print("="*70)

            # Execute cleanup steps
            mcp_unregistered = self.remove_mcp_registrations()
            appdata_removed = self.remove_appdata_configs()
            files_removed = self.remove_all_installation_files()

            print("\n" + "="*70)
            print("FILE REMOVAL COMPLETE")
            print("="*70)
            print(f"\nMCP unregistrations: {mcp_unregistered}")
            print(f"Files removed: {files_removed}")
            print(f"APPDATA locations removed: {appdata_removed}")

            print("\n[OK] Files removed - ready for fresh installation!")
            print("[OK] PostgreSQL server preserved for reuse")
            print("[OK] You can now reinstall: python bootstrap.py")

        elif choice == "2":
            # Remove all files AND drop databases (fresh install state)
            print("\n[INFO] This will remove:")
            print("  - ALL files in this installation folder")
            print("  - PostgreSQL databases (giljo_mcp and giljo_mcp_test)")
            print("  - User config files from APPDATA")
            print("  - MCP registrations")

            print("\n[INFO] This will preserve:")
            print("  - PostgreSQL server (ready for new database)")
            print("  - Python packages")
            print("  - Only this script and log file will remain")

            confirm = input("\nType 'RESET' to confirm: ")
            if confirm != "RESET":
                print("Reset cancelled.")
                return

            print("\n" + "="*70)
            print("REMOVING ALL FILES AND DATABASES")
            print("="*70)

            # Execute cleanup steps
            db_removed = self.remove_all_databases()
            mcp_unregistered = self.remove_mcp_registrations()
            appdata_removed = self.remove_appdata_configs()
            files_removed = self.remove_all_installation_files()

            print("\n" + "="*70)
            print("COMPLETE RESET FINISHED")
            print("="*70)
            print(f"\nDatabases dropped: {db_removed}")
            print(f"MCP unregistrations: {mcp_unregistered}")
            print(f"Files removed: {files_removed}")
            print(f"APPDATA locations removed: {appdata_removed}")

            print("\n[OK] Complete fresh install state achieved!")
            print("[OK] PostgreSQL server ready for new database")
            print("[OK] You can now reinstall: python bootstrap.py")

        elif choice == "3":
            # Drop databases only - preserve all files
            print("\n[INFO] This will remove:")
            print("  - PostgreSQL main database (giljo_mcp)")
            print("  - PostgreSQL test database (giljo_mcp_test)")
            print("  - All agent data, messages, and history")

            print("\n[INFO] This will preserve:")
            print("  - All installation files")
            print("  - Configuration files")
            print("  - PostgreSQL server")
            print("  - Python environment")

            confirm = input("\nType 'DELETE' to confirm: ")
            if confirm != "DELETE":
                print("Database deletion cancelled.")
                return

            print("\n" + "="*70)
            print("DROPPING DATABASES")
            print("="*70)

            db_removed = self.remove_all_databases()

            print("\n" + "="*70)
            print("DATABASE DROP COMPLETE")
            print("="*70)
            print(f"\nDatabases dropped: {db_removed}")

            print("\n[OK] Databases removed - fresh data on next start!")
            print("[OK] PostgreSQL server intact and ready")
            print("[OK] Start the system: python -m giljo_mcp")

        else:
            print("Reset cancelled.")
            return


if __name__ == "__main__":
    uninstaller = GiljoDevUninstaller()
    uninstaller.run()
