# ============================================================================
# DISABLED: Multi-tool support temporarily disabled
# See docs/Techdebt.md and CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md
# This script will be re-enabled when Codex CLI gains subagent capabilities
# or when hybrid orchestrator is implemented (Q2 2025)
# ============================================================================

#!/usr/bin/env python3
"""
GiljoAI MCP - Codex CLI Registration Script
Automatically configures GiljoAI MCP server for OpenAI Codex CLI
"""

import os
import sys
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
    print(f"{Colors.CYAN}{Colors.BOLD}GiljoAI MCP - Codex CLI Registration{Colors.RESET}")
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


def check_codex_installed():
    """Check if Codex CLI is installed"""
    return shutil.which("codex") is not None


def get_codex_config_path():
    """Get path to Codex config file"""
    home = Path.home()
    config_dir = home / ".codex"
    config_file = config_dir / "config.toml"
    return config_dir, config_file


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


def backup_config(config_file):
    """Create backup of existing config file"""
    if config_file.exists():
        backup_file = config_file.with_suffix('.toml.backup')
        shutil.copy2(config_file, backup_file)
        return backup_file
    return None


def read_config(config_file):
    """Read existing config file"""
    if config_file.exists():
        return config_file.read_text(encoding='utf-8')
    return ""


def check_existing_giljo_config(config_content):
    """Check if giljo-mcp is already configured"""
    return "[mcp_servers.giljo-mcp]" in config_content


def generate_giljo_config():
    """Generate GiljoAI MCP configuration for Codex"""
    install_dir = get_install_dir()
    python_path = get_python_path()

    # Use forward slashes for TOML (works on all platforms)
    install_dir_str = str(install_dir).replace('\\', '/')
    python_path_str = str(python_path).replace('\\', '/')

    config = f'''
# GiljoAI MCP Server Configuration
[mcp_servers.giljo-mcp]
command = "{python_path_str}"
args = ["-m", "giljo_mcp.mcp_adapter"]

[mcp_servers.giljo-mcp.env]
GILJO_MCP_HOME = "{install_dir_str}"
'''

    return config.strip()


def add_config_to_file(config_file, config_content, giljo_config):
    """Add GiljoAI config to existing config file"""
    # If config file doesn't exist or is empty, just write the giljo config
    if not config_content.strip():
        new_content = giljo_config
    else:
        # Append to existing config
        new_content = config_content.rstrip() + "\n\n" + giljo_config

    # Write the new config
    config_file.write_text(new_content, encoding='utf-8')

    return new_content


def show_config_preview(giljo_config):
    """Show what will be added to the config"""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Configuration to be added:{Colors.RESET}")
    print("─" * 70)
    print(f"{Colors.GRAY}{giljo_config}{Colors.RESET}")
    print("─" * 70)
    print()


def show_final_config(config_file):
    """Show the final config file"""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Final configuration:{Colors.RESET} {config_file}")
    print("─" * 70)
    content = config_file.read_text(encoding='utf-8')
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
    print("  2. Open Codex CLI and run:")
    print("     /mcp status")
    print()
    print("  3. You should see 'giljo-mcp' with 'connected' status")
    print()


def main():
    """Main registration process"""
    print_header()

    # Step 1: Check if Codex is installed
    print("Step 1: Checking Codex CLI installation...")
    if not check_codex_installed():
        print_error("Codex CLI not found!")
        print()
        print_info("Codex CLI is not installed or not in your PATH.")
        print()
        print("To install Codex CLI, visit:")
        print("  https://github.com/openai/codex")
        print()
        print("After installation, run this script again.")
        return 1

    print_success("Codex CLI found")
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

    # Step 3: Locate Codex config
    print("Step 3: Locating Codex configuration...")
    config_dir, config_file = get_codex_config_path()
    print_info(f"Config location: {config_file}")

    # Create config directory if it doesn't exist
    if not config_dir.exists():
        print_info("Creating Codex config directory...")
        config_dir.mkdir(parents=True, exist_ok=True)
        print_success("Config directory created")

    # Step 4: Read existing config
    print()
    print("Step 4: Reading existing configuration...")
    config_content = read_config(config_file)

    if config_content:
        print_success(f"Found existing config ({len(config_content)} bytes)")

        # Check if giljo-mcp is already configured
        if check_existing_giljo_config(config_content):
            print_warning("GiljoAI MCP is already configured in Codex!")
            print()
            response = input("Do you want to replace the existing configuration? (y/N): ").strip().lower()
            if response != 'y':
                print()
                print_info("Registration cancelled. Existing configuration preserved.")
                return 0

            # Remove existing giljo-mcp configuration
            lines = config_content.split('\n')
            new_lines = []
            skip_mode = False

            for line in lines:
                if line.strip().startswith('[mcp_servers.giljo-mcp]'):
                    skip_mode = True
                    continue
                elif skip_mode and line.strip().startswith('['):
                    skip_mode = False

                if not skip_mode:
                    new_lines.append(line)

            config_content = '\n'.join(new_lines).strip()
    else:
        print_info("No existing config found (will create new)")

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

    # Step 7: Backup existing config
    print()
    print("Step 6: Backing up existing configuration...")
    backup_file = backup_config(config_file)
    if backup_file:
        print_success(f"Backup created: {backup_file}")
    else:
        print_info("No existing config to backup")

    # Step 8: Write new config
    print()
    print("Step 7: Writing new configuration...")
    try:
        new_content = add_config_to_file(config_file, config_content, giljo_config)
        print_success(f"Configuration written to: {config_file}")
    except Exception as e:
        print_error(f"Failed to write configuration: {e}")
        if backup_file:
            print_info(f"Your original config is safe at: {backup_file}")
        return 1

    # Show final config
    show_final_config(config_file)

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
