#!/usr/bin/env python3
"""
Verification script to test config.yaml structure and parameter access
"""

import yaml
import json
from pathlib import Path

def verify_config():
    """Verify config.yaml structure"""
    config_path = Path("config.yaml")

    if not config_path.exists():
        print("[X] config.yaml not found")
        return False

    with open(config_path) as f:
        config = yaml.safe_load(f)

    print("Config structure:")
    print(json.dumps(config.get('services', {}), indent=2))

    # Check how ports are stored
    services = config.get('services', {})

    # Check API port access methods
    print("\nPort Access Tests:")

    # Method 1: services.api.port (correct structure)
    if 'api' in services and 'port' in services['api']:
        print(f"[OK] services.api.port: {services['api']['port']}")
    else:
        print("[X] services.api.port: NOT FOUND")

    # Method 2: services.api_port (what launcher expects)
    if 'api_port' in services:
        print(f"[OK] services.api_port: {services['api_port']}")
    else:
        print("[X] services.api_port: NOT FOUND")

    # Method 3: services.frontend.port
    if 'frontend' in services and 'port' in services['frontend']:
        print(f"[OK] services.frontend.port: {services['frontend']['port']}")
    else:
        print("[X] services.frontend.port: NOT FOUND")

    # Method 4: services.dashboard_port
    if 'dashboard_port' in services:
        print(f"[OK] services.dashboard_port: {services['dashboard_port']}")
    else:
        print("[X] services.dashboard_port: NOT FOUND")

    # Check paths section for install folder
    print("\nPaths Configuration:")
    paths = config.get('paths', {})
    print(json.dumps(paths, indent=2))

    if 'install_dir' in paths:
        print(f"[OK] Install directory configured: {paths['install_dir']}")
    else:
        print("[X] Install directory NOT configured")

    return True

if __name__ == "__main__":
    verify_config()
