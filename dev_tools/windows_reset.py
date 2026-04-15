#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
GiljoAI MCP — Windows Developer Reset Script

Resets a Windows PC to "rookie" state by removing ALL traces of GiljoAI MCP
installations, including dependencies installed by PostgreSQL (VC++ Redistributables).

This is a DEVELOPMENT tool for testing fresh install flows.
It does NOT delete the source repository itself.

Usage:
    python windows_reset.py           # Interactive (asks for confirmation)
    python windows_reset.py --force   # Skip confirmation prompts
    python windows_reset.py --dry-run # Show what would be removed without removing

Requires: Python 3.10+ (uses no external packages)
"""

import glob
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Colours (no colorama dependency — raw ANSI; Windows Terminal supports them)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    os.system("")  # enable ANSI escape codes on older Windows terminals

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET}    {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}[SKIP]{RESET}  {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET}  {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}[INFO]{RESET}  {msg}")


def header(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"  {BOLD}{msg}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rmtree_safe(path: Path, dry_run: bool) -> bool:
    """Remove a directory tree. Returns True if removed."""
    if not path.exists():
        return False
    if dry_run:
        info(f"Would remove: {path}")
        return True
    try:
        shutil.rmtree(path)
        ok(f"Removed: {path}")
        return True
    except PermissionError:
        # Try elevated removal on Windows
        try:
            subprocess.run(
                [
                    "powershell", "-Command",
                    f"Remove-Item '{path}' -Recurse -Force -Confirm:$false",
                ],
                check=True, capture_output=True, timeout=30,
            )
            ok(f"Removed (elevated): {path}")
            return True
        except Exception:
            fail(f"Permission denied: {path}")
            return False
    except Exception as e:
        fail(f"Error removing {path}: {e}")
        return False


def rm_file_safe(path: Path, dry_run: bool) -> bool:
    """Remove a single file. Returns True if removed."""
    if not path.exists():
        return False
    if dry_run:
        info(f"Would remove: {path}")
        return True
    try:
        path.unlink()
        ok(f"Removed: {path}")
        return True
    except Exception as e:
        fail(f"Error removing {path}: {e}")
        return False


def run_quiet(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a command quietly, returning the result."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ---------------------------------------------------------------------------
# Cleanup steps
# ---------------------------------------------------------------------------
def clean_giljo_user_dirs(dry_run: bool) -> int:
    """Remove ~/.giljo-mcp and related user directories."""
    header("User directories")
    home = Path.home()
    appdata = Path(os.getenv("APPDATA", ""))
    localappdata = Path(os.getenv("LOCALAPPDATA", ""))

    dirs = [
        home / ".giljo-mcp",
        home / ".giljo_mcp",
        home / ".giljo-config",
        appdata / "GiljoAI",
        localappdata / "GiljoAI",
    ]
    return sum(1 for d in dirs if rmtree_safe(d, dry_run))


def clean_mkcert(dry_run: bool) -> int:
    """Uninstall mkcert: untrust CA, remove CA files, uninstall binary."""
    header("mkcert (certificates)")
    count = 0
    mkcert_bin = shutil.which("mkcert")

    # Step 1: Untrust root CA
    if mkcert_bin:
        if dry_run:
            info("Would run: mkcert -uninstall")
        else:
            try:
                result = run_quiet([mkcert_bin, "-uninstall"])
                ok("Root CA removed from system trust store")
            except Exception as e:
                fail(f"mkcert -uninstall failed: {e}")
        count += 1

    # Step 2: Remove CA files
    ca_dir = Path(os.getenv("LOCALAPPDATA", "")) / "mkcert"
    if rmtree_safe(ca_dir, dry_run):
        count += 1

    # Step 3: Uninstall mkcert binary
    if mkcert_bin:
        # Try winget first
        if dry_run:
            info("Would uninstall mkcert via winget")
        else:
            try:
                result = run_quiet(
                    ["winget", "uninstall", "FiloSottile.mkcert", "--silent"],
                    timeout=60,
                )
                if result.returncode == 0:
                    ok("mkcert uninstalled via winget")
                    count += 1
                else:
                    warn("mkcert not found in winget, trying chocolatey...")
            except FileNotFoundError:
                pass

            # Clean chocolatey remnants
            choco_lib = Path(r"C:\ProgramData\chocolatey\lib\mkcert")
            choco_bin = Path(r"C:\ProgramData\chocolatey\bin\mkcert.exe")
            if choco_lib.exists() or choco_bin.exists():
                try:
                    subprocess.run(
                        [
                            "powershell", "-Command",
                            "Start-Process powershell -Verb RunAs -ArgumentList "
                            "'-Command', "
                            f"\"Remove-Item '{choco_lib}' -Recurse -Force -ErrorAction SilentlyContinue; "
                            f"Remove-Item '{choco_bin}' -Force -ErrorAction SilentlyContinue\" "
                            "-Wait",
                        ],
                        check=False, capture_output=True, timeout=30,
                    )
                    ok("Chocolatey mkcert remnants removed")
                    count += 1
                except Exception:
                    fail("Could not remove chocolatey mkcert (needs admin)")

    # Step 4: Remove mkcert cert from Windows cert store (if -uninstall missed it)
    if not dry_run:
        try:
            result = run_quiet([
                "powershell", "-Command",
                "Get-ChildItem Cert:\\CurrentUser\\Root "
                "| Where-Object { $_.Subject -like '*mkcert*' } "
                "| Remove-Item -Force",
            ])
            # No output = success or nothing to remove
        except Exception:
            pass

    if count == 0:
        warn("mkcert not installed — nothing to clean")
    return count


def clean_node_options(dry_run: bool) -> int:
    """Remove NODE_OPTIONS=--use-system-ca from persistent User environment."""
    header("NODE_OPTIONS environment variable")
    try:
        result = run_quiet([
            "powershell", "-Command",
            "[System.Environment]::GetEnvironmentVariable('NODE_OPTIONS', 'User')",
        ])
        current = result.stdout.strip()
        if current:
            if dry_run:
                info(f"Would remove NODE_OPTIONS={current}")
            else:
                run_quiet([
                    "powershell", "-Command",
                    "[System.Environment]::SetEnvironmentVariable('NODE_OPTIONS', $null, 'User')",
                ])
                ok(f"Removed NODE_OPTIONS={current}")
            return 1
        else:
            warn("NODE_OPTIONS not set — nothing to clean")
            return 0
    except Exception as e:
        fail(f"Error checking NODE_OPTIONS: {e}")
        return 0


def clean_postgresql(dry_run: bool) -> int:
    """Remove PostgreSQL remnants: service, directory, registry, temp files."""
    header("PostgreSQL")
    count = 0

    # Check and stop service
    for ver in ["18", "17", "16", "15"]:
        svc = f"postgresql-x64-{ver}"
        try:
            result = run_quiet(["sc", "query", svc])
            if result.returncode == 0:
                if dry_run:
                    info(f"Would stop and delete service: {svc}")
                else:
                    run_quiet(["sc", "stop", svc])
                    run_quiet(["sc", "delete", svc])
                    ok(f"Service {svc} stopped and deleted")
                count += 1
        except Exception:
            pass

    # Remove installation directory
    pg_base = Path(r"C:\Program Files\PostgreSQL")
    if pg_base.exists():
        if dry_run:
            info(f"Would remove: {pg_base}")
        else:
            try:
                subprocess.run(
                    [
                        "powershell", "-Command",
                        f"Start-Process powershell -Verb RunAs -ArgumentList "
                        f"'-Command', \"Remove-Item '{pg_base}' -Recurse -Force -Confirm:`$false\" "
                        f"-Wait",
                    ],
                    check=True, capture_output=True, timeout=60,
                )
                ok(f"Removed: {pg_base}")
                count += 1
            except Exception:
                fail(f"Could not remove {pg_base} (needs admin)")

    # Remove registry keys
    try:
        check = run_quiet([
            "powershell", "-Command",
            "Test-Path 'HKLM:\\SOFTWARE\\PostgreSQL'",
        ])
        if "True" in check.stdout:
            if dry_run:
                info("Would remove HKLM:\\SOFTWARE\\PostgreSQL registry keys")
            else:
                run_quiet([
                    "powershell", "-Command",
                    "Remove-Item 'HKLM:\\SOFTWARE\\PostgreSQL' -Recurse -Force -ErrorAction SilentlyContinue",
                ])
                ok("PostgreSQL registry keys removed")
            count += 1
    except Exception:
        pass

    # Remove temp files
    temp = Path(os.getenv("LOCALAPPDATA", "")) / "Temp"
    pg_temps = list(temp.glob("postgresql_installer_*"))
    pg_logs = [temp / "install-postgresql.log", temp / "uninstall-postgresql.log"]
    for p in pg_temps:
        if rmtree_safe(p, dry_run):
            count += 1
    for p in pg_logs:
        if rm_file_safe(p, dry_run):
            count += 1

    if count == 0:
        warn("No PostgreSQL remnants found")
    return count


def clean_vcredist(dry_run: bool) -> int:
    """Uninstall Visual C++ 2022/2015-2022 Redistributables (PostgreSQL dependency)."""
    header("Visual C++ Redistributables")
    count = 0

    packages = [
        "Microsoft.VCRedist.2015+.x64",
        "Microsoft.VCRedist.2015+.x86",
    ]

    for pkg in packages:
        try:
            check = run_quiet(["winget", "list", "--id", pkg], timeout=30)
            if pkg in check.stdout:
                if dry_run:
                    info(f"Would uninstall: {pkg}")
                else:
                    result = run_quiet(
                        ["winget", "uninstall", pkg, "--silent"],
                        timeout=60,
                    )
                    if result.returncode == 0:
                        ok(f"Uninstalled: {pkg}")
                    else:
                        fail(f"Failed to uninstall: {pkg}")
                count += 1
            else:
                warn(f"Not installed: {pkg}")
        except FileNotFoundError:
            fail("winget not available — cannot uninstall VC++ Redistributables")
            break
        except Exception as e:
            fail(f"Error checking {pkg}: {e}")

    return count


def clean_temp_files(dry_run: bool) -> int:
    """Remove giljoai temp/installer directories."""
    header("Temp files")
    count = 0
    temp = Path(os.getenv("LOCALAPPDATA", "")) / "Temp"

    patterns = [
        temp / "giljoai-install",
        temp / "giljo_mcp_installer",
        temp / "fresh_giljo_test",
        temp / "AI-assistant-Giljo",
    ]

    # Also check for giljo backup zips and giljo temp dirs
    for p in temp.glob("giljo_mcp_backup_*"):
        patterns.append(p)
    for p in temp.glob("tmp*"):
        giljo_sub = p / ".giljo-mcp"
        if giljo_sub.exists():
            patterns.append(p)

    # /tmp on git-bash maps to LOCALAPPDATA/Temp, but check anyway
    tmp = Path("/tmp") if Path("/tmp").exists() else None
    if tmp and tmp != temp:
        for p in tmp.glob("giljo*"):
            patterns.append(p)
        for p in tmp.glob("giljoai*"):
            patterns.append(p)

    for p in patterns:
        if p.is_dir():
            if rmtree_safe(p, dry_run):
                count += 1
        elif p.is_file():
            if rm_file_safe(p, dry_run):
                count += 1

    if count == 0:
        warn("No temp files found")
    return count


def clean_claude_mcp_logs(dry_run: bool) -> int:
    """Remove Claude CLI MCP log directories related to giljo."""
    header("Claude CLI MCP logs")
    count = 0
    cache_dir = Path(os.getenv("LOCALAPPDATA", "")) / "claude-cli-nodejs" / "Cache"

    if not cache_dir.exists():
        warn("No Claude CLI cache directory found")
        return 0

    for project_dir in cache_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for log_dir in project_dir.iterdir():
            if log_dir.is_dir() and "giljo" in log_dir.name.lower():
                if rmtree_safe(log_dir, dry_run):
                    count += 1
        # Also remove entire project dirs that are giljo-specific
        if "giljoai-mcp-landing" in project_dir.name.lower():
            if rmtree_safe(project_dir, dry_run):
                count += 1

    if count == 0:
        warn("No giljo MCP logs found")
    return count


def clean_desktop_shortcuts(dry_run: bool) -> int:
    """Remove GiljoAI desktop shortcuts."""
    header("Desktop shortcuts")
    count = 0
    desktop = Path.home() / "Desktop"

    shortcut_names = [
        "GiljoAI MCP.lnk",
        "Stop GiljoAI.lnk",
        "GiljoAI MCP.bat",
        "Stop GiljoAI.bat",
    ]

    for name in shortcut_names:
        p = desktop / name
        if rm_file_safe(p, dry_run):
            count += 1

    if count == 0:
        warn("No desktop shortcuts found")
    return count


def clean_caches(dry_run: bool) -> int:
    """Clear pip and npm caches."""
    header("Package caches")
    count = 0

    # pip cache
    try:
        result = run_quiet([sys.executable, "-m", "pip", "cache", "info"])
        if "cache size: 0 bytes" not in result.stdout:
            if dry_run:
                info("Would purge pip cache")
            else:
                run_quiet([sys.executable, "-m", "pip", "cache", "purge"])
                ok("pip cache purged")
            count += 1
        else:
            warn("pip cache already empty")
    except Exception:
        warn("Could not check pip cache")

    # npm cache
    npm = shutil.which("npm")
    if npm:
        try:
            result = run_quiet([npm, "cache", "verify"])
            if "Content verified: 0" not in result.stdout:
                if dry_run:
                    info("Would clean npm cache")
                else:
                    run_quiet([npm, "cache", "clean", "--force"])
                    ok("npm cache cleared")
                count += 1
            else:
                warn("npm cache already empty")
        except Exception:
            warn("Could not check npm cache")
    else:
        warn("npm not found — skipping")

    return count


def clean_install_dir_artifacts(install_dir: Path | None, dry_run: bool) -> int:
    """Remove generated artifacts from an install directory (not the repo itself)."""
    header("Install directory artifacts")
    if not install_dir or not install_dir.exists():
        warn("No install directory specified or found")
        return 0

    count = 0
    artifacts = [
        # Generated config files
        install_dir / ".env",
        install_dir / "config.yaml",
        install_dir / ".giljo_install_manifest.json",
    ]
    artifact_dirs = [
        install_dir / "venv",
        install_dir / "logs",
        install_dir / "data",
        install_dir / "frontend" / "node_modules",
        install_dir / "frontend" / "dist",
    ]
    # certs dir: remove contents but keep .gitkeep
    certs_dir = install_dir / "certs"
    if certs_dir.exists():
        for item in certs_dir.iterdir():
            if item.name != ".gitkeep":
                if item.is_dir():
                    if rmtree_safe(item, dry_run):
                        count += 1
                else:
                    if rm_file_safe(item, dry_run):
                        count += 1

    for f in artifacts:
        if rm_file_safe(f, dry_run):
            count += 1
    for d in artifact_dirs:
        if rmtree_safe(d, dry_run):
            count += 1

    if count == 0:
        warn("No install artifacts found")
    return count


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify_clean() -> None:
    """Run a quick verification sweep and report status."""
    header("Verification")
    all_clean = True
    home = Path.home()

    checks = [
        ("~/.giljo-mcp", (home / ".giljo-mcp").exists()),
        ("mkcert binary", shutil.which("mkcert") is not None),
        ("mkcert CA dir", (Path(os.getenv("LOCALAPPDATA", "")) / "mkcert").exists()),
        ("PostgreSQL dir", Path(r"C:\Program Files\PostgreSQL").exists()),
        ("psql in PATH", shutil.which("psql") is not None),
    ]

    # NODE_OPTIONS
    try:
        r = run_quiet([
            "powershell", "-Command",
            "[System.Environment]::GetEnvironmentVariable('NODE_OPTIONS', 'User')",
        ])
        checks.append(("NODE_OPTIONS", bool(r.stdout.strip())))
    except Exception:
        pass

    # mkcert in cert store
    try:
        r = run_quiet([
            "powershell", "-Command",
            "(Get-ChildItem Cert:\\CurrentUser\\Root "
            "| Where-Object { $_.Subject -like '*mkcert*' }).Count",
        ])
        checks.append(("mkcert in cert store", int(r.stdout.strip() or "0") > 0))
    except Exception:
        pass

    # VC++ 2022
    try:
        r = run_quiet(["winget", "list", "--id", "Microsoft.VCRedist.2015+.x64"], timeout=30)
        checks.append(("VC++ 2022 x64", "Microsoft.VCRedist.2015+.x64" in r.stdout))
    except Exception:
        pass

    # PG registry
    try:
        r = run_quiet(["powershell", "-Command", "Test-Path 'HKLM:\\SOFTWARE\\PostgreSQL'"])
        checks.append(("PostgreSQL registry", "True" in r.stdout))
    except Exception:
        pass

    for label, found in checks:
        if found:
            fail(f"{label} — still present!")
            all_clean = False
        else:
            ok(f"{label} — clean")

    if all_clean:
        print(f"\n  {GREEN}{BOLD}System is in rookie mode — ready for fresh install.{RESET}")
    else:
        print(f"\n  {YELLOW}{BOLD}Some items could not be removed. See failures above.{RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if platform.system() != "Windows":
        print("This script is for Windows only.")
        sys.exit(1)

    # Parse args (no argparse dependency)
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    force = "--force" in args
    install_dir = None

    # Check for --install-dir=<path>
    for arg in args:
        if arg.startswith("--install-dir="):
            install_dir = Path(arg.split("=", 1)[1])

    mode = "DRY RUN" if dry_run else "LIVE"

    print(f"\n{BOLD}{YELLOW}{'=' * 60}{RESET}")
    print(f"  {BOLD}GiljoAI MCP — Windows Developer Reset ({mode}){RESET}")
    print(f"{BOLD}{YELLOW}{'=' * 60}{RESET}")
    print()
    print("  This will remove ALL traces of GiljoAI MCP from this PC:")
    print("    - User config directories (~/.giljo-mcp)")
    print("    - mkcert (binary, root CA, trust store entries)")
    print("    - NODE_OPTIONS environment variable")
    print("    - PostgreSQL (service, files, registry, temp)")
    print("    - Visual C++ 2022 Redistributables")
    print("    - Desktop shortcuts")
    print("    - Temp/installer files")
    print("    - Claude CLI MCP logs")
    print("    - pip and npm caches")
    if install_dir:
        print(f"    - Install artifacts in: {install_dir}")
    print()
    print(f"  {GREEN}Keeping:{RESET} Python, Node.js, npm (global), git, source repos")

    if not force and not dry_run:
        print()
        confirm = input(f"  {YELLOW}Proceed with reset? [y/N]: {RESET}").strip().lower()
        if confirm not in ("y", "yes"):
            print("\n  Cancelled.")
            sys.exit(0)

    total = 0
    total += clean_giljo_user_dirs(dry_run)
    total += clean_mkcert(dry_run)
    total += clean_node_options(dry_run)
    total += clean_postgresql(dry_run)
    total += clean_vcredist(dry_run)
    total += clean_temp_files(dry_run)
    total += clean_claude_mcp_logs(dry_run)
    total += clean_desktop_shortcuts(dry_run)
    total += clean_caches(dry_run)
    total += clean_install_dir_artifacts(install_dir, dry_run)

    if not dry_run:
        verify_clean()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    if dry_run:
        print(f"  {CYAN}DRY RUN complete — {total} items would be removed.{RESET}")
    else:
        print(f"  {GREEN}Reset complete — {total} items cleaned.{RESET}")
        print(f"  {YELLOW}Recommendation: Reboot to clear in-memory env vars.{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
