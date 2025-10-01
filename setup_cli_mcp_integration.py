#!/usr/bin/env python3
"""
MCP Integration Methods for setup.py and setup_cli.py

This file contains the methods to be integrated into setup.py
for universal MCP registration support in CLI mode.
"""

# Add this import at the top of setup.py (around line 17):
# from installer.universal_mcp_installer import UniversalMCPInstaller

def setup_mcp_integration(self) -> bool:
    """
    Set up MCP integration with detected AI CLI tools.

    This method is called after dependencies are installed and before summary.
    It will never fail the installation - any errors are logged as warnings.

    Returns:
        bool: True if at least one tool was registered, False otherwise
    """
    try:
        from installer.universal_mcp_installer import UniversalMCPInstaller

        print("\n" + "="*40)
        print("AI Tool Integration")
        print("="*40)

        # Initialize the MCP installer
        installer = UniversalMCPInstaller()

        # Detect installed AI CLI tools
        print("\nDetecting installed AI CLI tools...")
        detected_tools = installer.detect_installed_tools()

        if not detected_tools:
            print("ℹ No AI CLI tools detected - skipping MCP registration")
            print("  You can register AI tools later using: python register_ai_tools.py")
            return False

        # Display detected tools
        tool_display_names = {
            'claude': 'Claude Code',
            'codex': 'Codex CLI (OpenAI)',
            'gemini': 'Gemini CLI (Google)'
        }

        print(f"\n✓ Detected {len(detected_tools)} AI CLI tool(s):")
        for tool in detected_tools:
            print(f"  • {tool_display_names.get(tool, tool)}")

        # Prepare MCP server configuration
        server_url = self.config.get('server_url', 'http://localhost:8000')
        if hasattr(self, 'deployment_mode') and self.deployment_mode == 'SERVER':
            # For server mode, use the configured host and port
            host = self.config.get('host', 'localhost')
            port = self.selected_port if hasattr(self, 'selected_port') else self.server_port
            server_url = f"http://{host}:{port}"

        # Ask user if they want to register
        print("\nWould you like to register GiljoAI MCP with these tools?")
        print("This will allow AI assistants to interact with your GiljoAI server.")
        response = input("Register now? (y/n) [y]: ").strip().lower()

        if response == 'n':
            print("ℹ Skipping MCP registration")
            print("  You can register later using: python register_ai_tools.py")
            return False

        # Register with each detected tool
        print("\nRegistering GiljoAI MCP server...")
        results = installer.register_all(
            server_name="giljo-mcp",
            command="python",
            args=["-m", "giljo_mcp"],
            env={
                "GILJO_SERVER_URL": server_url,
                "GILJO_MODE": self.deployment_mode if hasattr(self, 'deployment_mode') else 'LOCAL'
            }
        )

        # Report results
        success_count = 0
        print("\nRegistration results:")
        for tool, success in results.items():
            tool_name = tool_display_names.get(tool, tool)
            if success:
                print(f"  ✓ {tool_name}: Successfully registered")
                success_count += 1
            else:
                print(f"  ⚠ {tool_name}: Registration failed (manual setup may be needed)")

        # Verify registrations
        print("\nVerifying registrations...")
        verified = installer.verify_all("giljo-mcp")

        verified_count = sum(1 for v in verified.values() if v)

        # Summary
        print("\n" + "-"*40)
        if verified_count == len(detected_tools):
            print(f"✓ SUCCESS: All {verified_count} AI tools configured successfully!")
        elif verified_count > 0:
            print(f"⚠ PARTIAL: {verified_count}/{len(detected_tools)} AI tools configured")
            print("  Some tools may require manual configuration")
        else:
            print("⚠ WARNING: AI tool registration failed")
            print("  Manual setup required - run: python register_ai_tools.py")

        return success_count > 0

    except ImportError as e:
        # Handle missing dependencies gracefully
        print(f"\n⚠ MCP registration skipped - missing dependencies")
        print(f"  You can install missing dependencies and register later")
        print(f"  Run: python register_ai_tools.py")
        return False
    except Exception as e:
        # Catch all other errors and log as warnings
        print(f"\n⚠ MCP registration encountered an error: {e}")
        print("  Installation will continue")
        print("  You can register AI tools manually later")
        print("  Run: python register_ai_tools.py")
        return False


def display_summary_with_mcp(self, mcp_registered=False):
    """
    Enhanced display_summary that includes MCP registration status.

    Args:
        mcp_registered: Boolean indicating if any MCP tools were registered
    """
    # Call original display_summary if it exists
    if hasattr(self, '_original_display_summary'):
        self._original_display_summary()
    else:
        # Default summary
        print("\n" + "="*50)
        print("Installation Summary")
        print("="*50)

        print("\nConfiguration:")
        print(f"  Mode: {getattr(self, 'deployment_mode', 'LOCAL')}")
        if hasattr(self, 'selected_port'):
            print(f"  Port: {self.selected_port}")
        print(f"  Database: PostgreSQL")

        print("\nInstalled Components:")
        print("  ✓ Python dependencies")
        print("  ✓ Configuration files")
        print("  ✓ Directory structure")

    # Add MCP status
    print("\nAI Tool Integration:")
    if mcp_registered:
        print("  ✓ AI CLI tools configured")
        print("    Your AI assistants can now interact with GiljoAI")
    else:
        print("  ℹ AI tools not configured")
        print("    Run 'python register_ai_tools.py' to set up AI tool integration")


# Integration instructions for setup.py:
#
# 1. Add import at top (around line 17):
#    from installer.universal_mcp_installer import UniversalMCPInstaller
#
# 2. Add setup_mcp_integration method to GiljoSetup class
#
# 3. In main() function, after install_requirements() (around line ~650):
#    # MCP Integration
#    mcp_registered = False
#    if setup.install_requirements():
#        print("✓ Dependencies installed")
#        mcp_registered = setup.setup_mcp_integration()
#
# 4. Pass mcp_registered to display_summary:
#    setup.display_summary_with_mcp(mcp_registered)
#
# For setup_cli.py (if using enhanced CLI):
#
# 1. Add the same method to GiljoCLISetup class
#
# 2. Call it in the run() method after dependencies:
#    mcp_registered = self.setup_mcp_integration()
#
# 3. Include MCP status in final summary
