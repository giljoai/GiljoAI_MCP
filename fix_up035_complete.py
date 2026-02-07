#!/usr/bin/env python3
"""
Complete UP035 fix: Convert Optional/Union annotations AND remove unused imports.

Step 1: Convert Optional[X] → X | None and Union[A, B] → A | B
Step 2: Remove deprecated typing imports that are no longer used
"""

import re
import subprocess
import sys
from pathlib import Path


def convert_optional_union(content: str) -> str:
    """Convert Optional[X] to X | None and Union[A, B] to A | B."""

    # Convert Optional[X] to X | None
    # Handle nested generics like Optional[list[str]]
    def replace_optional(match):
        inner = match.group(1)
        return f"{inner} | None"

    content = re.sub(r'Optional\[([^\]]+(?:\[[^\]]+\])?)\]', replace_optional, content)

    # Convert Union[A, B, C] to A | B | C
    # This is trickier due to nesting, so we'll do simple cases
    def replace_union(match):
        inner = match.group(1)
        # Split by comma, but be careful of nested brackets
        # Simple approach: split and join with |
        types = [t.strip() for t in inner.split(',')]
        return ' | '.join(types)

    # Match Union[...] but avoid nested brackets for now
    content = re.sub(r'Union\[((?:[^\[\]]|\[[^\]]*\])+)\]', replace_union, content)

    return content


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
        if line.strip() and ":" in line and not line.startswith("Found "):
            file_path = line.split(":")[0]
            if "\\" in file_path or "/" in file_path:
                files.add(file_path)

    return sorted(files)


def fix_file(file_path: str) -> tuple[bool, bool]:
    """
    Fix a single file.

    Returns (annotations_changed, imports_changed).
    """
    path = Path(file_path)

    if not path.exists():
        print(f"  WARNING: File not found: {file_path}")
        return False, False

    content = path.read_text(encoding="utf-8")
    original_content = content

    # Step 1: Convert Optional/Union annotations
    content = convert_optional_union(content)
    annotations_changed = content != original_content

    # Step 2: Remove deprecated typing imports that are no longer used
    deprecated = {"List", "Dict", "Optional", "Set", "Tuple", "Deque", "Union"}

    # Check which deprecated types are still used
    used_types = set()
    for dtype in deprecated:
        if re.search(rf'\b{dtype}\s*\[', content):
            used_types.add(dtype)

    # Types to remove (deprecated and not used)
    types_to_remove = deprecated - used_types

    # Pattern to match typing imports
    import_pattern = r'^from typing import ([^\n]+?)(?:\n|$)'

    def fix_import_line(match):
        imports_str = match.group(1)

        # Handle multi-line imports
        if '(' in imports_str:
            paren_match = re.search(r'\((.*?)\)', imports_str, re.DOTALL)
            if paren_match:
                imports_content = paren_match.group(1)
            else:
                imports_content = imports_str
        else:
            imports_content = imports_str

        # Split by comma
        imports = [imp.strip() for imp in imports_content.split(',')]

        # Keep only non-deprecated or still-used imports
        kept_imports = [imp for imp in imports if imp and imp not in types_to_remove]

        if not kept_imports:
            return ""

        # Reconstruct
        if len(kept_imports) == 1:
            return f"from typing import {kept_imports[0]}\n"
        elif len(kept_imports) <= 3:
            return f"from typing import {', '.join(kept_imports)}\n"
        else:
            imports_formatted = ',\n    '.join(kept_imports)
            return f"from typing import (\n    {imports_formatted}\n)\n"

    original_before_imports = content
    content = re.sub(import_pattern, fix_import_line, content, flags=re.MULTILINE)
    imports_changed = content != original_before_imports

    # Remove excessive blank lines
    content = re.sub(r'\n\n\n+', '\n\n', content)

    # Write if changed
    if content != original_content:
        path.write_text(content, encoding="utf-8")

    return annotations_changed, imports_changed


def main():
    """Main execution."""
    print("Finding files with UP035 violations...")

    files = get_files_with_violations()

    if not files:
        print("No UP035 violations found!")
        return 0

    print(f"Found {len(files)} files with violations\n")

    annotations_count = 0
    imports_count = 0
    total_modified = 0

    for file_path in files:
        print(f"Processing: {file_path}")
        ann_changed, imp_changed = fix_file(file_path)

        if ann_changed or imp_changed:
            total_modified += 1
            changes = []
            if ann_changed:
                annotations_count += 1
                changes.append("annotations")
            if imp_changed:
                imports_count += 1
                changes.append("imports")
            print(f"  Fixed: {', '.join(changes)}")
        else:
            print(f"  No changes needed")

    print(f"\nSummary:")
    print(f"   Files processed: {len(files)}")
    print(f"   Files modified: {total_modified}")
    print(f"   Files with annotation fixes: {annotations_count}")
    print(f"   Files with import fixes: {imports_count}")

    # Verify
    print(f"\nVerifying UP035 fixes...")
    result = subprocess.run(
        ["ruff", "check", "src/", "api/", "--select", "UP035", "--statistics"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    if result.returncode == 0:
        print("SUCCESS: All UP035 violations resolved!")
    else:
        print("Remaining violations:")
        print(result.stdout)

    # Check for undefined names
    print(f"\nChecking for undefined names (F821)...")
    result = subprocess.run(
        ["ruff", "check", "src/", "api/", "--select", "F821", "--statistics"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    if result.returncode == 0:
        print("SUCCESS: No undefined names!")
    else:
        print("WARNING: Undefined names found:")
        print(result.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
