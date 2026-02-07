"""
Serena MCP Detection Service.

Detects if uvx and Serena MCP are installed on the system.
Uses cross-platform subprocess commands with proper error handling.
"""

import logging
import re
import subprocess  # nosec B404
from typing import Any, Optional


logger = logging.getLogger(__name__)


class SerenaDetector:
    """
    Service for detecting Serena MCP installation status.

    This service checks if:
    1. uvx is installed and accessible
    2. Serena MCP is available via uvx

    All operations are cross-platform and use subprocess with shell=False for security.
    """

    def __init__(self):
        """Initialize the SerenaDetector."""
        self.uvx_timeout = 5  # seconds for uvx check
        self.serena_timeout = 10  # seconds for serena check

    def detect(self) -> dict[str, Any]:
        """
        Detect if Serena MCP is installed.

        Returns:
            Dictionary containing:
                - installed (bool): True if Serena is available
                - uvx_available (bool): True if uvx is installed
                - version (str | None): Serena version if detected
                - error (str | None): Error message if detection failed
        """
        result = {
            "installed": False,
            "uvx_available": False,
            "version": None,
            "error": None,
        }

        # Step 1: Check if uvx is available
        uvx_available, uvx_error = self._check_uvx()
        result["uvx_available"] = uvx_available

        if not uvx_available:
            result["error"] = uvx_error or "uvx not found on system"
            logger.info(f"uvx not available: {result['error']}")
            return result

        # Step 2: Check if Serena is available via uvx
        serena_installed, version, serena_error = self._check_serena()

        if serena_installed:
            result["installed"] = True
            result["version"] = version
            logger.info(f"Serena MCP detected: version {version}")
        else:
            result["error"] = serena_error or "Serena MCP not found"
            logger.info(f"Serena MCP not available: {result['error']}")

        return result

    def _check_uvx(self) -> tuple[bool, Optional[str]]:
        """
        Check if uvx is installed.

        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            result = subprocess.run(  # noqa: S603 - uvx is standard Python tool installer
                ["uvx", "--version"],  # noqa: S607 - uvx is standard Python tool installer
                check=False,
                capture_output=True,
                text=True,
                timeout=self.uvx_timeout,
                shell=False,
            )

            if result.returncode == 0:
                return True, None
            return False, f"uvx check failed with code {result.returncode}"

        except FileNotFoundError:
            return False, "uvx not found on system PATH"
        except subprocess.TimeoutExpired:
            return False, "uvx check timeout"
        except subprocess.CalledProcessError as e:
            return False, f"uvx check failed: {e.stderr}"
        except (OSError, RuntimeError) as e:
            logger.error(f"Unexpected error checking uvx: {e}")
            return False, f"Unexpected error: {e!s}"

    def _check_serena(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if Serena MCP is available via uvx.

        Returns:
            Tuple of (is_installed, version, error_message)
        """
        try:
            result = subprocess.run(  # noqa: S603 - uvx is standard Python tool installer
                ["uvx", "serena", "--version"],  # noqa: S607 - uvx is standard Python tool installer
                check=False,
                capture_output=True,
                text=True,
                timeout=self.serena_timeout,
                shell=False,
            )

            if result.returncode == 0:
                version = self._parse_version(result.stdout)
                return True, version, None
            return False, None, f"Serena check failed with code {result.returncode}"

        except subprocess.TimeoutExpired:
            return False, None, "Serena check timeout"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, "stderr") else str(e)
            return False, None, f"Serena not found: {error_msg}"
        except (OSError, RuntimeError) as e:
            logger.error(f"Unexpected error checking Serena: {e}")
            return False, None, f"Unexpected error: {e!s}"

    def _parse_version(self, version_output: str) -> Optional[str]:
        """
        Parse version number from command output.

        Handles various version output formats:
        - "Serena MCP v1.2.3"
        - "serena 1.2.3"
        - "v1.2.3"
        - "1.2.3"

        Args:
            version_output: Raw output from version command

        Returns:
            Cleaned version string or None if not found
        """
        if not version_output:
            return None

        # Clean up whitespace
        version_output = version_output.strip()

        # Try to extract version number using regex
        # Matches patterns like: v1.2.3, 1.2.3, 1.2.3-beta
        version_pattern = r"v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)"
        match = re.search(version_pattern, version_output)

        if match:
            return match.group(1)

        # If no version found, return None
        return None
