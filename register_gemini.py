#!/usr/bin/env python3
"""
GiljoAI MCP - Gemini CLI Registration Script
Automatically configures GiljoAI MCP server for Google Gemini CLI
"""

import os
import sys
import json
from pathlib import Path
import shutil

# ANSI colors for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'


def print_header():
    """Print script header"""
    print("=" * 70)
    print(f"{Colors.CYAN}{Colors.BOLD}GiljoAI MCP - Gemini CLI Registration{Colors.RESET}")
    print("=" * 70)
    print()


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {message}{Colors.RESET}")


def check_gemini_installed():
    """Check if Gemini CLI is installed"""
    return shutil.which("gemini") is not None


def get_gemini_settings_path():
    """Get path to Gemini settings file"""
    home = Path.home()
    settings_dir = home / ".gemini"
    settings_file = settings_dir / "settings.json"
    return settings_dir, settings_file


def get_install_dir():
    """Get GiljoAI MCP installation directory (where this script is located)"""
    return Path(__file__).parent.resolve()


def get_python_path():
    """Get path to Python executable in venv"""
    install_dir = get_install_dir()

    if sys.platform == "win32":
        python_path = install_dir / "venv" / "Scripts" / "python.exe"
    else:
        python_path = install_dir / "venv" / "bin" / "python"

    return python_path


def verify_venv_exists():
    """Verify that the venv Python exists"""
    python_path = get_python_path()
    return python_path.exists()


def backup_settings(settings_file):
    """Create backup of existing settings file"""
    if settings_file.exists():
        backup_file = settings_file.with_suffix('.json.backup')
        shutil.copy2(settings_file, backup_file)
        return backup_file
    return None


def read_settings(settings_file):
    """Read existing settings file"""
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON in settings file: {e}")
            return None
    return {}


def check_existing_giljo_config(settings):
    """Check if giljo-mcp is already configured"""
    if not settings:
        return False

    mcp_servers = settings.get('mcpServers', {})
    return 'giljo-mcp' in mcp_servers


def generate_giljo_config():
    """Generate GiljoAI MCP configuration for Gemini"""
    install_dir = get_install_dir()
    python_path = get_python_path()

    # Use forward slashes for JSON (works on all platforms)
    install_dir_str = str(install_dir).replace('\\', '/')
    python_path_str = str(python_path).replace('\\', '/')

    config = {
        "command": python_path_str,
        "args": ["-m", "giljo_mcp.mcp_adapter"],
        "env": {
            "GILJO_MCP_HOME": install_dir_str
        }
    }

    return config


def add_config_to_settings(settings, giljo_config):
    """Add GiljoAI config to settings"""
    # Ensure mcpServers object exists
    if 'mcpServers' not in settings:
        settings['mcpServers'] = {}

    # Add giljo-mcp configuration
    settings['mcpServers']['giljo-mcp'] = giljo_config

    return settings


def write_settings(settings_file, settings):
    """Write settings to file with pretty formatting"""
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline


def show_config_preview(giljo_config):
    """Show what will be added to the settings"""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Configuration to be added:{Colors.RESET}")
    print("─" * 70)
    config_json = json.dumps({"giljo-mcp": giljo_config}, indent=2)
    print(f"{Colors.GRAY}{config_json}{Colors.RESET}")
    print("─" * 70)
    print()


def show_final_settings(settings_file):
    """Show the final settings file"""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Final configuration:{Colors.RESET} {settings_file}")
    print("─" * 70)
    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"{Colors.GRAY}{content}{Colors.RESET}")
    print("─" * 70)
    print()


def verify_registration():
    """Provide verification instructions"""
    print(f"\n{Colors.BOLD}Verification Steps:{Colors.RESET}")
    print("  1. Start GiljoAI MCP server:")
    install_dir = get_install_dir()
    if sys.platform == "win32":
        print(f"     {install_dir}\\start_giljo.bat")
    else:
        print(f"     {install_dir}/start_giljo.sh")
    print()
    print("  2. Open Gemini CLI and run:")
    print("     /mcp")
    print()
    print("  3. You should see 'giljo-mcp' with 'connected' status")
    print()


def main():
    """Main registration process"""
    print_header()

    # Step 1: Check if Gemini is installed
    print("Step 1: Checking Gemini CLI installation...")
    if not check_gemini_installed():
        print_error("Gemini CLI not found!")
        print()
        print_info("Gemini CLI is not installed or not in your PATH.")
        print()
        print("To install Gemini CLI, visit:")
        print("  https://github.com/google-gemini/gemini-cli")
        print()
        print("After installation, run this script again.")
        return 1

    print_success("Gemini CLI found")
    print()

    # Step 2: Verify GiljoAI installation
    print("Step 2: Verifying GiljoAI MCP installation...")
    install_dir = get_install_dir()
    print_info(f"Installation directory: {install_dir}")

    if not verify_venv_exists():
        print_error("Python virtual environment not found!")
        print()
        print_info("Expected location:")
        print(f"  {get_python_path()}")
        print()
        print("Please ensure GiljoAI MCP is properly installed.")
        return 1

    print_success("GiljoAI MCP installation verified")
    print()

    # Step 3: Locate Gemini settings
    print("Step 3: Locating Gemini settings...")
    settings_dir, settings_file = get_gemini_settings_path()
    print_info(f"Settings location: {settings_file}")

    # Create settings directory if it doesn't exist
    if not settings_dir.exists():
        print_info("Creating Gemini settings directory...")
        settings_dir.mkdir(parents=True, exist_ok=True)
        print_success("Settings directory created")

    # Step 4: Read existing settings
    print()
    print("Step 4: Reading existing settings...")
    settings = read_settings(settings_file)

    if settings is None:
        print_error("Failed to parse existing settings (invalid JSON)")
        print()
        response = input("Create new settings file? (y/N): ").strip().lower()
        if response != 'y':
            print()
            print_info("Registration cancelled.")
            return 1
        settings = {}

    if settings:
        print_success(f"Found existing settings")

        # Check if giljo-mcp is already configured
        if check_existing_giljo_config(settings):
            print_warning("GiljoAI MCP is already configured in Gemini!")
            print()
            response = input("Do you want to replace the existing configuration? (y/N): ").strip().lower()
            if response != 'y':
                print()
                print_info("Registration cancelled. Existing configuration preserved.")
                return 0

            # Will be replaced when we add the config
    else:
        print_info("No existing settings found (will create new)")

    # Step 5: Generate GiljoAI config
    print()
    print("Step 5: Generating GiljoAI MCP configuration...")
    giljo_config = generate_giljo_config()
    print_success("Configuration generated")

    # Show preview
    show_config_preview(giljo_config)

    # Step 6: Confirm
    response = input(f"{Colors.BOLD}Proceed with registration? (Y/n): {Colors.RESET}").strip().lower()
    if response == 'n':
        print()
        print_info("Registration cancelled.")
        return 0

    # Step 7: Backup existing settings
    print()
    print("Step 6: Backing up existing settings...")
    backup_file = backup_settings(settings_file)
    if backup_file:
        print_success(f"Backup created: {backup_file}")
    else:
        print_info("No existing settings to backup")

    # Step 8: Write new settings
    print()
    print("Step 7: Writing new settings...")
    try:
        new_settings = add_config_to_settings(settings, giljo_config)
        write_settings(settings_file, new_settings)
        print_success(f"Settings written to: {settings_file}")
    except Exception as e:
        print_error(f"Failed to write settings: {e}")
        if backup_file:
            print_info(f"Your original settings are safe at: {backup_file}")
        return 1

    # Show final settings
    show_final_settings(settings_file)

    # Success!
    print(f"{Colors.GREEN}{Colors.BOLD}✓ Registration Complete!{Colors.RESET}")
    print()
    verify_registration()

    print(f"{Colors.CYAN}For more information, see:{Colors.RESET}")
    print(f"  {install_dir}/docs/AI_TOOL_INTEGRATION.md")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_warning("Registration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
