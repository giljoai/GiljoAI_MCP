#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
GiljoAI MCP - Linux Reset Script
Removes all GiljoAI MCP traces from the system to simulate a fresh machine.
Keeps baseline Ubuntu packages and system config intact.

Usage:
    python3 linux_reset.py          # dry-run (shows what would be removed)
    python3 linux_reset.py --force  # actually remove everything
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


HOME = Path.home()
DRY_RUN = True


def ensure_sudo():
    """Acquire sudo credentials upfront so later commands don't stall."""
    print("\nThis script needs sudo access. You may be prompted for your password.\n")
    result = subprocess.run(["sudo", "-v"], check=False)
    if result.returncode != 0:
        print("  [ERROR] Failed to acquire sudo. Exiting.")
        sys.exit(1)
    print()


def run(cmd, check=False, sudo=False):
    if sudo:
        cmd = f"sudo {cmd}"
    if DRY_RUN:
        print(f"  [DRY-RUN] {cmd}")
        return None
    print(f"  [RUN] {cmd}")
    # Always run interactively so sudo prompts and apt progress are visible
    result = subprocess.run(cmd, shell=True, check=False)
    if check and result.returncode != 0:
        print(f"  [WARN] Command exited with code {result.returncode}")
    return result


def remove_path(path, sudo=False):
    p = Path(path).expanduser()
    if p.exists():
        if DRY_RUN:
            print(f"  [DRY-RUN] rm -rf {p}")
        else:
            print(f"  [REMOVE] {p}")
            if sudo:
                subprocess.run(f"sudo rm -rf {p}", shell=True, check=False)
            else:
                shutil.rmtree(p, ignore_errors=True)
                if p.exists() and p.is_file():
                    p.unlink()
        return True
    return False


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def find_postgres_packages():
    """Find all PostgreSQL-related packages in any state (installed, config-remaining, etc.)."""
    result = subprocess.run(
        "dpkg -l 2>/dev/null | grep -i postgres | awk '{print $2}'",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        return result.stdout.strip().splitlines()
    return []


def remove_postgresql():
    section("PostgreSQL (full purge)")

    # Auto-discover every installed postgres package (any version, any state: ii, rc, iU).
    # Hardcoding version-specific names (postgresql-16, postgresql-18, ...) breaks apt
    # if those packages aren't installed — apt aborts the whole batch on unknown names.
    packages = find_postgres_packages()

    if packages:
        # Detect installed major version(s) for visibility
        versions = sorted(
            {p.split("-", 2)[1] for p in packages if p.startswith("postgresql-") and p.split("-", 2)[1].isdigit()}
        )
        if versions:
            print(f"  Detected PostgreSQL version(s): {', '.join(versions)}")

        pkg_list = " ".join(packages)
        print(f"  Purging packages: {pkg_list}")
        run(f"apt-get purge -y {pkg_list}", sudo=True)
        run("apt-get autoremove --purge -y", sudo=True)
    else:
        print("  No PostgreSQL packages found")

    # Remove data, config, and repo files
    pg_paths = [
        "/var/lib/postgresql",
        "/etc/postgresql",
        "/etc/apt/sources.list.d/pgdg.list",
        "/etc/apt/sources.list.d/pgdg.sources",
        "/etc/apt/trusted.gpg.d/pgdg.gpg",
    ]
    for p in pg_paths:
        remove_path(p, sudo=True)

    # Remove crash reports
    crash_files = list(Path("/var/crash").glob("*postgres*")) if Path("/var/crash").exists() else []
    for f in crash_files:
        remove_path(f, sudo=True)


def remove_nodejs():
    section("Node.js (all install methods)")

    # Method 1: Direct binary install (nodejs.org tarball to /usr/local)
    node_bins = ["/usr/local/bin/node", "/usr/local/bin/npm", "/usr/local/bin/npx", "/usr/local/bin/corepack"]
    for b in node_bins:
        remove_path(b, sudo=True)
    remove_path("/usr/local/lib/node_modules", sudo=True)

    # Method 2: NodeSource apt install
    nodesource_packages = ["nodejs"]
    pkg_list = " ".join(nodesource_packages)
    print(f"  Purging apt packages: {pkg_list}")
    run(f"apt-get purge -y {pkg_list}", sudo=True)

    # Remove NodeSource repo config
    nodesource_paths = [
        "/etc/apt/sources.list.d/nodesource.list",
        "/etc/apt/keyrings/nodesource.gpg",
    ]
    for p in nodesource_paths:
        remove_path(p, sudo=True)

    # Method 3: Ubuntu bundled (same apt purge covers it)

    # Method 4: NVM (Node Version Manager) — installs to ~/.nvm
    nvm_dir = HOME / ".nvm"
    remove_path(str(nvm_dir))

    print("  Node.js removal complete")


def remove_mkcert():
    section("mkcert (CA + packages)")

    # Uninstall CA from trust stores (must happen before package removal)
    if shutil.which("mkcert"):
        run("mkcert -uninstall")

    # Remove from NSS browser database
    nssdb = HOME / ".pki" / "nssdb"
    if nssdb.exists():
        result = subprocess.run(
            f"certutil -d sql:{nssdb} -L 2>/dev/null | grep mkcert",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                nickname = line.rsplit(" ", 1)[0].strip()
                run(f'certutil -d sql:{nssdb} -D -n "{nickname}"')

    # Remove system CA certificate
    for f in Path("/usr/local/share/ca-certificates").glob("*mkcert*"):
        remove_path(f, sudo=True)
    for f in Path("/etc/ssl/certs").glob("*mkcert*"):
        remove_path(f, sudo=True)

    # Update system CA store
    run("update-ca-certificates --fresh", sudo=True)

    # Remove root CA files
    remove_path(HOME / ".local" / "share" / "mkcert")

    # Remove packages
    mkcert_pkgs = []
    for pkg in ["mkcert", "libnss3-tools"]:
        result = subprocess.run(
            f"dpkg -l {pkg} 2>/dev/null | grep -E '^(ii|rc)'",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            mkcert_pkgs.append(pkg)

    if mkcert_pkgs:
        run(f"apt-get purge -y {' '.join(mkcert_pkgs)}", sudo=True)
    else:
        print("  mkcert packages not installed")


def remove_giljoai_data():
    section("GiljoAI application data")

    # ~/.giljo-mcp
    remove_path(HOME / ".giljo-mcp")

    # Desktop shortcuts
    for f in (HOME / ".local" / "share" / "applications").glob("giljoai*"):
        remove_path(f)

    # /tmp files
    for pattern in ["GiljoAI_MCP", "giljoai_install.sh"]:
        for f in Path("/tmp").glob(pattern):
            remove_path(f)


def remove_bashrc_modifications():
    section("bashrc modifications")

    bashrc = HOME / ".bashrc"
    if not bashrc.exists():
        print("  No .bashrc found")
        return

    content = bashrc.read_text()
    lines = content.splitlines(keepends=True)
    new_lines = []
    removed = []
    skip_next_blank = False

    for line in lines:
        stripped = line.strip()
        if "GiljoAI MCP" in stripped or stripped == 'export NODE_OPTIONS="--use-system-ca"':
            removed.append(stripped)
            skip_next_blank = True
            continue
        if skip_next_blank and stripped == "":
            skip_next_blank = False
            continue
        skip_next_blank = False
        new_lines.append(line)

    if removed:
        for r in removed:
            print(f"  Removing line: {r}")
        if not DRY_RUN:
            bashrc.write_text("".join(new_lines))
            print("  [OK] .bashrc cleaned")
    else:
        print("  No GiljoAI lines found in .bashrc")


def clear_caches():
    section("Package caches (pip + npm)")

    run("pip cache purge")
    run("npm cache clean --force")


def empty_server_trash():
    section("Server drive trash")

    trash = Path("/media/gildemo/Server/.Trash-1000")
    if trash.exists():
        for subdir in ["files", "info", "expunged"]:
            d = trash / subdir
            if d.exists() and any(d.iterdir()):
                for item in d.iterdir():
                    remove_path(item, sudo=True)
    else:
        print("  No Server trash found")


def remove_mcp_logs():
    section("Claude CLI MCP logs (giljo-mcp)")

    cache_dir = HOME / ".cache" / "claude-cli-nodejs"
    if cache_dir.exists():
        found = False
        for log_dir in cache_dir.rglob("mcp-logs-giljo-mcp"):
            remove_path(log_dir)
            found = True
        if not found:
            print("  No MCP log directories found")
    else:
        print("  No Claude CLI cache directory")


def verify():
    section("Verification")

    checks = [
        ("mkcert binary", shutil.which("mkcert")),
        ("~/.giljo-mcp", (HOME / ".giljo-mcp").exists()),
        ("~/.local/share/mkcert", (HOME / ".local" / "share" / "mkcert").exists()),
        (
            "NODE_OPTIONS in .bashrc",
            "NODE_OPTIONS" in (HOME / ".bashrc").read_text() if (HOME / ".bashrc").exists() else False,
        ),
    ]

    # Check PostgreSQL packages -- only flag actually installed (ii), not config remnants (rc)
    pg_check = subprocess.run(
        "dpkg -l 2>/dev/null | grep -i postgres | grep '^ii'",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    checks.append(("PostgreSQL packages", bool(pg_check.stdout.strip())))

    # Check system CA
    sys_ca = list(Path("/usr/local/share/ca-certificates").glob("*mkcert*"))
    checks.append(("mkcert system CA", bool(sys_ca)))

    all_clean = True
    for name, found in checks:
        status = "FOUND" if found else "CLEAN"
        icon = "!!" if found else "OK"
        print(f"  [{icon}] {name}: {status}")
        if found:
            all_clean = False

    if all_clean:
        print("\n  All GiljoAI traces removed. System is pristine.")
    else:
        print("\n  Some traces remain -- re-run with --force if this was a dry run.")


def main():
    global DRY_RUN

    parser = argparse.ArgumentParser(description="Remove all GiljoAI MCP traces from this Linux system.")
    parser.add_argument("--force", action="store_true", help="Actually perform the removal (default is dry-run)")
    args = parser.parse_args()
    DRY_RUN = not args.force

    print("=" * 60)
    print("  GiljoAI MCP - Linux System Reset")
    print(
        f"  Mode: {'LIVE -- changes will be applied' if args.force else 'DRY RUN -- no changes (use --force to apply)'}"
    )
    print("=" * 60)

    if args.force:
        ensure_sudo()

    remove_nodejs()
    remove_mkcert()
    remove_postgresql()
    remove_giljoai_data()
    remove_bashrc_modifications()
    remove_mcp_logs()
    empty_server_trash()
    clear_caches()

    if not DRY_RUN:
        verify()
    else:
        print(f"\n{'=' * 60}")
        print("  Dry run complete. Run with --force to apply changes.")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
