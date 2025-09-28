#!/usr/bin/env python3
"""
Standardize folder naming across the GiljoAI MCP codebase

This script updates all references from .giljo_mcp to .giljo-mcp for consistency.
The standard naming convention will be: .giljo-mcp (with hyphen)
"""

import os
import sys
from pathlib import Path
import re
from typing import List, Tuple


class FolderNameStandardizer:
    """Standardize folder naming conventions across the codebase"""

    def __init__(self, project_root: Path = None):
        """Initialize the standardizer

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd().parent
        self.old_pattern = r"\.giljo_mcp"  # Underscore version
        self.new_pattern = ".giljo-mcp"    # Hyphen version (standard)
        self.changes_made = []
        self.files_skipped = []

    def find_files_with_pattern(self) -> List[Path]:
        """Find all files containing the old naming pattern

        Returns:
            List of file paths that need updating
        """
        files_to_update = []

        # File extensions to check
        extensions = ['.py', '.md', '.yaml', '.yml', '.json', '.txt', '.sh', '.bat', '.ini', '.toml']

        # Directories to skip
        skip_dirs = {'.git', '__pycache__', '.mypy_cache', '.ruff_cache', 'venv', 'node_modules',
                     '.pytest_cache', 'dist', 'build', '*.egg-info'}

        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                file_path = Path(root) / file

                # Check if file has relevant extension
                if any(file.endswith(ext) for ext in extensions):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if self.old_pattern.replace("\\", "") in content:
                                files_to_update.append(file_path)
                    except Exception as e:
                        self.files_skipped.append((file_path, str(e)))

        return files_to_update

    def update_file(self, file_path: Path) -> Tuple[bool, int]:
        """Update a single file with the new naming convention

        Args:
            file_path: Path to the file to update

        Returns:
            Tuple of (success, number of replacements)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Replace the pattern
            updated_content = re.sub(self.old_pattern, self.new_pattern, original_content)

            # Count replacements
            replacements = len(re.findall(self.old_pattern, original_content))

            if replacements > 0:
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                self.changes_made.append((file_path, replacements))
                return True, replacements

            return True, 0

        except Exception as e:
            print(f"  Error updating {file_path}: {e}")
            return False, 0

    def update_imports(self) -> None:
        """Update Python imports from giljo_mcp to giljo-mcp where appropriate"""
        # Note: Python module names can't have hyphens, so we need to be careful
        # This is primarily for path references, not import statements

        import_files = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Look for path references, not imports
                            if '".giljo_mcp"' in content or "'.giljo_mcp'" in content:
                                import_files.append(file_path)
                    except:
                        pass

        for file_path in import_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Update string path references only
                content = content.replace('".giljo_mcp"', '".giljo-mcp"')
                content = content.replace("'.giljo_mcp'", "'.giljo-mcp'")
                content = content.replace('/.giljo_mcp', '/.giljo-mcp')

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  Updated path references in: {file_path.relative_to(self.project_root)}")
            except Exception as e:
                print(f"  Error updating {file_path}: {e}")

    def migrate_existing_folders(self) -> None:
        """Migrate existing .giljo_mcp folders to .giljo-mcp"""
        home = Path.home()
        old_dir = home / ".giljo_mcp"
        new_dir = home / ".giljo-mcp"

        if old_dir.exists() and not new_dir.exists():
            print(f"\nMigrating folder: {old_dir} -> {new_dir}")
            try:
                import shutil
                shutil.move(str(old_dir), str(new_dir))
                print("  ✓ Folder migrated successfully")
            except Exception as e:
                print(f"  ✗ Migration failed: {e}")
                print("  You may need to manually rename the folder")
        elif old_dir.exists() and new_dir.exists():
            print(f"\n⚠ Both folders exist:")
            print(f"  - {old_dir}")
            print(f"  - {new_dir}")
            print("  Manual intervention required to merge or remove duplicate")

    def generate_report(self) -> str:
        """Generate a report of all changes made

        Returns:
            Formatted report string
        """
        report = ["=" * 60]
        report.append("Folder Naming Standardization Report")
        report.append("=" * 60)

        report.append(f"\nStandard naming: {self.new_pattern}")
        report.append(f"Replaced pattern: {self.old_pattern.replace(chr(92), '')}")

        if self.changes_made:
            report.append(f"\nFiles updated: {len(self.changes_made)}")
            report.append("-" * 40)
            total_replacements = 0
            for file_path, count in self.changes_made:
                rel_path = file_path.relative_to(self.project_root)
                report.append(f"  {rel_path}: {count} replacement(s)")
                total_replacements += count
            report.append(f"\nTotal replacements: {total_replacements}")

        else:
            report.append("\nNo files needed updating - naming is already standardized!")

        if self.files_skipped:
            report.append(f"\nFiles skipped (errors): {len(self.files_skipped)}")
            for file_path, reason in self.files_skipped[:5]:
                report.append(f"  {file_path}: {reason}")
            if len(self.files_skipped) > 5:
                report.append(f"  ... and {len(self.files_skipped) - 5} more")

        report.append("\n" + "=" * 60)
        return "\n".join(report)

    def run(self, dry_run: bool = False) -> bool:
        """Run the standardization process

        Args:
            dry_run: If True, only show what would be changed without making changes

        Returns:
            Success status
        """
        print("Scanning for files with old naming pattern...")
        files_to_update = self.find_files_with_pattern()

        if not files_to_update:
            print("✓ No files found with old naming pattern. Codebase is already standardized!")
            self.migrate_existing_folders()
            return True

        print(f"Found {len(files_to_update)} files to update")

        if dry_run:
            print("\nDRY RUN - No changes will be made")
            print("-" * 40)
            for file_path in files_to_update:
                rel_path = file_path.relative_to(self.project_root)
                print(f"  Would update: {rel_path}")
            return True

        # Update files
        print("\nUpdating files...")
        for file_path in files_to_update:
            rel_path = file_path.relative_to(self.project_root)
            success, count = self.update_file(file_path)
            if success and count > 0:
                print(f"  ✓ Updated: {rel_path} ({count} replacements)")
            elif not success:
                print(f"  ✗ Failed: {rel_path}")

        # Update import path references
        print("\nUpdating path references...")
        self.update_imports()

        # Migrate existing folders
        self.migrate_existing_folders()

        # Generate report
        print("\n" + self.generate_report())

        return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Standardize folder naming in GiljoAI MCP codebase")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--root", type=Path, help="Project root directory (default: parent of current dir)")

    args = parser.parse_args()

    standardizer = FolderNameStandardizer(args.root)

    print("GiljoAI MCP Folder Naming Standardization")
    print("=" * 60)
    print(f"Project root: {standardizer.project_root}")
    print(f"Old pattern: .giljo_mcp (underscore)")
    print(f"New pattern: .giljo-mcp (hyphen)")
    print()

    if args.dry_run:
        print("Running in DRY RUN mode - no changes will be made")
        print()

    try:
        if standardizer.run(dry_run=args.dry_run):
            return 0
        else:
            return 1
    except KeyboardInterrupt:
        print("\n\nStandardization cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
