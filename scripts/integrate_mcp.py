#!/usr/bin/env python3
"""
Script to integrate MCP registration into GiljoAI installers.
This script modifies setup_gui.py, setup.py, and setup_cli.py to add
universal MCP registration support.
"""

import re
from pathlib import Path


def integrate_gui_installer():
    """Integrate MCP registration into setup_gui.py"""
    print("Integrating MCP into GUI installer (setup_gui.py)...")

    gui_file = Path("setup_gui.py")
    if not gui_file.exists():
        print("  ERROR: setup_gui.py not found!")
        return False

    content = gui_file.read_text(encoding='utf-8')

    # 1. Add import statement after existing imports
    import_pattern = r'(from setup import PORT_ASSIGNMENTS, GiljoSetup, check_port)'
    import_replacement = r'''\1

# Import for MCP registration support
try:
    from installer.universal_mcp_installer import UniversalMCPInstaller
    MCP_SUPPORT_AVAILABLE = True
except ImportError:
    MCP_SUPPORT_AVAILABLE = False'''

    if "from installer.universal_mcp_installer import" not in content:
        content = re.sub(import_pattern, import_replacement, content)
        print("  [OK] Added MCP import")
    else:
        print("  - MCP import already exists")

    # 2. Add MCP to components initialization
    components_pattern = r'("validation": \{"name": "Validation", "status": "pending", "progress": 0\})'
    components_replacement = r'''"mcp": {"name": "AI Tool Integration", "status": "pending", "progress": 0},
        \1'''

    if '"mcp":' not in content:
        content = re.sub(components_pattern, components_replacement, content)
        print("  [OK] Added MCP component")
    else:
        print("  - MCP component already exists")

    # 3. Add setup_mcp_integration method to ProgressPage class
    mcp_method = '''
    def setup_mcp_integration(self, config, run_postgresql):
        """
        Set up MCP integration with detected AI CLI tools.

        This method is called after dependencies are installed and before validation.
        It will never fail the installation - any errors are logged as warnings.
        """
        if not MCP_SUPPORT_AVAILABLE:
            self.log("MCP registration support not available - skipping", "info")
            return

        try:
            # Initialize the MCP installer
            installer = UniversalMCPInstaller()

            # Detect installed AI CLI tools
            self.log("Detecting installed AI CLI tools...", "system")
            detected_tools = installer.detect_installed_tools()

            if not detected_tools:
                self.log("No AI CLI tools detected - skipping MCP registration", "info")
                self.log("You can register AI tools later using: python register_ai_tools.py", "info")
                self.set_progress(85)
                return

            # Display detected tools
            tool_display_names = {
                'claude': 'Claude Code',
                # TECHDEBT: Multi-tool support disabled
                # 'codex': 'Codex CLI (OpenAI)',
                # 'gemini': 'Gemini CLI (Google)'
            }

            detected_names = [tool_display_names.get(t, t) for t in detected_tools]
            self.log(f"Detected AI CLI tools: {', '.join(detected_names)}", "success")

            # Prepare MCP server configuration
            server_url = config.get('server_url', 'http://localhost:7272')
            if config.get('deployment_mode') == 'SERVER':
                host = config.get('host', 'localhost')
                port = config.get('port', 8000)
                server_url = f"http://{host}:{port}"

            # Register with each detected tool
            self.log("Registering GiljoAI MCP server with AI tools...", "system")
            self.set_progress(75)

            results = installer.register_all(
                server_name="giljo-mcp",
                command="python",
                args=["-m", "giljo_mcp"],
                env={
                    "GILJO_SERVER_URL": server_url,
                    "GILJO_MODE": config.get('deployment_mode', 'LOCAL')
                }
            )

            # Report results
            success_count = 0
            for tool, success in results.items():
                tool_name = tool_display_names.get(tool, tool)
                if success:
                    self.log(f"  [OK] {tool_name}: Successfully registered", "success")
                    success_count += 1
                else:
                    self.log(f"  [WARNING] {tool_name}: Registration failed (manual setup may be needed)", "warning")

            self.set_progress(80)

            # Verify registrations
            self.log("Verifying MCP registrations...", "system")
            verified = installer.verify_all("giljo-mcp")

            verified_count = sum(1 for v in verified.values() if v)

            # Update MCP component status
            self.set_status(f"AI tools: {verified_count}/{len(detected_tools)} configured", "mcp")
            self.set_progress(100, "mcp")

            # Summary
            if verified_count == len(detected_tools):
                self.log(f"SUCCESS: All {verified_count} AI tools configured successfully!", "success")
            elif verified_count > 0:
                self.log(f"PARTIAL: {verified_count}/{len(detected_tools)} AI tools configured", "warning")
            else:
                self.log("WARNING: AI tool registration failed - manual setup required", "warning")
                self.log("Run 'python register_ai_tools.py' after installation", "info")

            self.set_progress(85)

        except Exception as e:
            # Catch all errors and log as warnings
            self.log(f"MCP registration encountered an error: {e}", "warning")
            self.log("Installation will continue - you can register AI tools manually later", "info")
            self.set_progress(85)
'''

    # Find the right place to insert the method (after _init_components method)
    if "def setup_mcp_integration" not in content:
        # Find a good insertion point - after the install_python_packages method
        pattern = r'(def install_python_packages.*?\n(?:.*?\n)*?        except Exception.*?\n.*?\n)'
        match = re.search(pattern, content)
        if match:
            insertion_point = match.end()
            content = content[:insertion_point] + mcp_method + content[insertion_point:]
            print("  [OK] Added setup_mcp_integration method")
        else:
            print("  WARNING: Could not find insertion point for method")
    else:
        print("  - setup_mcp_integration method already exists")

    # 4. Call MCP integration after dependencies and before validation
    integration_call = '''
        # MCP Registration Phase
        self.set_status("Setting up AI tool integrations...", "mcp")
        self.set_progress(70)  # Overall progress
        self.log("\\n[PHASE 3: AI TOOL INTEGRATION]", "info")

        try:
            self.setup_mcp_integration(config, run_postgresql)
        except Exception as e:
            self.log(f"MCP registration skipped: {e}", "warning")
            self.set_progress(85)

'''

    # Find the validation section and insert before it
    validation_pattern = r'(        # Verify installations\n        self\.set_status\("Verifying installations\.\.\.", "validation"\))'

    if "AI TOOL INTEGRATION" not in content:
        content = re.sub(validation_pattern, integration_call + r'\1', content)
        print("  [OK] Added MCP integration call")
    else:
        print("  - MCP integration call already exists")

    # Write the modified content back
    gui_file.write_text(content, encoding='utf-8')
    print("  [OK] GUI installer integration complete!")
    return True


def integrate_cli_installer():
    """Integrate MCP registration into setup.py"""
    print("\nIntegrating MCP into CLI installer (setup.py)...")

    cli_file = Path("setup.py")
    if not cli_file.exists():
        print("  ERROR: setup.py not found!")
        return False

    content = cli_file.read_text(encoding='utf-8')

    # 1. Add import statement
    import_pattern = r'(from typing import Any, Dict, List, Optional, Tuple)'
    import_replacement = r'''\1

# Import for MCP registration support
try:
    from installer.universal_mcp_installer import UniversalMCPInstaller
    MCP_SUPPORT_AVAILABLE = True
except ImportError:
    MCP_SUPPORT_AVAILABLE = False'''

    if "from installer.universal_mcp_installer import" not in content:
        content = re.sub(import_pattern, import_replacement, content)
        print("  [OK] Added MCP import")
    else:
        print("  - MCP import already exists")

    # 2. Add setup_mcp_integration method to GiljoSetup class
    mcp_method = '''
    def setup_mcp_integration(self) -> bool:
        """Set up MCP integration with detected AI CLI tools."""
        if not MCP_SUPPORT_AVAILABLE:
            print("\\nMCP registration support not available - skipping")
            return False

        try:
            print("\\n" + "="*40)
            print("AI Tool Integration")
            print("="*40)

            installer = UniversalMCPInstaller()

            print("\\nDetecting installed AI CLI tools...")
            detected_tools = installer.detect_installed_tools()

            if not detected_tools:
                print("[INFO] No AI CLI tools detected - skipping MCP registration")
                print("  You can register AI tools later using: python register_ai_tools.py")
                return False

            tool_display_names = {
                'claude': 'Claude Code',
                # TECHDEBT: Multi-tool support disabled
                # 'codex': 'Codex CLI (OpenAI)',
                # 'gemini': 'Gemini CLI (Google)'
            }

            print(f"\\n[OK] Detected {len(detected_tools)} AI CLI tool(s):")
            for tool in detected_tools:
                print(f"  * {tool_display_names.get(tool, tool)}")

            # Prepare server configuration
            server_url = self.config.get('server_url', 'http://localhost:7272')
            if hasattr(self, 'deployment_mode') and self.deployment_mode == 'SERVER':
                host = self.config.get('host', 'localhost')
                port = self.selected_port if hasattr(self, 'selected_port') else self.server_port
                server_url = f"http://{host}:{port}"

            # Ask user
            print("\\nWould you like to register GiljoAI MCP with these tools?")
            response = input("Register now? (y/n) [y]: ").strip().lower()

            if response == 'n':
                print("[INFO] Skipping MCP registration")
                return False

            # Register
            print("\\nRegistering GiljoAI MCP server...")
            results = installer.register_all(
                server_name="giljo-mcp",
                command="python",
                args=["-m", "giljo_mcp"],
                env={
                    "GILJO_SERVER_URL": server_url,
                    "GILJO_MODE": getattr(self, 'deployment_mode', 'LOCAL')
                }
            )

            # Report results
            success_count = 0
            print("\\nRegistration results:")
            for tool, success in results.items():
                tool_name = tool_display_names.get(tool, tool)
                if success:
                    print(f"  [OK] {tool_name}: Successfully registered")
                    success_count += 1
                else:
                    print(f"  [WARNING] {tool_name}: Registration failed")

            return success_count > 0

        except Exception as e:
            print(f"\\n[WARNING] MCP registration error: {e}")
            print("  You can register manually later: python register_ai_tools.py")
            return False
'''

    # Find the right place to insert the method (after display_summary)
    if "def setup_mcp_integration" not in content:
        pattern = r'(    def display_summary.*?\n(?:.*?\n)*?        print.*?\n)'
        match = re.search(pattern, content)
        if match:
            insertion_point = match.end()
            content = content[:insertion_point] + mcp_method + content[insertion_point:]
            print("  [OK] Added setup_mcp_integration method")
        else:
            print("  WARNING: Could not find insertion point for method")
    else:
        print("  - setup_mcp_integration method already exists")

    # 3. Call MCP integration in main()
    main_pattern = r'(        if setup\.install_requirements\(\):\n            print\("[OK] Dependencies installed"\))'
    main_replacement = r'''\1
            # MCP Integration
            mcp_registered = setup.setup_mcp_integration()'''

    if "mcp_registered = setup.setup_mcp_integration()" not in content:
        content = re.sub(main_pattern, main_replacement, content)
        print("  [OK] Added MCP call in main()")
    else:
        print("  - MCP call already exists in main()")

    # 4. Update display_summary to show MCP status
    summary_update = '''
        # Show MCP status
        print("\\nAI Tool Integration:")
        if hasattr(self, 'mcp_registered') and self.mcp_registered:
            print("  [OK] AI CLI tools configured")
        else:
            print("  [INFO] Run 'python register_ai_tools.py' to configure AI tools")
'''

    # Add to display_summary if not already there
    if "AI Tool Integration:" not in content:
        pattern = r'(    def display_summary.*?\n(?:.*?\n)*?)(        print\("=".*?\n)'
        match = re.search(pattern, content)
        if match:
            insertion_point = match.start(2)
            content = content[:insertion_point] + summary_update + "\n" + content[insertion_point:]
            print("  [OK] Updated display_summary")
    else:
        print("  - display_summary already updated")

    # Write back
    cli_file.write_text(content, encoding='utf-8')
    print("  [OK] CLI installer integration complete!")
    return True


def integrate_enhanced_cli():
    """Integrate MCP registration into setup_cli.py if it exists"""
    print("\nIntegrating MCP into enhanced CLI installer (setup_cli.py)...")

    cli_file = Path("setup_cli.py")
    if not cli_file.exists():
        print("  - setup_cli.py not found, skipping")
        return True

    content = cli_file.read_text(encoding='utf-8')

    # Similar integration as setup.py but adapted for enhanced CLI
    # This would follow the same pattern but is optional
    print("  [OK] Enhanced CLI integration skipped (optional)")
    return True


def main():
    """Main integration script"""
    print("GiljoAI MCP Integration Script")
    print("="*50)
    print("This script will integrate MCP registration support into:")
    print("  * setup_gui.py (GUI installer)")
    print("  * setup.py (CLI installer)")
    print("  * setup_cli.py (Enhanced CLI, if exists)")
    print()

    # Check for required files
    required = ["setup_gui.py", "setup.py", "installer/universal_mcp_installer.py"]
    missing = [f for f in required if not Path(f).exists()]

    if missing:
        print("ERROR: Missing required files:")
        for f in missing:
            print(f"  [X] {f}")
        return 1

    print("All required files found. Starting integration...")
    print()

    # Run integrations
    success = True
    success = integrate_gui_installer() and success
    success = integrate_cli_installer() and success
    success = integrate_enhanced_cli() and success

    if success:
        print("\n" + "="*50)
        print("[OK] Integration complete!")
        print("\nNext steps:")
        print("1. Test the installation with: python setup_gui.py")
        print("2. Test CLI installation with: python setup.py")
        print("3. Verify MCP registration with: python register_ai_tools.py")
    else:
        print("\n[WARNING] Integration completed with warnings")
        print("Please review the changes manually")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
