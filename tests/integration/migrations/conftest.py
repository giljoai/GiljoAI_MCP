# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [SAAS] SaaS Edition.

"""
Local conftest for migration-bootstrap tests.

These tests run alembic against a separate scratch DB and do NOT need the
parent ``tests/integration/conftest.py`` autouse fixtures (test_user,
set_tenant_context) which would force a connection to ``giljo_mcp_test``
and require the schema to be present there. We override those fixtures
here as harmless no-ops so the parent autouse fires but does nothing.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def test_user():
    """Override parent's test_user fixture -- bootstrap tests don't need it."""
    return None


@pytest.fixture(autouse=True)
def set_tenant_context():
    """Override parent's autouse tenant-context fixture with a no-op."""
    return None
