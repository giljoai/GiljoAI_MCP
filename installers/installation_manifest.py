#!/usr/bin/env python3
"""
Installation Manifest System for GiljoAI MCP Orchestrator

Tracks all installed files, directories, and settings for clean uninstallation.
"""

import json
import os
import platform
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib


class InstallationManifest:
    """Manages installation tracking for clean uninstallation"""
    
    def __init__(self, install_dir: Path = None):
        """Initialize installation manifest
        
        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = Path(install_dir) if install_dir else Path.cwd()
        self.manifest_file = self.install_dir / ".giljo_install_manifest.json"
        self.manifest_data = self._load_manifest()
        
    def _load_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create new one
        
        Returns:
            Manifest data dictionary
        """
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Create new manifest
        return {
            "version": "1.0.0",
            "installation_date": datetime.datetime.now().isoformat(),
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "install_directory": str(self.install_dir),
            "files": {},
            "directories": [],
            "shortcuts": [],
            "registry_entries": [],
            "services": [],
            "virtual_environments": [],
            "dependencies": [],
            "data_directories": [],
            "config_files": [],
            "user_settings": {}
        }
    
    def save_manifest(self):
        """Save manifest to disk"""
        try:
            # Update last modified time
            self.manifest_data["last_modified"] = datetime.datetime.now().isoformat()
            
            # Write manifest with pretty formatting
            with open(self.manifest_file, 'w') as f:
                json.dump(self.manifest_data, f, indent=2, sort_keys=True)
            return True
        except Exception as e:
            print(f"Failed to save manifest: {e}")
            return False
    
    def add_file(self, file_path: Path, category: str = "general", 
                 is_user_data: bool = False, checksum: bool = False) -> bool:
        """Add a file to the manifest
        
        Args:
            file_path: Path to the file
            category: Category of file (general, config, script, data, etc.)
            is_user_data: Whether this is user data (should be preserved on partial uninstall)
            checksum: Whether to calculate and store file checksum
            
        Returns:
            Success status
        """
        try:
            abs_path = file_path.resolve()
            rel_path = abs_path.relative_to(self.install_dir) if abs_path.is_relative_to(self.install_dir) else abs_path
            
            file_info = {
                "absolute_path": str(abs_path),
                "relative_path": str(rel_path),
                "category": category,
                "is_user_data": is_user_data,
                "size": abs_path.stat().st_size if abs_path.exists() else 0,
                "created": datetime.datetime.now().isoformat()
            }
            
            # Calculate checksum if requested
            if checksum and abs_path.exists():
                with open(abs_path, 'rb') as f:
                    file_info["sha256"] = hashlib.sha256(f.read()).hexdigest()
            
            # Store in manifest
            self.manifest_data["files"][str(rel_path)] = file_info
            
            # Also categorize special files
            if category == "config":
                if str(rel_path) not in self.manifest_data["config_files"]:
                    self.manifest_data["config_files"].append(str(rel_path))
            elif is_user_data:
                if str(rel_path) not in self.manifest_data["data_directories"]:
                    self.manifest_data["data_directories"].append(str(rel_path))
            
            return True
        except Exception as e:
            print(f"Failed to add file {file_path}: {e}")
            return False
    
    def add_directory(self, dir_path: Path, category: str = "general",
                     is_user_data: bool = False) -> bool:
        """Add a directory to the manifest
        
        Args:
            dir_path: Path to the directory
            category: Category of directory
            is_user_data: Whether this contains user data
            
        Returns:
            Success status
        """
        try:
            abs_path = dir_path.resolve()
            rel_path = abs_path.relative_to(self.install_dir) if abs_path.is_relative_to(self.install_dir) else abs_path
            
            dir_info = {
                "absolute_path": str(abs_path),
                "relative_path": str(rel_path),
                "category": category,
                "is_user_data": is_user_data,
                "created": datetime.datetime.now().isoformat()
            }
            
            # Store in manifest
            self.manifest_data["directories"].append(dir_info)
            
            # Track data directories separately
            if is_user_data and str(rel_path) not in self.manifest_data["data_directories"]:
                self.manifest_data["data_directories"].append(str(rel_path))
            
            return True
        except Exception as e:
            print(f"Failed to add directory {dir_path}: {e}")
            return False
    
    def add_shortcut(self, shortcut_path: Path, target: Path, 
                    shortcut_type: str = "desktop") -> bool:
        """Add a shortcut to the manifest
        
        Args:
            shortcut_path: Path to the shortcut
            target: Target of the shortcut
            shortcut_type: Type of shortcut (desktop, start_menu, etc.)
            
        Returns:
            Success status
        """
        try:
            shortcut_info = {
                "path": str(shortcut_path),
                "target": str(target),
                "type": shortcut_type,
                "created": datetime.datetime.now().isoformat()
            }
            
            self.manifest_data["shortcuts"].append(shortcut_info)
            return True
        except Exception as e:
            print(f"Failed to add shortcut {shortcut_path}: {e}")
            return False
    
    def add_registry_entry(self, key: str, value: str, data: Any) -> bool:
        """Add a Windows registry entry to the manifest
        
        Args:
            key: Registry key path
            value: Value name
            data: Value data
            
        Returns:
            Success status
        """
        if platform.system() != "Windows":
            return True  # Skip on non-Windows
        
        try:
            registry_info = {
                "key": key,
                "value": value,
                "data": str(data),
                "created": datetime.datetime.now().isoformat()
            }
            
            self.manifest_data["registry_entries"].append(registry_info)
            return True
        except Exception as e:
            print(f"Failed to add registry entry: {e}")
            return False
    
    def add_virtual_environment(self, venv_path: Path) -> bool:
        """Add a virtual environment to the manifest
        
        Args:
            venv_path: Path to the virtual environment
            
        Returns:
            Success status
        """
        try:
            venv_info = {
                "path": str(venv_path),
                "python_version": platform.python_version(),
                "created": datetime.datetime.now().isoformat()
            }
            
            self.manifest_data["virtual_environments"].append(venv_info)
            return True
        except Exception as e:
            print(f"Failed to add virtual environment: {e}")
            return False
    
    def add_dependency(self, name: str, version: str, 
                      install_method: str = "pip") -> bool:
        """Add an installed dependency to the manifest
        
        Args:
            name: Package name
            version: Package version
            install_method: How it was installed (pip, npm, etc.)
            
        Returns:
            Success status
        """
        try:
            dep_info = {
                "name": name,
                "version": version,
                "install_method": install_method,
                "installed": datetime.datetime.now().isoformat()
            }
            
            self.manifest_data["dependencies"].append(dep_info)
            return True
        except Exception as e:
            print(f"Failed to add dependency: {e}")
            return False
    
    def set_user_setting(self, key: str, value: Any):
        """Store a user setting/preference
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.manifest_data["user_settings"][key] = value
    
    def get_files_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all files in a specific category
        
        Args:
            category: Category to filter by
            
        Returns:
            List of file information dictionaries
        """
        return [
            info for info in self.manifest_data["files"].values()
            if info.get("category") == category
        ]
    
    def get_user_data_files(self) -> List[Dict[str, Any]]:
        """Get all files marked as user data
        
        Returns:
            List of user data file information
        """
        return [
            info for info in self.manifest_data["files"].values()
            if info.get("is_user_data", False)
        ]
    
    def get_user_data_directories(self) -> List[str]:
        """Get all directories containing user data
        
        Returns:
            List of directory paths
        """
        user_dirs = []
        
        # From directories list
        for dir_info in self.manifest_data["directories"]:
            if dir_info.get("is_user_data", False):
                user_dirs.append(dir_info["absolute_path"])
        
        # From data_directories list
        for rel_path in self.manifest_data["data_directories"]:
            abs_path = self.install_dir / rel_path
            if str(abs_path) not in user_dirs:
                user_dirs.append(str(abs_path))
        
        return user_dirs
    
    def get_all_installed_files(self) -> List[str]:
        """Get all installed file paths
        
        Returns:
            List of absolute file paths
        """
        return [
            info["absolute_path"] 
            for info in self.manifest_data["files"].values()
        ]
    
    def get_all_shortcuts(self) -> List[Dict[str, str]]:
        """Get all created shortcuts
        
        Returns:
            List of shortcut information
        """
        return self.manifest_data["shortcuts"]
    
    def get_installation_info(self) -> Dict[str, Any]:
        """Get general installation information
        
        Returns:
            Installation metadata
        """
        return {
            "version": self.manifest_data.get("version"),
            "installation_date": self.manifest_data.get("installation_date"),
            "platform": self.manifest_data.get("platform"),
            "install_directory": self.manifest_data.get("install_directory"),
            "last_modified": self.manifest_data.get("last_modified")
        }
    
    def validate_installation(self) -> Dict[str, List[str]]:
        """Validate the installation by checking if tracked files exist
        
        Returns:
            Dictionary with lists of missing and present files
        """
        missing = []
        present = []
        
        for file_info in self.manifest_data["files"].values():
            file_path = Path(file_info["absolute_path"])
            if file_path.exists():
                present.append(str(file_path))
            else:
                missing.append(str(file_path))
        
        return {
            "missing": missing,
            "present": present,
            "total": len(self.manifest_data["files"]),
            "valid": len(missing) == 0
        }


def create_installation_report(manifest: InstallationManifest) -> str:
    """Create a human-readable installation report
    
    Args:
        manifest: Installation manifest object
        
    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 60)
    report.append("GiljoAI MCP Installation Report")
    report.append("=" * 60)
    
    # Installation info
    info = manifest.get_installation_info()
    report.append(f"\nInstallation Date: {info.get('installation_date', 'Unknown')}")
    report.append(f"Install Directory: {info.get('install_directory', 'Unknown')}")
    report.append(f"Platform: {info.get('platform', 'Unknown')}")
    report.append(f"Version: {info.get('version', 'Unknown')}")
    
    # File statistics
    files = manifest.manifest_data["files"]
    report.append(f"\nTotal Files Tracked: {len(files)}")
    
    # Categories
    categories = {}
    for file_info in files.values():
        cat = file_info.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1
    
    report.append("\nFiles by Category:")
    for cat, count in sorted(categories.items()):
        report.append(f"  - {cat}: {count}")
    
    # User data
    user_files = manifest.get_user_data_files()
    user_dirs = manifest.get_user_data_directories()
    report.append(f"\nUser Data Files: {len(user_files)}")
    report.append(f"User Data Directories: {len(user_dirs)}")
    
    # Shortcuts
    shortcuts = manifest.get_all_shortcuts()
    report.append(f"\nShortcuts Created: {len(shortcuts)}")
    for shortcut in shortcuts:
        report.append(f"  - {shortcut.get('type', 'unknown')}: {shortcut.get('path', 'unknown')}")
    
    # Virtual environments
    venvs = manifest.manifest_data.get("virtual_environments", [])
    report.append(f"\nVirtual Environments: {len(venvs)}")
    
    # Dependencies
    deps = manifest.manifest_data.get("dependencies", [])
    report.append(f"\nDependencies Installed: {len(deps)}")
    
    # Validation
    validation = manifest.validate_installation()
    report.append(f"\nInstallation Status: {'Valid' if validation['valid'] else 'Issues Detected'}")
    report.append(f"  - Files Present: {len(validation['present'])}")
    report.append(f"  - Files Missing: {len(validation['missing'])}")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)


def main():
    """Test the installation manifest"""
    print("Testing Installation Manifest System")
    print("=" * 40)
    
    # Create manifest
    manifest = InstallationManifest()
    
    # Add some test entries
    manifest.add_file(Path("config.yaml"), category="config", is_user_data=True)
    manifest.add_file(Path("start_giljo.bat"), category="script")
    manifest.add_directory(Path("data"), is_user_data=True)
    manifest.add_shortcut(
        Path.home() / "Desktop" / "GiljoAI MCP.lnk",
        Path.cwd() / "start_giljo.bat",
        "desktop"
    )
    
    # Save manifest
    if manifest.save_manifest():
        print(f"[OK] Manifest saved to: {manifest.manifest_file}")
    else:
        print(f"[FAIL] Failed to save manifest")
    
    # Generate report
    print("\n" + create_installation_report(manifest))


if __name__ == "__main__":
    main()