#!/usr/bin/env python3
"""Test database connectivity"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.config_manager import get_config
from sqlalchemy import text

async def test_database():
    """Test database connection and basic operations"""
    config = get_config()
    # Get the database connection string from config
    connection_string = config.database.get_connection_string()
    db = DatabaseManager(connection_string, is_async=True)  # Enable async mode
    
    try:        
        # Test getting an async session
        async with db.get_session_async() as session:
            # Test a simple query
            result = await session.execute(text("SELECT 1"))
            print("Database query executed successfully")
        
        print("Database connection test passed")
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        # Try with IP if localhost fails
        if "localhost" in connection_string:
            print("Retrying with IP address 10.1.0.164...")
            connection_string = connection_string.replace("localhost", "10.1.0.164")
            db = DatabaseManager(connection_string, is_async=True)  # Enable async mode
            try:
                async with db.get_session_async() as session:
                    result = await session.execute(text("SELECT 1"))
                    print("Database connection successful with IP address")
                    return True
            except Exception as e2:
                print(f"Failed with IP too: {e2}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database())
    sys.exit(0 if success else 1)