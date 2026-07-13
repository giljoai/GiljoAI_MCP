# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Python interpreter / virtualenv / pip dependency phase of the CE installer (BE-9060 split).

Methods moved VERBATIM out of install.py's UnifiedInstaller. This class is a
mixin: it is only ever instantiated as part of UnifiedInstaller and relies on
attributes (settings, platform, venv_dir, install_dir, requirements_file,
constraints_file) and the self._print_* helpers the main class defines.
"""

import subprocess
import sys
from typing import Any

from colorama import Fore, Style


MIN_PYTHON_VERSION = (3, 10)


class PythonEnvSetupMixin:
    """Python version check, venv creation, and pip dependency installation."""

    def _ensure_venv_site_packages(self) -> None:
        """Ensure virtualenv site-packages and src/ are available on sys.path."""
        paths_to_add = []

        # Windows site-packages
        paths_to_add.append(self.venv_dir / "Lib" / "site-packages")

        # POSIX site-packages with python version
        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        paths_to_add.append(self.venv_dir / "lib" / py_version / "site-packages")

        # Add src/ directory for giljo_mcp package imports
        paths_to_add.append(self.install_dir / "src")

        for path in paths_to_add:
            if path.exists():
                str_path = str(path)
                if str_path not in sys.path:
                    sys.path.insert(0, str_path)

    def check_python_version(self) -> bool:
        """
        Check if Python version meets requirements

        Returns:
            True if version is compatible, False otherwise
        """
        current_version = sys.version_info
        is_compatible = current_version >= MIN_PYTHON_VERSION

        # Handle both sys.version_info (named tuple) and regular tuple
        if hasattr(current_version, "major"):
            version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
        else:
            version_str = f"{current_version[0]}.{current_version[1]}.{current_version[2]}"

        if is_compatible:
            self._print_success(f"Python {version_str} detected")
        else:
            required_str = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
            self._print_error(f"Python {version_str} detected, but {required_str}+ required")
            return False

        # Debian/Ubuntu/WSL ship python3 without the ensurepip module (it
        # lives in a separate python3.X-venv apt package). venv creation
        # at line ~1529 fails with a CalledProcessError swallowed by
        # capture_output=True, leaving the user with no actionable
        # diagnosis. Probe ensurepip directly here so we can print a
        # clear remediation step before the failure. install.sh already
        # apt-installs python3.X-venv up front; this redundant check
        # protects standalone "python3 install.py" invocations on a
        # fresh Debian-family box.
        try:
            import importlib.util

            if importlib.util.find_spec("ensurepip") is None:
                self._print_error(f"Python {version_str} found, but the ensurepip module is missing.")
                print(
                    f"  {Fore.YELLOW}Fix:{Style.RESET_ALL}  "
                    f"sudo apt install -y python{sys.version_info.major}.{sys.version_info.minor}-venv"
                )
                print(f"  {Fore.YELLOW}Then:{Style.RESET_ALL} python3 install.py")
                return False
        except Exception as exc:  # pragma: no cover - defensive
            self._print_error(f"Could not probe ensurepip module: {exc}")
            return False

        return True

    def install_dependencies(self) -> dict[str, Any]:
        """
        Install Python dependencies

        Steps:
        1. Create virtual environment (if not exists)
        2. Install requirements from requirements.txt

        Returns:
            Installation result with success status
        """
        result = {"success": False}

        try:
            # Step 1: Create venv if needed
            if self.venv_dir.exists():
                self._print_info(f"Virtual environment already exists: {self.venv_dir}")
                result["venv_existed"] = True
            else:
                self._print_info(f"Creating virtual environment: {self.venv_dir}")
                subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True, capture_output=True)
                self._print_success("Virtual environment created")
                result["venv_created"] = True
                self.venv_created = True

            # Determine pip executable (platform-specific)
            self.platform.get_venv_pip(self.venv_dir)

            # Upgrade pip to latest before installing packages
            # Must use 'python -m pip' instead of pip.exe directly — on Windows,
            # pip.exe cannot replace itself while running.
            python_executable = self.platform.get_venv_python(self.venv_dir)
            self._print_info("Upgrading pip to latest version...")
            try:
                subprocess.run(
                    [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"],
                    check=True,
                    capture_output=True,
                    timeout=60,
                )
                self._print_success("pip upgraded")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                self._print_warning("pip upgrade skipped (non-critical)")

            # Step 2: Install requirements
            if not self.requirements_file.exists():
                self._print_error(f"requirements.txt not found: {self.requirements_file}")
                result["error"] = "requirements.txt missing"
                return result

            self._print_info("Installing Python packages (this may take 2-3 minutes)...")
            print(f"{Fore.WHITE}You will see pip's progress output below...{Style.RESET_ALL}\n")

            # INF-9057: constrain to the shipped pinned tree when present.
            # Tolerate its absence (an older extracted release) — pip then
            # resolves from the requirements.txt floors as before.
            constraints_args = []
            if self.constraints_file.exists():
                constraints_args = ["-c", str(self.constraints_file)]
                self._print_info("Applying pinned dependency constraints (requirements.lock)")
            else:
                self._print_warning("requirements.lock not found — installing from unpinned version floors")

            subprocess.run(
                [
                    str(python_executable),
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    "-r",
                    str(self.requirements_file),
                    *constraints_args,
                ],
                check=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            self._print_success("Dependencies installed successfully")

            # Register giljo_mcp as importable package (editable install, idempotent)
            try:
                subprocess.run(
                    [str(python_executable), "-m", "pip", "install", "-e", ".", "--quiet", *constraints_args],
                    check=True,
                    capture_output=True,
                    timeout=60,
                    cwd=str(self.install_dir),
                )
                self._print_success("Package registered (editable install)")
            except Exception as e:
                self._print_warning(f"Editable install skipped (non-fatal): {e}")

            # Dev-only steps: pre-commit hooks (use --dev flag)
            if self.settings.get("dev"):
                # Install pre-commit hooks (ensures git commits work without manual venv activation)
                self._print_info("Setting up pre-commit hooks...")
                try:
                    python_executable = self.platform.get_venv_python(self.venv_dir)
                    subprocess.run(
                        [str(python_executable), "-m", "pip", "install", "-q", "--no-cache-dir", "pre-commit>=3.5.0"],
                        check=True,
                        capture_output=True,
                        timeout=60,
                    )
                    subprocess.run(
                        [str(python_executable), "-m", "pre_commit", "install"],
                        check=True,
                        capture_output=True,
                        cwd=str(self.install_dir),
                        timeout=30,
                    )
                    self._print_success("Pre-commit hooks installed")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    self._print_warning(f"Pre-commit hook setup skipped: {e}")
                    self._print_info("Install later: pip install pre-commit && pre-commit install")

            else:
                self._print_info("Skipping dev tools (pre-commit). Use --dev to include them.")

            result["success"] = True
            return result

        except subprocess.TimeoutExpired:
            self._print_error("Installation timed out (exceeded 5 minutes)")
            result["error"] = "Timeout"
            return result

        except subprocess.CalledProcessError as e:
            self._print_error(f"pip install failed: {e}")
            result["error"] = str(e)
            return result

        except Exception as e:
            self._print_error(f"Dependency installation failed: {e}")
            result["error"] = str(e)
            return result
