"""
Test the production database safety mechanism.

This test verifies that the safety guards are working correctly.
Run this test to confirm your test environment is properly protected.
"""

import os
import pytest
from tests.helpers.test_db_helper import (
    validate_database_name,
    validate_connection_string,
    PRODUCTION_DB_NAME,
    TEST_DB_SUFFIX,
)


class TestDatabaseSafetyMechanism:
    """Test that safety guards prevent production database access."""

    def test_validate_database_name_blocks_production(self):
        """
        CRITICAL: Verify that validate_database_name() raises RuntimeError
        when given the production database name.
        """
        with pytest.raises(RuntimeError, match="SAFETY GUARD TRIGGERED"):
            validate_database_name("giljo_mcp")

    def test_validate_database_name_allows_test_db(self):
        """Verify that test database name is allowed."""
        # Should not raise
        validate_database_name("giljo_mcp_test")

    def test_validate_database_name_allows_other_test_dbs(self):
        """Verify that other test databases are allowed."""
        # These should not raise
        validate_database_name("my_app_test")
        validate_database_name("test_database")
        validate_database_name("giljo_mcp_test_isolated")

    def test_validate_connection_string_blocks_production_url(self):
        """Verify that connection strings to production are blocked."""
        production_urls = [
            "postgresql://localhost/giljo_mcp",
            "postgresql://user:pass@localhost:5432/giljo_mcp",
            "postgresql+asyncpg://postgres:***@localhost/giljo_mcp",
        ]
        for url in production_urls:
            with pytest.raises(RuntimeError, match="SAFETY GUARD TRIGGERED"):
                validate_connection_string(url)

    def test_validate_connection_string_allows_test_url(self):
        """Verify that test database URLs are allowed."""
        test_urls = [
            "postgresql://localhost/giljo_mcp_test",
            "postgresql://user:pass@localhost:5432/giljo_mcp_test",
            "postgresql+asyncpg://postgres:***@localhost/giljo_mcp_test",
        ]
        for url in test_urls:
            # Should not raise
            validate_connection_string(url)

    def test_constants_are_correct(self):
        """Verify safety constants are set correctly."""
        assert PRODUCTION_DB_NAME == "giljo_mcp"
        assert TEST_DB_SUFFIX == "_test"

    def test_environment_not_pointing_to_production(self):
        """
        Verify that current environment is not pointing to production.

        This test will FAIL if DATABASE_URL is set to production,
        which is the desired behavior - it catches misconfigurations.
        """
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            # If DATABASE_URL is set, it must contain _test
            assert "_test" in db_url or "giljo_mcp" not in db_url, (
                f"DATABASE_URL appears to point to production!\n"
                f"Current value: {db_url}\n"
                f"This is dangerous - unset it or change to test database."
            )


class TestSafetyMechanismDocumentation:
    """Document what the safety mechanism does."""

    def test_safety_banner_is_shown(self):
        """
        The pytest plugin shows a banner at startup:

        ╔══════════════════════════════════════════════════════════════════╗
        ║  ✓ DATABASE SAFETY CHECK PASSED                                  ║
        ║    Environment appears safe for testing                          ║
        ║    Target database: giljo_mcp_test                               ║
        ╚══════════════════════════════════════════════════════════════════╝

        If it detects production database, tests ABORT with:

        ╔══════════════════════════════════════════════════════════════════╗
        ║  ✗ DATABASE SAFETY CHECK FAILED - TESTS ABORTED                 ║
        ╠══════════════════════════════════════════════════════════════════╣
        ║  DANGER: Tests could potentially modify production database!     ║
        ╚══════════════════════════════════════════════════════════════════╝
        """
        # This test just documents the behavior
        assert True

    def test_how_to_bypass_if_needed(self):
        """
        If you REALLY need to bypass the safety check (not recommended):

        Option 1: Environment variable
            export GILJO_TEST_SAFE=1
            pytest tests/

        Option 2: Command line flag
            pytest --skip-db-safety-check tests/

        WARNING: Only do this if you understand the risks!
        """
        assert True
