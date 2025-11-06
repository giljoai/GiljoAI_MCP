"""
Fix migration errors from the automated migration script.
"""

import re
from pathlib import Path


def fix_file(file_path: Path) -> bool:
    """Fix malformed replacements in a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Fix malformed string concatenation like fPostgreSQLTestHelper
        content = re.sub(r'f(["\'])PostgreSQLTestHelper', r"\1PostgreSQLTestHelper", content)

        # Fix string prefix issues
        content = re.sub(
            r'(["\'])PostgreSQLTestHelper\.get_test_db_url\(', r"PostgreSQLTestHelper.get_test_db_url(", content
        )

        # Ensure import is added if PostgreSQLTestHelper is used
        if (
            "PostgreSQLTestHelper" in content
            and "from tests.helpers.test_db_helper import PostgreSQLTestHelper" not in content
        ):
            # Find first import
            import_match = re.search(r"^(import |from )", content, re.MULTILINE)
            if import_match:
                # Find all imports
                all_imports = list(re.finditer(r"^(?:import |from ).*$", content, re.MULTILINE))
                if all_imports:
                    last_import = all_imports[-1]
                    insert_pos = last_import.end()
                    content = (
                        content[:insert_pos]
                        + "\nfrom tests.helpers.test_db_helper import PostgreSQLTestHelper\n"
                        + content[insert_pos:]
                    )

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            print(f"Fixed: {file_path.relative_to(Path.cwd())}")
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    test_dir = Path(__file__).parent
    files_fixed = 0

    # Find all Python test files
    for file_path in test_dir.rglob("*.py"):
        if "test" in file_path.name.lower() or "conftest" in file_path.name:
            if fix_file(file_path):
                files_fixed += 1

    print(f"\nFixed {files_fixed} files")


if __name__ == "__main__":
    main()
