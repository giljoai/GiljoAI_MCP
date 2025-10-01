#!/usr/bin/env python3
"""
GiljoAI MCP - Universal AI Tool Registration Wizard
Interactive menu for registering GiljoAI MCP with multiple AI coding agents
"""

import sys
from pathlib import Path

from installer.universal_mcp_installer import UniversalMCPInstaller


class Colors:
    """ANSI colors for terminal output"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"


def print_header():
    """Print wizard header"""
    print()
    print("=" * 70)
    print(f"{Colors.CYAN}{Colors.BOLD}     GiljoAI MCP - Universal AI Tool Registration Wizard     {Colors.RESET}")
    print("=" * 70)
    print()


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}[X] {message}{Colors.RESET}")


def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}[!] {message}{Colors.RESET}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.CYAN}[i] {message}{Colors.RESET}")


def get_install_dir():
    """Get GiljoAI MCP installation directory"""
    return Path(__file__).parent.resolve()


def show_detection_results(installer: UniversalMCPInstaller):
    """Show AI tool detection results"""
    print(f"{Colors.BOLD}Scanning for installed AI coding agents...{Colors.RESET}")
    print()

    status = installer.get_tool_status()
    detected = [name for name, installed in status.items() if installed]
    not_detected = [name for name, installed in status.items() if not installed]

    if detected:
        print(f"{Colors.GREEN}{Colors.BOLD}Detected AI Tools:{Colors.RESET}")
        for tool_name in detected:
            print(f"  {Colors.GREEN}+{Colors.RESET} {installer.tool_names[tool_name]}")
        print()

    if not_detected:
        print(f"{Colors.GRAY}Not Detected:{Colors.RESET}")
        for tool_name in not_detected:
            print(f"  {Colors.GRAY}-{Colors.RESET} {Colors.GRAY}{installer.tool_names[tool_name]}{Colors.RESET}")
        print()


def show_menu(installer: UniversalMCPInstaller):
    """Show interactive menu"""
    print("-" * 70)
    print(f"{Colors.BOLD}What would you like to do?{Colors.RESET}")
    print("-" * 70)
    print()

    status = installer.get_tool_status()
    detected_tools = [name for name, installed in status.items() if installed]

    menu_items = {}
    item_num = 1

    if detected_tools:
        print(f"{Colors.CYAN}Configure detected tools:{Colors.RESET}")
        for tool_name in detected_tools:
            menu_items[str(item_num)] = ("register", tool_name)
            print(f"  {item_num}) Register with {installer.tool_names[tool_name]}")
            item_num += 1
        print()

    # Option to configure all at once
    if len(detected_tools) > 1:
        menu_items["a"] = ("all", None)
        print(f"{Colors.GREEN}  a) Register with ALL detected tools{Colors.RESET}")
        print()

    # Additional options
    print(f"{Colors.CYAN}Other options:{Colors.RESET}")
    menu_items["v"] = ("verify", None)
    print("  v) Verify registration status")

    menu_items["u"] = ("unregister", None)
    print("  u) Unregister from all tools")

    menu_items["d"] = ("docs", None)
    print("  d) Show installation instructions")

    menu_items["q"] = ("quit", None)
    print("  q) Quit")
    print()

    return menu_items


def register_single_tool(installer: UniversalMCPInstaller, tool_name: str):
    """Register with a single tool"""
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Registering with {installer.tool_names[tool_name]}...{Colors.RESET}")
    print("=" * 70)
    print()

    success = installer.register_single(tool_name)

    print()
    if success:
        print_success(f"Successfully registered with {installer.tool_names[tool_name]}")

        # Verify registration
        if installer.verify_single(tool_name):
            print_success("Registration verified")
        else:
            print_warning("Registration completed but verification failed")
    else:
        print_error(f"Registration with {installer.tool_names[tool_name]} failed")

    return success


def register_all_tools(installer: UniversalMCPInstaller):
    """Register with all detected tools"""
    detected = installer.detect_installed_tools()

    if not detected:
        print_warning("No AI tools detected to register")
        return

    print()
    print(f"{Colors.BOLD}Registering with all {len(detected)} detected tools...{Colors.RESET}")
    print()

    results = installer.register_all()

    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Registration Summary{Colors.RESET}")
    print("=" * 70)
    print()

    for tool_name, success in results.items():
        if success:
            print_success(f"{installer.tool_names[tool_name]} - Registered")
        else:
            print_error(f"{installer.tool_names[tool_name]} - Failed")

    # Verify all registrations
    print()
    print(f"{Colors.BOLD}Verifying registrations...{Colors.RESET}")
    verify_results = installer.verify_all()

    print()
    for tool_name, verified in verify_results.items():
        if verified:
            print_success(f"{installer.tool_names[tool_name]} - Verified")
        else:
            print_warning(f"{installer.tool_names[tool_name]} - Not verified")

    print()


def verify_registrations(installer: UniversalMCPInstaller):
    """Verify registration status for all tools"""
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Verification Results{Colors.RESET}")
    print("=" * 70)
    print()

    detected = installer.detect_installed_tools()

    if not detected:
        print_warning("No AI tools detected")
        return

    results = installer.verify_all()

    for tool_name in detected:
        verified = results.get(tool_name, False)
        if verified:
            print_success(f"{installer.tool_names[tool_name]} - Registered")
        else:
            print_error(f"{installer.tool_names[tool_name]} - Not registered")

    print()


def unregister_all_tools(installer: UniversalMCPInstaller):
    """Unregister from all tools"""
    detected = installer.detect_installed_tools()

    if not detected:
        print_warning("No AI tools detected")
        return

    print()
    print(f"{Colors.YELLOW}This will remove GiljoAI MCP registration from all detected tools.{Colors.RESET}")
    response = input(f"{Colors.BOLD}Are you sure? [y/N]: {Colors.RESET}").strip().lower()

    if response != "y":
        print("Cancelled")
        return

    print()
    print(f"{Colors.BOLD}Unregistering from all tools...{Colors.RESET}")
    print()

    results = installer.unregister_all()

    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Unregistration Summary{Colors.RESET}")
    print("=" * 70)
    print()

    for tool_name, success in results.items():
        if success:
            print_success(f"{installer.tool_names[tool_name]} - Unregistered")
        else:
            print_error(f"{installer.tool_names[tool_name]} - Failed")

    print()


def show_documentation(install_dir: Path):
    """Show installation and usage documentation"""
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Installation Instructions{Colors.RESET}")
    print("=" * 70)
    print()

    print(f"{Colors.CYAN}Configuration Files:{Colors.RESET}")
    print("  - Claude Code:  ~/.claude.json")
    # TECHDEBT: Multi-tool support disabled
    # print("  - Codex CLI:    ~/.codex/config.toml")
    # print("  - Gemini CLI:   ~/.gemini/settings.json")
    print()

    print(f"{Colors.CYAN}Verification Commands:{Colors.RESET}")
    print("  - Claude Code:  claude mcp list")
    # TECHDEBT: Multi-tool support disabled
    # print("  - Gemini CLI:   gemini mcp list")
    # print("  - Codex CLI:    (check config file directly)")
    print()

    print(f"{Colors.CYAN}Installation Guides:{Colors.RESET}")
    print("  - Claude Code:  https://claude.ai/download")
    # TECHDEBT: Multi-tool support disabled
    # print("  - Codex CLI:    https://github.com/openai/codex")
    # print("  - Gemini CLI:   https://github.com/google-gemini/gemini-cli")
    print()

    doc_path = install_dir / "docs" / "AI_TOOL_INTEGRATION.md"
    if doc_path.exists():
        print(f"{Colors.CYAN}Detailed Documentation:{Colors.RESET}")
        print(f"  {doc_path}")
        print()


def main():
    """Main wizard loop"""
    print_header()

    install_dir = get_install_dir()
    print_info(f"GiljoAI MCP Installation: {install_dir}")
    print()

    # Initialize universal installer
    try:
        installer = UniversalMCPInstaller()
    except Exception as e:
        print_error(f"Failed to initialize installer: {e}")
        return 1

    # Detect AI tools
    show_detection_results(installer)

    # Check if any tools detected
    detected = installer.detect_installed_tools()
    if not detected:
        print_warning("No AI coding agents detected!")
        print()
        print("Please install Claude Code:")
        print("  - Claude Code: https://claude.ai/download")
        # TECHDEBT: Multi-tool support disabled
        # print("  - Codex CLI: https://github.com/openai/codex")
        # print("  - Gemini CLI: https://github.com/google-gemini/gemini-cli")
        print()
        print("After installation, run this wizard again.")
        return 1

    # Main menu loop
    while True:
        menu_items = show_menu(installer)

        try:
            choice = input(f"{Colors.BOLD}Enter your choice: {Colors.RESET}").strip().lower()
            print()

            if choice not in menu_items:
                print_error("Invalid choice. Please try again.")
                print()
                continue

            action, tool_name = menu_items[choice]

            if action == "quit":
                print("Exiting wizard.")
                break

            if action == "register":
                success = register_single_tool(installer, tool_name)
                print()
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == "all":
                register_all_tools(installer)
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == "verify":
                verify_registrations(installer)
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == "unregister":
                unregister_all_tools(installer)
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == "docs":
                show_documentation(install_dir)
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

        except KeyboardInterrupt:
            print()
            print()
            print("Wizard cancelled by user.")
            break

    print()
    print("=" * 70)
    print(f"{Colors.GREEN}Thank you for using GiljoAI MCP!{Colors.RESET}")
    print("=" * 70)
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
