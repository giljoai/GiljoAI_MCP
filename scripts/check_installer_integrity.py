#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Installer integrity checks. Catches the regression classes that broke
fresh-machine installs in v1.1.9.x:

  1. UTF-8 BOM in install.ps1 or install.sh.
     A BOM makes 'irm giljo.ai/install.ps1 | iex' fail because PowerShell
     treats the BOM as a literal token before '#Requires'.

  2. start-giljoai.bat (the launcher heredoc inside install.ps1) must invoke
     'python startup.py', not 'python -m api.run_api'. The latter skips
     frontend, browser auto-open, and migrations.

  3. startup.py must defer third-party imports (click, colorama) until
     AFTER ensure_project_virtualenv() runs. Otherwise 'python startup.py'
     from a fresh shell crashes with ModuleNotFoundError before the venv
     relaunch guard can fire.

Run as a pre-commit hook and in CI. Exits non-zero on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

INSTALLER_SCRIPTS = [
    REPO_ROOT / "scripts" / "install.ps1",
    REPO_ROOT / "scripts" / "install.sh",
]

INSTALL_PS1 = REPO_ROOT / "scripts" / "install.ps1"
STARTUP_PY = REPO_ROOT / "startup.py"

UTF8_BOM = b"\xef\xbb\xbf"


def check_no_bom() -> list[str]:
    failures: list[str] = []
    for path in INSTALLER_SCRIPTS:
        if not path.exists():
            continue
        head = path.read_bytes()[:3]
        if head == UTF8_BOM:
            failures.append(
                f"{path.relative_to(REPO_ROOT)}: starts with UTF-8 BOM. "
                f"Re-save as UTF-8 without BOM, or run: "
                f"python -c \"p=open(r'{path}','rb');d=p.read();p.close();"
                f"open(r'{path}','wb').write(d[3:] if d[:3]==b'\\xef\\xbb\\xbf' else d)\""
            )
    return failures


def check_bat_entry_point() -> list[str]:
    failures: list[str] = []
    if not INSTALL_PS1.exists():
        return failures
    text = INSTALL_PS1.read_text(encoding="utf-8", errors="replace")
    if "start-giljoai.bat" not in text:
        return failures
    if "python -m api.run_api" in text:
        failures.append(
            "install.ps1: start-giljoai.bat heredoc invokes "
            "'python -m api.run_api'. It MUST invoke 'python startup.py "
            "--verbose' so the desktop shortcut runs the canonical entry "
            "point (frontend launch, browser auto-open, migrations)."
        )
    if "python startup.py" not in text:
        failures.append(
            "install.ps1: start-giljoai.bat heredoc does not "
            "invoke 'python startup.py'. The launcher and the post-install "
            "text instruction must run the same canonical entry point."
        )
    return failures


def check_startup_import_order() -> list[str]:
    failures: list[str] = []
    if not STARTUP_PY.exists():
        return failures
    lines = STARTUP_PY.read_text(encoding="utf-8").splitlines()

    guard_line = None
    third_party_lines: list[tuple[int, str]] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        # The relaunch guard is invoked here.
        if "ensure_project_virtualenv()" in stripped and not stripped.startswith("def "):
            guard_line = idx
        if stripped.startswith(("import click", "from click")):
            third_party_lines.append((idx, stripped))
        if stripped.startswith(("import colorama", "from colorama")):
            third_party_lines.append((idx, stripped))

    if guard_line is None:
        failures.append(
            "startup.py: ensure_project_virtualenv() invocation not found. "
            "The venv relaunch guard must be called at module level before "
            "any third-party imports."
        )
        return failures

    for line_no, code in third_party_lines:
        if line_no < guard_line:
            failures.append(
                f"startup.py:{line_no}: '{code}' is imported BEFORE "
                f"ensure_project_virtualenv() (line {guard_line}). Fresh-shell "
                f"installs without an activated venv will crash with "
                f"ModuleNotFoundError before the relaunch guard can fire. "
                f"Move this import below the guard."
            )

    return failures


def main() -> int:
    all_failures: list[str] = []
    all_failures += check_no_bom()
    all_failures += check_bat_entry_point()
    all_failures += check_startup_import_order()

    if not all_failures:
        print("[OK] Installer integrity checks passed.")
        return 0

    print("[FAIL] Installer integrity checks failed:\n")
    for failure in all_failures:
        print(f"  - {failure}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
