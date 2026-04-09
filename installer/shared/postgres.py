# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Cross-platform PostgreSQL discovery utility.

This module provides PostgreSQL installation detection across Windows, Linux, and macOS.
It searches the system PATH, common installation locations, and accepts custom paths.
"""

import platform
import shutil
import subprocess
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional


class PostgreSQLDiscovery:
    """
    Cross-platform PostgreSQL discovery and validation.

    This class implements a multi-strategy approach to find PostgreSQL:
    1. Check system PATH for psql binary
    2. Scan platform-specific common installation locations
    3. Validate custom user-provided paths
    4. Verify PostgreSQL version compatibility (>= 14, recommend 18)
    """

    MIN_VERSION = 14
    MAX_VERSION = 18
    RECOMMENDED_VERSION = 18

    def __init__(self, platform_handler: Optional[Any] = None):
        """
        Initialize PostgreSQL discovery.

        Args:
            platform_handler: Optional platform-specific handler for advanced discovery
        """
        self.platform_handler = platform_handler
        self.logger = logging.getLogger(self.__class__.__name__)
        self.system = platform.system()

    def discover(self) -> Dict[str, Any]:
        """
        Discover PostgreSQL installation using multiple strategies.

        Returns:
            Dict with discovery results:
            {
                'found': bool,
                'psql_path': Path or None,
                'version': int or None,
                'version_string': str or None,
                'method': str  # 'PATH', 'COMMON_LOCATION', 'CUSTOM', 'NOT_FOUND'
            }
        """
        result = {"found": False, "psql_path": None, "version": None, "version_string": None, "method": "NOT_FOUND"}

        # Strategy 1: Check system PATH
        self.logger.info("Searching for PostgreSQL in system PATH...")
        psql_path = shutil.which("psql")
        if psql_path:
            self.logger.info(f"Found psql in PATH: {psql_path}")
            result["found"] = True
            result["psql_path"] = Path(psql_path)
            result["method"] = "PATH"

            # Get version
            version_info = self.get_postgresql_version(psql_path)
            if version_info:
                result["version"] = version_info.get("version")
                result["version_string"] = version_info.get("version_string")

            return result

        # Strategy 2: Scan common installation locations
        self.logger.info("PostgreSQL not in PATH, scanning common locations...")
        common_locations = self._get_common_locations()

        for location in common_locations:
            psql_candidate = location / "psql" if self.system != "Windows" else location / "psql.exe"

            if psql_candidate.exists():
                self.logger.info(f"Found psql at: {psql_candidate}")
                result["found"] = True
                result["psql_path"] = psql_candidate
                result["method"] = "COMMON_LOCATION"

                # Get version
                version_info = self.get_postgresql_version(str(psql_candidate))
                if version_info:
                    result["version"] = version_info.get("version")
                    result["version_string"] = version_info.get("version_string")

                return result

        # Strategy 3: Use platform handler if available
        if self.platform_handler and hasattr(self.platform_handler, "find_postgresql"):
            self.logger.info("Using platform handler for PostgreSQL discovery...")
            handler_result = self.platform_handler.find_postgresql()
            if handler_result and handler_result.get("found"):
                return handler_result

        # Not found
        self.logger.warning("PostgreSQL not found in PATH or common locations")
        return result

    def _get_common_locations(self) -> List[Path]:
        """
        Get list of platform-specific common PostgreSQL installation directories.

        Returns:
            List of Path objects to search for psql binary
        """
        locations = []

        if self.system == "Windows":
            # Windows common locations
            program_files = Path("C:/Program Files")
            program_files_x86 = Path("C:/Program Files (x86)")

            # PostgreSQL official installer locations (versions 18 down to 14)
            for version in range(18, 13, -1):
                locations.extend(
                    [
                        program_files / f"PostgreSQL/{version}/bin",
                        program_files_x86 / f"PostgreSQL/{version}/bin",
                        program_files / f"PostgreSQL {version}/bin",
                    ]
                )

            # EnterpriseDB locations
            locations.extend(
                [
                    program_files / "PostgreSQL/bin",
                    program_files / "edb/languagepack/v2/PostgreSQL/bin",
                ]
            )

            # Custom drive installations (common for large databases)
            for drive in ["D:", "E:", "F:", "G:"]:
                locations.append(Path(f"{drive}/PostgreSQL/bin"))

        elif self.system == "Linux":
            # Linux common locations
            locations.extend(
                [
                    Path("/usr/bin"),
                    Path("/usr/local/bin"),
                    Path("/usr/pgsql-18/bin"),
                    Path("/usr/pgsql-17/bin"),
                    Path("/usr/pgsql-16/bin"),
                    Path("/usr/pgsql-15/bin"),
                    Path("/usr/pgsql-14/bin"),
                    Path("/usr/lib/postgresql/18/bin"),
                    Path("/usr/lib/postgresql/17/bin"),
                    Path("/usr/lib/postgresql/16/bin"),
                    Path("/usr/lib/postgresql/15/bin"),
                    Path("/usr/lib/postgresql/14/bin"),
                    Path("/opt/postgresql/bin"),
                ]
            )

        elif self.system == "Darwin":  # macOS
            # macOS common locations
            locations.extend(
                [
                    Path("/usr/local/bin"),
                    Path("/opt/homebrew/bin"),  # Apple Silicon Homebrew
                    Path("/usr/local/opt/postgresql@18/bin"),
                    Path("/usr/local/opt/postgresql@17/bin"),
                    Path("/usr/local/opt/postgresql@16/bin"),
                    Path("/usr/local/opt/postgresql@15/bin"),
                    Path("/usr/local/opt/postgresql@14/bin"),
                    Path("/Library/PostgreSQL/18/bin"),
                    Path("/Library/PostgreSQL/17/bin"),
                    Path("/Library/PostgreSQL/16/bin"),
                    Path("/Library/PostgreSQL/15/bin"),
                    Path("/Library/PostgreSQL/14/bin"),
                    Path("/Applications/Postgres.app/Contents/Versions/latest/bin"),
                ]
            )

        return locations

    def get_postgresql_version(self, psql_path: str) -> Optional[Dict[str, Any]]:
        """
        Get PostgreSQL version from psql binary.

        Args:
            psql_path: Path to psql executable

        Returns:
            Dict with version info or None if detection fails:
            {
                'version': int,  # Major version number
                'version_string': str  # Full version string
            }
        """
        try:
            result = subprocess.run([psql_path, "--version"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                version_output = result.stdout.strip()
                self.logger.debug(f"Version output: {version_output}")

                # Parse version (e.g., "psql (PostgreSQL) 18.0")
                match = re.search(r"(\d+)\.(\d+)", version_output)
                if match:
                    major_version = int(match.group(1))
                    return {"version": major_version, "version_string": version_output}

            return None

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.warning(f"Failed to get PostgreSQL version: {e}")
            return None

    def validate_custom_path(self, custom_path: str) -> Dict[str, Any]:
        """
        Validate a user-provided custom PostgreSQL path.

        Args:
            custom_path: User-provided path to psql or PostgreSQL bin directory

        Returns:
            Dict with validation result:
            {
                'valid': bool,
                'psql_path': Path or None,
                'version': int or None,
                'version_string': str or None,
                'method': str,
                'error': str or None
            }
        """
        result = {
            "valid": False,
            "psql_path": None,
            "version": None,
            "version_string": None,
            "method": "CUSTOM",
            "error": None,
        }

        try:
            custom_path_obj = Path(custom_path)

            # Check if path points directly to psql
            if custom_path_obj.name.startswith("psql"):
                psql_path = custom_path_obj
            else:
                # Assume it's a bin directory
                psql_path = custom_path_obj / ("psql.exe" if self.system == "Windows" else "psql")

            if not psql_path.exists():
                result["error"] = f"psql not found at {psql_path}"
                return result

            # Validate version
            version_info = self.get_postgresql_version(str(psql_path))
            if not version_info:
                result["error"] = "Could not determine PostgreSQL version"
                return result

            result["valid"] = True
            result["psql_path"] = psql_path
            result["version"] = version_info.get("version")
            result["version_string"] = version_info.get("version_string")

            return result

        except Exception as e:
            result["error"] = f"Path validation failed: {str(e)}"
            return result

    def validate_version(self, version: int) -> Dict[str, Any]:
        """
        Validate PostgreSQL version compatibility.

        Args:
            version: Major PostgreSQL version number

        Returns:
            Dict with validation result:
            {
                'compatible': bool,
                'message': str,
                'severity': str  # 'ok', 'warning', 'error'
            }
        """
        if version < self.MIN_VERSION:
            return {
                "compatible": False,
                "message": f"PostgreSQL {version} is not supported. Minimum version: {self.MIN_VERSION}",
                "severity": "error",
            }
        elif version > self.MAX_VERSION:
            return {
                "compatible": True,
                "message": f"PostgreSQL {version} is newer than tested version {self.MAX_VERSION}. Compatibility not guaranteed.",
                "severity": "warning",
            }
        elif version < self.RECOMMENDED_VERSION:
            return {
                "compatible": True,
                "message": f"PostgreSQL {version} is supported but version {self.RECOMMENDED_VERSION} is recommended.",
                "severity": "warning",
            }
        else:
            return {
                "compatible": True,
                "message": f"PostgreSQL {version} - Excellent! This is the recommended version.",
                "severity": "ok",
            }


def find_postgresql() -> Dict[str, Any]:
    """
    Convenience function for quick PostgreSQL discovery.

    Returns:
        Discovery result dict from PostgreSQLDiscovery.discover()
    """
    discovery = PostgreSQLDiscovery()
    return discovery.discover()
