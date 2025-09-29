#!/usr/bin/env python3
"""
GiljoAI MCP - Grok CLI Registration Helper
Provides instructions and commands for integrating with various Grok CLI implementations
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
    MAGENTA = '\033[95m'
    GRAY = '\033[90m'


def print_header():
    """Print script header"""
    print("=" * 70)
    print(f"{Colors.MAGENTA}{Colors.BOLD}GiljoAI MCP - Grok CLI Registration Helper{Colors.RESET}")
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


def print_command(message):
    """Print command to copy"""
    print(f"{Colors.GREEN}{Colors.BOLD}{message}{Colors.RESET}")


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


def detect_grok_variants():
    """Detect which Grok CLI implementations are installed"""
    variants = {}

    # Check for grok command
    if shutil.which("grok"):
        variants['grok'] = shutil.which("grok")

    # Check for npm version
    try:
        result = os.popen("npm list -g @webdevtoday/grok-cli 2>&1").read()
        if "@webdevtoday/grok-cli" in result:
            variants['grok-npm'] = "npx @webdevtoday/grok-cli"
    except:
        pass

    return variants


def show_detected_variants(variants):
    """Show detected Grok CLI variants"""
    if variants:
        print(f"{Colors.BOLD}Detected Grok CLI implementations:{Colors.RESET}")
        for name, path in variants.items():
            print(f"  ✓ {name}: {Colors.CYAN}{path}{Colors.RESET}")
        print()
    else:
        print_warning("No Grok CLI implementation detected")
        print()


def show_installation_instructions():
    """Show installation instructions for Grok CLI"""
    print(f"{Colors.BOLD}Grok CLI Installation Options:{Colors.RESET}")
    print()
    print("There are several community implementations of Grok CLI with MCP support:")
    print()
    print("1. superagent-ai/grok-cli (GitHub):")
    print("   https://github.com/superagent-ai/grok-cli")
    print()
    print("2. @webdevtoday/grok-cli (npm):")
    print_command("   npm install -g @webdevtoday/grok-cli")
    print()
    print("3. coldcanuk/grok-cli (GitHub):")
    print("   https://github.com/coldcanuk/grok-cli")
    print()
    print("4. Bob-lance/grok-mcp (GitHub):")
    print("   https://github.com/Bob-lance/grok-mcp")
    print()


def generate_registration_commands():
    """Generate registration commands for different Grok implementations"""
    install_dir = get_install_dir()
    python_path = get_python_path()

    # Use forward slashes (works on all platforms in most contexts)
    install_dir_str = str(install_dir).replace('\\', '/')
    python_path_str = str(python_path).replace('\\', '/')

    commands = {}

    # In-app command (for implementations supporting /mcp add)
    commands['in_app'] = f'/mcp add giljo-mcp "{python_path_str} -m giljo_mcp.mcp_adapter"'

    # JSON configuration
    commands['json'] = {
        "giljo-mcp": {
            "command": python_path_str,
            "args": ["-m", "giljo_mcp.mcp_adapter"],
            "env": {
                "GILJO_MCP_HOME": install_dir_str
            }
        }
    }

    return commands


def show_registration_instructions(commands):
    """Show registration instructions for Grok CLI"""
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Registration Instructions{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")

    # Method 1: In-App Command
    print(f"{Colors.CYAN}Method 1: In-App Command (Recommended){Colors.RESET}")
    print("─" * 70)
    print("\nIf your Grok CLI supports the /mcp add command:")
    print("\n1. Launch Grok CLI:")
    print_command("   grok")
    print("\n2. Inside Grok, run this command:")
    print_command(f"   {commands['in_app']}")
    print("\n3. Verify registration:")
    print_command("   /mcp list")
    print_command("   /mcp status")
    print()

    # Method 2: Configuration File
    print(f"\n{Colors.CYAN}Method 2: Manual Configuration File{Colors.RESET}")
    print("─" * 70)
    print("\nIf your Grok CLI uses a configuration file:")
    print("\n1. Locate your Grok config file (varies by implementation):")
    print("   • ~/.grok/config.json")
    print("   • ~/.grok-cli/settings.json")
    print("   • Or check your Grok documentation")
    print("\n2. Add this configuration:")
    print(f"{Colors.GRAY}")
    import json
    print(json.dumps({"mcpServers": commands['json']}, indent=2))
    print(f"{Colors.RESET}")
    print()

    # Method 3: Environment-Specific
    print(f"\n{Colors.CYAN}Method 3: Check Your Grok Documentation{Colors.RESET}")
    print("─" * 70)
    print("\nDifferent Grok implementations have different configuration methods.")
    print("Please refer to your specific Grok CLI documentation for details.")
    print()


def show_verification_steps():
    """Show verification steps"""
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Verification Steps{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")

    install_dir = get_install_dir()

    print("1. Start GiljoAI MCP server:")
    if sys.platform == "win32":
        print_command(f"   {install_dir}\\start_giljo.bat")
    else:
        print_command(f"   {install_dir}/start_giljo.sh")

    print("\n2. Open Grok CLI and check MCP status:")
    print_command("   /mcp")
    print_command("   /mcp list")
    print_command("   /mcp status")
    print_command("   /mcp tools")

    print("\n3. You should see 'giljo-mcp' in the list with 'connected' status")
    print()


def main():
    """Main helper process"""
    print_header()

    # Step 1: Verify GiljoAI installation
    print("Step 1: Verifying GiljoAI MCP installation...")
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

    # Step 2: Detect Grok variants
    print("Step 2: Detecting Grok CLI installations...")
    variants = detect_grok_variants()
    show_detected_variants(variants)

    # Step 3: Show installation instructions if not found
    if not variants:
        print_warning("Grok CLI not detected!")
        print()
        response = input("Would you like to see installation instructions? (Y/n): ").strip().lower()
        if response != 'n':
            print()
            show_installation_instructions()
        print()
        print_info("After installing Grok CLI, run this script again.")
        return 1

    # Step 4: Generate and show registration commands
    print("Step 3: Generating registration commands...")
    commands = generate_registration_commands()
    print_success("Commands generated")

    show_registration_instructions(commands)
    show_verification_steps()

    # Additional resources
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Additional Resources{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")
    print(f"{Colors.CYAN}For detailed instructions, see:{Colors.RESET}")
    print(f"  {install_dir}/docs/AI_TOOL_INTEGRATION.md")
    print()
    print(f"{Colors.CYAN}Grok CLI variants and documentation:{Colors.RESET}")
    print("  • superagent-ai: https://github.com/superagent-ai/grok-cli")
    print("  • webdevtoday: https://www.npmjs.com/package/@webdevtoday/grok-cli")
    print("  • coldcanuk: https://github.com/coldcanuk/grok-cli")
    print("  • Bob-lance: https://github.com/Bob-lance/grok-mcp")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_warning("Helper cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
