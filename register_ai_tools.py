#!/usr/bin/env python3
"""
GiljoAI MCP - Universal AI Tool Registration Wizard
Interactive menu for registering GiljoAI MCP with multiple AI coding agents
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

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
    """Print wizard header"""
    print()
    print("=" * 70)
    print(f"{Colors.CYAN}{Colors.BOLD}     GiljoAI MCP - Universal AI Tool Registration Wizard     {Colors.RESET}")
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


def get_install_dir():
    """Get GiljoAI MCP installation directory"""
    return Path(__file__).parent.resolve()


def detect_ai_tools():
    """Detect which AI CLI tools are installed"""
    tools = {}

    # Claude Code
    if shutil.which("claude"):
        tools['claude'] = {
            'name': 'Claude Code',
            'command': 'claude',
            'script': 'register_claude.bat' if sys.platform == 'win32' else 'register_claude.sh',
            'detected': True
        }
    else:
        tools['claude'] = {
            'name': 'Claude Code',
            'command': 'claude',
            'script': None,
            'detected': False
        }

    # Codex CLI
    if shutil.which("codex"):
        tools['codex'] = {
            'name': 'Codex CLI (OpenAI)',
            'command': 'codex',
            'script': 'register_codex.py',
            'detected': True
        }
    else:
        tools['codex'] = {
            'name': 'Codex CLI (OpenAI)',
            'command': 'codex',
            'script': None,
            'detected': False
        }

    # Gemini CLI
    if shutil.which("gemini"):
        tools['gemini'] = {
            'name': 'Gemini CLI (Google)',
            'command': 'gemini',
            'script': 'register_gemini.py',
            'detected': True
        }
    else:
        tools['gemini'] = {
            'name': 'Gemini CLI (Google)',
            'command': 'gemini',
            'script': None,
            'detected': False
        }

    # Grok CLI
    if shutil.which("grok"):
        tools['grok'] = {
            'name': 'Grok CLI (xAI)',
            'command': 'grok',
            'script': 'register_grok.py',
            'detected': True
        }
    else:
        tools['grok'] = {
            'name': 'Grok CLI (xAI)',
            'command': 'grok',
            'script': None,
            'detected': False
        }

    return tools


def show_detection_results(tools):
    """Show AI tool detection results"""
    print(f"{Colors.BOLD}Scanning for installed AI coding agents...{Colors.RESET}")
    print()

    detected = [t for t in tools.values() if t['detected']]
    not_detected = [t for t in tools.values() if not t['detected']]

    if detected:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Detected AI Tools:{Colors.RESET}")
        for tool in detected:
            print(f"  {Colors.GREEN}●{Colors.RESET} {tool['name']}")
        print()

    if not_detected:
        print(f"{Colors.GRAY}Not Detected:{Colors.RESET}")
        for tool in not_detected:
            print(f"  {Colors.GRAY}○{Colors.RESET} {Colors.GRAY}{tool['name']}{Colors.RESET}")
        print()


def show_menu(tools):
    """Show interactive menu"""
    print("─" * 70)
    print(f"{Colors.BOLD}What would you like to do?{Colors.RESET}")
    print("─" * 70)
    print()

    # Show options for detected tools
    menu_items = {}
    item_num = 1

    detected_tools = {k: v for k, v in tools.items() if v['detected']}
    if detected_tools:
        print(f"{Colors.CYAN}Configure detected tools:{Colors.RESET}")
        for key, tool in detected_tools.items():
            menu_items[str(item_num)] = ('register', key, tool)
            print(f"  {item_num}) Register with {tool['name']}")
            item_num += 1
        print()

    # Option to configure all at once
    if len(detected_tools) > 1:
        menu_items['a'] = ('all', None, None)
        print(f"{Colors.GREEN}  a) Register with ALL detected tools{Colors.RESET}")
        print()

    # Additional options
    print(f"{Colors.CYAN}Other options:{Colors.RESET}")
    menu_items['m'] = ('manual', None, None)
    print(f"  m) Show manual registration instructions")

    menu_items['d'] = ('docs', None, None)
    print(f"  d) Open full documentation")

    menu_items['q'] = ('quit', None, None)
    print(f"  q) Quit")
    print()

    return menu_items


def run_registration_script(tool_key, tool_info, install_dir):
    """Run registration script for a specific tool"""
    script = tool_info['script']
    if not script:
        print_error(f"No registration script available for {tool_info['name']}")
        return False

    script_path = install_dir / script

    if not script_path.exists():
        print_error(f"Registration script not found: {script_path}")
        return False

    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Registering with {tool_info['name']}...{Colors.RESET}")
    print("=" * 70)
    print()

    try:
        if script.endswith('.bat'):
            # Windows batch file
            result = subprocess.run([str(script_path)], cwd=str(install_dir))
        else:
            # Python script
            result = subprocess.run([sys.executable, str(script_path)], cwd=str(install_dir))

        return result.returncode == 0

    except Exception as e:
        print_error(f"Failed to run registration script: {e}")
        return False


def register_all_tools(tools, install_dir):
    """Register with all detected tools"""
    detected = {k: v for k, v in tools.items() if v['detected']}

    if not detected:
        print_warning("No AI tools detected to register")
        return

    print()
    print(f"{Colors.BOLD}Registering with all {len(detected)} detected tools...{Colors.RESET}")
    print()

    results = {}
    for key, tool in detected.items():
        success = run_registration_script(key, tool, install_dir)
        results[key] = success

        # Pause between registrations
        if key != list(detected.keys())[-1]:  # Not the last one
            print()
            input(f"{Colors.CYAN}Press Enter to continue to next tool...{Colors.RESET}")

    # Summary
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Registration Summary{Colors.RESET}")
    print("=" * 70)
    print()

    for key, success in results.items():
        tool = tools[key]
        if success:
            print_success(f"{tool['name']} - Configured")
        else:
            print_error(f"{tool['name']} - Failed")

    print()


def show_manual_instructions(tools, install_dir):
    """Show manual registration instructions"""
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Manual Registration Instructions{Colors.RESET}")
    print("=" * 70)
    print()

    print("To manually register GiljoAI MCP with each AI tool:")
    print()

    for key, tool in tools.items():
        print(f"{Colors.CYAN}{Colors.BOLD}{tool['name']}:{Colors.RESET}")

        if tool['script']:
            script_path = install_dir / tool['script']
            if sys.platform == 'win32':
                if tool['script'].endswith('.bat'):
                    cmd = str(script_path)
                else:
                    cmd = f"python {script_path}"
            else:
                if tool['script'].endswith('.sh'):
                    cmd = f"./{tool['script']}"
                else:
                    cmd = f"python {script_path}"

            print(f"  Run: {Colors.GREEN}{cmd}{Colors.RESET}")
        else:
            print(f"  {Colors.GRAY}Not detected - install first{Colors.RESET}")

        print()


def open_documentation(install_dir):
    """Open or show path to documentation"""
    doc_path = install_dir / "docs" / "AI_TOOL_INTEGRATION.md"

    if not doc_path.exists():
        print_error(f"Documentation not found: {doc_path}")
        return

    print()
    print(f"{Colors.CYAN}Documentation location:{Colors.RESET}")
    print(f"  {doc_path}")
    print()

    # Try to open with default application
    try:
        if sys.platform == 'win32':
            os.startfile(doc_path)
            print_success("Opened documentation in default viewer")
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(doc_path)])
            print_success("Opened documentation in default viewer")
        else:
            subprocess.run(['xdg-open', str(doc_path)])
            print_success("Opened documentation in default viewer")
    except:
        print_info("Could not open automatically. Please open manually:")
        print(f"  {doc_path}")

    print()


def main():
    """Main wizard loop"""
    print_header()

    install_dir = get_install_dir()
    print_info(f"GiljoAI MCP Installation: {install_dir}")
    print()

    # Detect AI tools
    tools = detect_ai_tools()
    show_detection_results(tools)

    # Check if any tools detected
    detected_count = sum(1 for t in tools.values() if t['detected'])
    if detected_count == 0:
        print_warning("No AI coding agents detected!")
        print()
        print("Please install at least one AI coding agent:")
        print("  • Claude Code: https://claude.ai/download")
        print("  • Codex CLI: https://github.com/openai/codex")
        print("  • Gemini CLI: https://github.com/google-gemini/gemini-cli")
        print("  • Grok CLI: Multiple implementations available")
        print()
        print("After installation, run this wizard again.")
        return 1

    # Main menu loop
    while True:
        menu_items = show_menu(tools)

        try:
            choice = input(f"{Colors.BOLD}Enter your choice: {Colors.RESET}").strip().lower()
            print()

            if choice not in menu_items:
                print_error("Invalid choice. Please try again.")
                print()
                continue

            action, tool_key, tool_info = menu_items[choice]

            if action == 'quit':
                print("Exiting wizard.")
                break

            elif action == 'register':
                success = run_registration_script(tool_key, tool_info, install_dir)
                print()
                if success:
                    print_success(f"✓ Successfully registered with {tool_info['name']}")
                else:
                    print_error(f"✗ Registration with {tool_info['name']} failed")
                print()
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == 'all':
                register_all_tools(tools, install_dir)
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == 'manual':
                show_manual_instructions(tools, install_dir)
                input(f"{Colors.CYAN}Press Enter to return to menu...{Colors.RESET}")
                print()

            elif action == 'docs':
                open_documentation(install_dir)
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
        sys.exit(1)
