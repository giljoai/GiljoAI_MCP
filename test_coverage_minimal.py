#!/usr/bin/env python3
"""
Minimal coverage test for config_manager.py to diagnose coverage issues.
"""

import sys
import os
from pathlib import Path

# Add src to path before any imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_config():
    """Test basic ConfigManager functionality for coverage measurement."""
    # Import inside function to ensure coverage can track
    from giljo_mcp.config_manager import ConfigManager, DeploymentMode
    
    print("Testing basic ConfigManager functionality...")
    
    # Test initialization
    config = ConfigManager()
    
    # Test basic properties
    assert config.server.mode == DeploymentMode.LOCAL
    assert config.server.debug is False
    assert config.server.mcp_host == "127.0.0.1"
    assert config.server.mcp_port == 6001
    assert config.database.type == "sqlite"
    
    print("[OK] \1")
    
    # Test dataclass aliases
    config.database.database_type = "postgresql"
    assert config.database.type == "postgresql"
    print("[OK] \1")
    
    # Test connection string generation
    conn_str = config.database.get_connection_string()
    assert "postgresql://" in conn_str
    print("[OK] \1")
    
    # Test validation
    config.validate()
    print("[OK] \1")
    
    print("All basic tests passed!")

if __name__ == "__main__":
    test_basic_config()