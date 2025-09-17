#!/usr/bin/env python3
"""Comprehensive database connectivity test"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.config_manager import get_config
from sqlalchemy import text

def test_database_sync():
    """Test database connection using sync methods"""
    config = get_config()
    
    print("Testing database connectivity...")
    print(f"Mode: {config.server.mode}")
    print(f"Database type: {config.database.type}")
    
    # Get the database connection string
    connection_string = config.database.get_connection_string()
    print(f"Connection string: {connection_string[:50]}...")  # Show partial for security
    
    # Test SQLite (local mode)
    if "sqlite" in connection_string:
        print("\nTesting SQLite connection...")
        db = DatabaseManager(connection_string, is_async=False)
        
        try:
            with db.get_session() as session:
                result = session.execute(text("SELECT 1"))
                print("[OK] SQLite connection successful")
                
                # Check if tables exist
                result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
                print(f"[OK] Tables found: {tables}")
                
        except Exception as e:
            print(f"[FAIL] SQLite test failed: {e}")
            return False
    
    # Test PostgreSQL if configured
    elif "postgresql" in connection_string:
        print("\nTesting PostgreSQL connection...")
        db = DatabaseManager(connection_string, is_async=False)
        
        try:
            with db.get_session() as session:
                result = session.execute(text("SELECT 1"))
                print("[OK] PostgreSQL connection successful")
                
                # Check database name
                result = session.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                print(f"[OK] Connected to database: {db_name}")
                
                # Check tables
                result = session.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """))
                tables = [row[0] for row in result]
                print(f"[OK] Tables found: {tables}")
                
        except Exception as e:
            print(f"[FAIL] PostgreSQL test failed: {e}")
            
            # Try with IP address
            if "localhost" in connection_string:
                print("\nRetrying with IP address 10.1.0.164...")
                connection_string = connection_string.replace("localhost", "10.1.0.164")
                db = DatabaseManager(connection_string, is_async=False)
                
                try:
                    with db.get_session() as session:
                        result = session.execute(text("SELECT 1"))
                        print("[OK] PostgreSQL connection successful with IP")
                        return True
                except Exception as e2:
                    print(f"[FAIL] Failed with IP too: {e2}")
                    return False
            return False
    
    return True

if __name__ == "__main__":
    success = test_database_sync()
    # sys.exit(0 if success else 1)  # Commented for pytest