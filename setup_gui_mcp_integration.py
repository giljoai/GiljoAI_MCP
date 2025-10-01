#!/usr/bin/env python3
"""
MCP Integration Methods for setup_gui.py

This file contains the methods to be integrated into setup_gui.py
for universal MCP registration support.
"""

# Add this import at the top of setup_gui.py (around line 20):
# from installer.universal_mcp_installer import UniversalMCPInstaller

def setup_mcp_integration(self, config, run_postgresql):
    """
    Set up MCP integration with detected AI CLI tools.

    This method is called after dependencies are installed and before validation.
    It will never fail the installation - any errors are logged as warnings.

    Args:
        config: Installation configuration dictionary
        run_postgresql: Boolean indicating if PostgreSQL is running
    """
    try:
        from installer.universal_mcp_installer import UniversalMCPInstaller

        # Initialize the MCP installer
        installer = UniversalMCPInstaller()

        # Detect installed AI CLI tools
        self.log("Detecting installed AI CLI tools...", "system")
        detected_tools = installer.detect_installed_tools()

        if not detected_tools:
            self.log("No AI CLI tools detected - skipping MCP registration", "info")
            self.log("You can register AI tools later using: python register_ai_tools.py", "info")
            self.set_progress(85)  # Move progress forward
            return

        # Display detected tools
        tool_display_names = {
            'claude': 'Claude Code',
            'codex': 'Codex CLI (OpenAI)',
            'gemini': 'Gemini CLI (Google)'
        }

        detected_names = [tool_display_names.get(t, t) for t in detected_tools]
        self.log(f"Detected AI CLI tools: {', '.join(detected_names)}", "success")

        # Prepare MCP server configuration
        server_url = config.get('server_url', 'http://localhost:8000')
        if config.get('deployment_mode') == 'SERVER':
            # For server mode, use the configured host
            host = config.get('host', 'localhost')
            port = config.get('port', 8000)
            server_url = f"http://{host}:{port}"

        # Register with each detected tool
        self.log("Registering GiljoAI MCP server with AI tools...", "system")
        self.set_progress(75)  # Update overall progress

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
                self.log(f"  ✓ {tool_name}: Successfully registered", "success")
                success_count += 1
            else:
                self.log(f"  ⚠ {tool_name}: Registration failed (manual setup may be needed)", "warning")

        self.set_progress(80)  # Update progress

        # Verify registrations
        self.log("Verifying MCP registrations...", "system")
        verified = installer.verify_all("giljo-mcp")

        verified_count = 0
        for tool, is_verified in verified.items():
            if is_verified:
                verified_count += 1

        # Summary
        if verified_count == len(detected_tools):
            self.log(f"SUCCESS: All {verified_count} AI tools configured successfully!", "success")
            self.set_status("AI tool integration complete ✓", "mcp")
        elif verified_count > 0:
            self.log(f"PARTIAL: {verified_count}/{len(detected_tools)} AI tools configured", "warning")
            self.set_status(f"AI tools: {verified_count}/{len(detected_tools)} configured", "mcp")
        else:
            self.log("WARNING: AI tool registration failed - manual setup required", "warning")
            self.log("Run 'python register_ai_tools.py' after installation to configure", "info")
            self.set_status("AI tools: Manual setup required", "mcp")

        self.set_progress(85)  # Final MCP progress

    except ImportError as e:
        # Handle missing dependencies gracefully
        self.log(f"MCP registration skipped - missing dependencies: {e}", "warning")
        self.log("You can install missing dependencies and register later", "info")
        self.set_progress(85)
    except Exception as e:
        # Catch all other errors and log as warnings
        self.log(f"MCP registration encountered an error: {e}", "warning")
        self.log("Installation will continue - you can register AI tools manually later", "info")
        self.log("Run 'python register_ai_tools.py' after installation", "info")
        self.set_progress(85)


# Integration instructions for setup_gui.py:
#
# 1. Add import at top (around line 20):
#    from installer.universal_mcp_installer import UniversalMCPInstaller
#
# 2. Add this method to ProgressPage class (around line 1600)
#
# 3. Call the method after dependencies and before validation (around line 2250):
#    # MCP Registration Phase
#    self.set_status("Setting up AI tool integrations...", "mcp")
#    self.set_progress(70)  # Overall progress
#    self.log("\n[PHASE 3: AI TOOL INTEGRATION]", "info")
#
#    try:
#        self.setup_mcp_integration(config, run_postgresql)
#    except Exception as e:
#        self.log(f"MCP registration skipped: {e}", "warning")
#
# 4. Update component initialization to include MCP:
#    In _init_components() method, add:
#    "mcp": {"name": "AI Tool Integration", "status": "pending", "progress": 0}
