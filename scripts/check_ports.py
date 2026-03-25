#!/usr/bin/env python3
"""
Port Conflict Checker for GiljoAI MCP v0.2 Beta
Ensures no conflicts with the unified HTTP server architecture
"""

import socket
import sys
from pathlib import Path

import yaml


# Port assignments for v0.2 Beta architecture
PORT_ASSIGNMENTS = {
    # Primary service - unified HTTP server
    "GiljoAI MCP": 7272,  # Main server (API + MCP + WebSocket) - changed from 8000
    # Optional services
    "Frontend Dev Server": 6000,  # Vite dev server (development only)
    "PostgreSQL": 5432,  # PostgreSQL database server
    # Alternative ports if 7272 is occupied
    "alternatives": [7273, 7274, 8747, 8823, 9456, 9789],
    # Legacy ports (deprecated in v0.2 Beta)
    # These are checked for migration purposes only
    "Legacy MCP Server": 6001,  # Old stdio server (deprecated)
    "Legacy REST API": 6002,  # Old separate API (deprecated)
    "Legacy WebSocket": 6003,  # Old separate WebSocket (deprecated)
    "Legacy Port 8000": 8000,  # Old default port (early versions)
}

# New default configuration
DEFAULT_CONFIG = {
    "server_port": 7272,  # Changed from 8000 to avoid conflicts
    "enable_frontend_dev": False,
    "database_type": "postgresql",
}


def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0  # True if port is in use
    except Exception:
        return False


def load_config() -> dict:
    """Load GiljoAI MCP configuration."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)

    # Try JSON format
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        import json

        with open(config_path) as f:
            return json.load(f)

    return DEFAULT_CONFIG


def get_configured_ports(config: dict) -> list[tuple[str, int]]:
    """Extract all configured ports from config."""
    ports = []

    # Main orchestrator server
    server_port = config.get("server", {}).get("port", 7272)  # Changed default
    ports.append(("GiljoAI MCP", server_port))

    # Frontend dev server (optional)
    if config.get("features", {}).get("frontend_dev", False):
        ports.append(("Frontend Dev Server", 6000))

    # Database
    if config.get("database", {}).get("type") == "postgresql":
        pg_port = config.get("database", {}).get("postgresql", {}).get("port", 5432)
        ports.append(("PostgreSQL", pg_port))

    return ports


def check_legacy_ports() -> list[tuple[str, int, bool]]:
    """Check if legacy ports are still in use (for migration warning)."""
    legacy = []
    for name, port in PORT_ASSIGNMENTS.items():
        if "Legacy" in name:
            in_use = check_port(port)
            if in_use:
                legacy.append((name, port, in_use))
    return legacy


def main():
    """Check for port conflicts."""

    print("GiljoAI MCP v0.2 Beta - Port Configuration Checker")
    print("=" * 50)

    # Load configuration
    config = load_config()
    configured_ports = get_configured_ports(config)

    # Check configured ports
    print("\nChecking configured ports:")
    conflicts = []
    available = []

    for service, port in configured_ports:
        in_use = check_port(port)
        status = "IN USE" if in_use else "Available"
        symbol = "❌" if in_use else "✅"

        print(f"  {symbol} {service:25} Port {port:5} - {status}")

        if in_use:
            conflicts.append((service, port))
        else:
            available.append((service, port))

    # Check for legacy services running
    print("\nChecking for legacy services:")
    legacy_running = check_legacy_ports()

    if legacy_running:
        print("  ⚠️  Legacy services detected!")
        for service, port, _ in legacy_running:
            print(f"     - {service} on port {port}")
        print("\n  These should be stopped before running GiljoAI MCP")
        print("  Run: stop_giljo.bat to stop all services")
    else:
        print("  ✅ No legacy services running")

    # Summary
    print("\n" + "=" * 50)
    if conflicts:
        print("❌ Port conflicts detected!")
        print("\nThe following ports are already in use:")
        for service, port in conflicts:
            print(f"  - {service}: {port}")

        print("\nPossible solutions:")
        print("1. Stop the conflicting service")
        print("2. Change the port in config.yaml")

        if any(port == 7272 for _, port in conflicts):
            print("\nPort 7272 conflict detected!")
            print("This is the main server port for GiljoAI MCP")
            print("Make sure no other GiljoAI instance is running")
            print("\nAlternative ports you can use:")
            for alt_port in PORT_ASSIGNMENTS.get("alternatives", []):
                print(f"  - {alt_port}")

        if any(port == 8000 for _, port in conflicts):
            print("\nPort 8000 conflict detected!")
            print("Note: GiljoAI MCP has moved from port 8000 to 7272")
            print("This avoids conflicts with common development servers")

        sys.exit(1)
    else:
        print("✅ All ports are available!")
        print("\nYou can proceed with starting the server:")
        print("  Run: start_giljo.bat")

    return 0


if __name__ == "__main__":
    sys.exit(main())
