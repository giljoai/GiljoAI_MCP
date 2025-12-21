#!/usr/bin/env python3
"""
Pre-commit hook to detect usage of deprecated models.

Part of Handover 0358d - MCPAgentJob deprecation.
Flags new usage of deprecated models in source files.
"""
import sys
import re
from pathlib import Path


DEPRECATED_MODELS = {
    "MCPAgentJob": "Use AgentJob and AgentExecution instead (Handover 0366a)"
}

# Patterns to detect usage (imports, type hints, instantiation)
PATTERNS = [
    r'\bMCPAgentJob\b',  # Any usage of MCPAgentJob
]

# Files/directories to skip
SKIP_PATHS = {
    'tests/',
    'migrations/',
    'handovers/',
    'scripts/check_deprecated_models.py',  # Self
    'src/giljo_mcp/models/agents.py',  # Definition file
    'src/giljo_mcp/models/__init__.py',  # Export file
}


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Check a file for deprecated model usage.

    Returns list of (line_number, line_content, model_name) tuples.
    """
    violations = []

    # Skip certain paths
    filepath_str = str(filepath).replace('\\', '/')
    for skip in SKIP_PATHS:
        if skip in filepath_str:
            return []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            for model_name in DEPRECATED_MODELS:
                if re.search(rf'\b{model_name}\b', line):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    violations.append((line_num, line.strip(), model_name))
    except Exception:
        pass  # Skip files that can't be read

    return violations


def main() -> int:
    """Main entry point for pre-commit hook."""
    files = sys.argv[1:] if len(sys.argv) > 1 else []

    if not files:
        # No files passed, scan all Python files
        root = Path('.')
        files = [str(p) for p in root.glob('src/**/*.py')]

    all_violations = []

    for filepath in files:
        if not filepath.endswith('.py'):
            continue
        path = Path(filepath)
        if not path.exists():
            continue

        violations = check_file(path)
        for line_num, line_content, model_name in violations:
            all_violations.append(
                f"{filepath}:{line_num}: {model_name} is deprecated. "
                f"{DEPRECATED_MODELS[model_name]}\n  {line_content}"
            )

    if all_violations:
        print("WARNING: Deprecated model usage detected:")
        print()
        for v in all_violations:
            print(v)
            print()
        print(f"Total: {len(all_violations)} violation(s)")
        print()
        print("These models are deprecated and will be removed in v4.0.")
        print("Please use AgentJob + AgentExecution instead.")
        # Return 0 for warnings only (don't block commits during transition)
        # Change to return 1 when ready to enforce
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
