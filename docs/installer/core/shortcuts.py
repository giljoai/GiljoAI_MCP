#!/usr/bin/env python3
"""
Desktop Shortcut Creator for GiljoAI MCP
Creates platform-specific desktop shortcuts with icons
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any
import logging


class ShortcutCreator:
    """Cross-platform desktop shortcut creator"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        # Initialize logger first
        self.logger = logging.getLogger(__name__)
        # Ensure install_dir is always an absolute path
        install_dir_raw = settings.get('install_dir', Path.cwd())
        self.install_dir = Path(install_dir_raw).resolve()
        self.system = platform.system()
        self.desktop_paths = self._get_all_desktop_paths()

        # Log paths for debugging
        self.logger.info(f"Install directory: {self.install_dir}")
        self.logger.info(f"Desktop locations found: {len(self.desktop_paths)}")
        for desktop in self.desktop_paths:
            self.logger.info(f"  - {desktop}")

    def _get_all_desktop_paths(self) -> list[Path]:
        """
        Get all available Desktop paths on the system.
        Creates shortcuts in multiple locations to ensure user sees them.

        Returns:
            List of valid Desktop paths (OneDrive, Local, etc.)
        """
        desktop_paths = []

        if platform.system() == "Windows":
            # Check OneDrive Desktop (personal)
            onedrive_desktop = os.environ.get('OneDrive')
            if onedrive_desktop:
                onedrive_desktop_path = Path(onedrive_desktop) / "Desktop"
                if onedrive_desktop_path.exists():
                    desktop_paths.append(onedrive_desktop_path)
                    self.logger.info(f"Found OneDrive Desktop: {onedrive_desktop_path}")

            # Check OneDrive Commercial (business)
            onedrive_commercial = os.environ.get('OneDriveCommercial')
            if onedrive_commercial:
                onedrive_commercial_path = Path(onedrive_commercial) / "Desktop"
                if onedrive_commercial_path.exists():
                    desktop_paths.append(onedrive_commercial_path)
                    self.logger.info(f"Found OneDrive Commercial Desktop: {onedrive_commercial_path}")

            # Always check local Desktop folder
            local_desktop = Path.home() / "Desktop"
            if local_desktop.exists() and local_desktop not in desktop_paths:
                desktop_paths.append(local_desktop)
                self.logger.info(f"Found Local Desktop: {local_desktop}")

        else:
            # Linux/macOS - standard Desktop location
            desktop_path = Path.home() / "Desktop"
            if desktop_path.exists():
                desktop_paths.append(desktop_path)
                self.logger.info(f"Found Desktop: {desktop_path}")

        # If no desktop found, create local Desktop as fallback
        if not desktop_paths:
            desktop_path = Path.home() / "Desktop"
            self.logger.warning(f"No Desktop found, creating: {desktop_path}")
            try:
                desktop_path.mkdir(parents=True, exist_ok=True)
                desktop_paths.append(desktop_path)
            except Exception as e:
                self.logger.error(f"Failed to create Desktop directory: {e}")

        return desktop_paths

    def create_shortcuts(self) -> Dict[str, Any]:
        """Create desktop shortcuts based on OS - creates in all available desktop locations"""
        result = {'success': False, 'created': [], 'errors': []}

        try:
            # Ensure all desktop directories exist
            for desktop in self.desktop_paths:
                desktop.mkdir(parents=True, exist_ok=True)

            if self.system == "Windows":
                result = self._create_windows_shortcuts()
            elif self.system == "Linux":
                result = self._create_linux_shortcuts()
            elif self.system == "Darwin":
                result = self._create_macos_shortcuts()
            else:
                result['errors'].append(f"Unsupported OS: {self.system}")

            return result

        except Exception as e:
            self.logger.error(f"Failed to create shortcuts: {e}")
            result['errors'].append(str(e))
            return result

    def _create_windows_shortcuts(self) -> Dict[str, Any]:
        """Create Windows .lnk shortcuts using PowerShell"""
        result = {'success': False, 'created': [], 'errors': []}

        # Verify install directory exists
        if not self.install_dir.exists():
            result['errors'].append(f"Install directory does not exist: {self.install_dir}")
            self.logger.error(f"Install directory not found: {self.install_dir}")
            return result

        # Icon paths (try both lowercase and capitalized)
        icon_dir = self.install_dir / "frontend" / "public"
        start_icon = icon_dir / "Start.ico" if (icon_dir / "Start.ico").exists() else icon_dir / "start.ico"
        stop_icon = icon_dir / "Stop.ico" if (icon_dir / "Stop.ico").exists() else icon_dir / "stop.ico"
        frontend_icon = icon_dir / "Fontend.ico" if (icon_dir / "Fontend.ico").exists() else icon_dir / "fontend.ico"
        giljo_icon = self.install_dir / "giljo.ico"  # Main icon is in root directory

        shortcuts = [
            {
                'name': 'Start GiljoAI Backend.lnk',
                'target': str(self.install_dir / 'start_backend.bat'),
                'icon': str(start_icon) if start_icon.exists() else None,
                'admin': False
            },
            {
                'name': 'Start GiljoAI Frontend.lnk',
                'target': str(self.install_dir / 'start_frontend.bat'),
                'icon': str(frontend_icon) if frontend_icon.exists() else None,
                'admin': False
            },
            {
                'name': 'Stop GiljoAI Backend.lnk',
                'target': str(self.install_dir / 'stop_backend.bat'),
                'icon': str(stop_icon) if stop_icon.exists() else None,
                'admin': True  # Stop should run as admin
            },
            {
                'name': 'Stop GiljoAI Frontend.lnk',
                'target': str(self.install_dir / 'stop_frontend.bat'),
                'icon': str(stop_icon) if stop_icon.exists() else None,
                'admin': True  # Stop should run as admin
            },
            {
                'name': 'Start GiljoAI (All Services).lnk',
                'target': str(self.install_dir / 'start_giljo.bat'),
                'icon': str(giljo_icon) if giljo_icon.exists() else None,
                'admin': False
            }
        ]

        # Create shortcuts in all available desktop locations
        for desktop_path in self.desktop_paths:
            for shortcut in shortcuts:
                try:
                    # Verify target file exists (only warn once, not per desktop)
                    if desktop_path == self.desktop_paths[0]:  # First desktop only
                        target_path = Path(shortcut['target'])
                        if not target_path.exists():
                            warning_msg = f"Target file not found: {target_path} - shortcut may not work"
                            self.logger.warning(warning_msg)

                    shortcut_path = desktop_path / shortcut['name']

                    # PowerShell script to create shortcut
                    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{shortcut['target']}"
$Shortcut.WorkingDirectory = "{self.install_dir}"
'''
                    if shortcut['icon']:
                        ps_script += f'$Shortcut.IconLocation = "{shortcut["icon"]}"\n'

                    ps_script += '$Shortcut.Save()'

                    # Log what we're creating
                    self.logger.debug(f"Creating shortcut: {shortcut['name']}")
                    self.logger.debug(f"  Target: {shortcut['target']}")
                    self.logger.debug(f"  Desktop: {shortcut_path}")
                    self.logger.debug(f"  Working Dir: {self.install_dir}")

                    # Execute PowerShell
                    proc = subprocess.run(
                        ['powershell', '-Command', ps_script],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if proc.returncode == 0:
                        result['created'].append(str(shortcut_path))
                        self.logger.info(f"Created shortcut: {shortcut['name']} -> {desktop_path}")
                    else:
                        error_msg = f"Failed to create {shortcut['name']} in {desktop_path}: {proc.stderr}"
                        result['errors'].append(error_msg)
                        self.logger.error(error_msg)

                except Exception as e:
                    error_msg = f"Error creating {shortcut['name']} in {desktop_path}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(error_msg)

        result['success'] = len(result['created']) > 0
        return result

    def _create_linux_shortcuts(self) -> Dict[str, Any]:
        """Create Linux .desktop files"""
        result = {'success': False, 'created': [], 'errors': []}

        # Verify install directory exists
        if not self.install_dir.exists():
            result['errors'].append(f"Install directory does not exist: {self.install_dir}")
            self.logger.error(f"Install directory not found: {self.install_dir}")
            return result

        # Icon paths
        start_icon = self.install_dir / "frontend" / "public" / "start.png"
        stop_icon = self.install_dir / "frontend" / "public" / "stop.png"
        frontend_icon = self.install_dir / "frontend" / "public" / "fontend.png"
        giljo_icon = self.install_dir / "giljo.png"

        shortcuts = [
            {
                'name': 'Start-GiljoAI-Backend.desktop',
                'exec': str(self.install_dir / 'start_backend.sh'),
                'icon': str(start_icon) if start_icon.exists() else 'system-run',
                'comment': 'Start GiljoAI Backend API Server',
                'terminal': True
            },
            {
                'name': 'Start-GiljoAI-Frontend.desktop',
                'exec': str(self.install_dir / 'start_frontend.sh'),
                'icon': str(frontend_icon) if frontend_icon.exists() else 'applications-internet',
                'comment': 'Start GiljoAI Frontend Dashboard',
                'terminal': True
            },
            {
                'name': 'Stop-GiljoAI-Backend.desktop',
                'exec': str(self.install_dir / 'stop_backend.sh'),
                'icon': str(stop_icon) if stop_icon.exists() else 'process-stop',
                'comment': 'Stop GiljoAI Backend API Server',
                'terminal': True
            },
            {
                'name': 'Stop-GiljoAI-Frontend.desktop',
                'exec': str(self.install_dir / 'stop_frontend.sh'),
                'icon': str(stop_icon) if stop_icon.exists() else 'process-stop',
                'comment': 'Stop GiljoAI Frontend Dashboard',
                'terminal': True
            },
            {
                'name': 'Start-GiljoAI-All-Services.desktop',
                'exec': str(self.install_dir / 'start_giljo.sh'),
                'icon': str(giljo_icon) if giljo_icon.exists() else 'system-run',
                'comment': 'Start All GiljoAI Services (Backend Only)',
                'terminal': True
            }
        ]

        # Create shortcuts in all available desktop locations
        for desktop_path in self.desktop_paths:
            for shortcut in shortcuts:
                try:
                    # Verify target script exists (only warn once, not per desktop)
                    if desktop_path == self.desktop_paths[0]:  # First desktop only
                        exec_path = Path(shortcut['exec'])
                        if not exec_path.exists():
                            warning_msg = f"Target script not found: {exec_path} - shortcut may not work"
                            self.logger.warning(warning_msg)

                    desktop_file = desktop_path / shortcut['name']

                    content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={shortcut['name'].replace('.desktop', '').replace('-', ' ')}
Comment={shortcut['comment']}
Exec={shortcut['exec']}
Icon={shortcut['icon']}
Path={self.install_dir}
Terminal={str(shortcut['terminal']).lower()}
Categories=Development;Utility;
'''

                    # Log what we're creating
                    self.logger.debug(f"Creating desktop file: {shortcut['name']}")
                    self.logger.debug(f"  Exec: {shortcut['exec']}")
                    self.logger.debug(f"  Path: {self.install_dir}")

                    desktop_file.write_text(content)
                    desktop_file.chmod(0o755)  # Make executable

                    result['created'].append(str(desktop_file))
                    self.logger.info(f"Created desktop file: {shortcut['name']} -> {desktop_path}")

                except Exception as e:
                    error_msg = f"Error creating {shortcut['name']} in {desktop_path}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(error_msg)

        result['success'] = len(result['created']) > 0
        return result

    def _create_macos_shortcuts(self) -> Dict[str, Any]:
        """Create macOS .command files"""
        result = {'success': False, 'created': [], 'errors': []}

        # Verify install directory exists
        if not self.install_dir.exists():
            result['errors'].append(f"Install directory does not exist: {self.install_dir}")
            self.logger.error(f"Install directory not found: {self.install_dir}")
            return result

        shortcuts = [
            {
                'name': 'Start GiljoAI Backend.command',
                'script': str(self.install_dir / 'start_backend.sh')
            },
            {
                'name': 'Start GiljoAI Frontend.command',
                'script': str(self.install_dir / 'start_frontend.sh')
            },
            {
                'name': 'Stop GiljoAI Backend.command',
                'script': str(self.install_dir / 'stop_backend.sh')
            },
            {
                'name': 'Stop GiljoAI Frontend.command',
                'script': str(self.install_dir / 'stop_frontend.sh')
            },
            {
                'name': 'Start GiljoAI (All Services).command',
                'script': str(self.install_dir / 'start_giljo.sh')
            }
        ]

        # Create shortcuts in all available desktop locations
        for desktop_path in self.desktop_paths:
            for shortcut in shortcuts:
                try:
                    # Verify target script exists (only warn once, not per desktop)
                    if desktop_path == self.desktop_paths[0]:  # First desktop only
                        script_path = Path(shortcut['script'])
                        if not script_path.exists():
                            warning_msg = f"Target script not found: {script_path} - shortcut may not work"
                            self.logger.warning(warning_msg)

                    command_file = desktop_path / shortcut['name']

                    content = f'''#!/bin/bash
cd "{self.install_dir}"
{shortcut['script']}
'''

                    # Log what we're creating
                    self.logger.debug(f"Creating command file: {shortcut['name']}")
                    self.logger.debug(f"  Script: {shortcut['script']}")
                    self.logger.debug(f"  Working Dir: {self.install_dir}")

                    command_file.write_text(content)
                    command_file.chmod(0o755)  # Make executable

                    result['created'].append(str(command_file))
                    self.logger.info(f"Created command file: {shortcut['name']} -> {desktop_path}")

                except Exception as e:
                    error_msg = f"Error creating {shortcut['name']} in {desktop_path}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(error_msg)

        result['success'] = len(result['created']) > 0
        return result


def create_desktop_shortcuts(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create desktop shortcuts for GiljoAI MCP

    Args:
        settings: Installation settings containing install_dir

    Returns:
        Dict with success status, list of created shortcuts, and any errors
    """
    creator = ShortcutCreator(settings)
    return creator.create_shortcuts()
