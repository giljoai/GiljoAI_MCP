#!/usr/bin/env python3
"""
Enhanced Installation Manifest System for GiljoAI MCP Orchestrator

This module provides comprehensive tracking of all installed components,
directories, services, and configurations for clean uninstallation.

STANDARD NAMING: .giljo_mcp (with underscore)
"""

import json
import os
import platform
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import sys


class EnhancedInstallationManifest:
    """Enhanced manifest that tracks ALL installation artifacts"""

    def __init__(self, install_dir: Path = None):
        """Initialize enhanced installation manifest

        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = Path(install_dir) if install_dir else Path.cwd()
        self.manifest_file = self.install_dir / ".giljo_install_manifest.json"
        self.manifest_data = self._load_or_create_manifest()

    def _load_or_create_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create comprehensive new one"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r") as f:
                    data = json.load(f)
                    # Upgrade old manifest format if needed
                    if data.get("version", "1.0") < "2.0":
                        return self._upgrade_manifest(data)
                    return data
            except Exception:
                pass

        # Create new comprehensive manifest
        return {
            "version": "2.0",
            "installation_date": datetime.datetime.now().isoformat(),
            "last_modified": datetime.datetime.now().isoformat(),
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "install_directory": str(self.install_dir),

            # Core directories
            "external_directories": [],
            "home_config_directories": [],

            # Files tracking
            "files": {
                "core": [],
                "config": [],
                "data": [],
                "logs": []
            },

            # System components
            "services": [],
            "shortcuts": [],
            "registry_entries": [],
            "environment_variables": [],

            # Dependencies
            "dependencies": {
                "postgresql": {
                    "installed": False,
                    "location": None,
                    "service_name": None,
                    "data_directory": None
                },
                "redis": {
                    "installed": False,
                    "location": None,
                    "service_name": None,
                    "config_file": None
                },
                "docker": {
                    "installed": False,
                    "containers": [],
                    "volumes": [],
                    "networks": []
                }
            },

            # Configuration
            "configuration": {
                "profile": None,
                "database_type": None,
                "home_config_dir": None,
                "ports": {}
            },

            # User data (to be preserved on partial uninstall)
            "user_data": {
                "databases": [],
                "backups": [],
                "exports": [],
                "custom_configs": []
            }
        }

    def _upgrade_manifest(self, old_data: Dict) -> Dict:
        """Upgrade old manifest format to new comprehensive format"""
        new_data = self._load_or_create_manifest()

        # Preserve old data
        if "version" in old_data:
            new_data["original_version"] = old_data["version"]
        if "installation_date" in old_data:
            new_data["installation_date"] = old_data["installation_date"]
        if "profile" in old_data:
            new_data["configuration"]["profile"] = old_data["profile"]
        if "dependencies" in old_data:
            new_data["dependencies"].update(old_data["dependencies"])
        if "configuration" in old_data:
            new_data["configuration"].update(old_data["configuration"])

        return new_data

    def track_external_directory(self, directory: Path, purpose: str = "config"):
        """Track directories created outside the installation directory

        Args:
            directory: Path to external directory
            purpose: Purpose of directory (config, data, logs, etc.)
        """
        dir_entry = {
            "path": str(directory),
            "purpose": purpose,
            "created": datetime.datetime.now().isoformat()
        }

        # Check for home config directories specifically
        if str(directory).startswith(str(Path.home())):
            # Track both standard (.giljo_mcp) and legacy (.giljo-mcp) directories
            if ".giljo_mcp" in str(directory) or ".giljo-mcp" in str(directory):
                if dir_entry not in self.manifest_data["home_config_directories"]:
                    self.manifest_data["home_config_directories"].append(dir_entry)

        if dir_entry not in self.manifest_data["external_directories"]:
            self.manifest_data["external_directories"].append(dir_entry)

    def track_service(self, service_name: str, service_type: str, config: Dict = None):
        """Track installed services

        Args:
            service_name: Name of the service
            service_type: Type (windows_service, systemd, launchd, etc.)
            config: Service configuration details
        """
        service_entry = {
            "name": service_name,
            "type": service_type,
            "config": config or {},
            "created": datetime.datetime.now().isoformat()
        }

        # Remove duplicates
        self.manifest_data["services"] = [
            s for s in self.manifest_data["services"]
            if s["name"] != service_name
        ]
        self.manifest_data["services"].append(service_entry)

    def track_dependency(self, dep_name: str, details: Dict):
        """Track installed dependencies like PostgreSQL, Redis, etc.

        Args:
            dep_name: Name of dependency (postgresql, redis, docker)
            details: Installation details
        """
        if dep_name in self.manifest_data["dependencies"]:
            self.manifest_data["dependencies"][dep_name].update(details)

    def scan_and_update(self):
        """Scan system and update manifest with discovered components"""
        # Scan for home directories
        home = Path.home()

        # Standard naming convention: .giljo_mcp (underscore)
        config_dir = home / ".giljo_mcp"
        if config_dir.exists():
            self.track_external_directory(config_dir, "config")

            # Track subdirectories
            for subdir in ["config", "data", "logs"]:
                subdir_path = config_dir / subdir
                if subdir_path.exists():
                    self.track_external_directory(subdir_path, subdir)

        # Also check for legacy hyphen version to clean it up
        legacy_dir = home / ".giljo-mcp"
        if legacy_dir.exists():
            self.track_external_directory(legacy_dir, "legacy_config")
            print(f"  ⚠️  Found legacy directory: {legacy_dir}")
            print(f"     This will be removed during uninstall")

        # Windows-specific locations
        if platform.system() == "Windows":
            # ProgramData
            programdata_dir = Path("C:/ProgramData/GiljoAI")
            if programdata_dir.exists():
                self.track_external_directory(programdata_dir, "system_config")

            # AppData/Local
            appdata_dir = Path.home() / "AppData" / "Local" / "GiljoAI"
            if appdata_dir.exists():
                self.track_external_directory(appdata_dir, "app_data")

            # Check for Windows services
            try:
                import subprocess
                result = subprocess.run(
                    ["sc", "query", "type=", "service"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if "Redis" in result.stdout:
                    self.track_service("Redis", "windows_service")
                if "postgresql" in result.stdout:
                    self.track_service("postgresql-x64-16", "windows_service")
            except:
                pass

    def get_all_tracked_directories(self) -> List[str]:
        """Get list of all tracked directories for cleanup

        Returns:
            List of directory paths
        """
        dirs = [self.manifest_data["install_directory"]]

        # Add external directories
        for dir_entry in self.manifest_data["external_directories"]:
            if isinstance(dir_entry, dict):
                dirs.append(dir_entry["path"])
            else:
                dirs.append(str(dir_entry))

        # Add home config directories
        for dir_entry in self.manifest_data["home_config_directories"]:
            if isinstance(dir_entry, dict):
                dirs.append(dir_entry["path"])
            else:
                dirs.append(str(dir_entry))

        # Remove duplicates while preserving order
        seen = set()
        unique_dirs = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                unique_dirs.append(d)

        return unique_dirs

    def get_user_data_directories(self) -> List[str]:
        """Get directories containing user data (to preserve on partial uninstall)

        Returns:
            List of user data directory paths
        """
        user_dirs = []

        # Main data directories
        install_data = Path(self.manifest_data["install_directory"]) / "data"
        if install_data.exists():
            user_dirs.append(str(install_data))

        # External data directories
        for dir_entry in self.manifest_data["external_directories"]:
            if isinstance(dir_entry, dict):
                if dir_entry.get("purpose") in ["data", "backups", "exports"]:
                    user_dirs.append(dir_entry["path"])

        # User data from manifest
        for category in ["databases", "backups", "exports"]:
            for item in self.manifest_data["user_data"].get(category, []):
                if isinstance(item, str) and Path(item).exists():
                    user_dirs.append(str(Path(item).parent))

        return list(set(user_dirs))

    def save(self) -> bool:
        """Save manifest to disk

        Returns:
            Success status
        """
        try:
            self.manifest_data["last_modified"] = datetime.datetime.now().isoformat()

            # Create backup of existing manifest
            if self.manifest_file.exists():
                backup = self.manifest_file.with_suffix(".json.bak")
                import shutil
                shutil.copy2(self.manifest_file, backup)

            # Write manifest with pretty formatting
            with open(self.manifest_file, "w") as f:
                json.dump(self.manifest_data, f, indent=2, sort_keys=True)

            return True
        except Exception as e:
            print(f"Failed to save manifest: {e}")
            return False

    def generate_uninstall_report(self) -> str:
        """Generate a report of what will be uninstalled

        Returns:
            Formatted report string
        """
        report = ["=" * 60]
        report.append("GiljoAI MCP Installation Report")
        report.append("=" * 60)

        # Installation info
        report.append(f"\nInstalled: {self.manifest_data.get('installation_date', 'Unknown')}")
        report.append(f"Profile: {self.manifest_data['configuration'].get('profile', 'Unknown')}")
        report.append(f"Install Directory: {self.manifest_data['install_directory']}")

        # External directories
        if self.manifest_data["external_directories"]:
            report.append("\nExternal Directories:")
            for dir_entry in self.manifest_data["external_directories"]:
                if isinstance(dir_entry, dict):
                    path = dir_entry['path']
                    purpose = dir_entry.get('purpose', 'unknown')
                    if ".giljo-mcp" in path:
                        report.append(f"  - {path} (LEGACY HYPHEN VERSION - will be removed)")
                    else:
                        report.append(f"  - {path} ({purpose})")
                else:
                    report.append(f"  - {dir_entry}")

        # Home config directories
        if self.manifest_data["home_config_directories"]:
            report.append("\nHome Configuration Directories:")
            for dir_entry in self.manifest_data["home_config_directories"]:
                if isinstance(dir_entry, dict):
                    path = dir_entry['path']
                    if ".giljo-mcp" in path:
                        report.append(f"  - {path} (LEGACY - will be removed)")
                    else:
                        report.append(f"  - {path}")

        # Services
        if self.manifest_data["services"]:
            report.append("\nInstalled Services:")
            for service in self.manifest_data["services"]:
                report.append(f"  - {service['name']} ({service['type']})")

        # Dependencies
        report.append("\nDependencies:")
        for dep_name, dep_info in self.manifest_data["dependencies"].items():
            if dep_info.get("installed"):
                report.append(f"  - {dep_name}: {dep_info.get('location', 'Unknown location')}")

        # User data
        user_dirs = self.get_user_data_directories()
        if user_dirs:
            report.append("\nUser Data Directories (preserved on partial uninstall):")
            for dir_path in user_dirs:
                report.append(f"  - {dir_path}")

        report.append("\n" + "=" * 60)
        return "\n".join(report)


def main():
    """Test the enhanced manifest system"""
    manifest = EnhancedInstallationManifest()

    print("Scanning for installation components...")
    print("Standard naming: .giljo_mcp (underscore)")
    print("-" * 40)

    manifest.scan_and_update()

    print("\nInstallation Report:")
    print(manifest.generate_uninstall_report())

    if manifest.save():
        print(f"\nManifest saved to: {manifest.manifest_file}")
    else:
        print("\nFailed to save manifest")

    # Show what would be cleaned
    all_dirs = manifest.get_all_tracked_directories()
    print("\nDirectories tracked for complete uninstall:")
    for d in all_dirs:
        if ".giljo-mcp" in d:
            print(f"  - {d} [LEGACY - TO BE REMOVED]")
        else:
            print(f"  - {d}")


if __name__ == "__main__":
    main()
