# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6014 — regression tests for the test-database safety validator.

The validator (``validate_database_name``) is a PRODUCTION-SAFETY guard: it is
the gate that prevents the test suite from ever connecting to / creating /
dropping a real database. BE-6014 loosened it to accept per-worker xdist
databases (``giljo_mcp_test_gwN``); the parallel-clone work widened it again to
accept NUMBERED bases (``giljo_mcp_test2``, ``giljo_test3_gwN``, ...) so
simultaneous dev clones on one Postgres don't collide. These tests pin that the
widening is EXACTLY ``^(giljo_mcp_test\\d*|giljo_test\\d*)(_gw\\d+)?$`` plus the
static allowlist — and nothing looser. Production names (``giljo_mcp``,
``giljo_mcp_saas``) and near-misses (``giljo_mcp_testx``) MUST still hard-fail.

Pure-function tests: no database connection required.
"""

import pytest

from tests.helpers.test_db_helper import (
    PostgreSQLTestHelper,
    validate_database_name,
)


# Names the validator MUST accept (test databases only).
ACCEPTED = [
    "giljo_mcp_test",  # canonical local/CI test DB
    "giljo_mcp_test_gw0",  # xdist worker 0
    "giljo_mcp_test_gw1",
    "giljo_mcp_test_gw15",  # double-digit worker index
    "giljo_test",  # CI alias (static allowlist)
    "postgres",  # admin DB for CREATE/DROP DATABASE
    # Parallel-clone numbered bases (simultaneous dev clones on one Postgres):
    "giljo_mcp_test2",  # clone CI2 base
    "giljo_mcp_test3",  # clone CI3 base
    "giljo_mcp_test2_gw0",  # numbered base + xdist worker
    "giljo_mcp_test4_gw11",
    "giljo_test2",  # CI-alias numbered variant
]

# Names the validator MUST reject — production, near-misses, and junk.
REJECTED = [
    "giljo_mcp",  # PRODUCTION
    "giljo_mcp_saas",  # PRODUCTION (SaaS)
    "giljo",
    "giljo_mcp_testx",  # suffix not matching _gwN
    "giljo_mcp_test_gw",  # _gw with no number
    "giljo_mcp_test_gwx",  # _gw with non-digit
    "giljo_mcp_test_extra",
    "production",
    "",
]


@pytest.mark.parametrize("name", ACCEPTED)
def test_validator_accepts_test_databases(name):
    # Must not raise.
    validate_database_name(name)


@pytest.mark.parametrize("name", REJECTED)
def test_validator_rejects_non_test_databases(name):
    with pytest.raises(RuntimeError):
        validate_database_name(name)


def test_validator_hard_rejects_production_by_name():
    """The two real production databases must never validate."""
    for prod in ("giljo_mcp", "giljo_mcp_saas"):
        with pytest.raises(RuntimeError):
            validate_database_name(prod)


def test_resolve_test_db_name_plain_run(monkeypatch):
    """Without an xdist worker, the bare canonical name is used."""
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert PostgreSQLTestHelper.resolve_test_db_name() == "giljo_mcp_test"


@pytest.mark.parametrize(
    ("worker", "expected"),
    [
        ("gw0", "giljo_mcp_test_gw0"),
        ("gw7", "giljo_mcp_test_gw7"),
        ("gw13", "giljo_mcp_test_gw13"),
    ],
)
def test_resolve_test_db_name_per_worker(monkeypatch, worker, expected):
    """Under xdist the worker id is appended — and the result still validates."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PYTEST_XDIST_WORKER", worker)
    resolved = PostgreSQLTestHelper.resolve_test_db_name()
    assert resolved == expected
    validate_database_name(resolved)  # the resolved name must always be allowed


def test_resolve_ignores_non_worker_token(monkeypatch):
    """A non-``gwN`` value (e.g. xdist controller 'master') yields the bare name."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "master")
    assert PostgreSQLTestHelper.resolve_test_db_name() == "giljo_mcp_test"


def test_get_test_db_url_rejects_production():
    """The URL builder must refuse an explicit production database name."""
    with pytest.raises(RuntimeError):
        PostgreSQLTestHelper.get_test_db_url(database="giljo_mcp")
