#!/usr/bin/env python3
"""
Uninstaller for GiljoAI MCP Orchestrator

Provides options for partial (keep data) or complete uninstallation.
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
    from installers.installation_manifest import InstallationManifest
except ImportError:
    print("Warning: Installation manifest module not found. Some features may be limited.")
    InstallationManifest = None


class GiljoUninstaller:
    """Handles uninstallation of GiljoAI MCP Orchestrator"""

    def __init__(self, install_dir: Path = None):
        """Initialize uninstaller

        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = Path(install_dir) if install_dir else Path.cwd()
        self.platform = platform.system().lower()
        self.manifest = None
        self.accessed_folders = set()  # Track all folders accessed during uninstall

        # Try to load installation manifest
        if InstallationManifest:
            self.manifest = InstallationManifest(self.install_dir)

        # Define what to keep in partial uninstall
        self.user_data_patterns = [
            "data/",
            "logs/",
            "config.yaml",
            ".env",
            "*.db",
            "*.sqlite",
            "backup/",
            "exports/",
            "docs/Sessions/",
            ".giljo_install_manifest.json",  # Keep manifest for potential reinstall
        ]

        # Define core application patterns
        self.app_patterns = [
            "src/",
            "api/",
            "frontend/",
            "tests/",
            "scripts/",
            "installers/",
            "*.bat",
            "*.sh",
            "*.py",
            "requirements.txt",
            "package.json",
            "package-lock.json",
        ]

    def track_folder(self, path: Path):
        """Track a folder that was accessed during uninstall

        Args:
            path: Path to add to tracking
        """
        if isinstance(path, str):
            path = Path(path)

        # Add the parent folder if it's a file
        if path.is_file():
            self.accessed_folders.add(str(path.parent))
        else:
            self.accessed_folders.add(str(path))

    def print_banner(self):
        """Print uninstaller banner"""
        print("\n" + "=" * 60)
        print("GiljoAI MCP Orchestrator Uninstaller")
        print("=" * 60)

    def get_user_choice(self) -> str:
        """Get user's uninstallation preference

        Returns:
            User choice: 'partial', 'complete', or 'cancel'
        """
        print("\nUninstallation Options:")
        print("-" * 40)
        print("1. PARTIAL - Remove application but keep data & settings")
        print("   Keeps: databases, configs, logs, user data")
        print("   Removes: application files, scripts, shortcuts")
        print()
        print("2. COMPLETE - Remove everything (clean uninstall)")
        print("   Removes: ALL files, data, configs, and shortcuts")
        print("   WARNING: This will delete all your data permanently!")
        print()
        print("3. CANCEL - Exit without making changes")
        print()

        while True:
            sys.stdout.flush()  # Ensure prompt is displayed
            choice = input("Select option [1-3]: ").strip()

            if choice == "1":
                return "partial"
            elif choice == "2":
                # Double confirmation for complete uninstall
                print("\n[WARNING] Complete uninstall will DELETE ALL DATA!")
                sys.stdout.flush()
                confirm = input("Type 'DELETE ALL' to confirm: ").strip()
                if confirm == "DELETE ALL":
                    return "complete"
                print("Complete uninstall cancelled.")
                continue
            elif choice == "3":
                return "cancel"
            elif choice == "":
                continue  # Ignore empty input
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

    def stop_services(self) -> bool:
        """Stop any running GiljoAI services

        Returns:
            Success status
        """
        print("\nStopping services...")

        try:
            if self.platform == "windows":
                # Try to run stop script if it exists
                stop_script = self.install_dir / "stop_giljo.bat"
                if stop_script.exists():
                    # Don't wait for stop script to complete, just trigger it
                    subprocess.Popen([str(stop_script)])
                    time.sleep(2)  # Give it a moment to start stopping services

                # Force kill by port
                ports = [6000, 6001, 6002]
                for port in ports:
                    cmd = ["cmd", "/c", f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port}') do taskkill /F /PID %a"]
                    subprocess.run(
                        cmd,
                        capture_output=True,
                        check=False,
                    )
            else:
                # Unix-like systems
                stop_script = self.install_dir / "stop_giljo.sh"
                if stop_script.exists():
                    # Don't wait for stop script to complete, just trigger it
                    subprocess.Popen(["bash", str(stop_script)])
                    time.sleep(2)  # Give it a moment to start stopping services

                # Force kill by port
                subprocess.run("pkill -f 'giljo_mcp'", shell=True, capture_output=True, check=False)

            print("  [OK] Services stopped")
            return True

        except Exception as e:
            print(f"  [WARNING] Could not stop services: {e}")
            return False

    def remove_shortcuts(self) -> int:
        """Remove desktop and start menu shortcuts

        Returns:
            Number of shortcuts removed
        """
        removed = 0
        print("\nRemoving shortcuts...")

        if self.manifest:
            # Use manifest to find shortcuts
            try:
                shortcuts = self.manifest.get_all_shortcuts()
                for shortcut in shortcuts:
                    shortcut_path = Path(shortcut["path"])
                    if shortcut_path.exists():
                        try:
                            self.track_folder(shortcut_path)
                            shortcut_path.unlink()
                            print(f"  [OK] Removed: {shortcut_path}")
                            removed += 1
                        except Exception as e:
                            print(f"  [FAIL] Could not remove {shortcut_path}: {e}")
            except (KeyError, AttributeError) as e:
                # Manifest might not have shortcuts section
                print(f"  [INFO] No shortcuts found in manifest")
        else:
            # Fallback: Try common locations
            shortcuts_to_remove = []

            if self.platform == "windows":
                # Desktop
                desktop = Path.home() / "Desktop" / "GiljoAI MCP Orchestrator.lnk"
                if desktop.exists():
                    shortcuts_to_remove.append(desktop)

                # Start Menu
                start_menu = (
                    Path(os.environ.get("APPDATA", ""))
                    / "Microsoft"
                    / "Windows"
                    / "Start Menu"
                    / "Programs"
                    / "GiljoAI MCP"
                )
                if start_menu.exists():
                    shortcuts_to_remove.append(start_menu)

            for shortcut in shortcuts_to_remove:
                try:
                    self.track_folder(shortcut)
                    if shortcut.is_dir():
                        shutil.rmtree(shortcut)
                    else:
                        shortcut.unlink()
                    print(f"  [OK] Removed: {shortcut}")
                    removed += 1
                except Exception as e:
                    print(f"  [FAIL] Could not remove {shortcut}: {e}")

        return removed

    def remove_virtual_environment(self) -> bool:
        """Remove virtual environment

        Returns:
            Success status
        """
        venv_path = self.install_dir / "venv"

        if venv_path.exists():
            print("\nRemoving virtual environment...")
            try:
                self.track_folder(venv_path)
                shutil.rmtree(venv_path)
                print(f"  [OK] Removed: {venv_path}")
                return True
            except Exception as e:
                print(f"  [FAIL] Could not remove virtual environment: {e}")
                return False
        return True

    def remove_redis(self) -> bool:
        """Remove Redis installation and service

        Returns:
            Success status
        """
        print("\nRemoving Redis...")
        removed_something = False

        try:
            # Stop and remove Redis service if it exists
            try:
                result = subprocess.run(["sc", "query", "Redis"], capture_output=True, text=True)
                if result.returncode == 0:
                    print("  Stopping Redis service...")
                    subprocess.run(["sc", "stop", "Redis"], capture_output=True, timeout=10, check=False)
                    time.sleep(2)
                    print("  Removing Redis service...")
                    subprocess.run(["sc", "delete", "Redis"], capture_output=True, timeout=10, check=False)
                    print("  [OK] Redis service removed")
                    removed_something = True
            except Exception as e:
                print(f"  [WARNING] Could not remove Redis service: {e}")

            # Remove Redis installation directories
            redis_paths = [
                Path("C:/Redis"),
                Path("C:/Program Files/Redis"),
                Path("C:/Program Files (x86)/Redis"),
                Path("C:/tools/redis"),  # Chocolatey installation
            ]

            for redis_path in redis_paths:
                if redis_path.exists():
                    try:
                        self.track_folder(redis_path)
                        shutil.rmtree(redis_path)
                        print(f"  [OK] Removed Redis from: {redis_path}")
                        removed_something = True
                    except Exception as e:
                        print(f"  [FAIL] Could not remove {redis_path}: {e}")

            if not removed_something:
                print("  [INFO] No Redis installation found")

            return True

        except Exception as e:
            print(f"  [ERROR] Redis removal failed: {e}")
            return False

    def remove_postgresql(self) -> bool:
        """Remove PostgreSQL installation and service

        Note: This only removes services and notes the installation.
        Full PostgreSQL uninstallation should be done through its uninstaller.

        Returns:
            Success status
        """
        print("\nChecking PostgreSQL...")

        try:
            # Check for PostgreSQL service
            pg_services = ["postgresql-x64-18", "postgresql-x64-16", "postgresql-x64-15", "postgresql-x64-14", "postgresql"]
            found_service = False

            for service_name in pg_services:
                result = subprocess.run(["sc", "query", service_name], capture_output=True, text=True)
                if result.returncode == 0:
                    found_service = True
                    print(f"  [WARNING] PostgreSQL service '{service_name}' found")

            if found_service:
                print("  [INFO] PostgreSQL should be uninstalled using its own uninstaller")
                print("         Go to Control Panel > Programs > Uninstall PostgreSQL")
            else:
                print("  [OK] No PostgreSQL service found")

            # Check for PostgreSQL installation directory
            pg_paths = [
                Path("C:/PostgreSQL"),
                Path("C:/Program Files/PostgreSQL"),
            ]

            for pg_path in pg_paths:
                if pg_path.exists():
                    print(f"  [INFO] PostgreSQL installation found at: {pg_path}")
                    print("         Use PostgreSQL uninstaller to remove completely")

            return True

        except Exception as e:
            print(f"  [ERROR] PostgreSQL check failed: {e}")
            return False

    def get_files_to_remove(self, keep_user_data: bool) -> Tuple[List[Path], List[Path]]:
        """Get lists of files to remove and keep

        Args:
            keep_user_data: Whether to keep user data

        Returns:
            Tuple of (files_to_remove, files_to_keep)
        """
        files_to_remove = []
        files_to_keep = []

        if self.manifest and self.manifest.manifest_file.exists():
            # Use manifest for precise removal
            all_files = self.manifest.get_all_installed_files()

            for file_path_str in all_files:
                file_path = Path(file_path_str)
                file_info = None

                # Get file info from manifest
                files_data = self.manifest.manifest_data.get("files", {})
                for info in files_data.values():
                    if info["absolute_path"] == file_path_str:
                        file_info = info
                        break

                if keep_user_data and file_info and file_info.get("is_user_data", False):
                    files_to_keep.append(file_path)
                else:
                    files_to_remove.append(file_path)
        else:
            # Fallback: Use pattern matching
            for item in self.install_dir.iterdir():
                if keep_user_data:
                    # Check if it matches user data patterns
                    is_user_data = False
                    for pattern in self.user_data_patterns:
                        if pattern.endswith("/"):
                            if item.is_dir() and item.name == pattern[:-1]:
                                is_user_data = True
                                break
                        elif "*" in pattern:
                            if item.match(pattern):
                                is_user_data = True
                                break
                        elif item.name == pattern:
                            is_user_data = True
                            break

                    if is_user_data:
                        files_to_keep.append(item)
                    else:
                        files_to_remove.append(item)
                else:
                    files_to_remove.append(item)

        return files_to_remove, files_to_keep

    def perform_partial_uninstall(self) -> bool:
        """Perform partial uninstallation (keep user data)

        Returns:
            Success status
        """
        print("\n" + "=" * 60)
        print("PERFORMING PARTIAL UNINSTALL")
        print("=" * 60)

        # Stop services
        self.stop_services()

        # Remove shortcuts
        shortcuts_removed = self.remove_shortcuts()
        print(f"  Shortcuts removed: {shortcuts_removed}")

        # Remove virtual environment
        self.remove_virtual_environment()

        # Remove dependencies (Redis, PostgreSQL)
        self.remove_redis()
        self.remove_postgresql()

        # Get files to remove
        try:
            files_to_remove, files_to_keep = self.get_files_to_remove(keep_user_data=True)
        except (KeyError, AttributeError) as e:
            # Manifest might be missing or incomplete, use fallback
            files_to_remove = []
            files_to_keep = []

        # Show what will be kept
        if files_to_keep:
            print("\nPreserving user data:")
            for file in files_to_keep[:10]:  # Show first 10
                print(f"  [KEEP] {file.name}")
            if len(files_to_keep) > 10:
                print(f"  ... and {len(files_to_keep) - 10} more items")

        # Remove application files
        print("\nRemoving application files...")
        removed_count = 0
        failed_count = 0

        for file_path in files_to_remove:
            try:
                if file_path.exists():
                    self.track_folder(file_path)
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()
                    removed_count += 1
            except Exception as e:
                print(f"  [FAIL] Could not remove {file_path.name}: {e}")
                failed_count += 1

        print(f"\n  Files removed: {removed_count}")
        if failed_count > 0:
            print(f"  Failed to remove: {failed_count}")

        # Create uninstall receipt
        self.create_uninstall_receipt(partial=True, files_kept=files_to_keep)

        return failed_count == 0

    def perform_complete_uninstall(self) -> bool:
        """Perform complete uninstallation (remove everything)

        Returns:
            Success status
        """
        print("\n" + "=" * 60)
        print("PERFORMING COMPLETE UNINSTALL")
        print("=" * 60)

        # Stop services
        self.stop_services()

        # Remove shortcuts
        shortcuts_removed = self.remove_shortcuts()
        print(f"  Shortcuts removed: {shortcuts_removed}")

        # Backup critical data before deletion (optional)
        backup_created = self.create_backup()

        print("\nRemoving all files and directories...")

        # Try to get files from manifest, but don't fail if it doesn't work
        try:
            files_to_remove, _ = self.get_files_to_remove(keep_user_data=False)
        except (KeyError, AttributeError) as e:
            # Manifest might be missing or incomplete, just remove everything
            files_to_remove = []

        removed_count = 0
        failed_count = 0
        failed_items = []

        # Remove all files and directories
        for item in self.install_dir.iterdir():
            # Skip the uninstaller itself
            if item.name == "uninstall.py" or item.name == "__pycache__":
                continue

            try:
                self.track_folder(item)
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed_count += 1
                print(f"  [OK] Removed: {item.name}")
            except Exception as e:
                print(f"  [FAIL] Could not remove {item.name}: {e}")
                failed_count += 1
                failed_items.append(item.name)

        print(f"\n  Items removed: {removed_count}")
        if failed_count > 0:
            print(f"  Failed to remove: {failed_count}")
            print("  Failed items:")
            for item in failed_items:
                print(f"    - {item}")

        # Create uninstall receipt
        self.create_uninstall_receipt(partial=False, backup_path=backup_created)

        # Remove manifest file if it exists
        manifest_file = self.install_dir / ".giljo_install_manifest.json"
        if manifest_file.exists():
            try:
                manifest_file.unlink()
            except:
                pass

        return failed_count == 0

    def create_backup(self) -> Optional[Path]:
        """Create backup of critical user data before complete uninstall

        Returns:
            Path to backup or None if no backup created
        """
        try:
            import tempfile
            import zipfile
            from datetime import datetime

            # Check if there's data worth backing up
            data_dir = self.install_dir / "data"
            config_file = self.install_dir / "config.yaml"

            if not data_dir.exists() and not config_file.exists():
                return None

            print("\nCreating backup of user data...")

            # Create backup in temp directory
            backup_name = f"giljo_mcp_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = Path(tempfile.gettempdir()) / backup_name

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Backup data directory
                if data_dir.exists():
                    for file in data_dir.rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(self.install_dir))

                # Backup config
                if config_file.exists():
                    zf.write(config_file, config_file.name)

                # Backup manifest
                manifest_file = self.install_dir / ".giljo_install_manifest.json"
                if manifest_file.exists():
                    zf.write(manifest_file, manifest_file.name)

            print(f"  [OK] Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            print(f"  [WARNING] Could not create backup: {e}")
            return None

    def print_access_summary(self):
        """Print summary of folders that were accessed during uninstallation"""
        if not self.accessed_folders:
            return

        print("\n" + "=" * 60)
        print("UNINSTALLATION SUMMARY")
        print("=" * 60)
        print("\nFolders accessed during uninstallation:")
        print("-" * 40)

        # Sort and categorize folders
        system_folders = []
        appdata_folders = []
        program_folders = []
        install_folders = []

        appdata_path = os.environ.get("APPDATA", "")
        localappdata_path = os.environ.get("LOCALAPPDATA", "")
        programfiles = os.environ.get("PROGRAMFILES", "")
        programfiles_x86 = os.environ.get("PROGRAMFILES(X86)", "")

        for folder in sorted(self.accessed_folders):
            folder_lower = folder.lower()

            if appdata_path and appdata_path.lower() in folder_lower:
                appdata_folders.append(folder)
            elif localappdata_path and localappdata_path.lower() in folder_lower:
                appdata_folders.append(folder)
            elif programfiles and programfiles.lower() in folder_lower:
                program_folders.append(folder)
            elif programfiles_x86 and programfiles_x86.lower() in folder_lower:
                program_folders.append(folder)
            elif "system32" in folder_lower or "windows" in folder_lower:
                system_folders.append(folder)
            else:
                install_folders.append(folder)

        # Print categorized folders
        if install_folders:
            print("\nInstallation directory:")
            for folder in install_folders:
                print(f"  • {folder}")

        if appdata_folders:
            print("\nApplication data folders (AppData):")
            for folder in appdata_folders:
                print(f"  • {folder}")

        if program_folders:
            print("\nProgram Files folders:")
            for folder in program_folders:
                print(f"  • {folder}")

        if system_folders:
            print("\nSystem folders:")
            for folder in system_folders:
                print(f"  • {folder}")

        print("\n" + "=" * 60)

    def create_uninstall_receipt(self, partial: bool, files_kept: List[Path] = None, backup_path: Path = None):
        """Create an uninstall receipt/log

        Args:
            partial: Whether this was a partial uninstall
            files_kept: List of files that were kept
            backup_path: Path to backup if created
        """
        try:
            from datetime import datetime

            receipt_name = f"giljo_uninstall_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            receipt_path = Path.home() / receipt_name

            with open(receipt_path, "w") as f:
                f.write("GiljoAI MCP Uninstall Receipt\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Date: {datetime.now().isoformat()}\n")
                f.write(f"Type: {'Partial' if partial else 'Complete'} Uninstall\n")
                f.write(f"Install Directory: {self.install_dir}\n")

                if backup_path:
                    f.write(f"\nBackup Created: {backup_path}\n")

                if partial and files_kept:
                    f.write("\nFiles/Directories Preserved:\n")
                    for file in files_kept:
                        f.write(f"  - {file}\n")

                f.write("\n" + "=" * 60 + "\n")
                f.write("Uninstallation completed.\n")

                if partial:
                    f.write("\nTo reinstall: Run install.bat (Windows) or ./quickstart.sh (Unix)\n")
                    f.write("Your data and settings have been preserved.\n")

            print(f"\nUninstall receipt saved to: {receipt_path}")

        except Exception as e:
            print(f"Could not create uninstall receipt: {e}")

    def run(self) -> int:
        """Main uninstaller execution

        Returns:
            Exit code (0 for success)
        """
        self.print_banner()

        # Check if we're in the right directory
        if not (self.install_dir / "install.bat").exists() and not (self.install_dir / "quickstart.sh").exists():
            print("\n[WARNING] Installation files not found in current directory!")
            print(f"Current directory: {self.install_dir}")
            response = input("\nContinue anyway? [y/N]: ").strip().lower()
            if response != "y":
                print("Uninstall cancelled.")
                return 1

        # Show installation info if available
        if self.manifest and self.manifest.manifest_file.exists():
            info = self.manifest.get_installation_info()
            print("\nInstallation found:")
            print(f"  Version: {info.get('version', 'Unknown')}")
            print(f"  Installed: {info.get('installation_date', 'Unknown')}")
            print(f"  Directory: {info.get('install_directory', 'Unknown')}")

        # Get user choice
        choice = self.get_user_choice()

        if choice == "cancel":
            print("\nUninstall cancelled.")
            return 0
        if choice == "partial":
            success = self.perform_partial_uninstall()
        else:  # complete
            success = self.perform_complete_uninstall()

        # Print summary of accessed folders
        self.print_access_summary()

        if success:
            print("\n" + "=" * 60)
            print("[SUCCESS] Uninstallation completed successfully!")
            print("=" * 60)

            if choice == "partial":
                print("\nYour data and settings have been preserved.")
                print("You can reinstall GiljoAI MCP anytime by running the quickstart script.")
            else:
                print("\nAll GiljoAI MCP files have been removed.")
                print("Thank you for using GiljoAI MCP Orchestrator!")

            return 0
        print("\n" + "=" * 60)
        print("[WARNING] Uninstallation completed with warnings")
        print("=" * 60)
        print("Some files could not be removed. Please check the output above.")
        return 1


def main():
    """Main entry point"""
    try:
        uninstaller = GiljoUninstaller()
        return uninstaller.run()
    except KeyboardInterrupt:
        print("\n\nUninstall cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Uninstaller error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
