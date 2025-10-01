"""
Pytest plugin for PostgreSQL test database management.

Provides command-line options for managing the test database.
"""

import asyncio

import pytest


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--drop-test-db",
        action="store_true",
        default=False,
        help="Drop the test database after test run completes",
    )
    parser.addoption(
        "--create-test-db",
        action="store_true",
        default=False,
        help="Create the test database before running tests (happens automatically)",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "postgresql: mark test as requiring PostgreSQL database")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """
    Hook that runs after all tests are complete.

    If --drop-test-db flag is set, drops the test database.
    """
    if session.config.getoption("--drop-test-db"):
        print("\n\nDropping test database...")

        async def drop_db():
            from tests.helpers.test_db_helper import PostgreSQLTestHelper

            try:
                await PostgreSQLTestHelper.drop_test_database()
                print("Test database dropped successfully")
            except Exception as e:
                print(f"Error dropping test database: {e}")

        # Run the async drop operation
        asyncio.run(drop_db())


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test characteristics.
    """
    for item in items:
        # Add postgresql marker to all tests (since we only use PostgreSQL now)
        item.add_marker(pytest.mark.postgresql)

        # Mark tests with "slow" in their name as slow
        if "slow" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
