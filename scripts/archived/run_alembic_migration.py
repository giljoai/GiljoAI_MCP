#!/usr/bin/env python3
"""
Alembic Database Migration Runner for GiljoAI MCP Server

This script runs Alembic migrations for the GiljoAI MCP database.
It handles configuration setup and provides clear feedback during migration.

Usage:
    python run_alembic_migration.py upgrade     # Run all pending migrations
    python run_alembic_migration.py downgrade   # Rollback one migration
    python run_alembic_migration.py current     # Show current migration status
    python run_alembic_migration.py history     # Show migration history
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def setup_alembic_config():
    """
    Setup Alembic configuration programmatically.

    Returns:
        Config: Alembic configuration object
    """
    # Get project root directory
    project_root = Path(__file__).parent.absolute()

    # Create Alembic config
    alembic_cfg = Config()

    # Set script location (migrations directory)
    alembic_cfg.set_main_option("script_location", str(project_root / "migrations"))

    # Database URL will be loaded from .env by migrations/env.py
    print(f"Project root: {project_root}")
    print(f"Migrations directory: {project_root / 'migrations'}")

    return alembic_cfg


def run_migration(action: str):
    """
    Run database migration based on action.

    Args:
        action: Migration action (upgrade, downgrade, current, history)
    """
    try:
        # Setup Alembic config
        alembic_cfg = setup_alembic_config()

        print(f"\nRunning migration action: {action}")
        print("=" * 60)

        if action == "upgrade":
            # Run all pending migrations
            print("\nUpgrading database to latest revision...")
            command.upgrade(alembic_cfg, "head")
            print("\nMigration completed successfully!")

        elif action == "downgrade":
            # Rollback one migration
            print("\nRolling back one migration...")
            print("WARNING: This will undo the most recent migration!")
            confirm = input("Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                command.downgrade(alembic_cfg, "-1")
                print("\nRollback completed successfully!")
            else:
                print("\nRollback cancelled.")

        elif action == "current":
            # Show current migration status
            print("\nCurrent migration status:")
            command.current(alembic_cfg, verbose=True)

        elif action == "history":
            # Show migration history
            print("\nMigration history:")
            command.history(alembic_cfg, verbose=True)

        else:
            print(f"Unknown action: {action}")
            print_usage()
            sys.exit(1)

        print("=" * 60)

    except Exception as e:
        print("\nERROR: Migration failed!")
        print(f"Error details: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check .env file contains database credentials")
        print("3. Verify database connection: psql -U postgres -d giljo_mcp")
        sys.exit(1)


def print_usage():
    """Print usage instructions."""
    print("\nUsage:")
    print("  python run_alembic_migration.py upgrade     # Run all pending migrations")
    print("  python run_alembic_migration.py downgrade   # Rollback one migration")
    print("  python run_alembic_migration.py current     # Show current migration status")
    print("  python run_alembic_migration.py history     # Show migration history")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("ERROR: Invalid number of arguments")
        print_usage()
        sys.exit(1)

    action = sys.argv[1].lower()
    run_migration(action)


if __name__ == "__main__":
    main()
