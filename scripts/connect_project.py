#!/usr/bin/env python3
"""
GiljoAI MCP Project Connection Script
======================================

This script configures a development project to connect to an existing
GiljoAI MCP server installation. Run this in your project directory to
enable MCP orchestration for your coding agent.

Usage: python connect_project.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional


def detect_mcp_server() -> Optional[Dict[str, str]]:
    """Detect installed GiljoAI MCP server"""
    # Check common installation locations
    possible_locations = [
        Path.home() / "giljo-mcp",
        Path.home() / "GiljoAI_MCP",
        Path("C:/GiljoAI_MCP"),
        Path("/opt/giljo-mcp"),
        Path("/usr/local/giljo-mcp"),
    ]

    # Check environment variable
    if os.environ.get("GILJO_MCP_HOME"):
        possible_locations.insert(0, Path(os.environ["GILJO_MCP_HOME"]))

    for location in possible_locations:
        if location.exists() and (location / "venv").exists():
            return {
                "path": str(location),
                "type": "local",
                "python": str(location / "venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"),
            }

    return None


def get_server_config() -> Dict[str, any]:
    """Get MCP server configuration from user"""
    print("\n" + "=" * 60)
    print("   GiljoAI MCP Project Connection Setup")
    print("=" * 60 + "\n")

    # Try to detect existing installation
    detected = detect_mcp_server()

    if detected:
        print(f"✓ Found GiljoAI MCP installation at: {detected['path']}")
        use_detected = input("\nUse this installation? (y/n) [y]: ").lower()
        if use_detected != "n":
            return {"type": "local", "path": detected["path"], "python": detected["python"]}

    # Manual configuration
    print("\nConfigure MCP Server Connection:")
    print("1. Local installation (same machine)")
    print("2. Network server (LAN/WAN)")

    choice = input("\nSelect connection type (1/2) [1]: ").strip()

    if choice == "2":
        # Network server configuration
        host = input("Server hostname/IP [localhost]: ").strip() or "localhost"
        port = input("Server port [8000]: ").strip() or "8000"

        print("\nAuthentication:")
        print("1. None (local network)")
        print("2. API Key")

        auth_choice = input("Select authentication (1/2) [1]: ").strip()

        config = {"type": "network", "host": host, "port": port, "url": f"http://{host}:{port}"}

        if auth_choice == "2":
            api_key = input("Enter API key: ").strip()
            config["api_key"] = api_key

        return config

    # Local installation
    default_path = detected["path"] if detected else ""
    install_path = input(f"GiljoAI MCP installation path [{default_path}]: ").strip()

    if not install_path and detected:
        install_path = detected["path"]

    if not Path(install_path).exists():
        print(f"\n⚠ Warning: Path '{install_path}' does not exist!")
        print("Make sure to install GiljoAI MCP server first.")

    venv_path = Path(install_path) / "venv"
    python_exe = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "python"

    return {"type": "local", "path": install_path, "python": str(python_exe)}


def create_mcp_config(config: Dict[str, any]) -> None:
    """Create or update .mcp.json configuration in current directory"""

    # Build the GiljoAI MCP server configuration
    if config["type"] == "local":
        # Local installation - use direct Python execution
        giljo_server = {
            "command": config["python"],
            "args": ["-m", "giljo_mcp"],
            "env": {"GILJO_MCP_HOME": config["path"], "GILJO_MCP_MODE": "local"},
            "description": "GiljoAI MCP Orchestrator - Local Installation",
        }
    else:
        # Network server - use proxy connection
        giljo_server = {
            "type": "http",
            "url": config["url"],
            "description": "GiljoAI MCP Orchestrator - Network Server",
        }

        if config.get("api_key"):
            giljo_server["headers"] = {"Authorization": f"Bearer {config['api_key']}"}

    # Check for existing configuration
    config_file = Path.cwd() / ".mcp.json"

    if config_file.exists():
        print("\n📋 Found existing .mcp.json file")

        try:
            with open(config_file) as f:
                existing_config = json.load(f)

            # Check if there are existing MCP servers
            existing_servers = existing_config.get("mcpServers", {})

            if existing_servers:
                print("\nExisting MCP servers found:")
                for server_name in existing_servers.keys():
                    print(f"  • {server_name}")

                # Check if giljo-orchestrator already exists
                if "giljo-orchestrator" in existing_servers:
                    print("\n⚠ 'giljo-orchestrator' already configured")
                    update = input("Update existing configuration? (y/n) [y]: ").lower()
                    if update == "n":
                        print("Configuration unchanged.")
                        return

                print("\n✅ Adding GiljoAI MCP to existing configuration...")

            # Merge configurations
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}

            # Add or update giljo-orchestrator
            existing_config["mcpServers"]["giljo-orchestrator"] = giljo_server

            # Update project settings without overwriting other settings
            if "projectSettings" not in existing_config:
                existing_config["projectSettings"] = {}

            # Only update GiljoAI-specific settings
            if "giljoAI" not in existing_config["projectSettings"]:
                existing_config["projectSettings"]["giljoAI"] = {}

            existing_config["projectSettings"]["giljoAI"].update(
                {"autoConnect": True, "projectName": Path.cwd().name, "orchestratorConfig": config}
            )

            final_config = existing_config
            action = "updated"

        except json.JSONDecodeError as e:
            print(f"\n❌ Error: Existing .mcp.json is not valid JSON: {e}")
            backup = input("Create backup and write new config? (y/n) [y]: ").lower()

            if backup != "n":
                # Backup the corrupted file
                backup_file = config_file.with_suffix(".mcp.json.backup")
                import shutil

                shutil.copy(config_file, backup_file)
                print(f"✓ Backup created: {backup_file}")

                # Create new config
                final_config = {
                    "mcpServers": {"giljo-orchestrator": giljo_server},
                    "projectSettings": {
                        "giljoAI": {"autoConnect": True, "projectName": Path.cwd().name, "orchestratorConfig": config}
                    },
                }
                action = "created"
            else:
                print("Configuration aborted.")
                return

        except Exception as e:
            print(f"\n❌ Unexpected error reading .mcp.json: {e}")
            return

    else:
        # No existing file, create new
        final_config = {
            "mcpServers": {"giljo-orchestrator": giljo_server},
            "projectSettings": {
                "giljoAI": {"autoConnect": True, "projectName": Path.cwd().name, "orchestratorConfig": config}
            },
        }
        action = "created"

    # Write the configuration
    try:
        with open(config_file, "w") as f:
            json.dump(final_config, f, indent=2)

        print(f"\n✓ Successfully {action} .mcp.json configuration")

        # Show summary of all configured servers
        if len(final_config.get("mcpServers", {})) > 1:
            print("\nConfigured MCP servers:")
            for server_name in final_config["mcpServers"].keys():
                print(f"  • {server_name}")

    except Exception as e:
        print(f"\n❌ Error writing .mcp.json: {e}")
        return


def create_env_file(config: Dict[str, any]) -> None:
    """Create .env file for project-specific settings"""
    env_file = Path.cwd() / ".env.giljo"

    env_content = []
    env_content.append("# GiljoAI MCP Configuration")
    env_content.append(f"GILJO_MCP_TYPE={config['type']}")

    if config["type"] == "local":
        env_content.append(f"GILJO_MCP_HOME={config['path']}")
    else:
        env_content.append(f"GILJO_MCP_URL={config['url']}")
        if config.get("api_key"):
            env_content.append(f"GILJO_MCP_API_KEY={config['api_key']}")

    env_content.append(f"GILJO_PROJECT_NAME={Path.cwd().name}")
    env_content.append("")

    with open(env_file, "w") as f:
        f.write("\n".join(env_content))

    print("✓ Created .env.giljo configuration")

    # Update .gitignore if it exists
    gitignore = Path.cwd() / ".gitignore"
    if gitignore.exists():
        with open(gitignore) as f:
            content = f.read()

        if ".env.giljo" not in content:
            with open(gitignore, "a") as f:
                f.write("\n# GiljoAI MCP\n.env.giljo\n")
            print("✓ Updated .gitignore")


def verify_connection(config: Dict[str, any]) -> bool:
    """Verify connection to MCP server"""
    print("\n🔍 Verifying connection...")

    if config["type"] == "local":
        # Check if Python executable exists
        python_path = Path(config["python"])
        if not python_path.exists():
            print(f"❌ Python executable not found: {python_path}")
            return False

        # Try to import giljo_mcp
        try:
            import subprocess

            result = subprocess.run(
                [config["python"], "-c", "import giljo_mcp; print('OK')"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and "OK" in result.stdout:
                print("✓ Local MCP server is accessible")
                return True
            print(f"❌ Could not verify MCP server: {result.stderr}")
            return False
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

    else:
        # Network server - try to connect
        try:
            import urllib.error
            import urllib.request

            # Validate URL format to prevent SSRF attacks
            if not config["url"].startswith(("http://", "https://")):
                raise ValueError("Invalid URL format")

            # Sanitize and validate the URL components
            from urllib.parse import urlparse

            parsed = urlparse(config["url"])
            if not parsed.hostname:
                raise ValueError("Invalid hostname in URL")

            # Build safe URL for health check
            health_url = f"{parsed.scheme}://{parsed.netloc}/health"
            req = urllib.request.Request(health_url)
            if config.get("api_key"):
                req.add_header("Authorization", f"Bearer {config['api_key']}")

            response = urllib.request.urlopen(req, timeout=5)  # nosec B310 - URL is validated above
            if response.status == 200:
                print("✓ Network MCP server is accessible")
                return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("❌ Authentication failed - check API key")
            else:
                print(f"❌ Server returned error: {e.code}")
            return False
        except Exception as e:
            print(f"❌ Could not connect to server: {e}")
            return False

    return False


def main():
    """Main entry point"""
    try:
        # Get server configuration
        config = get_server_config()

        # Create configuration files
        create_mcp_config(config)
        create_env_file(config)

        # Verify connection
        connected = verify_connection(config)

        # Print summary
        print("\n" + "=" * 60)
        print("   Setup Complete!")
        print("=" * 60)

        if connected:
            print("\n✅ Your project is now connected to GiljoAI MCP")
        else:
            print("\n⚠️  Configuration saved but connection could not be verified")
            print("   Make sure the MCP server is installed and running")

        print("\nNext steps:")
        print("1. Restart your coding agent (Claude, Cursor, etc.)")
        print("2. The MCP orchestrator will be available automatically")
        print("3. Use MCP tools to coordinate multi-agent tasks")

        if config["type"] == "local" and not connected:
            print("\nTo install the MCP server, run:")
            print("  python bootstrap.py")
            print(f"  in directory: {config.get('path', 'your chosen directory')}")

    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
