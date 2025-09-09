#!/usr/bin/env python3
"""
Database initialization script for GiljoAI MCP.

Creates tables and runs migrations for both SQLite and PostgreSQL.
"""

import sys
import os
from pathlib import Path
import argparse
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from giljo_mcp.database import DatabaseManager, get_db_manager
from giljo_mcp.models import Base
from alembic.config import Config
from alembic import command


def init_database(
    database_url: Optional[str] = None,
    drop_existing: bool = False,
    run_migrations: bool = True
):
    """
    Initialize the database with tables and optionally run migrations.
    
    Args:
        database_url: Database URL. If None, uses default SQLite.
        drop_existing: Whether to drop existing tables first.
        run_migrations: Whether to run Alembic migrations.
    """
    print(f"Initializing database...")
    
    # Create database manager
    db_manager = get_db_manager(database_url)
    
    if database_url:
        print(f"Using database: {database_url}")
    else:
        print(f"Using default SQLite database: {db_manager.database_url}")
    
    try:
        # Drop tables if requested
        if drop_existing:
            print("Dropping existing tables...")
            db_manager.drop_tables()
            print("Tables dropped successfully.")
        
        # Create tables
        print("Creating tables...")
        db_manager.create_tables()
        print("Tables created successfully.")
        
        # Run migrations if requested
        if run_migrations:
            print("Running migrations...")
            alembic_cfg = Config(Path(__file__).parent.parent / "alembic.ini")
            
            # Set database URL for Alembic
            if database_url:
                alembic_cfg.set_main_option("sqlalchemy.url", database_url)
            else:
                alembic_cfg.set_main_option("sqlalchemy.url", db_manager.database_url)
            
            # Stamp database with current revision
            command.stamp(alembic_cfg, "head")
            print("Migrations completed successfully.")
        
        print("\nDatabase initialization complete!")
        
        # Print summary
        print("\nDatabase Summary:")
        print(f"  Type: {'SQLite' if db_manager.is_sqlite else 'PostgreSQL' if db_manager.is_postgresql else 'Other'}")
        print(f"  URL: {db_manager.database_url}")
        
        if db_manager.is_sqlite:
            db_path = db_manager.database_url.replace("sqlite:///", "")
            print(f"  File: {db_path}")
        
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        return False
    finally:
        db_manager.close()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Initialize GiljoAI MCP database")
    
    parser.add_argument(
        "--database-url",
        help="Database URL (e.g., sqlite:///path/to/db.db or postgresql://user:pass@host/db)",
        default=None
    )
    
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing tables before creating new ones"
    )
    
    parser.add_argument(
        "--no-migrations",
        action="store_true",
        help="Skip running Alembic migrations"
    )
    
    parser.add_argument(
        "--postgresql",
        action="store_true",
        help="Use PostgreSQL with default local settings"
    )
    
    args = parser.parse_args()
    
    # Build database URL if PostgreSQL flag is set
    database_url = args.database_url
    if args.postgresql and not database_url:
        database_url = DatabaseManager.build_postgresql_url(
            host="localhost",
            port=5432,
            database="giljo_mcp",
            username="postgres",
            password=os.getenv("DB_PASSWORD", "")
        )
    
    # Initialize database
    success = init_database(
        database_url=database_url,
        drop_existing=args.drop_existing,
        run_migrations=not args.no_migrations
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()