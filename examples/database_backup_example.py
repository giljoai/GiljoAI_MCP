"""
Database Backup Example Script

This script demonstrates how to use the DatabaseBackupUtility module
to create backups of the GiljoAI MCP PostgreSQL database.

Usage:
    python examples/database_backup_example.py

Requirements:
    - PostgreSQL installed and in system PATH (or provide custom path)
    - Database running and accessible
    - Sufficient disk space (500+ MB recommended)
    - PostgreSQL superuser credentials (default password: 4010)
"""

import logging
import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database_backup import (
    BackupExecutionError,
    DatabaseBackupError,
    DatabaseBackupUtility,
    DatabaseConnectionError,
    PgDumpNotFoundError,
    create_database_backup,
)


def setup_logging():
    """Configure logging for the script."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def example_basic_backup():
    """
    Example 1: Create a basic backup using default configuration.

    This will:
    - Load config from .env or config.yaml
    - Create backup in docs/archive/database_backups/YYYY-MM-DD_HH-MM-SS/
    - Generate metadata file with schema information
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Backup")
    print("=" * 70)

    try:
        # Simple one-line backup
        result = create_database_backup()

        print("\nBackup completed successfully!")
        print(f"  Backup directory: {result['backup_dir']}")
        print(f"  Backup file: {result['backup_file']}")
        print(f"  Metadata file: {result['metadata_file']}")
        print(f"  Execution time: {result['execution_time']:.2f} seconds")
        print(f"  Backup size: {result['backup_size'] / 1024:.1f} KB")
        print("\nDatabase statistics:")
        print(f"  Tables: {result['total_tables']}")
        print(f"  Total rows: {result['total_rows']:,}")

        return True

    except PgDumpNotFoundError as e:
        print("\nError: PostgreSQL not found")
        print(f"  {e}")
        print("\nSolution:")
        print("  1. Add PostgreSQL bin directory to system PATH, or")
        print("  2. Provide custom PostgreSQL path (see Example 2)")
        return False

    except DatabaseConnectionError as e:
        print("\nError: Could not connect to database")
        print(f"  {e}")
        print("\nSolution:")
        print("  1. Ensure PostgreSQL server is running")
        print("  2. Verify database credentials in .env or config.yaml")
        print("  3. Check database name and port are correct")
        return False

    except BackupExecutionError as e:
        print("\nError: Backup execution failed")
        print(f"  {e}")
        return False

    except DatabaseBackupError as e:
        print(f"\nError: {e}")
        return False


def example_custom_config():
    """
    Example 2: Create backup with custom configuration.

    Demonstrates:
    - Custom database credentials
    - Custom backup directory
    - Manual utility instantiation
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Custom Configuration")
    print("=" * 70)

    # Custom database configuration
    custom_config = {
        "host": "localhost",
        "port": "5432",
        "database": "giljo_mcp",
        "user": "postgres",
        "password": "4010",  # Superuser password for full backup
    }

    # Custom backup directory
    custom_backup_dir = Path.cwd() / "backups" / "manual"

    print("Using custom configuration:")
    print(f"  Database: {custom_config['database']}")
    print(f"  Host: {custom_config['host']}:{custom_config['port']}")
    print(f"  User: {custom_config['user']}")
    print(f"  Backup directory: {custom_backup_dir}")

    try:
        # Create utility with custom settings
        utility = DatabaseBackupUtility(db_config=custom_config, backup_base_dir=custom_backup_dir)

        # Perform backup
        result = utility.create_backup(include_metadata=True)

        print(f"\nBackup created: {result['backup_dir']}")
        return True

    except DatabaseBackupError as e:
        print(f"\nError: {e}")
        return False


def example_backup_without_metadata():
    """
    Example 3: Quick backup without metadata generation.

    Useful for:
    - Fast backups
    - When metadata is not needed
    - Automated backup scripts where speed is critical
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Quick Backup (No Metadata)")
    print("=" * 70)

    try:
        # Fast backup without metadata
        result = create_database_backup(include_metadata=False)

        print("\nQuick backup completed!")
        print(f"  Backup file: {result['backup_file']}")
        print(f"  Execution time: {result['execution_time']:.2f} seconds")

        return True

    except DatabaseBackupError as e:
        print(f"\nError: {e}")
        return False


def example_error_handling():
    """
    Example 4: Comprehensive error handling.

    Demonstrates handling different error types.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Error Handling")
    print("=" * 70)

    try:
        result = create_database_backup()
        print(f"Backup successful: {result['backup_dir']}")
        return True

    except PgDumpNotFoundError:
        print("PostgreSQL tools not found - install PostgreSQL or add to PATH")
        return False

    except DatabaseConnectionError:
        print("Cannot connect to database - check if server is running")
        return False

    except BackupExecutionError:
        print("Backup process failed - check logs for details")
        return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def example_inspect_backup():
    """
    Example 5: Inspect an existing backup's metadata.

    Shows how to read backup metadata without creating a new backup.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Inspect Backup Metadata")
    print("=" * 70)

    backup_base = Path.cwd() / "docs" / "archive" / "database_backups"

    if not backup_base.exists():
        print(f"No backups found at: {backup_base}")
        return False

    # Find most recent backup
    backups = sorted(backup_base.iterdir(), reverse=True)
    if not backups:
        print("No backup directories found")
        return False

    latest_backup = backups[0]
    metadata_file = latest_backup / "backup_metadata.md"

    print(f"Latest backup: {latest_backup.name}")

    if metadata_file.exists():
        print("\nMetadata preview:")
        with open(metadata_file, encoding="utf-8") as f:
            lines = f.readlines()[:20]  # First 20 lines
            print("".join(lines))
            if len(lines) >= 20:
                print("... (truncated)")
        return True
    print("No metadata file found")
    return False


def main():
    """Run example demonstrations."""
    setup_logging()

    print("=" * 70)
    print("DATABASE BACKUP UTILITY - USAGE EXAMPLES")
    print("=" * 70)
    print("\nThis script demonstrates various ways to use the backup utility.")
    print("Choose which examples to run:\n")

    examples = [
        ("Basic backup (recommended for first time)", example_basic_backup),
        ("Custom configuration", example_custom_config),
        ("Quick backup without metadata", example_backup_without_metadata),
        ("Error handling patterns", example_error_handling),
        ("Inspect existing backup", example_inspect_backup),
    ]

    print("Available examples:")
    for i, (desc, _) in enumerate(examples, 1):
        print(f"  {i}. {desc}")
    print("  0. Run all examples")

    try:
        choice = input("\nEnter choice (0-5): ").strip()

        if choice == "0":
            # Run all examples
            for desc, func in examples:
                func()
                input("\nPress Enter to continue...")
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            # Run selected example
            desc, func = examples[int(choice) - 1]
            func()
        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    main()
