#!/usr/bin/env python3
"""
GiljoAI MCP Production Uninstaller
TRUE NUCLEAR OPTION - Removes EVERYTHING including all dependencies

WARNING: Use this ONLY on production servers with no other Python projects!
This will remove ALL Python packages installed by GiljoAI and PostgreSQL!

For development/testing, use devuninstall.py instead.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class GiljoProductionUninstaller:
    """Production uninstaller - removes EVERYTHING"""

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

    def remove_all_python_packages(self):
        """Remove ALL Python packages installed by GiljoAI"""
        self.log("Removing ALL Python packages...")

        try:
            # Get list of packages from manifest
            packages = self.manifest.get('dependencies', {}).get('python_packages', [])

            if packages:
                # Extract package names (before ==)
                pkg_names = [pkg.split('==')[0] for pkg in packages]

                self.log(f"Uninstalling {len(pkg_names)} Python packages...", "INFO")

                # Uninstall in batches
                batch_size = 50
                for i in range(0, len(pkg_names), batch_size):
                    batch = pkg_names[i:i+batch_size]
                    try:
                        subprocess.run(
                            [sys.executable, "-m", "pip", "uninstall", "-y"] + batch,
                            capture_output=True,
                            timeout=300
                        )
                    except Exception as e:
                        self.log(f"Error uninstalling batch: {e}", "WARNING")

                self.log(f"Removed {len(pkg_names)} Python packages", "SUCCESS")
            else:
                self.log("No package list found in manifest", "WARNING")
                # Try requirements.txt as fallback
                req_file = self.root_path / "requirements.txt"
                if req_file.exists():
                    self.log("Attempting uninstall from requirements.txt...", "INFO")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "uninstall", "-r", str(req_file), "-y"],
                        capture_output=True,
                        timeout=300
                    )
        except Exception as e:
            self.log(f"Error removing packages: {e}", "ERROR")

    def remove_postgresql_completely(self):
        """Remove PostgreSQL database AND server installation"""
        self.log("Removing PostgreSQL completely...")

        # First, drop the database
        pg_info = self.manifest.get('postgresql', {})
        database = pg_info.get('database', 'giljo_mcp')

        try:
            subprocess.run(
                ["psql", "-U", "postgres", "-c", f"DROP DATABASE IF EXISTS {database};"],
                capture_output=True,
                timeout=10
            )
            self.log(f"Database '{database}' dropped", "SUCCESS")
        except:
            pass

        # Then remove PostgreSQL server
        pg_deps = self.manifest.get('dependencies', {}).get('postgresql', {})

        if pg_deps.get('installed'):
            self.log("Uninstalling PostgreSQL server...", "INFO")
            try:
                if self.platform == "win32":
                    location = pg_deps.get('location', 'C:/PostgreSQL/16')
                    uninstaller = Path(location) / "uninstall-postgresql.exe"
                    if uninstaller.exists():
                        subprocess.run([str(uninstaller), "--mode", "unattended"], timeout=120)
                        self.log("PostgreSQL server uninstalled", "SUCCESS")
                    else:
                        self.log(f"PostgreSQL uninstaller not found at: {uninstaller}", "WARNING")
                elif self.platform == "darwin":
                    subprocess.run(["brew", "uninstall", "postgresql@16"], timeout=60)
                    subprocess.run(["brew", "services", "stop", "postgresql@16"], timeout=30)
                    self.log("PostgreSQL server uninstalled", "SUCCESS")
                else:
                    subprocess.run(["sudo", "apt", "remove", "postgresql", "postgresql-contrib", "-y"], timeout=120)
                    self.log("PostgreSQL server uninstalled", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to uninstall PostgreSQL: {e}", "ERROR")
        else:
            self.log("PostgreSQL was not installed by installer (external)", "INFO")
            self.log("Manual PostgreSQL uninstall required if desired", "WARNING")

    def remove_all_installation_files(self):
        """Remove ALL files in installation directory except this script"""
        self.log("Removing ALL installation files...")
        script_name = Path(__file__).name

        removed = 0
        for item in self.root_path.iterdir():
            # Skip this script and the log file
            if item.name in [script_name, "uninstall.log", "uninstall_complete.log"]:
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

    def remove_appdata_completely(self):
        """Remove ALL files from APPDATA and user directories"""
        self.log("Removing ALL APPDATA and user directory files...")

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
        """Run the complete production uninstall"""
        print("\n" + "="*70)
        print("   GiljoAI MCP Production Uninstaller")
        print("   TRUE NUCLEAR OPTION - REMOVES EVERYTHING")
        print("="*70)

        print("\n" + "*"*70)
        print("  !!!  CRITICAL WARNING  !!!")
        print("*"*70)
        print("\n[CRITICAL] This will remove:")
        print("  - ALL files in this directory")
        print("  - ALL Python packages installed by GiljoAI (196+ packages)")
        print("  - PostgreSQL database AND server (if installed by us)")
        print("  - All configuration in APPDATA/user directories")
        print("  - EVERYTHING related to GiljoAI MCP")

        print("\n[CRITICAL] This WILL:")
        print("  - Break other Python projects using these packages")
        print("  - Remove ALL databases in PostgreSQL (if we installed it)")
        print("  - Be irreversible")

        print("\n[INFO] For development/testing, use devuninstall.py instead!")
        print("[INFO] devuninstall.py keeps Python packages and PostgreSQL server")

        print("\n" + "*"*70)
        print("  Use this ONLY on production servers with no other projects!")
        print("*"*70)

        confirm1 = input("\nType 'I UNDERSTAND' to continue: ")
        if confirm1 != "I UNDERSTAND":
            print("Uninstall cancelled.")
            return

        confirm2 = input("Type 'DESTROY EVERYTHING' to confirm: ")
        if confirm2 != "DESTROY EVERYTHING":
            print("Uninstall cancelled.")
            return

        print("\n" + "="*70)
        print("STARTING NUCLEAR UNINSTALL")
        print("="*70)

        # Execute uninstall steps
        self.remove_all_python_packages()
        self.remove_postgresql_completely()
        appdata_removed = self.remove_appdata_completely()
        files_removed = self.remove_all_installation_files()

        # Create completion log
        log_path = self.root_path / "uninstall_complete.log"
        with open(log_path, 'w') as f:
            f.write("GiljoAI MCP Nuclear Uninstall Complete\n")
            f.write(f"Files removed: {files_removed}\n")
            f.write(f"APPDATA locations removed: {appdata_removed}\n")
            f.write("All Python packages uninstalled\n")
            f.write("PostgreSQL removed\n")

        print("\n" + "="*70)
        print("NUCLEAR UNINSTALL COMPLETE")
        print("="*70)
        print(f"\nFiles removed: {files_removed}")
        print(f"APPDATA locations removed: {appdata_removed}")
        print("Python packages: ALL UNINSTALLED")
        print("PostgreSQL: REMOVED")

        print("\n[OK] Complete production uninstall successful!")
        print("[OK] All GiljoAI MCP components removed from system.")
        print(f"\n[INFO] Log saved to: {log_path}")


if __name__ == "__main__":
    uninstaller = GiljoProductionUninstaller()
    uninstaller.run()