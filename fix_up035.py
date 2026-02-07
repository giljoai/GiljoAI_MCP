#!/usr/bin/env python3
"""
Fix UP035 violations: Remove deprecated typing imports.

Removes deprecated generic types from typing imports:
- List, Dict, Optional, Set, Tuple, Deque (use lowercase built-ins instead)
- Keeps: Any, Literal, TypeVar, Protocol, etc.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_files_with_violations() -> list[str]:
    """Get list of files with UP035 violations."""
    result = subprocess.run(
        ["ruff", "check", "src/", "api/", "--select", "UP035", "--output-format=concise"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    # Parse output to get unique file paths
    files = set()
    for line in result.stdout.splitlines():
        if line.strip() and ":" in line:
            # Format: path:line:col: CODE message
            # Skip summary lines like "Found 116 errors."
            if not line.startswith("Found "):
                file_path = line.split(":")[0]
                # Only add if it looks like a file path
                if "\\" in file_path or "/" in file_path:
                    files.add(file_path)

    return sorted(files)


def fix_typing_imports(file_path: str) -> bool:
    """
    Fix typing imports in a single file.

    Only removes deprecated types that are NOT used in the code.
    If a deprecated type is still used, keeps it in the import.

    Returns True if file was modified.
    """
    path = Path(file_path)

    if not path.exists():
        print(f"  WARNING: File not found: {file_path}")
        return False

    content = path.read_text(encoding="utf-8")
    original_content = content

    # Deprecated generic types that should be removed
    deprecated = {"List", "Dict", "Optional", "Set", "Tuple", "Deque"}

    # Check which deprecated types are actually used in the code
    used_types = set()
    for dtype in deprecated:
        # Look for usage patterns like Optional[, Dict[, etc.
        if re.search(rf'\b{dtype}\s*\[', content):
            used_types.add(dtype)

    # Types to actually remove (deprecated but not used)
    types_to_remove = deprecated - used_types

    # Pattern to match typing imports
    # Matches both single-line and multi-line imports
    import_pattern = r'^from typing import ([^\n]+?)(?:\n|$)'

    def fix_import_line(match):
        imports_str = match.group(1)

        # Handle multi-line imports (with parentheses)
        if '(' in imports_str:
            # Extract content between parentheses
            paren_match = re.search(r'\((.*?)\)', imports_str, re.DOTALL)
            if paren_match:
                imports_content = paren_match.group(1)
            else:
                imports_content = imports_str
        else:
            imports_content = imports_str

        # Split by comma and clean up
        imports = [imp.strip() for imp in imports_content.split(',')]

        # Filter out only the deprecated imports that are NOT used
        kept_imports = [imp for imp in imports if imp and imp not in types_to_remove]

        if not kept_imports:
            # No imports left, remove the entire line
            return ""

        # Reconstruct import statement
        if len(kept_imports) == 1:
            return f"from typing import {kept_imports[0]}\n"
        elif len(kept_imports) <= 3:
            return f"from typing import {', '.join(kept_imports)}\n"
        else:
            # Multi-line format for many imports
            imports_formatted = ',\n    '.join(kept_imports)
            return f"from typing import (\n    {imports_formatted}\n)\n"

    # Fix imports
    content = re.sub(import_pattern, fix_import_line, content, flags=re.MULTILINE)

    # Remove empty lines that might have been left
    content = re.sub(r'\n\n\n+', '\n\n', content)

    # Only write if changed
    if content != original_content:
        path.write_text(content, encoding="utf-8")
        return True

    return False


def main():
    """Main execution."""
    print("Finding files with UP035 violations...")

    files = get_files_with_violations()

    if not files:
        print("No UP035 violations found!")
        return 0

    print(f"Found {len(files)} files with violations\n")

    modified_count = 0

    for file_path in files:
        print(f"Processing: {file_path}")
        if fix_typing_imports(file_path):
            modified_count += 1
            print(f"  Fixed")
        else:
            print(f"  No changes needed")

    print(f"\nSummary:")
    print(f"   Files processed: {len(files)}")
    print(f"   Files modified: {modified_count}")
    print(f"   Files unchanged: {len(files) - modified_count}")

    # Verify fixes
    print(f"\nVerifying fixes...")
    result = subprocess.run(
        ["ruff", "check", "src/", "api/", "--select", "UP035", "--statistics"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
