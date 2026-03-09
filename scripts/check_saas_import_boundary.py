#!/usr/bin/env python3
"""
Pre-commit hook: CE/SaaS import boundary enforcement.

Rule: No file OUTSIDE of saas/ directories may import from any saas/ module.
This prevents Community Edition (CE) code from depending on SaaS-only code.

SaaS directories:
  - src/giljo_mcp/saas/   (Python backend)
  - frontend/src/saas/     (JS/Vue frontend)
  - tests/saas/            (test files for SaaS code -- allowed to import saas)
"""

import re
import sys
from pathlib import PurePosixPath


# Patterns that indicate an import from a saas module.
#
# Python:
#   from giljo_mcp.saas.auth import ...
#   from saas.billing import ...
#   import giljo_mcp.saas.analytics
#   from .saas import ...
#   from ..saas.auth import ...
#
# JS/TS/Vue:
#   import { thing } from '@/saas/components/...'
#   import SaasThing from '../saas/stores/...'
#   require('./saas/...')
#
# We match broadly: any import/from line containing a saas path segment.
# The regex looks for "saas" appearing as a path component in an import context.

PYTHON_IMPORT_PATTERNS = [
    # "from <something>.saas" or "from saas"
    re.compile(r"^\s*from\s+[\w.]*\.?saas(?:\.\w+)*\s+import\b"),
    # "import <something>.saas"
    re.compile(r"^\s*import\s+[\w.]*\.?saas(?:\.\w+)*"),
]

JS_IMPORT_PATTERNS = [
    # ES module: import ... from '...saas...'
    re.compile(r"""^\s*import\s+.*\bfrom\s+['"].*[/\\\\]saas[/\\\\]"""),
    # ES module: import '...saas...' (side-effect import)
    re.compile(r"""^\s*import\s+['"].*[/\\\\]saas[/\\\\]"""),
    # CommonJS: require('...saas...')
    re.compile(r"""require\s*\(\s*['"].*[/\\\\]saas[/\\\\]"""),
    # Dynamic import: import('...saas...')
    re.compile(r"""import\s*\(\s*['"].*[/\\\\]saas[/\\\\]"""),
]

# File extensions and their corresponding patterns
EXTENSION_PATTERNS = {
    ".py": PYTHON_IMPORT_PATTERNS,
    ".js": JS_IMPORT_PATTERNS,
    ".ts": JS_IMPORT_PATTERNS,
    ".vue": JS_IMPORT_PATTERNS,
    ".jsx": JS_IMPORT_PATTERNS,
    ".tsx": JS_IMPORT_PATTERNS,
}


def is_inside_saas_directory(filepath: str) -> bool:
    """Return True if the file is inside a saas/ directory at any level."""
    # Normalize to forward slashes for consistent matching
    normalized = filepath.replace("\\", "/")
    parts = normalized.split("/")
    return "saas" in parts


def is_inside_tests_saas_directory(filepath: str) -> bool:
    """Return True if the file is inside tests/saas/."""
    normalized = filepath.replace("\\", "/")
    return "/tests/saas/" in normalized or normalized.startswith("tests/saas/")


def is_in_pycache(filepath: str) -> bool:
    """Return True if file is inside a __pycache__ directory."""
    normalized = filepath.replace("\\", "/")
    return "/__pycache__/" in normalized or normalized.startswith("__pycache__/")


def check_file(filepath: str) -> list[tuple[int, str]]:
    """Check a single file for saas import violations.

    Returns list of (line_number, line_content) tuples.
    """
    # Determine which patterns to use based on extension
    suffix = PurePosixPath(filepath.replace("\\", "/")).suffix.lower()
    patterns = EXTENSION_PATTERNS.get(suffix)
    if patterns is None:
        return []

    violations = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, 1):
                # Skip comment lines
                stripped = line.strip()
                if suffix == ".py" and stripped.startswith("#"):
                    continue
                if suffix in (".js", ".ts", ".vue", ".jsx", ".tsx") and stripped.startswith("//"):
                    continue

                for pattern in patterns:
                    if pattern.search(line):
                        violations.append((line_num, stripped))
                        break  # One match per line is enough
    except OSError:
        pass  # Skip files that cannot be read

    return violations


def main() -> int:
    """Main entry point for pre-commit hook."""
    files = sys.argv[1:] if len(sys.argv) > 1 else []

    if not files:
        print("No files to check.")
        return 0

    all_violations: list[str] = []

    for filepath in files:
        # Skip files inside saas/ directories (they are allowed to import saas)
        if is_inside_saas_directory(filepath):
            continue

        # Skip files inside tests/saas/ (they test saas code)
        if is_inside_tests_saas_directory(filepath):
            continue

        # Skip __pycache__
        if is_in_pycache(filepath):
            continue

        violations = check_file(filepath)
        for line_num, line_content in violations:
            all_violations.append(
                f"  {filepath}:{line_num}: {line_content}"
            )

    if all_violations:
        print()
        print("ERROR: CE code cannot import from saas/ directories.")
        print()
        print("The following files violate the CE/SaaS import boundary:")
        print()
        for v in all_violations:
            print(v)
        print()
        print(f"Total: {len(all_violations)} violation(s)")
        print()
        print("SaaS-only code lives in saas/ directories and must not be")
        print("imported by Community Edition code. If you need shared")
        print("functionality, extract it to a CE module first.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
