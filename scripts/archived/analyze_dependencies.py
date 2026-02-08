#!/usr/bin/env python3
"""Analyze which packages from requirements.txt are actually used in the codebase."""

import re
from pathlib import Path


# Read requirements.txt
requirements = {}
with open("requirements.txt") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            # Extract package name (before >= or [)
            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if match:
                pkg_name = match.group(1).lower().replace("-", "_")
                requirements[pkg_name] = line

# Get all Python files in src/, api/, installer/
python_files = []
for pattern in ["src/**/*.py", "api/**/*.py", "installer/**/*.py", "*.py"]:
    python_files.extend(Path().glob(pattern))

# Filter out venv, node_modules, etc.
python_files = [f for f in python_files if "venv" not in str(f) and "node_modules" not in str(f)]

# Extract all imports
imports = set()
for py_file in python_files:
    try:
        with open(py_file, encoding="utf-8") as f:
            for line in f:
                # Match 'import x' or 'from x import'
                if (match := re.match(r"^import\s+([a-zA-Z0-9_]+)", line)) or (
                    match := re.match(r"^from\s+([a-zA-Z0-9_]+)", line)
                ):
                    imports.add(match.group(1).lower())
    except:
        pass

# Map common package names to their import names
package_mappings = {
    "pyyaml": "yaml",
    "python_jose": "jose",
    "python_dotenv": "dotenv",
    "python_multipart": "multipart",
    "pygithub": "github",
    "prometheus_client": "prometheus_client",
    "psycopg2_binary": "psycopg2",
    "slack_sdk": "slack_sdk",
    "google_generativeai": "google",
    "mkdocs_material": "material",
}

# Check which packages are used
used_packages = []
unused_packages = []
uncertain_packages = []

for pkg_name, req_line in requirements.items():
    # Check direct match
    if pkg_name in imports:
        used_packages.append((pkg_name, req_line, "direct"))
        continue

    # Check mapped name
    if pkg_name in package_mappings and package_mappings[pkg_name] in imports:
        used_packages.append((pkg_name, req_line, "mapped"))
        continue

    # Check if it's a dependency category
    if pkg_name in [
        "pytest",
        "pytest_asyncio",
        "pytest_cov",
        "black",
        "ruff",
        "mypy",
        "mkdocs",
        "mkdocs_material",
        "gunicorn",
        "celery",
        "docker",
    ]:
        uncertain_packages.append((pkg_name, req_line, "dev/optional"))
        continue

    # Core dependencies that might be indirect
    if pkg_name in ["uvicorn", "alembic", "passlib", "httpx", "websockets", "aiohttp", "psutil", "tiktoken", "pywin32"]:
        uncertain_packages.append((pkg_name, req_line, "core/indirect"))
        continue

    unused_packages.append((pkg_name, req_line))

print("=" * 80)
print("DEPENDENCY ANALYSIS")
print("=" * 80)
print(f"\nTotal packages in requirements.txt: {len(requirements)}")
print(f"Unique imports found: {len(imports)}")

print("\n" + "=" * 80)
print("DEFINITELY USED PACKAGES")
print("=" * 80)
for pkg, req, match_type in sorted(used_packages):
    print(f"[USED] {req:50} [{match_type}]")

print("\n" + "=" * 80)
print("UNCERTAIN (dev tools, optional, or indirect dependencies)")
print("=" * 80)
for pkg, req, category in sorted(uncertain_packages):
    print(f"[MAYBE] {req:50} [{category}]")

print("\n" + "=" * 80)
print("LIKELY UNUSED PACKAGES")
print("=" * 80)
for pkg, req in sorted(unused_packages):
    print(f"[UNUSED] {req}")

print("\n" + "=" * 80)
print("IMPORTS FOUND IN CODE")
print("=" * 80)
for imp in sorted(imports):
    print(f"  - {imp}")
