# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for TSK-9116: PostgreSQL version floor 14 -> 16.

installer/shared/postgres.py declared MIN_VERSION=14 (bare honest minimum for
NULLS NOT DISTINCT, which is PG15+) while the CI-enforced, continuously-tested
floor is PG16 (postgres:16 container). A PG14 customer passed the prereq
check, then died mid-migration -- the dishonest-late-failure pattern.

Covers both version-floor constants:
  * installer.shared.postgres.PostgreSQLDiscovery.MIN_VERSION == 16, and its
    validate_version() boundary (15 rejected, 16 accepted).
  * installer.core.database.DatabaseInstaller.MIN_PG_VERSION == 16 (the
    constant setup() checks against during a live install).
"""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def test_postgresql_discovery_min_version_is_16() -> None:
    from installer.shared.postgres import PostgreSQLDiscovery

    assert PostgreSQLDiscovery.MIN_VERSION == 16


def test_database_installer_min_pg_version_is_16() -> None:
    import installer.core.database as db_mod

    assert db_mod.DatabaseInstaller.MIN_PG_VERSION == 16


def test_validate_version_rejects_pg15() -> None:
    from installer.shared.postgres import PostgreSQLDiscovery

    result = PostgreSQLDiscovery().validate_version(15)
    assert result["compatible"] is False
    assert result["severity"] == "error"
    assert "16" in result["message"]


def test_validate_version_accepts_pg16() -> None:
    from installer.shared.postgres import PostgreSQLDiscovery

    result = PostgreSQLDiscovery().validate_version(16)
    assert result["compatible"] is True
    assert result["severity"] == "warning"  # below RECOMMENDED_VERSION (18)


def test_validate_version_recommends_pg18() -> None:
    from installer.shared.postgres import PostgreSQLDiscovery

    result = PostgreSQLDiscovery().validate_version(18)
    assert result["compatible"] is True
    assert result["severity"] == "ok"
