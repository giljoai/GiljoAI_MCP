#!/usr/bin/env python3
"""
Enhanced Uninstaller for GiljoAI MCP Orchestrator

Uses the enhanced manifest system to ensure complete cleanup of all components.
STANDARD NAMING: .giljo_mcp (with underscore)
"""

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Add installers to path for manifest access
sys.path.insert(0, str(Path(__file__).parent / "installers"))

try:
    from installers.enhanced_manifest import EnhancedInstallationManifest
except ImportError:
    print("Warning: Enhanced manifest module not found. Using basic uninstall.")
    from installers.installation_manifest import InstallationManifest as EnhancedInstallationManifest


class EnhancedGiljoUninstaller:
    """Enhanced uninstaller using comprehensive manifest tracking"""

    def __init__(self, install_dir: Path = None):
        """Initialize enhanced uninstaller

        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = Path(install_dir) if install_dir else Path.cwd()
        self.platform = platform.system().lower()

        # Load or create manifest
        self.manifest = EnhancedInstallationManifest(self.install_dir)
        self.manifest.scan_and_update()  # Scan for any untracked components

    def print_banner(self):
        """Print uninstaller banner"""
        print("\n" + "=" * 60)
        print("GiljoAI MCP Orchestrator - Enhanced Uninstaller")
        print("=" * 60)

    def print_installation_report(self):
        """Show what's installed before uninstalling"""
        print(self.manifest.generate_uninstall_report())

    def get_user_choice(self) -> str:
        """Get user's uninstallation preference

        Returns:
            User choice: 'partial', 'complete', 'report', or 'cancel'
        """
        print("\nUninstallation Options:")
        print("-" * 40)
        print("1. REPORT - Show what's installed (no changes)")
        print("   Shows all installed components and directories")
        print()
        print("2. PARTIAL - Remove application but keep data & settings")
        print("   Keeps: databases, configs, logs, user data")
        print("   Removes: application files, scripts, shortcuts")
        print()
        print("3. COMPLETE - Remove everything (clean uninstall)")
        print("   Removes: ALL files, data, configs, external directories")
        print("   WARNING: This will delete all your data permanently!")
        print()
        print("4. CANCEL - Exit without making changes")
        print()

        while True:
            choice = input("Select option [1-4]: ").strip()

            if choice == "1":
                return "report"
            elif choice == "2":
                return "partial"
            elif choice == "3":
                # Double confirmation for complete uninstall
                print("\n⚠️  WARNING: Complete uninstall will DELETE ALL DATA!")
                print("This includes:")
                all_dirs = self.manifest.get_all_tracked_directories()
                for d in all_dirs[:5]:  # Show first 5 directories
                    print(f"  - {d}")
                if len(all_dirs) > 5:
                    print(f"  ... and {len(all_dirs) - 5} more directories")

                confirm = input("\nType 'DELETE ALL' to confirm: ").strip()
                if confirm == "DELETE ALL":
                    return "complete"
                else:
                    print("Complete uninstall cancelled.")
                    continue
            elif choice == "4":
                return "cancel"
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")

    def stop_services(self) -> bool:
        """Stop any running GiljoAI services using manifest data

        Returns:
            Success status
        """
        print("\nStopping services...")
        success = True

        # Stop tracked services from manifest
        for service in self.manifest.manifest_data.get("services", []):
            service_name = service["name"]
            service_type = service["type"]

            try:
                if service_type == "windows_service" and self.platform == "windows":
                    print(f"  Stopping {service_name}...")
                    subprocess.run(["sc", "stop", service_name], capture_output=True, timeout=10, check=False)
                    time.sleep(2)
                    print(f"  [OK] Stopped {service_name}")
                elif service_type == "systemd" and self.platform == "linux":
                    subprocess.run(["systemctl", "stop", service_name], capture_output=True, timeout=10, check=False)
                    print(f"  [OK] Stopped {service_name}")
            except Exception as e:
                print(f"  [WARNING] Could not stop {service_name}: {e}")
                success = False

        # Also try stop scripts
        if self.platform == "windows":
            stop_script = self.install_dir / "stop_giljo.bat"
            if stop_script.exists():
                subprocess.run([str(stop_script)], capture_output=True, timeout=10, check=False)
        else:
            stop_script = self.install_dir / "stop_giljo.sh"
            if stop_script.exists():
                subprocess.run(["bash", str(stop_script)], capture_output=True, timeout=10, check=False)

        return success

    def remove_services(self) -> bool:
        """Remove installed services using manifest data

        Returns:
            Success status
        """
        print("\nRemoving services...")
        success = True

        for service in self.manifest.manifest_data.get("services", []):
            service_name = service["name"]
            service_type = service["type"]

            try:
                if service_type == "windows_service" and self.platform == "windows":
                    print(f"  Removing {service_name}...")
                    subprocess.run(["sc", "delete", service_name], capture_output=True, timeout=10, check=False)
                    print(f"  [OK] Removed {service_name}")
                elif service_type == "systemd" and self.platform == "linux":
                    subprocess.run(["systemctl", "disable", service_name], capture_output=True, check=False)
                    service_file = Path(f"/etc/systemd/system/{service_name}.service")
                    if service_file.exists():
                        service_file.unlink()
                    print(f"  [OK] Removed {service_name}")
            except Exception as e:
                print(f"  [WARNING] Could not remove {service_name}: {e}")
                success = False

        return success

    def remove_external_directories(self, keep_user_data: bool = True) -> int:
        """Remove directories created outside installation directory

        Args:
            keep_user_data: Whether to preserve user data directories

        Returns:
            Number of directories removed
        """
        print("\nRemoving external directories...")
        removed = 0

        # Get directories to remove
        if keep_user_data:
            # Get all directories except user data
            all_dirs = set(self.manifest.get_all_tracked_directories())
            user_dirs = set(self.manifest.get_user_data_directories())
            dirs_to_remove = all_dirs - user_dirs - {str(self.install_dir)}
        else:
            # Remove all tracked directories except install dir (handled separately)
            dirs_to_remove = set(self.manifest.get_all_tracked_directories()) - {str(self.install_dir)}

        # Remove directories
        for dir_path in sorted(dirs_to_remove):
            dir_obj = Path(dir_path)
            if dir_obj.exists():
                try:
                    # Special handling for home directories with both naming conventions
                    if ".giljo_mcp" in str(dir_path) or ".giljo-mcp" in str(dir_path):
                        print(f"  Removing home config: {dir_path}")
                    else:
                        print(f"  Removing: {dir_path}")

                    shutil.rmtree(dir_obj)
                    removed += 1
                    print(f"    [OK] Removed")
                except Exception as e:
                    print(f"    [FAIL] Could not remove: {e}")

        if removed == 0:
            print("  [INFO] No external directories to remove")

        return removed

    def remove_dependencies(self) -> bool:
        """Remove or note installed dependencies

        Returns:
            Success status
        """
        print("\nChecking dependencies...")

        # Redis - removed as not actually implemented
        # Legacy check for old installations that may have Redis
        redis_info = self.manifest.manifest_data["dependencies"].get("redis", {})
        if redis_info.get("installed"):
            print("\n  Redis (Legacy - no longer used):")
            print("    [INFO] Redis is no longer required by GiljoAI MCP")
            print("    [INFO] You may uninstall Redis separately if not needed")

        # PostgreSQL - just note it
        pg_info = self.manifest.manifest_data["dependencies"].get("postgresql", {})
        if pg_info.get("installed"):
            print("\n  PostgreSQL:")
            print(f"    [INFO] PostgreSQL detected at: {pg_info.get('location', 'Unknown')}")
            print("    [INFO] Please use PostgreSQL's uninstaller to remove it properly")
            if pg_info.get("data_directory"):
                print(f"    [INFO] Data directory: {pg_info['data_directory']}")

        # Docker - just note it
        docker_info = self.manifest.manifest_data["dependencies"].get("docker", {})
        if docker_info.get("installed"):
            print("\n  Docker:")
            if docker_info.get("containers"):
                print(f"    [INFO] Active containers: {', '.join(docker_info['containers'])}")
                print("    [INFO] Use 'docker rm' to remove containers")
            if docker_info.get("volumes"):
                print(f"    [INFO] Volumes: {', '.join(docker_info['volumes'])}")
                print("    [INFO] Use 'docker volume rm' to remove volumes")

        return True

    def remove_application_files(self, keep_user_data: bool = True) -> bool:
        """Remove application files from installation directory

        Args:
            keep_user_data: Whether to preserve user data

        Returns:
            Success status
        """
        print("\nRemoving application files...")

        # Patterns to remove (application files)
        app_patterns = [
            "src", "api", "frontend", "tests", "scripts", "installer", "installers",
            "examples", "migrations", "__pycache__", ".mypy_cache", ".ruff_cache",
            "*.pyc", "*.pyo", "venv", "node_modules"
        ]

        # Patterns to keep for partial uninstall
        keep_patterns = [] if not keep_user_data else [
            "data", "logs", "backups", "exports", "*.db", "*.sqlite",
            "config.yaml", ".env", ".giljo_install_manifest.json"
        ]

        removed_count = 0
        for item in self.install_dir.iterdir():
            should_remove = False
            item_name = item.name

            # Check if should remove
            for pattern in app_patterns:
                if pattern.startswith("*"):
                    if item_name.endswith(pattern[1:]):
                        should_remove = True
                        break
                elif item_name == pattern:
                    should_remove = True
                    break

            # Check if should keep
            if should_remove and keep_user_data:
                for pattern in keep_patterns:
                    if pattern.startswith("*"):
                        if item_name.endswith(pattern[1:]):
                            should_remove = False
                            break
                    elif item_name == pattern:
                        should_remove = False
                        break

            if should_remove:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    print(f"  [OK] Removed: {item.name}")
                    removed_count += 1
                except Exception as e:
                    print(f"  [FAIL] Could not remove {item.name}: {e}")

        # Remove all .py files in root if complete uninstall
        if not keep_user_data:
            for py_file in self.install_dir.glob("*.py"):
                try:
                    py_file.unlink()
                    print(f"  [OK] Removed: {py_file.name}")
                    removed_count += 1
                except Exception as e:
                    print(f"  [FAIL] Could not remove {py_file.name}: {e}")

        if removed_count == 0:
            print("  [INFO] No application files to remove")

        return True

    def perform_uninstall(self, mode: str) -> bool:
        """Perform the actual uninstallation

        Args:
            mode: Uninstallation mode ('partial' or 'complete')

        Returns:
            Success status
        """
        print(f"\nPerforming {mode.upper()} uninstall...")
        print("-" * 40)

        # Stop services first
        self.stop_services()

        if mode == "partial":
            # Partial uninstall - keep user data
            self.remove_services()
            self.remove_application_files(keep_user_data=True)
            self.remove_external_directories(keep_user_data=True)
            print("\n✓ Partial uninstall complete")
            print("  User data and configurations have been preserved")

        elif mode == "complete":
            # Complete uninstall - remove everything
            self.remove_services()
            self.remove_dependencies()
            self.remove_external_directories(keep_user_data=False)
            self.remove_application_files(keep_user_data=False)

            # Finally, try to remove the installation directory itself
            if self.install_dir.exists():
                try:
                    # Remove manifest last
                    manifest_file = self.install_dir / ".giljo_install_manifest.json"
                    if manifest_file.exists():
                        manifest_file.unlink()

                    # Check if directory is empty
                    if not list(self.install_dir.iterdir()):
                        self.install_dir.rmdir()
                        print(f"\n✓ Removed installation directory: {self.install_dir}")
                    else:
                        print(f"\n⚠ Installation directory not empty: {self.install_dir}")
                        print("  Remaining files:")
                        for item in self.install_dir.iterdir():
                            print(f"    - {item.name}")
                except Exception as e:
                    print(f"\n⚠ Could not remove installation directory: {e}")

            print("\n✓ Complete uninstall finished")
            print("  All GiljoAI MCP components have been removed")

        return True

    def run(self) -> int:
        """Main uninstaller execution

        Returns:
            Exit code (0 for success)
        """
        self.print_banner()

        # Get user choice
        choice = self.get_user_choice()

        if choice == "cancel":
            print("\nUninstallation cancelled")
            return 0

        elif choice == "report":
            self.print_installation_report()
            print("\nNo changes made. Run uninstaller again to remove components.")
            return 0

        elif choice in ["partial", "complete"]:
            # Show what will be removed
            print("\nThe following will be removed:")
            if choice == "partial":
                print("  • Application files and scripts")
                print("  • External configuration directories")
                print("  • Services and shortcuts")
                print("\nThe following will be KEPT:")
                print("  • User data and databases")
                print("  • Logs and backups")
                print("  • Configuration files")
            else:
                all_dirs = self.manifest.get_all_tracked_directories()
                for d in all_dirs:
                    print(f"  • {d}")

            confirm = input("\nProceed with uninstallation? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Uninstallation cancelled")
                return 0

            # Perform uninstallation
            if self.perform_uninstall(choice):
                return 0
            else:
                print("\n⚠ Uninstallation completed with warnings")
                return 1

        return 0


def main():
    """Main entry point"""
    try:
        # Check if running from installation directory
        if not Path("src").exists() and not Path(".giljo_install_manifest.json").exists():
            print("Error: Please run this script from the GiljoAI MCP installation directory")
            return 1

        uninstaller = EnhancedGiljoUninstaller()
        return uninstaller.run()

    except KeyboardInterrupt:
        print("\n\nUninstallation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Uninstaller error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
