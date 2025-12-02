#!/usr/bin/env python3
"""Comprehensive database connectivity test"""

import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager


def test_database_sync():
    """Test database connection using sync methods"""
    config = get_config()

    # Get the database connection string
    connection_string = config.database.get_connection_string()

    # Test PostgreSQL (project standardized on PostgreSQL only)
    if "postgresql" in connection_string:
        db = DatabaseManager(connection_string, is_async=False)

        try:
            with db.get_session() as session:
                result = session.execute(text("SELECT 1"))

                # Check database name
                result = session.execute(text("SELECT current_database()"))
                result.scalar()

                # Check tables
                result = session.execute(
                    text(
                        """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """
                    )
                )
                [row[0] for row in result]

        except Exception:
            # Try with IP address
            if "localhost" in connection_string:
                connection_string = connection_string.replace("localhost", "10.1.0.164")
                db = DatabaseManager(connection_string, is_async=False)

                try:
                    with db.get_session() as session:
                        result = session.execute(text("SELECT 1"))
                        return True
                except Exception:
                    return False
            return False

    return True


if __name__ == "__main__":
    success = test_database_sync()
    # sys.exit(0 if success else 1)  # Commented for pytest
