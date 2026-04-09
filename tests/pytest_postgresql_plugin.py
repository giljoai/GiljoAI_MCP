# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Pytest plugin for PostgreSQL test database management.

Provides command-line options for managing the test database.

CRITICAL SAFETY: This plugin includes a HARD BLOCK that prevents tests
from running if they could potentially hit the production database.
Tests will ABORT before collection if the environment is unsafe.
"""

import asyncio
import os
import sys

import pytest

# =============================================================================
# PRODUCTION DATABASE SAFETY CONSTANTS
# =============================================================================
PRODUCTION_DB_NAME = "giljo_mcp"
TEST_DB_NAME = "giljo_mcp_test"
SAFETY_ENV_VAR = "GILJO_TEST_SAFE"


class ProductionDatabaseProtectionError(Exception):
    """Raised when tests might accidentally hit production database."""


def _check_database_safety() -> tuple[bool, str]:
    """
    Check if the test environment is safe (not pointing to production).

    Returns:
        tuple: (is_safe: bool, message: str)
    """
    # Check 1: Is safety bypass explicitly enabled?
    if os.environ.get(SAFETY_ENV_VAR) == "1":
        return True, "Safety bypass enabled via GILJO_TEST_SAFE=1"

    # Check 2: Is DATABASE_URL set and pointing to production?
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        # Check if it contains production DB name without _test
        if f"/{PRODUCTION_DB_NAME}" in db_url and f"/{TEST_DB_NAME}" not in db_url:
            return False, (
                f"DATABASE_URL points to production database!\n"
                f"  Found: {db_url[:60]}...\n"
                f"  Expected: URL containing '{TEST_DB_NAME}'\n\n"
                f"To fix:\n"
                f"  1. Unset DATABASE_URL: unset DATABASE_URL\n"
                f"  2. Or set it to test DB: export DATABASE_URL=postgresql://.../{TEST_DB_NAME}\n"
                f"  3. Or bypass (DANGEROUS): export {SAFETY_ENV_VAR}=1"
            )

    # Check 3: Verify test helper defaults are correct
    try:
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        default_db = PostgreSQLTestHelper.DEFAULT_CONFIG.get("database", "")
        if default_db != TEST_DB_NAME:
            return False, (
                f"Test helper default database is not '{TEST_DB_NAME}'!\n"
                f"  Found: {default_db}\n"
                f"  This is a code bug - fix test_db_helper.py"
            )
    except ImportError:
        # If we can't import the helper, that's a different problem
        pass

    return True, "Environment appears safe for testing"


def _print_safety_banner(is_safe: bool, message: str):
    """Print a visible safety status banner."""
    if is_safe:
        banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║  ✓ DATABASE SAFETY CHECK PASSED                                  ║
║    {message:<60} ║
║    Target database: {TEST_DB_NAME:<43} ║
╚══════════════════════════════════════════════════════════════════╝
"""
    else:
        banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║  ✗ DATABASE SAFETY CHECK FAILED - TESTS ABORTED                 ║
╠══════════════════════════════════════════════════════════════════╣
║  DANGER: Tests could potentially modify production database!     ║
║                                                                  ║
║  {message[:62]:<62} ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner, file=sys.stderr)


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
    parser.addoption(
        "--skip-db-safety-check",
        action="store_true",
        default=False,
        help="Skip database safety check (DANGEROUS - use only if you know what you're doing)",
    )


def pytest_configure(config):
    """
    Configure pytest with custom markers and SAFETY CHECKS.

    CRITICAL: This runs before any tests are collected.
    If the environment is unsafe, we abort the entire test session.
    """
    # Register markers
    config.addinivalue_line("markers", "postgresql: mark test as requiring PostgreSQL database")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "production_safe: mark test as verified safe from production DB access")

    # ==========================================================================
    # HARD SAFETY CHECK - ABORT IF ENVIRONMENT IS UNSAFE
    # ==========================================================================
    # Skip check if explicitly requested (for special cases)
    if config.getoption("--skip-db-safety-check", default=False):
        print("\n⚠️  WARNING: Database safety check SKIPPED (--skip-db-safety-check)\n", file=sys.stderr)
        return

    is_safe, message = _check_database_safety()
    _print_safety_banner(is_safe, message)

    if not is_safe:
        # ABORT THE TEST SESSION
        raise ProductionDatabaseProtectionError(
            f"\n\n"
            f"{'=' * 70}\n"
            f"TESTS ABORTED: Production database protection triggered!\n"
            f"{'=' * 70}\n\n"
            f"{message}\n\n"
            f"This is a safety feature to prevent accidental data loss.\n"
            f"{'=' * 70}\n"
        )


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
