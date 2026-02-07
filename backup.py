#!/usr/bin/env python3
"""
GiljoAI MCP Project Backup Script
==================================
Creates a complete backup of the project (excluding venv) with timestamp.

Usage:
    python backup.py           # Create backup with default settings
    python backup.py --no-git  # Exclude .git directory
    python backup.py --quick   # Exclude large/temporary files
"""

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# Configuration
PROJECT_DIR = Path(__file__).parent
BACKUP_ROOT = Path("C:/Projects/Backups")

# Directories to always exclude
EXCLUDE_DIRS = [
    "venv",
    ".venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".eggs",
    "*.egg-info",
    "htmlcov",
    "dist",
    "build",
]

# Additional excludes for quick backup
QUICK_EXCLUDE_DIRS = [
    "logs",
    "data",
    "temp",
    "tmp",
    "backups",
    "uploads",
    ".serena",
]

QUICK_EXCLUDE_FILES = [
    "*.log",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "*.sqlite",
    "*.sqlite3",
]


def get_backup_folder_name():
    """Generate timestamped backup folder name"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d_%H-%M-%S") + "_Backup"


def get_directory_size(path: Path):
    """Calculate total size of directory"""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return total


def should_exclude_dir(dir_name: str, exclude_list: list) -> bool:
    """Check if directory should be excluded"""
    return dir_name in exclude_list


def should_exclude_file(file_name: str, exclude_patterns: list) -> bool:
    """Check if file matches exclusion patterns"""
    for pattern in exclude_patterns:
        if pattern.startswith("*"):
            if file_name.endswith(pattern[1:]):
                return True
        elif file_name == pattern:
            return True
    return False


def copy_with_exclusions(src: Path, dst: Path, exclude_dirs: list, exclude_files: list = None):
    """Copy directory tree with exclusions"""
    exclude_files = exclude_files or []

    # Create destination
    dst.mkdir(parents=True, exist_ok=True)

    copied_files = 0
    copied_dirs = 0
    skipped_files = 0
    skipped_dirs = 0

    print(f"\nCopying from: {src}")
    print(f"         to: {dst}")
    print("\nProgress:")

    for root, dirs, files in os.walk(src):
        # Get relative path
        rel_root = Path(root).relative_to(src)

        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not should_exclude_dir(d, exclude_dirs)]

        # Count skipped directories
        all_dirs = os.listdir(root) if Path(root).is_dir() else []
        skipped_dirs += len([d for d in all_dirs if Path(root, d).is_dir() and should_exclude_dir(d, exclude_dirs)])

        # Create directory structure
        for dir_name in dirs:
            dst_dir = dst / rel_root / dir_name
            dst_dir.mkdir(parents=True, exist_ok=True)
            copied_dirs += 1

        # Copy files
        for file_name in files:
            if should_exclude_file(file_name, exclude_files):
                skipped_files += 1
                continue

            src_file = Path(root) / file_name
            dst_file = dst / rel_root / file_name

            try:
                shutil.copy2(src_file, dst_file)
                copied_files += 1

                # Print progress every 100 files
                if copied_files % 100 == 0:
                    print(f"  Copied {copied_files} files...")

            except Exception as e:
                print(f"  [ERROR] Failed to copy {src_file.name}: {e}")

    return copied_files, copied_dirs, skipped_files, skipped_dirs


def main():
    parser = argparse.ArgumentParser(
        description="Backup GiljoAI MCP project", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--no-git", action="store_true", help="Exclude .git directory from backup")
    parser.add_argument("--quick", action="store_true", help="Quick backup (exclude logs, data, temp files)")
    parser.add_argument("--auto", action="store_true", help="Auto mode (skip confirmation prompts)")

    args = parser.parse_args()

    # Build exclusion list
    exclude_dirs = EXCLUDE_DIRS.copy()
    exclude_files = []

    if args.no_git:
        exclude_dirs.append(".git")

    if args.quick:
        exclude_dirs.extend(QUICK_EXCLUDE_DIRS)
        exclude_files.extend(QUICK_EXCLUDE_FILES)

    # Create backup folder name
    backup_name = get_backup_folder_name()
    backup_path = BACKUP_ROOT / backup_name

    print("=" * 70)
    print("  GiljoAI MCP Project Backup")
    print("=" * 70)
    print()
    print(f"Project:     {PROJECT_DIR}")
    print(f"Backup to:   {backup_path}")
    print(f"Mode:        {'Quick' if args.quick else 'Full'}")
    print(f"Include git: {'No' if args.no_git else 'Yes'}")
    print()
    print("Excluding:")
    for exc in exclude_dirs:
        print(f"  - {exc}/")
    if exclude_files:
        for exc in exclude_files:
            print(f"  - {exc}")
    print()

    # Calculate source size
    print("Calculating source size...")
    source_size = get_directory_size(PROJECT_DIR)
    print(f"Source size: {source_size / (1024 * 1024):.1f} MB")
    print()

    # Confirm
    if not args.auto:
        confirm = input("Proceed with backup? (Y/N): ").strip().upper()
        if confirm != "Y":
            print("Backup cancelled.")
            return 1
    else:
        print("Auto mode: Proceeding with backup...")

    print()
    print("Starting backup...")

    # Create backup
    try:
        copied_files, copied_dirs, skipped_files, skipped_dirs = copy_with_exclusions(
            PROJECT_DIR, backup_path, exclude_dirs, exclude_files
        )

        # Calculate backup size
        backup_size = get_directory_size(backup_path)

        print()
        print("=" * 70)
        print("  Backup Complete!")
        print("=" * 70)
        print()
        print(f"Backup location: {backup_path}")
        print()
        print("Statistics:")
        print(f"  Files copied:    {copied_files:,}")
        print(f"  Dirs copied:     {copied_dirs:,}")
        print(f"  Files skipped:   {skipped_files:,}")
        print(f"  Dirs skipped:    {skipped_dirs:,}")
        print()
        print(f"  Source size:     {source_size / (1024 * 1024):.1f} MB")
        print(f"  Backup size:     {backup_size / (1024 * 1024):.1f} MB")
        print(f"  Space saved:     {(source_size - backup_size) / (1024 * 1024):.1f} MB")
        print()

        # Ask to open folder
        if not args.auto:
            open_folder = input("Open backup folder? (Y/N): ").strip().upper()
            if open_folder == "Y":
                os.startfile(backup_path)

        return 0

    except Exception as e:
        print()
        print("=" * 70)
        print("  Backup Failed!")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
