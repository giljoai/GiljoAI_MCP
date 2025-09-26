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
            choice = input("Select option [1-3]: ").strip()

            if choice == "1":
                return "partial"
            if choice == "2":
                # Double confirmation for complete uninstall
                print("\n⚠️  WARNING: Complete uninstall will DELETE ALL DATA!")
                confirm = input("Type 'DELETE ALL' to confirm: ").strip()
                if confirm == "DELETE ALL":
                    return "complete"
                print("Complete uninstall cancelled.")
                continue
            if choice == "3":
                return "cancel"
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
                    subprocess.run([str(stop_script)], capture_output=True, timeout=10, check=False)

                # Force kill by port
                ports = [6000, 6001, 6002]
                for port in ports:
                    subprocess.run(
                        f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port}') do taskkill /F /PID %a",
                        shell=True,
                        capture_output=True,
                        check=False,
                    )
            else:
                # Unix-like systems
                stop_script = self.install_dir / "stop_giljo.sh"
                if stop_script.exists():
                    subprocess.run(["bash", str(stop_script)], capture_output=True, timeout=10, check=False)

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
            for shortcut in self.manifest.get_all_shortcuts():
                shortcut_path = Path(shortcut["path"])
                if shortcut_path.exists():
                    try:
                        shortcut_path.unlink()
                        print(f"  [OK] Removed: {shortcut_path}")
                        removed += 1
                    except Exception as e:
                        print(f"  [FAIL] Could not remove {shortcut_path}: {e}")
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
                shutil.rmtree(venv_path)
                print(f"  [OK] Removed: {venv_path}")
                return True
            except Exception as e:
                print(f"  [FAIL] Could not remove virtual environment: {e}")
                return False
        return True

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
                for info in self.manifest.manifest_data["files"].values():
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

        # Get files to remove
        files_to_remove, files_to_keep = self.get_files_to_remove(keep_user_data=True)

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

        # Get all files to remove
        files_to_remove, _ = self.get_files_to_remove(keep_user_data=False)

        removed_count = 0
        failed_count = 0
        failed_items = []

        # Remove all files and directories
        for item in self.install_dir.iterdir():
            # Skip the uninstaller itself
            if item.name == "uninstall.py" or item.name == "__pycache__":
                continue

            try:
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
                    f.write("\nTo reinstall: Run quickstart.bat (Windows) or ./quickstart.sh (Unix)\n")
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
        if not (self.install_dir / "quickstart.bat").exists() and not (self.install_dir / "quickstart.sh").exists():
            print("\n⚠️  WARNING: Installation files not found in current directory!")
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

        if success:
            print("\n" + "=" * 60)
            print("✅ Uninstallation completed successfully!")
            print("=" * 60)

            if choice == "partial":
                print("\nYour data and settings have been preserved.")
                print("You can reinstall GiljoAI MCP anytime by running the quickstart script.")
            else:
                print("\nAll GiljoAI MCP files have been removed.")
                print("Thank you for using GiljoAI MCP Orchestrator!")

            return 0
        print("\n" + "=" * 60)
        print("⚠️  Uninstallation completed with warnings")
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
        print(f"\n❌ Uninstaller error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
