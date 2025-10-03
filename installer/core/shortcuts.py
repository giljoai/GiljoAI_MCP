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
        self.install_dir = Path(settings.get('install_dir', Path.cwd()))
        self.desktop = self._get_desktop_path()
        self.system = platform.system()
        self.logger = logging.getLogger(__name__)

    def _get_desktop_path(self) -> Path:
        """Get the correct Desktop path, checking for OneDrive Desktop on Windows"""
        if platform.system() == "Windows":
            # Check for OneDrive Desktop first
            onedrive_desktop = os.environ.get('OneDrive')
            if onedrive_desktop:
                onedrive_desktop_path = Path(onedrive_desktop) / "Desktop"
                if onedrive_desktop_path.exists():
                    return onedrive_desktop_path

            # Check OneDriveCommercial (for business accounts)
            onedrive_commercial = os.environ.get('OneDriveCommercial')
            if onedrive_commercial:
                onedrive_commercial_path = Path(onedrive_commercial) / "Desktop"
                if onedrive_commercial_path.exists():
                    return onedrive_commercial_path

        # Fall back to standard Desktop location
        return Path.home() / "Desktop"

    def create_shortcuts(self) -> Dict[str, Any]:
        """Create desktop shortcuts based on OS"""
        result = {'success': False, 'created': [], 'errors': []}

        try:
            # Ensure desktop directory exists
            self.desktop.mkdir(parents=True, exist_ok=True)

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

        # Icon paths (try both lowercase and capitalized)
        icon_dir = self.install_dir / "frontend" / "public"
        start_icon = icon_dir / "Start.ico" if (icon_dir / "Start.ico").exists() else icon_dir / "start.ico"
        stop_icon = icon_dir / "Stop.ico" if (icon_dir / "Stop.ico").exists() else icon_dir / "stop.ico"

        shortcuts = [
            {
                'name': 'Start GiljoAI.lnk',
                'target': str(self.install_dir / 'start_giljo.bat'),
                'icon': str(start_icon) if start_icon.exists() else None,
                'admin': False
            },
            {
                'name': 'Stop GiljoAI.lnk',
                'target': str(self.install_dir / 'stop_giljo.bat'),
                'icon': str(stop_icon) if stop_icon.exists() else None,
                'admin': True  # Stop should run as admin
            }
        ]

        for shortcut in shortcuts:
            try:
                shortcut_path = self.desktop / shortcut['name']

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

                # Execute PowerShell
                proc = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if proc.returncode == 0:
                    result['created'].append(str(shortcut_path))
                    self.logger.info(f"Created shortcut: {shortcut['name']}")
                else:
                    result['errors'].append(f"Failed to create {shortcut['name']}: {proc.stderr}")

            except Exception as e:
                result['errors'].append(f"Error creating {shortcut['name']}: {e}")

        result['success'] = len(result['created']) > 0
        return result

    def _create_linux_shortcuts(self) -> Dict[str, Any]:
        """Create Linux .desktop files"""
        result = {'success': False, 'created': [], 'errors': []}

        # Icon paths
        start_icon = self.install_dir / "frontend" / "public" / "start.png"
        stop_icon = self.install_dir / "frontend" / "public" / "stop.png"

        shortcuts = [
            {
                'name': 'Start-GiljoAI.desktop',
                'exec': str(self.install_dir / 'start_giljo.sh'),
                'icon': str(start_icon) if start_icon.exists() else 'system-run',
                'comment': 'Start GiljoAI MCP Services',
                'terminal': True
            },
            {
                'name': 'Stop-GiljoAI.desktop',
                'exec': str(self.install_dir / 'stop_giljo.sh'),
                'icon': str(stop_icon) if stop_icon.exists() else 'process-stop',
                'comment': 'Stop GiljoAI MCP Services',
                'terminal': True
            }
        ]

        for shortcut in shortcuts:
            try:
                desktop_file = self.desktop / shortcut['name']

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

                desktop_file.write_text(content)
                desktop_file.chmod(0o755)  # Make executable

                result['created'].append(str(desktop_file))
                self.logger.info(f"Created desktop file: {shortcut['name']}")

            except Exception as e:
                result['errors'].append(f"Error creating {shortcut['name']}: {e}")

        result['success'] = len(result['created']) > 0
        return result

    def _create_macos_shortcuts(self) -> Dict[str, Any]:
        """Create macOS .command files"""
        result = {'success': False, 'created': [], 'errors': []}

        shortcuts = [
            {
                'name': 'Start GiljoAI.command',
                'script': str(self.install_dir / 'start_giljo.sh')
            },
            {
                'name': 'Stop GiljoAI.command',
                'script': str(self.install_dir / 'stop_giljo.sh')
            }
        ]

        for shortcut in shortcuts:
            try:
                command_file = self.desktop / shortcut['name']

                content = f'''#!/bin/bash
cd "{self.install_dir}"
{shortcut['script']}
'''

                command_file.write_text(content)
                command_file.chmod(0o755)  # Make executable

                result['created'].append(str(command_file))
                self.logger.info(f"Created command file: {shortcut['name']}")

            except Exception as e:
                result['errors'].append(f"Error creating {shortcut['name']}: {e}")

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
