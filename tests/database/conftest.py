"""
Shared fixtures for database tests.
"""

import pytest
from sqlalchemy import create_engine

from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture
def db_engine():
    """Get synchronous database engine for inspection/migration tests"""
    # Create a synchronous engine for SQLAlchemy inspect() operations
    sync_url = PostgreSQLTestHelper.get_test_db_url().replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    yield engine
    engine.dispose()
