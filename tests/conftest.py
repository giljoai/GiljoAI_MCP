# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Pytest configuration for test suite
Provides test fixtures and database setup
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio


# Add src to path
# TODO: Remove after editable install confirmed on all platforms
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env first so POSTGRES_SUPERUSER_PASSWORD reaches PostgreSQLTestHelper
# without requiring manual `export $(... .env | xargs)` before invoking pytest.
# load_dotenv is a no-op if .env is missing (CI sets env via secrets instead).
try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

# Ensure config validation passes without real secrets
os.environ.setdefault("DB_PASSWORD", "test-password")
os.environ.setdefault("JWT_SECRET", "test_secret_key")

# --------------------------------------------------------------------------
# INF-5012b Part 3: Pin DATABASE_URL to test credentials BEFORE any
# application module (api.app, api.endpoints.*, src.giljo_mcp.auth.*) is
# imported by a test. Those modules call load_dotenv() without override,
# which silently injects the production DATABASE_URL (giljo_user@giljo_mcp)
# mid-run. The first use survives because db_manager() resolved the URL
# before that import; on the second function-scoped db_manager fixture
# the production URL wins, and PostgreSQLTestHelper._config_from_env()
# reuses giljo_user — which has no privileges on postgres-owned test
# tables. Result: every test after the first fails with
#   permission denied for table organizations
# and a trailing SAWarning: transaction already deassociated from
# connection.
#
# Setting DATABASE_URL here (before app imports) makes the later
# load_dotenv(override=False) calls no-ops, so the test database URL
# sticks for the entire session.
#
# IMPORTANT: If the existing DATABASE_URL points to a NON-test database
# (typically because .env injected the production URL giljo_user@giljo_mcp),
# we must POP it before constructing a test URL. PostgreSQLTestHelper
# ._config_from_env() reads DATABASE_URL when present and reuses its
# credentials (just swapping the database name). Reusing giljo_user's
# credentials against the postgres-owned test tables yields
#   permission denied for table organizations
# Unsetting forces the helper to fall through to DEFAULT_CONFIG, which
# correctly uses the postgres superuser + POSTGRES_SUPERUSER_PASSWORD.
#
# CI sets DATABASE_URL to its own test URL (e.g. giljo_test@giljo_test)
# with credentials that DO own the test tables in the CI Postgres service.
# That URL must be honored as-is, NOT replaced with a DEFAULT_CONFIG that
# expects a 'postgres' user CI doesn't have.
# --------------------------------------------------------------------------
_existing_db_url = os.environ.get("DATABASE_URL", "")


def _existing_url_targets_test_db(url: str) -> bool:
    """True if URL's database name is a recognized test database."""
    if not url:
        return False
    db_part = url.rsplit("/", 1)[-1].split("?")[0]
    return db_part in ("giljo_mcp_test", "giljo_test", "postgres")


if not _existing_url_targets_test_db(_existing_db_url):
    os.environ.pop("DATABASE_URL", None)
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

    os.environ["DATABASE_URL"] = PostgreSQLTestHelper.get_test_db_url()


# Import Product model for test_product fixture
from giljo_mcp.models import Product  # noqa: E402 -- must follow DATABASE_URL setup above
from giljo_mcp.services.project_service import ProjectService  # noqa: E402
from giljo_mcp.tenant import TenantManager  # noqa: E402

# Import PostgreSQL test fixtures from base_fixtures
from tests.fixtures.base_fixtures import (  # noqa: E402
    db_manager,
    db_session,
    test_project,
)


# Import pytest plugin for PostgreSQL database management
pytest_plugins = ["tests.pytest_postgresql_plugin"]

# Re-export fixtures so they're available to all tests
__all__ = [
    "db_manager",
    "db_session",
    "test_project",
]


@pytest.fixture(scope="function")
def event_loop():
    """
    Create event loop for async tests.

    Note: Using function scope to avoid event loop closed issues.
    Each test gets a fresh event loop for proper async isolation.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    # Cleanup pending tasks before closing
    with contextlib.suppress(Exception):
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_agent_coordination(db_manager, db_session):
    """
    Auto-setup fixture to inject db_manager and session into agent_coordination module.

    This allows spawn_agent() to work in tests with proper
    session isolation (Handover 0366c).
    """
    from giljo_mcp.tools import agent_coordination

    agent_coordination.init_for_testing(db_manager, db_session)
    yield


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_context_module(db_manager):
    """
    Auto-setup fixture to inject db_manager into context module.

    This allows fetch_context() and other context tools to work in tests
    by setting the global _db_manager (Handover 0366c).
    Note: update_context_usage() was removed in Handover 0422 (dead token budget cleanup).
    """
    import giljo_mcp.database as db_module

    db_module.set_db_manager(db_manager)
    yield


# Note: db_session fixture is imported from base_fixtures.py
# and provides transaction-based test isolation


@pytest_asyncio.fixture(scope="function")
async def tenant_manager() -> TenantManager:
    """Create tenant manager for testing"""
    return TenantManager()


@pytest_asyncio.fixture(scope="function")
async def project_service_with_session(db_session, db_manager, tenant_manager, test_tenant_key):
    """ProjectService using shared test session for E2E/integration tests."""
    # Set the tenant context for the service
    tenant_manager.set_current_tenant(test_tenant_key)
    return ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


# Note: db_manager fixture is imported from base_fixtures.py above


@pytest_asyncio.fixture(scope="function")
async def test_tenant_key():
    """Generate a test tenant key"""
    from giljo_mcp.tenant import TenantManager

    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def test_project_id(db_session, test_tenant_key):
    """Create a test project and return its ID"""
    import random
    import uuid

    from giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        description="Test project description for integration testing",
        mission="Test mission for integration testing",
        status="active",
        tenant_key=test_tenant_key,
        series_number=random.randint(1, 999999),
    )

    db_session.add(project)
    await db_session.commit()

    return project.id


@pytest_asyncio.fixture(scope="function")
async def test_product(db_session, test_tenant_key):
    """Create a test product for testing."""
    import uuid

    product = Product(
        id=str(uuid.uuid4()),
        name="Test Product",
        description="Test product for repository testing",
        tenant_key=test_tenant_key,
        is_active=True,
        product_memory={},
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(
        product,
        attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
    )

    return product


def pytest_configure(config):
    """
    Pytest hook to configure test session.

    Registers custom markers and disables coverage threshold enforcement
    for smoke tests, since they are integration workflow validators
    (not unit coverage targets).

    CRITICAL SAFETY: Also validates that tests cannot access production database.
    """
    # ==========================================================================
    # PRODUCTION DATABASE SAFETY GUARD
    # ==========================================================================
    # Verify environment is set up for testing, not production
    import os

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url and "/giljo_mcp" in db_url and "/giljo_mcp_test" not in db_url:
        import warnings

        warnings.warn(
            f"WARNING: DATABASE_URL appears to point to production database!\n"
            f"Tests should use giljo_mcp_test, not giljo_mcp.\n"
            f"Current DATABASE_URL: {db_url[:50]}...",
            UserWarning,
        )

    # Register custom markers
    config.addinivalue_line(
        "markers", "tenant_isolation: marks tests for tenant isolation verification (Handover 0325)"
    )
    config.addinivalue_line(
        "markers", "production_safe: marks tests that have been verified safe from production DB access"
    )

    # Check if we're only running smoke tests
    selected_tests = config.getoption("file_or_dir", default=[])
    markers = config.getoption("-m", default="")

    # If running smoke tests specifically, disable fail_under threshold
    if "smoke" in markers or any("smoke" in str(test) for test in selected_tests):
        # Store original fail_under value
        if hasattr(config, "_coverage_config"):
            # Access coverage plugin configuration
            try:
                cov_plugin = config.pluginmanager.get_plugin("_cov")
                if cov_plugin and hasattr(cov_plugin, "cov_controller"):
                    # Disable fail_under for smoke tests
                    cov_config = cov_plugin.cov_controller.cov.config
                    if hasattr(cov_config, "fail_under"):
                        cov_config.fail_under = None
            except (AttributeError, KeyError):
                # Coverage plugin not loaded or configured differently
                pass
