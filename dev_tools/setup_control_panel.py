#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
GiljoAI MCP - Developer Control Panel Setup

Cross-platform installer that sets up the Developer Control Panel with its own
isolated virtual environment and all required dependencies.

Usage:
    python dev_tools/setup_control_panel.py          # Interactive setup
    python dev_tools/setup_control_panel.py --check   # Check status only

Why a separate venv?
    The control panel needs to delete the main project venv/ during pristine
    resets. Running from the main venv would lock those files. The isolated
    dev_tools/venv_devtools/ environment allows full cleanup without conflicts.

Cross-platform: Windows, Linux, macOS
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# ─── Constants ────────────────────────────────────────────────────────────────

DEVTOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEVTOOLS_DIR.parent
VENV_DIR = DEVTOOLS_DIR / "venv_devtools"
REQUIREMENTS_FILE = DEVTOOLS_DIR / "requirements.txt"

PYTHON_DEPS = ["psutil", "psycopg2-binary", "pyyaml"]

# System packages needed per platform
LINUX_SYSTEM_DEPS = {
    "dbus-x11": "Required for gnome-terminal integration",
    "python3-tk": "Required for tkinter GUI",
    "python3-venv": "Required to create virtual environments",
}

MACOS_BREW_DEPS = {
    "python-tk": "Required for tkinter GUI (via Homebrew python-tk@3.x)",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_ok(text: str) -> None:
    print(f"  [OK] {text}")


def print_warn(text: str) -> None:
    print(f"  [!!] {text}")


def print_info(text: str) -> None:
    print(f"  [..] {text}")


def print_fail(text: str) -> None:
    print(f"  [FAIL] {text}")


def run_cmd(cmd: list, check: bool = True, capture: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Run a command with sensible defaults."""
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        **kwargs,
    )


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


# ─── Platform Detection ──────────────────────────────────────────────────────

def get_platform() -> str:
    """Return 'windows', 'linux', or 'macos'."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return "linux"


# ─── Check Functions ─────────────────────────────────────────────────────────

def check_python() -> bool:
    version = sys.version_info
    if version >= (3, 10):
        print_ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    print_fail(f"Python {version.major}.{version.minor} (need 3.10+)")
    return False


def check_tkinter() -> bool:
    try:
        import tkinter  # noqa: F401
        print_ok("tkinter available")
        return True
    except ImportError:
        print_fail("tkinter not available")
        return False


def check_venv_exists() -> bool:
    plat = get_platform()
    if plat == "windows":
        python_path = VENV_DIR / "Scripts" / "python.exe"
    else:
        python_path = VENV_DIR / "bin" / "python"

    if python_path.exists():
        print_ok(f"venv_devtools exists at {VENV_DIR.relative_to(PROJECT_ROOT)}")
        return True
    print_info("venv_devtools not found (will be created)")
    return False


def check_venv_deps() -> bool:
    """Check if all Python dependencies are installed in the devtools venv."""
    plat = get_platform()
    if plat == "windows":
        python_path = VENV_DIR / "Scripts" / "python.exe"
    else:
        python_path = VENV_DIR / "bin" / "python"

    if not python_path.exists():
        return False

    missing = []
    for dep in PYTHON_DEPS:
        # Map package name to import name
        import_name = dep.replace("-binary", "").replace("-", "_")
        result = run_cmd(
            [str(python_path), "-c", f"import {import_name}"],
            check=False,
            capture=True,
        )
        if result.returncode != 0:
            missing.append(dep)

    if not missing:
        print_ok(f"All Python deps installed ({', '.join(PYTHON_DEPS)})")
        return True
    print_info(f"Missing Python deps: {', '.join(missing)}")
    return False


def check_linux_system_deps() -> dict:
    """Check which Linux system packages are missing. Returns dict of missing packages."""
    missing = {}

    # Check dbus-launch (provided by dbus-x11)
    if not cmd_exists("dbus-launch"):
        missing["dbus-x11"] = LINUX_SYSTEM_DEPS["dbus-x11"]

    # Check tkinter (python3-tk)
    try:
        import tkinter  # noqa: F401
    except ImportError:
        missing["python3-tk"] = LINUX_SYSTEM_DEPS["python3-tk"]

    # Check venv module
    result = run_cmd(
        [sys.executable, "-c", "import venv"],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        missing["python3-venv"] = LINUX_SYSTEM_DEPS["python3-venv"]

    return missing


# ─── Install Functions ────────────────────────────────────────────────────────

def install_linux_system_deps(missing: dict) -> bool:
    """Install missing Linux system packages via apt."""
    if not missing:
        print_ok("All system dependencies present")
        return True

    packages = list(missing.keys())
    print_info(f"Installing system packages: {', '.join(packages)}")

    # Check if we can use sudo
    if os.geteuid() == 0:
        cmd = ["apt-get", "install", "-y"] + packages
    elif cmd_exists("sudo"):
        cmd = ["sudo", "apt-get", "install", "-y"] + packages
    else:
        print_fail("Cannot install system packages (not root and sudo not available)")
        print_info(f"Install manually: sudo apt install {' '.join(packages)}")
        return False

    try:
        run_cmd(cmd)
        print_ok(f"Installed: {', '.join(packages)}")
        return True
    except subprocess.CalledProcessError as e:
        print_fail(f"apt install failed: {e}")
        print_info(f"Install manually: sudo apt install {' '.join(packages)}")
        return False


def install_macos_system_deps() -> bool:
    """Check and advise on macOS system dependencies."""
    try:
        import tkinter  # noqa: F401
        print_ok("tkinter available")
        return True
    except ImportError:
        if cmd_exists("brew"):
            print_info("Installing python-tk via Homebrew...")
            try:
                run_cmd(["brew", "install", "python-tk"])
                print_ok("python-tk installed via Homebrew")
                return True
            except subprocess.CalledProcessError:
                print_fail("Homebrew install failed")
        print_warn("tkinter not available. Install via:")
        print_info("  brew install python-tk")
        print_info("  or reinstall Python from python.org (includes tkinter)")
        return False


def create_venv() -> bool:
    """Create the isolated devtools virtual environment."""
    if VENV_DIR.exists():
        print_info("Removing existing venv_devtools...")
        shutil.rmtree(VENV_DIR)

    print_info("Creating virtual environment...")
    try:
        run_cmd([sys.executable, "-m", "venv", str(VENV_DIR)])
        print_ok(f"Created {VENV_DIR.relative_to(PROJECT_ROOT)}")
        return True
    except subprocess.CalledProcessError as e:
        print_fail(f"Failed to create venv: {e}")
        plat = get_platform()
        if plat == "linux":
            print_info("Try: sudo apt install python3-venv")
        return False


def install_python_deps() -> bool:
    """Install Python dependencies into the devtools venv."""
    plat = get_platform()
    if plat == "windows":
        pip_path = VENV_DIR / "Scripts" / "pip"
    else:
        pip_path = VENV_DIR / "bin" / "pip"

    # Upgrade pip first
    print_info("Upgrading pip...")
    try:
        run_cmd([str(pip_path), "install", "--upgrade", "pip", "-q"])
    except subprocess.CalledProcessError:
        pass  # Non-fatal

    # Install from requirements.txt if it exists, otherwise install directly
    if REQUIREMENTS_FILE.exists():
        print_info(f"Installing from {REQUIREMENTS_FILE.name}...")
        try:
            run_cmd([str(pip_path), "install", "-r", str(REQUIREMENTS_FILE), "-q"])
            print_ok(f"Installed: {', '.join(PYTHON_DEPS)}")
            return True
        except subprocess.CalledProcessError as e:
            print_fail(f"pip install failed: {e}")
            return False
    else:
        print_info(f"Installing: {', '.join(PYTHON_DEPS)}...")
        try:
            run_cmd([str(pip_path), "install"] + PYTHON_DEPS + ["-q"])
            print_ok(f"Installed: {', '.join(PYTHON_DEPS)}")
            return True
        except subprocess.CalledProcessError as e:
            print_fail(f"pip install failed: {e}")
            return False


# ─── Update Launchers ────────────────────────────────────────────────────────

def update_launchers() -> None:
    """Ensure launcher scripts point to venv_devtools first."""
    plat = get_platform()

    # Update the shell launcher
    launcher_sh = DEVTOOLS_DIR / "launch_control_panel.sh"
    if launcher_sh.exists():
        content = launcher_sh.read_text()
        # Check if it already references venv_devtools
        if "venv_devtools" not in content:
            new_content = content.replace(
                'if [ -x "$PROJECT_ROOT/venv/bin/python" ]; then',
                'if [ -x "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" ]; then\n'
                '    exec "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"\n'
                'elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then',
            )
            launcher_sh.write_text(new_content)
            print_ok("Updated launch_control_panel.sh (prefers venv_devtools)")
        else:
            print_ok("launch_control_panel.sh already configured")

    # Update the bat launcher
    launcher_bat = DEVTOOLS_DIR / "launch_control_panel.bat"
    if launcher_bat.exists():
        content = launcher_bat.read_text()
        if "venv_devtools" not in content:
            new_content = content.replace(
                'if exist "venv\\Scripts\\python.exe" (',
                'if exist "dev_tools\\venv_devtools\\Scripts\\python.exe" (\n'
                '    echo Starting GiljoAI MCP Developer Control Panel...\n'
                '    echo Using dev_tools venv_devtools Python\n'
                '    echo.\n'
                '    "dev_tools\\venv_devtools\\Scripts\\python.exe" "dev_tools\\control_panel.py" %*\n'
                '    goto :done\n'
                ')\n\n'
                'if exist "venv\\Scripts\\python.exe" (',
            )
            launcher_bat.write_text(new_content)
            print_ok("Updated launch_control_panel.bat (prefers venv_devtools)")
        else:
            print_ok("launch_control_panel.bat already configured")

    # Update sudo launcher
    launcher_sudo = DEVTOOLS_DIR / "control_panel_sudo.sh"
    if launcher_sudo.exists():
        content = launcher_sudo.read_text()
        if "venv_devtools" not in content:
            new_content = content.replace(
                'if [ -x "$PROJECT_ROOT/venv/bin/python" ]; then',
                'if [ -x "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" ]; then\n'
                '    exec "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"\n'
                'elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then',
            )
            launcher_sudo.write_text(new_content)
            print_ok("Updated control_panel_sudo.sh (prefers venv_devtools)")
        else:
            print_ok("control_panel_sudo.sh already configured")


# ─── Main ─────────────────────────────────────────────────────────────────────

def check_only() -> None:
    """Check status without installing anything."""
    print_header("Developer Control Panel - Status Check")

    plat = get_platform()
    print_info(f"Platform: {plat}")

    check_python()
    check_tkinter()
    check_venv_exists()
    check_venv_deps()

    if plat == "linux":
        missing = check_linux_system_deps()
        if missing:
            for pkg, reason in missing.items():
                print_warn(f"Missing: {pkg} ({reason})")
        else:
            print_ok("All Linux system deps present")

    print()


def main() -> None:
    if "--check" in sys.argv:
        check_only()
        return

    plat = get_platform()
    errors = []

    print_header("GiljoAI MCP - Developer Control Panel Setup")
    print_info(f"Platform: {plat}")
    print_info(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print_info(f"Project: {PROJECT_ROOT}")

    # Step 1: Check Python version
    print_header("Step 1/5: Checking Python")
    if not check_python():
        print_fail("Python 3.10+ is required. Please upgrade.")
        sys.exit(1)

    # Step 2: Install system dependencies (platform-specific)
    print_header("Step 2/5: System Dependencies")
    if plat == "linux":
        missing = check_linux_system_deps()
        if missing:
            if not install_linux_system_deps(missing):
                errors.append("Some system packages could not be installed")
        else:
            print_ok("All system dependencies present")
    elif plat == "macos":
        if not install_macos_system_deps():
            errors.append("tkinter may not be available")
    else:
        # Windows: tkinter ships with Python installer
        if check_tkinter():
            print_ok("Windows: tkinter included with Python")
        else:
            print_warn("tkinter not found - reinstall Python with tkinter option checked")
            errors.append("tkinter not available")

    # Step 3: Check tkinter is working
    print_header("Step 3/5: Checking tkinter")
    if not check_tkinter():
        errors.append("tkinter not available - GUI will not work")

    # Step 4: Create virtual environment and install deps
    print_header("Step 4/5: Virtual Environment")
    if not create_venv():
        print_fail("Cannot continue without virtual environment")
        sys.exit(1)

    if not install_python_deps():
        print_fail("Failed to install Python dependencies")
        errors.append("Python dependencies incomplete")

    # Step 5: Update launcher scripts
    print_header("Step 5/5: Updating Launchers")
    update_launchers()

    # Summary
    print_header("Setup Complete")

    if errors:
        print_warn(f"{len(errors)} warning(s):")
        for err in errors:
            print_warn(f"  - {err}")
        print()

    print_ok(f"Virtual environment: dev_tools/venv_devtools/")
    print_ok(f"Dependencies: {', '.join(PYTHON_DEPS)}")
    print()
    print("  Launch the control panel:")
    if plat == "windows":
        print("    dev_tools\\launch_control_panel.bat")
    else:
        print("    bash dev_tools/launch_control_panel.sh")
    print()
    print("  Or run directly:")
    if plat == "windows":
        print("    dev_tools\\venv_devtools\\Scripts\\python dev_tools\\control_panel.py")
    else:
        print("    dev_tools/venv_devtools/bin/python dev_tools/control_panel.py")
    print()


if __name__ == "__main__":
    main()
