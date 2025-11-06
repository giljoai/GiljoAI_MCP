#!/usr/bin/env python3
"""
GiljoAI MCP - Release Simulation & Test Deployment Script
==========================================================

PURPOSE:
    Simulates a "download from GitHub release and extract" experience by copying
    only the files that would be included in a GitHub release archive.

WHAT IT DOES:
    1. Reads exclusion rules from .gitattributes (export-ignore)
    2. Copies ONLY release-ready files (no dev files, tests, logs, etc.)
    3. Preserves existing data if updating an installation
    4. Simulates what a user would get downloading GiljoAI_MCP_v2.0.zip

FILE COUNT:
    - Development: ~1,600 files (includes tests, logs, sessions, etc.)
    - Release Simulation: ~400 files (production-ready only)
    - This script copies ~400 files to match GitHub release behavior

USE CASES:
    - Test installation scripts on clean "release" copy
    - Verify installer works with release files (not dev environment)
    - Simulate fresh user download experience
    - Test upgrade scenarios (preserve data option)

TECHNICAL NOTES:
    - Uses robocopy for efficient file copying (Windows)
    - Mirrors .gitattributes export-ignore rules
    - Handles data preservation for upgrade testing
    - Some patterns adjusted for robocopy limitations
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


# Configuration
SOURCE_DIR = Path(__file__).parent
TEST_DIR = Path("C:/install_test/Giljo_MCP")
BACKUP_DIR = Path("C:/install_test/Giljo_MCP_backup")

# Directories to preserve
PRESERVE_DIRS = ["data", "logs", "backups", "projects"]
PRESERVE_FILES = [".env", "config.yaml"]

# ============================================================================
# DOCUMENTATION POLICY FOR RELEASES
# ============================================================================
# KEEP (User-Facing):
#   Root:
#     - README.md, INSTALLATION.md, CLAUDE.md, CONTRIBUTING.md, SECURITY.md
#     - LICENSE, PROJECT_CONNECTION.md
#   docs/:
#     - ARCHITECTURE_V2.md, TECHNICAL_ARCHITECTURE.md (architecture)
#     - AI_TOOL_INTEGRATION.md (user guide we just created)
#     - color_themes.md (UI customization)
#     - installer_user_guide.md, installer_troubleshooting.md (user-facing)
#
# EXCLUDE (Development/Internal):
#   Root:
#     - NEXT_AGENT_*, PHASE*, context recovery.md, POSTGRESQL_MIGRATION.md
#     - *_REPORT.md, *_summary.md, GILTEST_README.md
#   docs/:
#     - Sessions/, devlog/, adr/, backup_pre_subagent/, design/, component_specs/
#     - AGENT_INSTRUCTIONS.md, audit_report*.md, linting_*.md, PROJECT_*.md
#     - All internal planning, reports, and development guides
# ============================================================================

# Exclusions for copy - based on .gitattributes export-ignore rules
# This matches what GitHub releases exclude
EXCLUDE_DIRS = [
    # Version control
    ".git",
    ".github",  # Keep workflows out of test copy
    # Development environments
    "venv",
    ".venv",
    "env",
    "ENV",
    # Python caches and build
    "__pycache__",
    ".eggs",
    "*.egg-info",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "coverage",
    # Node/frontend build
    "node_modules",
    # IDE and editor
    ".vscode",
    ".idea",
    ".claude",
    # Development directories
    ".serena",  # Serena MCP cache
    "tests",
    "Tests",
    "test",
    "Test",  # All test directories
    "benchmark*",
    "performance*",
    "scratch",
    "drafts",
    # Documentation directories not for release (from .gitattributes)
    "docs/Sessions",
    "docs/sessions",  # Development session logs
    "docs/devlog",  # Development logs
    "docs/Vision",
    "docs/vision",  # Internal vision docs
    "docs/Development",
    "docs/development",  # Development docs
    "docs/adr",  # Architecture Decision Records (internal)
    "docs/planning",  # Planning docs
    "docs/templates",  # Templates (internal)
    "docs/tests",  # Test documentation
    "docs/techdebt",  # Technical debt documentation
    "docs/backup_pre_subagent",  # Backup documentation (internal)
    "docs/design",  # Design docs (internal)
    "docs/component_specs",  # Component specs (internal)
    "docs/dependencies",  # Dependency analysis (internal)
    "agent_comms",  # Agent communication files
    "sessions",  # Session memory files (root level)
    "devlog",  # DevLog files (root level)
    # Temp directories
    "tmp",
    "temp",
    "backups",
    # Data directories (user will create their own)
    "data",
    "logs",
    "secrets",
    "credentials",
]

EXCLUDE_FILES = [
    # Python files
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    # Test files (from .gitattributes)
    "test_*.py",
    "*_test.py",
    "*.test.py",
    "conftest.py",
    "pytest.ini",
    "*test_results*.json",
    "*test_report*.json",
    "*validation_results*.json",
    "*validation_report*.json",
    "test_*.db",
    "test_*.db-shm",
    "test_*.db-wal",
    # Coverage files (from .gitattributes)
    "coverage*.*",
    "*coverage*.py",
    "*coverage*.md",
    "*coverage*.json",
    "*coverage*.xml",
    "*coverage*.html",
    ".coverage",
    # Benchmark and performance files (from .gitattributes)
    "benchmark*.py",
    "*benchmark*.py",
    "performance*.py",
    "*performance*.py",
    # Debug and monitoring tools (from .gitattributes)
    "debug*.py",
    "*debug*.py",
    "monitor*.py",
    "*monitor*.py",
    "*_monitor.py",
    "visual_*.py",
    # Development scripts (from .gitattributes)
    "fix_*.py",
    "final_*.py",
    "run_*.py",
    "create_distribution.*",
    # Development configs
    ".gitignore",
    ".gitignore.release",
    ".gitattributes",
    ".dockerignore",
    ".coveragerc",
    ".pre-commit-config.yaml",
    ".claude*",  # Claude AI config files
    ".eslintrc*",
    ".prettierrc*",
    "tsconfig.json",
    "jest.config.*",
    "ruff.toml",
    ".ruff.toml",  # Python linter/formatter configs
    # NOTE: pyproject.toml is NEEDED for package installation - DO NOT EXCLUDE
    # Environment and config files
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.p12",
    ".env.local",
    ".env.development",
    ".env.dev",
    ".env.test",
    "config.yaml",
    "config.yml",  # User configs trigger reinstall
    # Logs and databases (from .gitattributes)
    "*.log",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    # Temp and backup files (from .gitattributes)
    "*.tmp",
    "*.temp",
    "*.TMP",
    "*.TEMP",
    "*.bak",
    "*.BAK",
    "*.backup",
    "*.old",
    "*.OLD",
    "*.orig",
    "*~",
    ".~*",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "Thumbs.db",
    "Desktop.ini",
    ".AppleDouble",
    ".LSOverride",
    "ehthumbs.db",
    ".directory",
    # Work in progress files (from .gitattributes)
    "*WIP*",
    "*wip*",
    "*draft*",
    "*DRAFT*",
    # Development docs (from .gitattributes)
    "TODO.md",
    "NOTES.md",
    "ROADMAP.md",
    "PLANNING.md",
    "BACKLOG.md",
    "*_INTERNAL.md",
    "*.md.bak",
    # Note: robocopy doesn't support **/ patterns, using simple wildcards
    "VISION*.md",
    "vision*.md",
    "project_*.md",
    "PROJECT_*.md",
    "workflow*.md",
    "WORKFLOW*.md",
    "management*.md",
    "MANAGEMENT*.md",
    "TEST_*.md",
    "WEBSOCKET_*.md",
    "session_*.md",
    "devlog*.md",
    "NEXT_AGENT_MISSION.md",  # Agent task files
    "NEXT_AGENT_HANDOFF.md",  # Agent handoff files
    "context recovery.md",  # Development context
    # Internal docs in docs/ folder (keep ARCHITECTURE_V2.md, TECHNICAL_ARCHITECTURE.md, AI_TOOL_INTEGRATION.md, color_themes.md)
    "AGENT_INSTRUCTIONS.md",  # Internal agent guide
    "audit_report*.md",  # Internal audits
    "forensic_*.md",  # Internal analysis
    "integration_report*.md",  # Internal reports
    "linting_*.md",  # Internal linting docs
    "performance_analysis*.md",  # Internal performance
    "phase_*.md",  # Internal phase docs
    "unification_*.md",  # Internal reports
    "backend_enhancements*.md",  # Internal planning
    "gui_*.md",  # Internal GUI docs
    "installer_developer_guide.md",  # Internal (developer)
    "installer_implementation_checklist.md",  # Internal
    "installer_ux_redesign_plan.md",  # Internal planning
    "CONFIGURATION_AND_REFERENCE_INDEX.md",  # Internal
    "DEPENDENCIES.md",  # Internal dependency list
    "MESSAGE_QUEUE_GUIDE.md",  # Internal (could be kept if user-facing?)
    "PRODUCT_*.md",  # Internal product docs
    "PROJECT_*.md",  # Internal project docs
    "PROVEN_FEATURES*.md",  # Internal
    "README_FIRST.md",  # Internal
    "SUB_AGENT_*.md",  # Internal
    "Techdebt*.md",  # Internal tech debt
    "PRODUCTION_READINESS*.md"  # Internal certification
    # Deprecated files (v2.0 architecture)
    "*.deprecated",  # All deprecated files
    "__main__.py.deprecated",
    "server.py.deprecated",
    # Reports (from .gitattributes)
    "PRODUCTION_READINESS_REPORT.md",
    "FINAL_CLEAN_COVERAGE_REPORT.md",
    "WEBSOCKET_TEST_COVERAGE_REPORT.md",
    "api_coverage_summary.md",
    "coverage_gap_analysis_report.md",
    "dependency_report.json",
    "MANIFEST.txt",
    # Agent files (from .gitattributes)
    "*_agent_*.json",
    "orchestrator_*.json",
    # Specific exclusions
    "test_installation.py",  # Our test script
    "test_mcp_registration.py",  # MCP test script
    "cleanup_mcp_test.py",  # MCP cleanup script
    # setup_*.py files removed - use installer/cli/install.py instead
    "integrate_mcp.py",  # Dev integration script
    "giltest.py",  # This deployment script itself
    "giltest.bat",  # The batch wrapper
    ".mcp.json",  # MCP config
    "commit.bat",  # Git helper
    # Session and personal files
    "PHASE*.md",
    "PHASE*.jsonl",
    # Migration and update docs (internal)
    "POSTGRESQL_MIGRATION.md",
    # Build and distribution
    "create_shortcuts.py",
    # Testing documentation (internal)
    "GILTEST_README.md",
]


def print_header(quick_sync=False):
    """Print script header"""
    print("=" * 70)
    if quick_sync:
        print("  GiljoAI MCP - Quick Sync (Recent Changes Only)")
    else:
        print("  GiljoAI MCP - Release Simulation & Test Deployment")
    print("=" * 70)
    print()
    if quick_sync:
        print("This script copies ONLY files changed in the last 2 minutes.")
        print("Perfect for rapid testing of recent code changes.")
    else:
        print("This script simulates downloading and extracting a GitHub release.")
        print("It copies ONLY files that would be in a release archive (no dev files).")
    print()
    print(f"Source (Development): {SOURCE_DIR}")
    print(f"Target (Release Test): {TEST_DIR}")
    print()
    if not quick_sync:
        print("Exclusions: Using .gitattributes export-ignore rules")
        print("Expected: ~400 files (vs ~1,600 in development)")
    print()

    # Verify source directory
    if not SOURCE_DIR.exists():
        print("\nERROR: Source directory does not exist!")
        sys.exit(1)

    # Show what's in source
    print("\nSource directory contains:")
    items = list(SOURCE_DIR.iterdir())[:10]  # Show first 10 items
    for item in items:
        if item.is_dir():
            print(f"  - {item.name}/")
        else:
            print(f"  - {item.name}")
    if len(list(SOURCE_DIR.iterdir())) > 10:
        print(f"  ... and {len(list(SOURCE_DIR.iterdir())) - 10} more items")
    print()


def check_existing_installation():
    """Check if test installation exists with data"""
    has_data = (TEST_DIR / "data").exists()
    has_config = (TEST_DIR / ".env").exists() or (TEST_DIR / "config.yaml").exists()

    if TEST_DIR.exists():
        if has_data:
            print("IMPORTANT: Found existing data directory in test installation")
        elif has_config:
            print("Found existing configuration in test installation")
        else:
            print("Found existing installation (no data)")
    else:
        print("No existing installation found")

    return has_data or has_config


def get_user_choice(has_existing):
    """Get user's choice for how to proceed"""
    print()
    print("Select an option:")
    if has_existing:
        print("  1. Preserve data (databases, projects, logs) - Recommended")
    else:
        print("  1. Preserve data (databases, projects, logs) - N/A")
    print("  2. Clean install (delete everything)")
    print("  3. Quick sync (copy only files changed in last 2 minutes)")
    print("  4. Cancel operation")
    print()

    while True:
        choice = input("Enter choice (1/2/3/4): ").strip()

        if choice == "4":
            print("Operation cancelled.")
            return None

        if choice == "1":
            if not has_existing:
                print("No existing data to preserve. Proceeding with clean install.")
                return "clean"
            return "preserve"

        if choice == "2":
            confirm = input("\nWARNING: Delete everything? (Y/N): ").strip().upper()
            if confirm == "Y":
                return "clean"
            print("Cancelled.\n")
            continue

        if choice == "3":
            if not has_existing:
                print("ERROR: Test directory does not exist!")
                print("Run option 1 or 2 first to create the initial deployment.\n")
                continue
            return "quick"

        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def backup_data():
    """Backup important data and configuration"""
    print("\n[1/5] Backing up important data...")

    # Clean backup directory
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    BACKUP_DIR.mkdir(parents=True)

    backed_up = []

    # Backup directories
    for dir_name in PRESERVE_DIRS:
        src = TEST_DIR / dir_name
        if src.exists():
            dst = BACKUP_DIR / dir_name
            shutil.copytree(src, dst)
            backed_up.append(dir_name)
            print(f"      Backed up: {dir_name}/")

    # Backup files
    for file_name in PRESERVE_FILES:
        src = TEST_DIR / file_name
        if src.exists():
            dst = BACKUP_DIR / file_name
            shutil.copy2(src, dst)
            backed_up.append(file_name)
            print(f"      Backed up: {file_name}")

    if backed_up:
        print("      Backup complete!")
    else:
        print("      Nothing to backup")

    return backed_up


def clean_directory(preserve_mode=False):
    """Clean the test directory"""
    if preserve_mode:
        print("[2/5] Cleaning test directory (preserving data)...")

        # Delete everything except preserved directories
        for item in TEST_DIR.iterdir():
            if item.is_dir():
                if item.name not in PRESERVE_DIRS:
                    shutil.rmtree(item)
            elif item.name not in PRESERVE_FILES:
                item.unlink()
    else:
        print("[1/3] Cleaning test directory...")
        if TEST_DIR.exists():
            try:
                shutil.rmtree(TEST_DIR)
                print("      Removed old test directory")
            except Exception as e:
                print(f"ERROR: Could not remove {TEST_DIR}")
                print(f"      {e}")
                print("Make sure no programs are using files in that directory.")
                return False

    return True


def copy_files_quick_sync():
    """Copy only files changed in the last 2 minutes"""
    print("[1/2] Scanning for recently changed files...")

    # Ensure target exists
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    # Calculate cutoff time (2 minutes ago)
    cutoff_time = time.time() - (2 * 60)

    # Find recently modified files
    recent_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            # Skip excluded files
            if any(
                file == pattern or (pattern.startswith("*") and file.endswith(pattern[1:])) for pattern in EXCLUDE_FILES
            ):
                continue

            src_path = Path(root) / file
            try:
                if src_path.stat().st_mtime > cutoff_time:
                    recent_files.append(src_path)
            except Exception:
                continue

    if not recent_files:
        print("      No files changed in the last 2 minutes")
        return True

    print(f"      Found {len(recent_files)} recently changed file(s)")
    print()

    # Copy each recent file
    print("[2/2] Copying recently changed files...")
    copied_count = 0
    for src_path in recent_files:
        # Calculate relative path and destination
        rel_path = src_path.relative_to(SOURCE_DIR)
        dst_path = TEST_DIR / rel_path

        # Create parent directory if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        try:
            shutil.copy2(src_path, dst_path)
            copied_count += 1
            print(f"      Copied: {rel_path}")
        except Exception as e:
            print(f"      Failed: {rel_path} - {e}")

    print()
    print(f"      Successfully copied {copied_count} file(s)")
    return True


def copy_files(preserve_mode=False):
    """Copy files using robocopy"""
    if preserve_mode:
        print("[3/5] Copying updated files...")
        # Exclude data directories when preserving
        exclude_dirs = EXCLUDE_DIRS + PRESERVE_DIRS
        exclude_files = EXCLUDE_FILES + PRESERVE_FILES + ["giljo_mcp.db"]
    else:
        print("[2/3] Copying files...")
        exclude_dirs = EXCLUDE_DIRS
        exclude_files = EXCLUDE_FILES

    print("      This may take a moment...")

    # Ensure target exists
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    # Build robocopy command
    cmd = [
        "robocopy",
        str(SOURCE_DIR),
        str(TEST_DIR),
        "/E",  # Copy subdirectories including empty ones
    ]

    # Add exclusions
    for dir_pattern in exclude_dirs:
        cmd.extend(["/XD", dir_pattern])

    for file_pattern in exclude_files:
        cmd.extend(["/XF", file_pattern])

    # Show the command being run
    print("\n      Running robocopy command:")
    print(f"      Source: {SOURCE_DIR}")
    print(f"      Target: {TEST_DIR}")
    print(f"      Excluding dirs: {', '.join(exclude_dirs)}")
    print(f"      Excluding files: {', '.join(exclude_files)}")
    print()

    # Run robocopy with visible output
    print("      Copy progress:")
    print("-" * 50)
    result = subprocess.run(cmd, check=False, text=True)
    print("-" * 50)

    # Robocopy exit codes 0-7 are success
    if result.returncode <= 7:
        # Count what was copied
        file_count = 0
        dir_count = 0
        for root, dirs, files in os.walk(TEST_DIR):
            dir_count += len(dirs)
            file_count += len(files)

        print("\n      Copy complete!")
        print(f"      Copied {file_count} files in {dir_count} directories")

        # Show sample of what was copied
        print("\n      Sample of copied items:")
        items_shown = 0
        for item in TEST_DIR.iterdir():
            if items_shown >= 10:
                print("      ... and more")
                break
            if item.is_dir():
                file_count_in_dir = sum(1 for _ in item.rglob("*") if _.is_file())
                print(f"      {item.name}/ ({file_count_in_dir} files)")
            else:
                print(f"      {item.name}")
            items_shown += 1

        return True
    print(f"\nERROR: Robocopy failed with exit code {result.returncode}")
    print("      Exit codes: 0-7=success, 8=some files failed, 16=serious error")
    return False


def restore_data():
    """Restore backed up data"""
    print("[4/5] Restoring preserved data...")

    restored = []

    # Restore directories
    for dir_name in PRESERVE_DIRS:
        src = BACKUP_DIR / dir_name
        dst = TEST_DIR / dir_name
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)
            restored.append(dir_name)
            print(f"      Restored: {dir_name}/")

    # Restore files
    for file_name in PRESERVE_FILES:
        src = BACKUP_DIR / file_name
        dst = TEST_DIR / file_name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            restored.append(file_name)
            print(f"      Restored: {file_name}")

    # Clean up backup
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)

    if restored:
        print("      Restore complete!")

    return restored


def setup_symlinks():
    """Create symlinks for shared development folders"""
    print("\n[Symlinks] Setting up shared development folders...")

    # Folders to symlink from test -> dev
    SYMLINK_FOLDERS = {
        "docs": SOURCE_DIR / "docs",
        "scripts": SOURCE_DIR / "scripts",
        "examples": SOURCE_DIR / "examples",
        "devlog": SOURCE_DIR / "docs" / "devlog",  # devlog -> docs/devlog
    }

    created = []
    failed = []

    for folder_name, target_path in SYMLINK_FOLDERS.items():
        link_path = TEST_DIR / folder_name

        # Check if target exists in dev repo
        if not target_path.exists():
            print(f"      [SKIP] {folder_name} (target not found in dev repo)")
            continue

        # Remove existing folder/link if it exists
        if link_path.exists():
            if link_path.is_symlink():
                link_path.unlink()
                print(f"      [REMOVE] Removed old symlink: {folder_name}")
            else:
                shutil.rmtree(link_path) if link_path.is_dir() else link_path.unlink()
                print(f"      [REMOVE] Removed real folder: {folder_name}")

        # Create symlink using PowerShell (Windows)
        try:
            cmd = [
                "powershell",
                "-Command",
                f"New-Item -ItemType SymbolicLink -Path '{link_path}' -Target '{target_path}'",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            created.append(folder_name)
            print(f"      [OK] Created symlink: {folder_name} -> {target_path.relative_to(SOURCE_DIR)}")
        except subprocess.CalledProcessError as e:
            failed.append(folder_name)
            print(f"      [FAIL] Could not create symlink for {folder_name}: {e.stderr}")

    if created:
        print(f"\n      Successfully created {len(created)} symlink(s)")
        print("      These folders are now shared with the dev repo:")
        for name in created:
            print(f"        - {name}/")

    if failed:
        print(f"\n      Failed to create {len(failed)} symlink(s): {', '.join(failed)}")

    return created


def verify_deployment(preserved_items=None):
    """Verify the deployment and show summary"""
    print("\n" + "=" * 70)

    # Check if files were actually copied
    if not TEST_DIR.exists():
        print("ERROR: Test directory does not exist!")
        print("=" * 70)
        return False

    # Count files in target
    file_count = 0
    dir_count = 0
    for root, dirs, files in os.walk(TEST_DIR):
        dir_count += len(dirs)
        file_count += len(files)

    if file_count == 0:
        print("ERROR: No files were copied!")
        print("=" * 70)
        print("\nTroubleshooting:")
        print("1. Check if source directory has files")
        print("2. Check robocopy output above for errors")
        print("3. Verify no antivirus is blocking file copy")
        return False

    # Count source files for comparison
    source_file_count = 0
    for root, dirs, files in os.walk(SOURCE_DIR):
        source_file_count += len(files)

    print("SUCCESS: Release Simulation Complete!")
    print("=" * 70)
    print()
    print(f"Release Test Directory: {TEST_DIR}")
    print("File Statistics:")
    print(f"   • Development (source): {source_file_count:,} files")
    print(f"   • Release (copied):     {file_count:,} files")
    print(f"   • Excluded (dev only):  {source_file_count - file_count:,} files")
    print(f"   • Reduction:            {((source_file_count - file_count) / source_file_count * 100):.1f}%")
    print()

    # Show key files that should exist
    print("\nKey files verification:")
    key_files = [
        "bootstrap.py",
        "install.bat",
        "quickstart.sh",
        "setup.py",
        # Note: setup_*.py files removed - use installer/cli/install.py instead
        "requirements.txt",
        "README.md",
        "devuninstall.py",
        "uninstall.py",
    ]

    for file_name in key_files:
        file_path = TEST_DIR / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  [OK] {file_name} ({size:,} bytes)")
        else:
            print(f"  [MISSING] {file_name}")

    if preserved_items:
        print("\nData preservation status:")
        if (TEST_DIR / "data" / "giljo_mcp.db").exists():
            print("  [OK] Database preserved")
        if (TEST_DIR / ".env").exists():
            print("  [OK] Configuration preserved")
        if (TEST_DIR / "projects").exists():
            print("  [OK] Projects preserved")

    # Show what was excluded
    print("\nRelease Simulation Details:")
    print("   Excluded from release (simulating GitHub export-ignore):")
    print("   • Development docs (sessions/, devlog/, docs/Sessions/, docs/adr/)")
    print("   • Internal docs (AGENT_*, PROJECT_*, audit_*, linting_*, etc.)")
    print("   • Test files (tests/, test_*.py, *_test.py)")
    print("   • Development tools (giltest.py, fix_*.py, debug*.py)")
    print("   • Cache and builds (__pycache__/, venv/, .mypy_cache/)")
    print("   • IDE configs (.vscode/, .idea/, .claude/)")
    print("   • Logs and databases (logs/, *.log, *.db)")
    print("   • Git metadata (.git/, .gitignore, .gitattributes)")
    print("   • Coverage and reports (coverage*, *_REPORT.md)")
    print()
    print("   Included in release (user-facing files):")
    print("   - README.md, INSTALLATION.md, CLAUDE.md, LICENSE")
    print("   - devuninstall.py (dev reset), uninstall.py (production)")
    print("   - docs/ARCHITECTURE_V2.md, docs/TECHNICAL_ARCHITECTURE.md")
    print("   - docs/AI_TOOL_INTEGRATION.md (integration guide)")
    print("   - docs/color_themes.md, docs/installer_user_guide.md")
    print()

    print("This simulates what a user gets from GitHub releases:")
    print("   Download -> Extract -> Run install.bat")
    print()

    print("You can now:")
    print(f"  1. Navigate to {TEST_DIR}")
    print("  2. Run install.bat to test installer")
    print("  3. Verify installer works with 'release' files only")
    print()

    return True


def main():
    """Main execution"""
    try:
        # Check for quick sync mode via command line
        quick_sync_cmdline = "--quick" in sys.argv or "-q" in sys.argv

        if quick_sync_cmdline:
            print_header(quick_sync=True)

            if not TEST_DIR.exists():
                print("ERROR: Test directory does not exist!")
                print("Run giltest without --quick first to create the initial deployment.")
                return 1

            if not copy_files_quick_sync():
                return 1

            print()
            print("=" * 70)
            print("Quick sync complete!")
            print("=" * 70)
            print()
            print(f"Test directory: {TEST_DIR}")
            print("Recent changes have been synced.")
            print()
            return 0

        # Normal interactive mode
        print_header(quick_sync=False)

        # Check existing installation
        has_existing = check_existing_installation()

        # Get user choice
        choice = get_user_choice(has_existing)
        if choice is None:
            return 1

        # Handle quick sync from menu
        if choice == "quick":
            if not copy_files_quick_sync():
                return 1

            print()
            print("=" * 70)
            print("Quick sync complete!")
            print("=" * 70)
            print()
            print(f"Test directory: {TEST_DIR}")
            print("Recent changes have been synced.")
            print()
            return 0

        preserve_mode = choice == "preserve"

        # Execute based on choice
        if preserve_mode:
            # Preserve workflow
            backed_up = backup_data()

            if not clean_directory(preserve_mode=True):
                return 1

            print("[3/5] Creating directory structure...")
            TEST_DIR.mkdir(parents=True, exist_ok=True)

            if not copy_files(preserve_mode=True):
                return 1

            restored = restore_data()

            # Setup symlinks to dev repo
            setup_symlinks()

            print("[5/5] Verification...")
            if not verify_deployment(preserved_items=restored):
                return 1

        else:
            # Clean install workflow
            if not clean_directory(preserve_mode=False):
                return 1

            print("[2/3] Creating test directory...")
            TEST_DIR.mkdir(parents=True, exist_ok=True)

            if not copy_files(preserve_mode=False):
                return 1

            # Setup symlinks to dev repo
            setup_symlinks()

            print("[3/3] Verification...")
            if not verify_deployment():
                return 1

        # Ask if user wants to open directory
        open_dir = input("Open test directory in Explorer? (Y/N): ").strip().upper()
        if open_dir == "Y":
            os.startfile(TEST_DIR)

        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
