#!/usr/bin/env python3
"""
Port Conflict Checker for GiljoAI MCP
Ensures no conflicts with other services
"""

import socket
import sys
from pathlib import Path

import yaml


# Port assignments for different services
PORT_ASSIGNMENTS = {
    # GiljoAI MCP Services
    "GiljoAI Dashboard": 6000,
    "GiljoAI MCP Server": 6001,
    "GiljoAI REST API": 6002,
    "GiljoAI WebSocket": 6003,

    # Common services
    "PostgreSQL": 5432,
    "Vite Dev Server": 5173,
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
    return {}


def get_configured_ports(config: dict) -> list[tuple[str, int]]:
    """Extract all configured ports from config."""
    ports = []

    # MCP Server
    if "server" in config:
        if "mcp" in config["server"]:
            ports.append(("GiljoAI MCP Server", config["server"]["mcp"].get("port", 6001)))
        if "api" in config["server"]:
            ports.append(("GiljoAI REST API", config["server"]["api"].get("port", 6002)))
        if "websocket" in config["server"]:
            ports.append(("GiljoAI WebSocket", config["server"]["websocket"].get("port", 6003)))
        if "dashboard" in config["server"]:
            ports.append(("GiljoAI Dashboard", config["server"]["dashboard"].get("port", 6000)))
            ports.append(("Vite Dev Server", config["server"]["dashboard"].get("dev_server_port", 5173)))

    # Database
    if "database" in config and config["database"].get("type") == "postgresql":
        ports.append(("PostgreSQL", config["database"]["postgresql"].get("port", 5432)))

    return ports


def main():
    """Check for port conflicts."""

    # Load configuration
    config = load_config()
    get_configured_ports(config)

    # Check all ports
    conflicts = []
    available = []


    for service, port in PORT_ASSIGNMENTS.items():
        in_use = check_port(port)


        # Check for conflicts with GiljoAI services
        if service.startswith("GiljoAI") and in_use:
            conflicts.append((service, port))
        elif service.startswith("GiljoAI"):
            available.append((service, port))


    if conflicts:
        for service, port in conflicts:
            pass
        return 1
    for service, port in available:
        pass




    return 0


if __name__ == "__main__":
    sys.exit(main())
