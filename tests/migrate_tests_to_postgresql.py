"""
Automated migration script to update test files from SQLite to PostgreSQL.

This script:
1. Replaces SQLite connection strings with PostgreSQL test helpers
2. Updates tempfile-based database creation to use fixtures
3. Removes SQLite-specific imports
4. Updates fixture dependencies

Usage:
    python tests/migrate_tests_to_postgresql.py --dry-run  # Preview changes
    python tests/migrate_tests_to_postgresql.py            # Apply changes
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple


class TestMigrator:
    """Migrates test files from SQLite to PostgreSQL."""

    # Patterns to find and replace
    PATTERNS = [
        # SQLite connection strings
        (
            r'["\']sqlite\+aiosqlite:///[^"\']*["\']',
            "PostgreSQLTestHelper.get_test_db_url()",
            "Replace SQLite async connection string with PostgreSQL helper",
        ),
        (
            r'["\']sqlite:///[^"\']*["\']',
            "PostgreSQLTestHelper.get_test_db_url(async_driver=False)",
            "Replace SQLite sync connection string with PostgreSQL helper",
        ),
        (
            r'["\']sqlite\+aiosqlite:///:memory:["\']',
            "PostgreSQLTestHelper.get_test_db_url()",
            "Replace SQLite in-memory with PostgreSQL test database",
        ),
        # Tempfile database creation
        (
            r"temp_db\s*=\s*tempfile\.NamedTemporaryFile\([^)]*\)",
            "# PostgreSQL test database used instead of temp file",
            "Remove tempfile creation",
        ),
        (
            r"temp_db\.close\(\)",
            "# PostgreSQL test database managed by fixtures",
            "Remove tempfile close",
        ),
        (
            r"os\.unlink\(temp_db\.name\)",
            "# PostgreSQL test database cleanup handled by fixtures",
            "Remove file cleanup",
        ),
    ]

    IMPORT_ADDITIONS = """
# PostgreSQL test database helper
from tests.helpers.test_db_helper import PostgreSQLTestHelper
"""

    def __init__(self, dry_run: bool = False):
        """
        Initialize migrator.

        Args:
            dry_run: If True, only show what would be changed
        """
        self.dry_run = dry_run
        self.files_modified = 0
        self.changes_made = 0

    def should_add_import(self, content: str) -> bool:
        """Check if PostgreSQLTestHelper import should be added."""
        return "PostgreSQLTestHelper" not in content and "sqlite" in content.lower() and "test" in content.lower()

    def migrate_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Migrate a single test file.

        Args:
            file_path: Path to test file

        Returns:
            Tuple of (was_modified, list_of_changes)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content
            changes = []

            # Apply all pattern replacements
            for pattern, replacement, description in self.PATTERNS:
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    changes.append(f"{description}: {len(matches)} occurrence(s)")

            # Add import if needed
            if self.should_add_import(content) and content != original_content:
                # Find where to add import (after existing imports)
                import_section_match = re.search(r"(^import .*$|^from .* import .*$)", content, re.MULTILINE)

                if import_section_match:
                    # Find the last import line
                    all_imports = re.finditer(r"^(?:import |from ).*$", content, re.MULTILINE)
                    last_import = None
                    for match in all_imports:
                        last_import = match

                    if last_import:
                        insert_pos = last_import.end()
                        content = content[:insert_pos] + "\n" + self.IMPORT_ADDITIONS + content[insert_pos:]
                        changes.append("Added PostgreSQLTestHelper import")

            # Write changes if not dry run
            if content != original_content:
                if not self.dry_run:
                    file_path.write_text(content, encoding="utf-8")
                return True, changes

            return False, []

        except Exception as e:
            return False, [f"Error: {e!s}"]

    def migrate_all_tests(self, test_dir: Path):
        """
        Migrate all test files in the test directory.

        Args:
            test_dir: Root test directory
        """
        # Find all test files with SQLite references
        test_files = []

        for pattern in ["**/*.py"]:
            for file_path in test_dir.glob(pattern):
                if "test" in file_path.name.lower() or "conftest" in file_path.name:
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if "sqlite" in content.lower():
                            test_files.append(file_path)
                    except Exception:
                        pass

        print(f"\nFound {len(test_files)} test files with SQLite references\n")

        if self.dry_run:
            print("DRY RUN - No files will be modified\n")
            print("=" * 80)

        # Migrate each file
        for file_path in sorted(test_files):
            modified, changes = self.migrate_file(file_path)

            if modified:
                self.files_modified += 1
                self.changes_made += len(changes)

                relative_path = file_path.relative_to(test_dir)
                print(f"\n{'[DRY RUN] ' if self.dry_run else ''}Modified: {relative_path}")
                for change in changes:
                    print(f"  - {change}")

        # Summary
        print("\n" + "=" * 80)
        print(f"\nMigration {'Preview' if self.dry_run else 'Complete'}!")
        print(f"Files {'would be ' if self.dry_run else ''}modified: {self.files_modified}")
        print(f"Total changes: {self.changes_made}")

        if self.dry_run:
            print("\nRun without --dry-run to apply these changes")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate test files from SQLite to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Test directory to migrate (default: current directory)",
    )

    args = parser.parse_args()

    migrator = TestMigrator(dry_run=args.dry_run)
    migrator.migrate_all_tests(args.test_dir)


if __name__ == "__main__":
    main()
