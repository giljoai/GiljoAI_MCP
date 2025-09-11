#!/usr/bin/env python3
"""Test async database operations and connection pooling"""

import asyncio
import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.config_manager import get_config
from sqlalchemy import text

async def test_async_operations():
    """Test async database operations with concurrent queries"""
    config = get_config()
    connection_string = config.database.get_connection_string()
    
    print("Testing Async PostgreSQL Operations")
    print("=" * 40)
    
    # Test with async mode
    db = DatabaseManager(connection_string, is_async=True)
    
    try:
        # Test single async query
        print("\n1. Testing single async query...")
        async with db.get_session_async() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"[OK] Connected to: {version[:50]}...")
        
        # Test concurrent queries (connection pooling)
        print("\n2. Testing concurrent queries (connection pooling)...")
        
        async def run_query(query_id):
            """Run a query with ID for tracking"""
            async with db.get_session_async() as session:
                # Simulate some work
                result = await session.execute(
                    text(f"SELECT :id as query_id, pg_sleep(0.1)")
                    .bindparams(id=query_id)
                )
                return f"Query {query_id} completed"
        
        # Run 5 concurrent queries
        start_time = time.time()
        tasks = [run_query(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"[OK] Ran 5 concurrent queries in {end_time - start_time:.2f} seconds")
        print(f"     (Should be ~0.1s with pooling, not 0.5s sequential)")
        
        # Test transaction handling
        print("\n3. Testing async transaction handling...")
        async with db.get_session_async() as session:
            async with session.begin():
                # Create a temp table
                await session.execute(text("""
                    CREATE TEMP TABLE IF NOT EXISTS test_async (
                        id SERIAL PRIMARY KEY,
                        data TEXT
                    )
                """))
                
                # Insert data
                await session.execute(text("""
                    INSERT INTO test_async (data) VALUES ('test1'), ('test2')
                """))
                
                # Query data
                result = await session.execute(text("SELECT COUNT(*) FROM test_async"))
                count = result.scalar()
                print(f"[OK] Transaction completed, inserted {count} rows")
        
        print("\n[SUCCESS] All async PostgreSQL tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Async test failed: {e}")
        return False

async def test_both_modes():
    """Test both SQLite and PostgreSQL modes"""
    print("\n\nTesting Database Mode Switching")
    print("=" * 40)
    
    config = get_config()
    
    # Test with current configured mode
    current_mode = config.database.type
    print(f"\nCurrent database type: {current_mode}")
    
    connection_string = config.database.get_connection_string()
    
    if "sqlite" in connection_string:
        print("\n[INFO] SQLite mode detected (sync only)")
        db = DatabaseManager(connection_string, is_async=False)
        
        # Test sync SQLite
        with db.get_session() as session:
            result = session.execute(text("SELECT sqlite_version()"))
            version = result.scalar()
            print(f"[OK] SQLite version: {version}")
    else:
        print("\n[INFO] PostgreSQL mode detected (async capable)")
        # Already tested above
        print("[OK] PostgreSQL async mode working")
    
    return True

async def main():
    """Run all async tests"""
    
    # Test async operations
    success1 = await test_async_operations()
    
    # Test mode switching
    success2 = await test_both_modes()
    
    return success1 and success2

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)