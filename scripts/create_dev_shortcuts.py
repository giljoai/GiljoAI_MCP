#!/usr/bin/env python3
"""
Create desktop shortcuts for development environment
Run this once to create shortcuts pointing to the dev repo
"""

from installer.core.shortcuts import create_desktop_shortcuts


# Settings for development environment
settings = {"install_dir": r"C:\Projects\GiljoAI_MCP"}

print("Creating desktop shortcuts for development environment...")
print(f"Install dir: {settings['install_dir']}")
print()

result = create_desktop_shortcuts(settings)

if result["success"]:
    print("\nSuccessfully created shortcuts:")
    for shortcut in result["created"]:
        print(f"  - {shortcut}")
else:
    print("\nFailed to create shortcuts")

if result["errors"]:
    print("\nErrors:")
    for error in result["errors"]:
        print(f"  - {error}")

print("\nDone!")
