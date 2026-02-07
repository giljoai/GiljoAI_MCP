from pathlib import Path


# Directories to skip during path safety scan
SKIP_DIRS = {
    ".git",
    ".uv-cache",
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    ".pytest_cache",
    ".mypy_cache",
    "htmlcov",
    "dist",
    "build",
    ".eggs",
}


def test_no_malformed_windows_drive_paths():
    bad = []
    for p in Path().glob("**/*"):
        # Skip problematic directories
        if any(skip in p.parts for skip in SKIP_DIRS):
            continue
        try:
            if not p.is_file():
                continue
        except (OSError, PermissionError):
            # Skip files we can't access
            continue
        s = str(p)
        # Detect paths like 'F:somepath' or 'C:folder' without a separator
        if len(s) >= 2 and s[1] == ":" and (len(s) == 2 or s[2] not in ("/", "\\")):
            bad.append(s)
        # Specifically catch legacy pollution patterns we have seen
        if s.startswith("F:GiljoAI_MCP"):
            bad.append(s)
        if s.startswith("backup_%date") or s == "**Central":
            bad.append(s)

    assert not bad, f"Malformed Windows-style paths detected in repo: {bad}"
