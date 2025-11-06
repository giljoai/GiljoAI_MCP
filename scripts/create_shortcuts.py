#!/usr/bin/env python3
"""
Create desktop shortcuts for GiljoAI MCP Server
Works on Windows, Mac, and Linux
"""

import os
import platform
from pathlib import Path


def create_windows_shortcut(name, target, args="", icon_path=None, description="", working_dir=None):
    """Create a Windows shortcut (.lnk file)"""
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = Path(shell.SpecialFolders("Desktop"))

        shortcut_path = desktop / f"{name}.lnk"
        shortcut = shell.CreateShortcut(str(shortcut_path))

        shortcut.TargetPath = str(target)
        if args:
            shortcut.Arguments = args
        if icon_path and Path(icon_path).exists():
            shortcut.IconLocation = str(icon_path)
        if description:
            shortcut.Description = description
        if working_dir:
            shortcut.WorkingDirectory = str(working_dir)
        else:
            shortcut.WorkingDirectory = str(Path(target).parent)

        # Set to run minimized to system tray
        if "stop" not in name.lower():
            shortcut.WindowStyle = 7  # Minimized

        shortcut.Save()

        return shortcut_path
    except Exception as e:
        print(f"Error creating Windows shortcut: {e}")
        return None


def create_linux_desktop_file(name, exec_cmd, icon_path=None, comment="", terminal=True):
    """Create a Linux .desktop file"""
    desktop_dir = Path.home() / "Desktop"
    if not desktop_dir.exists():
        desktop_dir = Path.home() / ".local" / "share" / "applications"

    desktop_file = desktop_dir / f"giljo-mcp-{name.lower().replace(' ', '-')}.desktop"

    content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment={comment}
Exec={exec_cmd}
Terminal={"true" if terminal else "false"}
"""

    if icon_path and Path(icon_path).exists():
        content += f"Icon={icon_path}\n"

    content += "Categories=Development;Network;\n"

    try:
        with open(desktop_file, "w") as f:
            f.write(content)

        # Make it executable (owner only, readable by all)
        os.chmod(desktop_file, 0o744)  # nosec B103 - Desktop files need execute permission for owner

        return desktop_file
    except Exception as e:
        print(f"Error creating Linux desktop file: {e}")
        return None


def create_mac_app(name, script_path, icon_path=None):
    """Create a Mac .app bundle"""
    applications_dir = Path.home() / "Desktop"
    app_name = f"GiljoMCP {name}.app"
    app_path = applications_dir / app_name

    try:
        # Create app structure
        contents_dir = app_path / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"

        macos_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Create launcher script
        launcher = macos_dir / "launcher"
        with open(launcher, "w") as f:
            f.write(f"""#!/bin/bash
cd {Path.cwd()}
{script_path}
""")
        os.chmod(launcher, 0o744)  # nosec B103 - Launcher script needs execute permission for owner

        # Create Info.plist
        info_plist = contents_dir / "Info.plist"
        with open(info_plist, "w") as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleName</key>
    <string>{name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.giljo.mcp.{name.lower().replace(" ", "")}</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>""")

        # Copy icon if available
        if icon_path and Path(icon_path).exists():
            import shutil

            shutil.copy(icon_path, resources_dir / "icon.icns")

        return app_path
    except Exception as e:
        print(f"Error creating Mac app: {e}")
        return None


def create_shortcuts():
    """Create all desktop shortcuts for GiljoAI MCP"""

    install_dir = Path.cwd()
    icon_path = install_dir / "giljo.ico"

    # Ensure icon exists
    if not icon_path.exists():
        # Try to copy from frontend
        frontend_icon = install_dir / "frontend" / "public" / "icons" / "favicon.ico"
        if frontend_icon.exists():
            import shutil

            shutil.copy(frontend_icon, icon_path)

    system = platform.system()
    shortcuts_created = []

    if system == "Windows":
        # Start Server shortcut
        start_script = install_dir / "start_giljo.bat"
        if start_script.exists():
            shortcut = create_windows_shortcut(
                name="GiljoAI MCP - Start Server",
                target=str(start_script),
                icon_path=icon_path,
                description="Start GiljoAI MCP Orchestration Server",
                working_dir=install_dir,
            )
            if shortcut:
                shortcuts_created.append(shortcut)
                print(f"✓ Created: {shortcut}")

        # Stop Server shortcut
        stop_script = install_dir / "stop_giljo.bat"
        if not stop_script.exists():
            # Create stop script if it doesn't exist
            with open(stop_script, "w") as f:
                f.write("""@echo off
echo Stopping GiljoAI MCP Server...
taskkill /F /IM python.exe /T 2>nul
echo Server stopped.
pause
""")

        shortcut = create_windows_shortcut(
            name="GiljoAI MCP - Stop Server",
            target=str(stop_script),
            icon_path=icon_path,
            description="Stop GiljoAI MCP Orchestration Server",
            working_dir=install_dir,
        )
        if shortcut:
            shortcuts_created.append(shortcut)
            print(f"✓ Created: {shortcut}")

        # Connect Project shortcut
        connect_script = install_dir / "connect_project.bat"
        if connect_script.exists():
            shortcut = create_windows_shortcut(
                name="GiljoAI MCP - Connect Project",
                target="cmd.exe",
                args=f'/k "{connect_script}"',
                icon_path=icon_path,
                description="Connect a project to GiljoAI MCP Server",
                working_dir=install_dir,
            )
            if shortcut:
                shortcuts_created.append(shortcut)
                print(f"✓ Created: {shortcut}")

        # Server Status shortcut
        status_script = install_dir / "check_status.bat"
        if not status_script.exists():
            with open(status_script, "w") as f:
                f.write(f"""@echo off
echo ============================================================
echo   GiljoAI MCP Server Status
echo ============================================================
echo.
echo Checking if server is running...
echo.

netstat -an | findstr :7272 >nul
if %errorlevel% == 0 (
    echo [OK] Server is RUNNING on port 8000
    echo.
    echo You can connect projects using:
    echo   {install_dir}\\connect_project.bat
) else (
    echo [!] Server is NOT RUNNING
    echo.
    echo Start the server using:
    echo   {install_dir}\\start_giljo.bat
)

echo.
pause
""")

        shortcut = create_windows_shortcut(
            name="GiljoAI MCP - Check Status",
            target=str(status_script),
            icon_path=icon_path,
            description="Check GiljoAI MCP Server Status",
            working_dir=install_dir,
        )
        if shortcut:
            shortcuts_created.append(shortcut)
            print(f"✓ Created: {shortcut}")

    elif system == "Linux":
        # Create Linux desktop files
        shortcuts = [
            ("Start Server", f"{install_dir}/start_giljo.sh", "Start GiljoAI MCP Server"),
            ("Stop Server", f"{install_dir}/stop_giljo.sh", "Stop GiljoAI MCP Server"),
            ("Connect Project", f"{install_dir}/connect_project.py", "Connect project to server"),
        ]

        for name, exec_path, comment in shortcuts:
            desktop_file = create_linux_desktop_file(
                name=f"GiljoAI MCP {name}", exec_cmd=exec_path, icon_path=icon_path, comment=comment
            )
            if desktop_file:
                shortcuts_created.append(desktop_file)
                print(f"✓ Created: {desktop_file}")

    elif system == "Darwin":  # Mac
        # Create Mac apps
        shortcuts = [
            ("Start Server", "./start_giljo.sh"),
            ("Stop Server", "./stop_giljo.sh"),
            ("Connect Project", "python3 connect_project.py"),
        ]

        for name, script in shortcuts:
            app = create_mac_app(name=name, script_path=script, icon_path=icon_path)
            if app:
                shortcuts_created.append(app)
                print(f"✓ Created: {app}")

    return shortcuts_created


def add_to_startup_windows():
    """Add GiljoAI MCP to Windows startup (optional)"""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE
        )

        install_dir = Path.cwd()
        start_script = install_dir / "start_giljo_silent.bat"

        # Create silent start script
        if not start_script.exists():
            with open(start_script, "w") as f:
                f.write(f"""@echo off
cd /d "{install_dir}"
start /min "" python -m giljo_mcp
""")

        winreg.SetValueEx(key, "GiljoAI_MCP_Server", 0, winreg.REG_SZ, str(start_script))
        winreg.CloseKey(key)

        print("✓ Added GiljoAI MCP to Windows startup")
        return True
    except Exception as e:
        print(f"Could not add to startup: {e}")
        return False


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("Creating Desktop Shortcuts for GiljoAI MCP")
    print("=" * 60 + "\n")

    shortcuts = create_shortcuts()

    if shortcuts:
        print(f"\n✓ Created {len(shortcuts)} desktop shortcuts")

        # Ask about auto-start on Windows
        if platform.system() == "Windows":
            print("\nWould you like GiljoAI MCP Server to start automatically with Windows?")
            response = input("(This can be changed later in Task Manager > Startup) [y/N]: ")
            if response.lower() == "y":
                add_to_startup_windows()
    else:
        print("\n⚠ No shortcuts were created")

    print("\nShortcuts created! You can now:")
    print("• Click 'Start Server' to run the MCP server")
    print("• Click 'Connect Project' in any project folder")
    print("• Click 'Check Status' to see if server is running")
    print("• Click 'Stop Server' when done")


if __name__ == "__main__":
    main()
