#!/usr/bin/env python3
"""
Launcher Creator for GiljoAI MCP Orchestrator

Creates desktop shortcuts, start menu entries, and launch scripts
across Windows, macOS, and Linux platforms.
"""

import os
import sys
import platform
import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Try to import installation manifest
try:
    from installation_manifest import InstallationManifest
except ImportError:
    InstallationManifest = None


class LauncherCreator:
    """Creates launchers and shortcuts for GiljoAI MCP"""

    def __init__(self, install_dir: Path = None):
        """Initialize launcher creator

        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = Path(install_dir) if install_dir else Path.cwd()
        self.system = platform.system().lower()
        self.home_dir = Path.home()

        # Define paths for different platforms
        self.desktop_path = self._get_desktop_path()
        self.start_menu_path = self._get_start_menu_path()

        # Application metadata
        self.app_name = "GiljoAI MCP Orchestrator"
        self.app_id = "com.giljoai.mcp"
        self.app_description = "AI-Powered Development Orchestration System"
        self.app_version = "1.0.0"
        
        # Initialize installation manifest if available
        self.manifest = None
        if InstallationManifest:
            try:
                self.manifest = InstallationManifest(self.install_dir)
            except Exception as e:
                print(f"Warning: Could not initialize installation manifest: {e}")

    def _get_desktop_path(self) -> Path:
        """Get the desktop path for the current platform"""
        if self.system == 'windows':
            # Try multiple methods to get desktop path
            desktop = os.environ.get('USERPROFILE', '')
            if desktop:
                return Path(desktop) / 'Desktop'
            return self.home_dir / 'Desktop'
        elif self.system == 'darwin':  # macOS
            return self.home_dir / 'Desktop'
        else:  # Linux
            # Check XDG desktop directory first
            xdg_desktop = os.environ.get('XDG_DESKTOP_DIR')
            if xdg_desktop:
                return Path(xdg_desktop)
            return self.home_dir / 'Desktop'

    def _get_start_menu_path(self) -> Optional[Path]:
        """Get the start menu path for Windows"""
        if self.system == 'windows':
            appdata = os.environ.get('APPDATA')
            if appdata:
                return Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'GiljoAI MCP'
        return None

    def create_desktop_shortcut(self) -> Tuple[bool, str]:
        """Create desktop shortcut for the application

        Returns:
            Tuple of (success, message)
        """
        if not self.desktop_path or not self.desktop_path.exists():
            return False, f"Desktop path not found: {self.desktop_path}"

        if self.system == 'windows':
            return self._create_windows_shortcut()
        elif self.system == 'darwin':
            return self._create_macos_app()
        else:
            return self._create_linux_desktop()

    def _create_windows_shortcut(self) -> Tuple[bool, str]:
        """Create Windows .lnk shortcut"""
        try:
            # Create VBScript to generate shortcut
            shortcut_path = self.desktop_path / f"{self.app_name}.lnk"
            vbs_script = self.install_dir / "create_shortcut.vbs"

            # Get the start script path
            start_script = self.install_dir / "start_giljo.bat"
            icon_path = self.install_dir / "frontend" / "public" / "favicon.ico"

            # Create VBScript content
            vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut("{shortcut_path}")
oShortcut.TargetPath = "{start_script}"
oShortcut.WorkingDirectory = "{self.install_dir}"
oShortcut.Description = "{self.app_description}"
oShortcut.IconLocation = "{icon_path}"
oShortcut.Save
'''

            # Write and execute VBScript
            vbs_script.write_text(vbs_content)
            subprocess.run(['cscript', '//nologo', str(vbs_script)], check=True)
            vbs_script.unlink()  # Clean up

            # Track in manifest
            if self.manifest:
                self.manifest.add_shortcut(shortcut_path, start_script, "desktop")
                self.manifest.save_manifest()

            return True, f"Created desktop shortcut: {shortcut_path}"

        except Exception as e:
            return False, f"Failed to create Windows shortcut: {e}"

    def _create_macos_app(self) -> Tuple[bool, str]:
        """Create macOS .app bundle"""
        try:
            app_name = f"{self.app_name}.app"
            app_path = self.desktop_path / app_name

            # Create app bundle structure
            contents_dir = app_path / "Contents"
            macos_dir = contents_dir / "MacOS"
            resources_dir = contents_dir / "Resources"

            # Create directories
            macos_dir.mkdir(parents=True, exist_ok=True)
            resources_dir.mkdir(parents=True, exist_ok=True)

            # Create launcher script
            launcher_script = macos_dir / "launcher"
            launcher_content = f'''#!/bin/bash
cd "{self.install_dir}"
./start_giljo.sh
'''
            launcher_script.write_text(launcher_content)
            launcher_script.chmod(0o755)

            # Create Info.plist
            info_plist = contents_dir / "Info.plist"
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>{self.app_id}</string>
    <key>CFBundleName</key>
    <string>{self.app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{self.app_name}</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleVersion</key>
    <string>{self.app_version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.app_version}</string>
</dict>
</plist>
'''
            info_plist.write_text(plist_content)

            # Copy icon if available
            icon_source = self.install_dir / "frontend" / "public" / "giljo-logo.png"
            if icon_source.exists():
                shutil.copy(icon_source, resources_dir / "icon.png")

            return True, f"Created macOS app bundle: {app_path}"

        except Exception as e:
            return False, f"Failed to create macOS app: {e}"

    def _create_linux_desktop(self) -> Tuple[bool, str]:
        """Create Linux .desktop file"""
        try:
            desktop_file = self.desktop_path / f"{self.app_id}.desktop"
            start_script = self.install_dir / "start_giljo.sh"
            icon_path = self.install_dir / "frontend" / "public" / "giljo-logo.png"

            # Create .desktop file content
            desktop_content = f'''[Desktop Entry]
Version={self.app_version}
Type=Application
Name={self.app_name}
Comment={self.app_description}
Exec={start_script}
Icon={icon_path}
Terminal=false
Categories=Development;Utility;
'''

            # Write desktop file
            desktop_file.write_text(desktop_content)
            desktop_file.chmod(0o755)

            return True, f"Created Linux desktop file: {desktop_file}"

        except Exception as e:
            return False, f"Failed to create Linux desktop file: {e}"

    def create_start_menu_entry(self) -> Tuple[bool, str]:
        """Create start menu entry (Windows only)

        Returns:
            Tuple of (success, message)
        """
        if self.system != 'windows':
            return True, "Start menu not applicable for this platform"

        if not self.start_menu_path:
            return False, "Start menu path not found"

        try:
            # Create program group directory
            self.start_menu_path.mkdir(parents=True, exist_ok=True)

            # Create shortcuts for different components
            shortcuts = [
                ("GiljoAI MCP Orchestrator", "start_giljo.bat", "Start the orchestrator"),
                ("Stop GiljoAI MCP", "stop_giljo.bat", "Stop the orchestrator"),
                ("GiljoAI Dashboard", "open_dashboard.bat", "Open web dashboard"),
                ("Configuration", "config.yaml", "Edit configuration"),
                ("Uninstall GiljoAI MCP", "uninstall.py", "Uninstall the application"),
            ]

            for name, target, description in shortcuts:
                shortcut_path = self.start_menu_path / f"{name}.lnk"
                target_path = self.install_dir / target

                # Skip if target doesn't exist
                if not target_path.exists() and target != "config.yaml":
                    continue

                # Create VBScript for each shortcut
                vbs_script = self.install_dir / f"create_{target.replace('.', '_')}_shortcut.vbs"
                icon_path = self.install_dir / "frontend" / "public" / "favicon.ico"

                vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut("{shortcut_path}")
oShortcut.TargetPath = "{target_path}"
oShortcut.WorkingDirectory = "{self.install_dir}"
oShortcut.Description = "{description}"
oShortcut.IconLocation = "{icon_path}"
oShortcut.Save
'''

                vbs_script.write_text(vbs_content)
                subprocess.run(['cscript', '//nologo', str(vbs_script)], check=True, capture_output=True)
                vbs_script.unlink()
                
                # Track in manifest
                if self.manifest:
                    self.manifest.add_shortcut(shortcut_path, target_path, "start_menu")

            # Save manifest after all shortcuts created
            if self.manifest:
                self.manifest.save_manifest()

            return True, f"Created start menu entries in: {self.start_menu_path}"

        except Exception as e:
            return False, f"Failed to create start menu entries: {e}"

    def create_start_script(self) -> Tuple[bool, str]:
        """Create platform-specific start script

        Returns:
            Tuple of (success, message)
        """
        if self.system == 'windows':
            return self._create_windows_start_script()
        else:
            return self._create_unix_start_script()

    def _create_windows_start_script(self) -> Tuple[bool, str]:
        """Create Windows batch start script"""
        try:
            script_path = self.install_dir / "start_giljo.bat"

            script_content = '''@echo off
setlocal

echo Starting GiljoAI MCP Orchestrator...
echo =====================================

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please run quickstart.bat to install Python
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv\\Scripts\\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\\Scripts\\activate.bat
    pip install -r requirements.txt
) else (
    call venv\\Scripts\\activate.bat
)

:: Start the MCP server in the background
echo Starting MCP server on port 6001...
start /b python -m giljo_mcp.server

:: Wait a moment for server to start
timeout /t 2 /nobreak >nul

:: Start the API server
echo Starting API server on port 6002...
start /b python -m giljo_mcp.api_server

:: Wait for API to be ready
timeout /t 2 /nobreak >nul

:: Start the frontend development server
if exist "frontend\\package.json" (
    echo Starting frontend on port 6000...
    cd frontend
    start /b npm run dev
    cd ..
)

:: Open browser to dashboard
timeout /t 3 /nobreak >nul
echo Opening dashboard in browser...
start http://localhost:6000

echo.
echo GiljoAI MCP Orchestrator is running!
echo =====================================
echo Dashboard: http://localhost:6000
echo API: http://localhost:6002
echo MCP Server: localhost:6001
echo.
echo Press Ctrl+C to stop all services
echo.

:: Keep the script running
:loop
timeout /t 60 /nobreak >nul
goto loop
'''

            script_path.write_text(script_content)
            
            # Track in manifest
            if self.manifest:
                self.manifest.add_file(script_path, category="script")
                self.manifest.save_manifest()
            
            return True, f"Created Windows start script: {script_path}"

        except Exception as e:
            return False, f"Failed to create Windows start script: {e}"

    def _create_unix_start_script(self) -> Tuple[bool, str]:
        """Create Unix shell start script"""
        try:
            script_path = self.install_dir / "start_giljo.sh"

            script_content = '''#!/bin/bash

echo "Starting GiljoAI MCP Orchestrator..."
echo "====================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please run ./quickstart.sh to install Python"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv/bin" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Function to cleanup on exit
cleanup() {
    echo "\\nStopping services..."
    kill $MCP_PID $API_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Start the MCP server in the background
echo "Starting MCP server on port 6001..."
python -m giljo_mcp.server &
MCP_PID=$!

# Wait a moment for server to start
sleep 2

# Start the API server
echo "Starting API server on port 6002..."
python -m giljo_mcp.api_server &
API_PID=$!

# Wait for API to be ready
sleep 2

# Start the frontend development server
if [ -f "frontend/package.json" ]; then
    echo "Starting frontend on port 6000..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

# Open browser to dashboard (platform-specific)
sleep 3
echo "Opening dashboard in browser..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:6000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:6000
fi

echo ""
echo "GiljoAI MCP Orchestrator is running!"
echo "====================================="
echo "Dashboard: http://localhost:6000"
echo "API: http://localhost:6002"
echo "MCP Server: localhost:6001"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep the script running
wait
'''

            script_path.write_text(script_content)
            script_path.chmod(0o755)
            
            # Track in manifest
            if self.manifest:
                self.manifest.add_file(script_path, category="script")
                self.manifest.save_manifest()
            
            return True, f"Created Unix start script: {script_path}"

        except Exception as e:
            return False, f"Failed to create Unix start script: {e}"

    def create_stop_script(self) -> Tuple[bool, str]:
        """Create platform-specific stop script

        Returns:
            Tuple of (success, message)
        """
        if self.system == 'windows':
            return self._create_windows_stop_script()
        else:
            return self._create_unix_stop_script()

    def _create_windows_stop_script(self) -> Tuple[bool, str]:
        """Create Windows batch stop script"""
        try:
            script_path = self.install_dir / "stop_giljo.bat"

            script_content = '''@echo off
echo Stopping GiljoAI MCP Orchestrator...

:: Kill Python processes running our services
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *giljo_mcp*" 2>nul
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *frontend*" 2>nul

:: Kill processes by port if still running
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6000') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6001') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6002') do taskkill /F /PID %%a 2>nul

echo All services stopped.
pause
'''

            script_path.write_text(script_content)
            
            # Track in manifest
            if self.manifest:
                self.manifest.add_file(script_path, category="script")
                self.manifest.save_manifest()
            
            return True, f"Created Windows stop script: {script_path}"

        except Exception as e:
            return False, f"Failed to create Windows stop script: {e}"

    def _create_unix_stop_script(self) -> Tuple[bool, str]:
        """Create Unix shell stop script"""
        try:
            script_path = self.install_dir / "stop_giljo.sh"

            script_content = '''#!/bin/bash

echo "Stopping GiljoAI MCP Orchestrator..."

# Kill processes by port
for port in 6000 6001 6002; do
    pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        kill -9 $pid 2>/dev/null
        echo "Stopped service on port $port"
    fi
done

# Kill any remaining Python processes with giljo_mcp
pkill -f "python.*giljo_mcp" 2>/dev/null

echo "All services stopped."
'''

            script_path.write_text(script_content)
            script_path.chmod(0o755)
            
            # Track in manifest
            if self.manifest:
                self.manifest.add_file(script_path, category="script")
                self.manifest.save_manifest()
            
            return True, f"Created Unix stop script: {script_path}"

        except Exception as e:
            return False, f"Failed to create Unix stop script: {e}"

    def create_open_dashboard_script(self) -> Tuple[bool, str]:
        """Create script to open dashboard in browser

        Returns:
            Tuple of (success, message)
        """
        if self.system == 'windows':
            script_path = self.install_dir / "open_dashboard.bat"
            script_content = '''@echo off
start http://localhost:6000
'''
        else:
            script_path = self.install_dir / "open_dashboard.sh"
            script_content = '''#!/bin/bash
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:6000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:6000
else
    echo "Please open http://localhost:6000 in your browser"
fi
'''

        try:
            script_path.write_text(script_content)
            if self.system != 'windows':
                script_path.chmod(0o755)
            
            # Track in manifest
            if self.manifest:
                self.manifest.add_file(script_path, category="script")
                self.manifest.save_manifest()
            
            return True, f"Created dashboard opener: {script_path}"
        except Exception as e:
            return False, f"Failed to create dashboard opener: {e}"

    def create_all_launchers(self) -> Dict[str, Tuple[bool, str]]:
        """Create all launchers and scripts

        Returns:
            Dictionary of results for each launcher type
        """
        results = {}

        # Create start/stop scripts
        results['start_script'] = self.create_start_script()
        results['stop_script'] = self.create_stop_script()
        results['dashboard_opener'] = self.create_open_dashboard_script()

        # Create desktop shortcut
        results['desktop_shortcut'] = self.create_desktop_shortcut()

        # Create start menu entries (Windows only)
        if self.system == 'windows':
            results['start_menu'] = self.create_start_menu_entry()

        return results

    def print_summary(self, results: Dict[str, Tuple[bool, str]]):
        """Print a summary of launcher creation results"""
        print("\n" + "="*50)
        print("LAUNCHER CREATION SUMMARY")
        print("="*50)

        success_count = 0
        for name, (success, message) in results.items():
            # Use ASCII characters for better compatibility
            status = "[OK]" if success else "[FAIL]"
            color = "\033[92m" if success else "\033[91m"
            reset = "\033[0m"

            # Handle encoding issues on Windows
            try:
                print(f"{color}{status}{reset} {name}: {message}")
            except UnicodeEncodeError:
                # Fallback to no colors
                print(f"{status} {name}: {message}")

            if success:
                success_count += 1

        print("="*50)
        print(f"Successfully created {success_count}/{len(results)} launchers")
        print("="*50)


def main():
    """Main entry point for launcher creator"""
    print("GiljoAI MCP Launcher Creator")
    print("============================\n")

    # Get installation directory
    if len(sys.argv) > 1:
        install_dir = Path(sys.argv[1])
    else:
        install_dir = Path.cwd()

    print(f"Installation directory: {install_dir}")
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}\n")

    # Create launcher creator instance
    creator = LauncherCreator(install_dir)

    # Create all launchers
    print("Creating launchers...")
    results = creator.create_all_launchers()

    # Print summary
    creator.print_summary(results)

    # Return success if at least critical components were created
    critical_success = results.get('start_script', (False,))[0]
    return 0 if critical_success else 1


if __name__ == "__main__":
    sys.exit(main())