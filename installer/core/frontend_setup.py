# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Frontend (npm) dependency phase of the CE installer (BE-9060 split).

Methods moved VERBATIM out of install.py's UnifiedInstaller. This class is a
mixin: it is only ever instantiated as part of UnifiedInstaller and relies on
attributes (settings, platform, install_dir) and the self._print_* helpers
the main class defines.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


MIN_DISK_SPACE_MB = 500
NPM_INSTALL_TIMEOUT = 300
NPM_MAX_RETRIES = 3


class FrontendSetupMixin:
    """npm preflight, install-with-retry, and frontend dependency verification."""

    @staticmethod
    def _get_node_version() -> str:
        """Get Node.js version string, or 'unknown' on failure."""
        with contextlib.suppress(Exception):
            proc = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10, check=False)
            return proc.stdout.strip()
        return "unknown"

    def _npm_preflight_checks(self, frontend_dir: Path) -> dict[str, Any]:
        """
        Run pre-flight checks before npm installation.

        Checks:
        1. npm registry accessibility (npm ping)
        2. Disk space (minimum 500MB)
        3. package-lock.json existence (warning if missing)

        Args:
            frontend_dir: Path to frontend directory

        Returns:
            Dict with 'healthy' (bool), 'issues' (list), 'warnings' (list)
        """
        result = {"healthy": True, "issues": [], "warnings": []}

        # Check 1: npm registry accessibility
        try:
            npm_ping = self.platform.run_npm_command(cmd=["npm", "ping"], cwd=frontend_dir, timeout=30)

            if not npm_ping["success"]:
                result["healthy"] = False
                result["issues"].append(f"npm registry unreachable: {npm_ping.get('stderr', 'Unknown error')}")
        except FileNotFoundError:
            result["healthy"] = False
            result["issues"].append("npm is not installed or not in PATH")
        except Exception as e:
            result["healthy"] = False
            result["issues"].append(f"npm registry check failed: {e!s}")

        # Check 2: Disk space
        try:
            disk_usage = shutil.disk_usage(frontend_dir)
            free_mb = disk_usage.free / (1024 * 1024)

            if free_mb < MIN_DISK_SPACE_MB:
                result["healthy"] = False
                result["issues"].append(
                    f"Insufficient disk space: {free_mb:.0f}MB available, {MIN_DISK_SPACE_MB}MB required"
                )
        except Exception as e:
            result["warnings"].append(f"Could not check disk space: {e!s}")

        # Check 3: package-lock.json existence
        lockfile = frontend_dir / "package-lock.json"
        if not lockfile.exists():
            result["warnings"].append("package-lock.json not found - will use 'npm install' instead of 'npm ci'")

        return result

    def _verify_npm_dependencies(self, frontend_dir: Path) -> bool:
        """
        Verify that critical npm dependencies are installed.

        Checks for presence of key packages that are imported by the frontend.
        This prevents false positives where node_modules exists but is incomplete.

        Args:
            frontend_dir: Path to frontend directory

        Returns:
            True if all critical dependencies are present, False otherwise
        """
        node_modules = frontend_dir / "node_modules"

        if not node_modules.exists():
            return False

        # Critical dependencies that must be present
        critical_deps = [
            "vue",
            "vuetify",
            "vue-router",
            "pinia",
            "axios",
            "lodash-es",  # Imported by useAutoSave.js
            "date-fns",
            "dompurify",
        ]

        for dep in critical_deps:
            dep_path = node_modules / dep
            if not dep_path.exists():
                self._print_warning(f"Missing dependency: {dep}")
                return False

        return True

    def _install_npm_dependencies_with_retry(self, frontend_dir: Path, max_retries: int = NPM_MAX_RETRIES) -> bool:
        """
        Install npm dependencies with production-grade retry logic.

        Strategy:
        1. Run pre-flight checks (npm registry, disk space, lockfile)
        2. Try npm ci (if package-lock.json exists)
        3. Fallback to npm install (if lockfile missing/corrupted)
        4. Two-tier verification (folder check + npm list)
        5. Clear cache on final retry
        6. Log all attempts to logs/install_npm.log

        Args:
            frontend_dir: Path to frontend directory
            max_retries: Maximum number of retry attempts (default: NPM_MAX_RETRIES)

        Returns:
            True if installation succeeded, False otherwise
        """
        # Ensure logs directory exists
        logs_dir = self._ensure_logs_dir()
        log_file = logs_dir / "install_npm.log"

        # Run pre-flight checks
        self._print_info("Running npm pre-flight checks...")
        preflight = self._npm_preflight_checks(frontend_dir)

        if not preflight["healthy"]:
            self._print_error("Pre-flight checks failed:")
            for issue in preflight["issues"]:
                self._print_error(f"  • {issue}")
            # Store pre-flight results for error reporting
            self._npm_preflight_results = preflight
            return False

        if preflight["warnings"]:
            for warning in preflight["warnings"]:
                self._print_warning(f"  • {warning}")

        # Store pre-flight results for error reporting
        self._npm_preflight_results = preflight

        # Determine strategy: npm ci vs npm install
        lockfile = frontend_dir / "package-lock.json"
        use_npm_ci = lockfile.exists()

        for attempt in range(max_retries):
            if attempt > 0:
                self._print_info(f"Retrying npm install (attempt {attempt + 1}/{max_retries})...")
            else:
                self._print_info("Installing frontend dependencies...")

            # Clear cache on final retry
            if attempt == max_retries - 1 and attempt > 0:
                self._print_info("Clearing npm cache before final attempt...")
                cache_result = self.platform.run_npm_command(
                    cmd=["npm", "cache", "clean", "--force"], cwd=frontend_dir, timeout=60
                )
                if cache_result["success"]:
                    self._print_success("npm cache cleared")

            # Choose npm command
            if use_npm_ci and attempt == 0:
                npm_cmd = ["npm", "ci"]
                cmd_name = "npm ci"
            else:
                npm_cmd = ["npm", "install"]
                cmd_name = "npm install"
                use_npm_ci = False  # Switch to npm install after first failure

            # Log attempt
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 70}\n")
                f.write(f"Attempt {attempt + 1}/{max_retries} - {datetime.now(UTC).isoformat()}\n")
                f.write(f"Command: {' '.join(npm_cmd)}\n")
                f.write(f"{'=' * 70}\n\n")

            # Run npm command
            npm_result = self.platform.run_npm_command(cmd=npm_cmd, cwd=frontend_dir, timeout=NPM_INSTALL_TIMEOUT)

            # Log output
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("STDOUT:\n")
                f.write(npm_result.get("stdout", "") + "\n\n")
                f.write("STDERR:\n")
                f.write(npm_result.get("stderr", "") + "\n\n")

            if npm_result["success"]:
                # First tier verification: folder check
                if not self._verify_npm_dependencies(frontend_dir):
                    self._print_warning(f"{cmd_name} succeeded but folder verification failed")
                    continue

                # Second tier verification: npm list
                self._print_info("Verifying installation integrity...")
                list_result = self.platform.run_npm_command(
                    cmd=["npm", "list", "--depth=0"], cwd=frontend_dir, timeout=30
                )

                # npm list can return non-zero even for valid installs (peer deps warnings)
                # So we just check that it doesn't completely fail
                if "ENOENT" in list_result.get("stderr", "") or "ERR!" in list_result.get("stderr", ""):
                    self._print_warning(f"{cmd_name} succeeded but npm list verification failed")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write("NPM LIST VERIFICATION FAILED:\n")
                        f.write(list_result.get("stderr", "") + "\n\n")
                    continue

                # Both tiers passed
                self._print_success("Frontend dependencies installed and verified successfully")
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write("SUCCESS: Installation verified\n")
                return True
            # npm command failed
            error_msg = npm_result.get("stderr", npm_result.get("error", "Unknown error"))
            self._print_warning(f"Attempt {attempt + 1} failed: {error_msg[:100]}...")

            # If npm ci failed, try npm install next
            if "ci" in npm_cmd and attempt == 0:
                self._print_info("npm ci failed, will try npm install next")
                use_npm_ci = False

            # Wait before retry (exponential backoff: 2s, 4s, 8s)
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                self._print_info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        # All retries exhausted
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\nFAILURE: All {max_retries} attempts exhausted\n")
        return False

    def install_frontend_dependencies(self) -> dict[str, Any]:
        """
        Install frontend dependencies during the main installation process.

        This method handles npm dependency installation with production-grade
        retry logic, pre-flight checks, and comprehensive error handling.

        Returns:
            Result dictionary with success status and details
        """
        result = {"success": False}

        try:
            # Check if npm is available
            if not shutil.which("npm"):
                self._print_warning("npm not found - skipping frontend dependencies")
                self._print_info("Install Node.js from: https://nodejs.org/")
                result["success"] = True  # Not a failure - just skipped
                result["skipped"] = True
                result["reason"] = "npm not available"
                return result

            # Check if frontend directory exists
            frontend_dir = self.install_dir / "frontend"
            if not frontend_dir.exists():
                self._print_warning("Frontend directory not found - skipping frontend dependencies")
                result["success"] = True  # Not a failure - just skipped
                result["skipped"] = True
                result["reason"] = "frontend directory not found"
                return result

            self._print_info("Installing frontend dependencies...")

            # Check if dependencies are already installed and verified
            if self._verify_npm_dependencies(frontend_dir):
                self._print_success("Frontend dependencies already installed and verified")
                result["success"] = True
                result["already_installed"] = True
                return result

            # Install dependencies with retry logic
            if self._install_npm_dependencies_with_retry(frontend_dir):
                self._print_success("Frontend dependencies installed successfully")
                result["success"] = True
                return result
            # CRITICAL: Frontend dependencies failed after retries - FAIL HARD
            self._print_error("=" * 70)
            self._print_error("INSTALLATION FAILED: Frontend dependencies could not be installed")
            self._print_error("=" * 70)
            self._print_error("")

            # Show pre-flight check results if available
            if hasattr(self, "_npm_preflight_results"):
                preflight = self._npm_preflight_results
                if preflight.get("issues"):
                    self._print_error("Pre-flight check issues detected:")
                    for issue in preflight["issues"]:
                        self._print_error(f"  • {issue}")
                    self._print_error("")

            # Show log file location
            log_file = self.install_dir / "logs" / "install_npm.log"
            if log_file.exists():
                self._print_error(f"Detailed logs: {log_file}")
                self._print_error("")

            self._print_error("Troubleshooting steps:")
            self._print_error("  1. Check network connectivity to npm registry:")
            self._print_error("     npm ping")
            self._print_error("     curl https://registry.npmjs.org/")
            self._print_error("")
            self._print_error(f"  2. Verify disk space (need ~{MIN_DISK_SPACE_MB}MB):")
            if self.platform.platform_name == "Windows":
                self._print_error("     dir")
            else:
                self._print_error("     df -h")
            self._print_error("")
            self._print_error("  3. Clear npm cache and retry manually:")
            self._print_error(f"     cd {frontend_dir}")
            self._print_error("     npm cache clean --force")
            self._print_error("     npm cache verify")
            self._print_error("     npm install --verbose")
            self._print_error("")
            self._print_error("  4. Check for proxy/firewall blocking npm registry:")
            self._print_error("     npm config get proxy")
            self._print_error("     npm config get https-proxy")
            self._print_error("")
            self._print_error("  5. If behind corporate proxy, configure npm:")
            self._print_error("     npm config set proxy http://proxy.company.com:8080")
            self._print_error("     npm config set https-proxy http://proxy.company.com:8080")
            self._print_error("")
            self._print_error("=" * 70)

            result["error"] = f"npm install failed after {NPM_MAX_RETRIES} retry attempts"
            result["success"] = False
            return result

        except Exception as e:
            self._print_error(f"Frontend dependency installation failed: {e}")
            result["error"] = str(e)
            result["success"] = False
            return result
