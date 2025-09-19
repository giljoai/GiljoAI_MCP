#!/usr/bin/env python3
"""Debug script to test mode detection logic."""

import sys
import os
sys.path.insert(0, 'src')

from giljo_mcp.config_manager import ConfigManager, DeploymentMode
import ipaddress

def test_mode_detection():
    print("Testing mode detection logic...")
    
    # Check environment variables
    print(f"GILJO_MCP_MODE env var: {os.getenv('GILJO_MCP_MODE')}")
    
    # Test 1: Private IP
    print("\n=== Test 1: Private IP ===")
    config = ConfigManager()
    print(f"Initial mode: {config.server.mode}")
    print(f"Initial api_host: {config.server.api_host}")
    
    config.server.api_host = "192.168.1.100"
    print(f"After setting api_host to 192.168.1.100: {config.server.api_host}")
    
    # Check if IP is private
    try:
        ip = ipaddress.ip_address("192.168.1.100")
        print(f"IP address object: {ip}")
        print(f"Is private: {ip.is_private}")
    except ValueError as e:
        print(f"ValueError: {e}")
    
    print(f"Before _detect_mode(): {config.server.mode}")
    
    # Add debug to see what's happening inside _detect_mode
    print(f"Checking if api_host '{config.server.api_host}' is not in ['127.0.0.1', 'localhost']...")
    if config.server.api_host not in ("127.0.0.1", "localhost"):
        print("API host is not localhost - proceeding with IP check")
        try:
            ip = ipaddress.ip_address(config.server.api_host)
            print(f"IP parsed successfully: {ip}")
            if ip.is_private:
                print("IP is private - should set mode to LAN")
            else:
                print("IP is public - should set mode to WAN")
        except ValueError as e:
            print(f"IP parsing failed: {e}")
    else:
        print("API host is localhost - no mode change")
    
    config._detect_mode()
    print(f"After _detect_mode(): {config.server.mode}")
    
    # Test 2: Public IP
    print("\n=== Test 2: Public IP ===")
    config2 = ConfigManager()
    config2.server.api_host = "8.8.8.8"
    print(f"Before _detect_mode(): {config2.server.mode}")
    config2._detect_mode()
    print(f"After _detect_mode(): {config2.server.mode}")
    
    # Test 3: API Key
    print("\n=== Test 3: API Key ===")
    config3 = ConfigManager()
    config3.server.api_key = "test-key"
    print(f"Before _detect_mode(): {config3.server.mode}")
    config3._detect_mode()
    print(f"After _detect_mode(): {config3.server.mode}")

if __name__ == "__main__":
    test_mode_detection()