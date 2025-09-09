#!/usr/bin/env python3
"""
Port Conflict Checker for GiljoAI MCP
Ensures no conflicts with AKE-MCP or other services
"""

import socket
import sys
from pathlib import Path
import yaml
from typing import Dict, List, Tuple

# Port assignments for different services
PORT_ASSIGNMENTS = {
    # AKE-MCP (Currently in use)
    "AKE-MCP Dashboard": 5000,
    "AKE-MCP Server": 5001,
    "AKE-MCP Lock": 5002,
    
    # GiljoAI MCP (Planned)
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


def load_config() -> Dict:
    """Load GiljoAI MCP configuration."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def get_configured_ports(config: Dict) -> List[Tuple[str, int]]:
    """Extract all configured ports from config."""
    ports = []
    
    # MCP Server
    if 'server' in config:
        if 'mcp' in config['server']:
            ports.append(("GiljoAI MCP Server", config['server']['mcp'].get('port', 6001)))
        if 'api' in config['server']:
            ports.append(("GiljoAI REST API", config['server']['api'].get('port', 6002)))
        if 'websocket' in config['server']:
            ports.append(("GiljoAI WebSocket", config['server']['websocket'].get('port', 6003)))
        if 'dashboard' in config['server']:
            ports.append(("GiljoAI Dashboard", config['server']['dashboard'].get('port', 6000)))
            ports.append(("Vite Dev Server", config['server']['dashboard'].get('dev_server_port', 5173)))
    
    # Database
    if 'database' in config and config['database'].get('type') == 'postgresql':
        ports.append(("PostgreSQL", config['database']['postgresql'].get('port', 5432)))
    
    return ports


def main():
    """Check for port conflicts."""
    print("=" * 60)
    print("GiljoAI MCP - Port Conflict Checker")
    print("=" * 60)
    print()
    
    # Load configuration
    config = load_config()
    configured_ports = get_configured_ports(config)
    
    # Check all ports
    conflicts = []
    available = []
    
    print("Checking port availability...")
    print("-" * 40)
    
    for service, port in PORT_ASSIGNMENTS.items():
        in_use = check_port(port)
        status = "IN USE" if in_use else "AVAILABLE"
        symbol = "[X]" if in_use else "[OK]"
        
        print(f"{symbol} Port {port:5} ({service:20}): {status}")
        
        # Check for conflicts with GiljoAI services
        if service.startswith("GiljoAI") and in_use:
            conflicts.append((service, port))
        elif service.startswith("GiljoAI"):
            available.append((service, port))
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if conflicts:
        print("\n[WARNING] CONFLICTS DETECTED:")
        for service, port in conflicts:
            print(f"   - {service} cannot use port {port} (already in use)")
        print("\n   Please update config.yaml with alternative ports.")
        return 1
    else:
        print("\n[OK] No conflicts detected!")
        print("\nGiljoAI MCP can safely use:")
        for service, port in available:
            print(f"   - {service}: port {port}")
    
    # Show AKE-MCP status
    print("\n" + "=" * 60)
    print("AKE-MCP STATUS")
    print("=" * 60)
    
    ake_running = False
    for service, port in PORT_ASSIGNMENTS.items():
        if service.startswith("AKE-MCP"):
            if check_port(port):
                print(f"[OK] {service} is running on port {port}")
                ake_running = True
            else:
                print(f"[-] {service} is not running (port {port} available)")
    
    if ake_running:
        print("\n[NOTE] AKE-MCP is currently running.")
        print("   GiljoAI MCP is configured to use different ports.")
        print("   Both can run simultaneously without conflicts.")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print()
    print("1. Keep AKE-MCP running during GiljoAI MCP development")
    print("2. Use the configured ports in config.yaml:")
    print("   - Dashboard: http://localhost:6000")
    print("   - REST API: http://localhost:6002")
    print("   - MCP Server: localhost:6001")
    print("3. When ready to transition, stop AKE-MCP first")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())