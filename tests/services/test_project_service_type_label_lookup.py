# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Integration tests for ProjectService.get_project_type_by_label() (Handover 0837b).

Verifies case-insensitive lookup of TaxonomyType by label within a tenant.
"""

from uuid import uuid4

import pytest

from giljo_mcp.models.projects import TaxonomyType
from giljo_mcp.services.project_service import ProjectService


@pytest.fixture
async def project_service(project_service_with_session):
    return project_service_with_session


class TestGetTaxonomyTypeByLabel:
    """Test case-insensitive TaxonomyType label lookup."""

    @pytest.mark.asyncio
    async def test_exact_match(self, project_service: ProjectService, test_tenant_key: str, db_session):
        """Exact label match returns the TaxonomyType."""
        pt = TaxonomyType(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            label="Frontend",
            abbreviation="FE",
        )
        db_session.add(pt)
        await db_session.commit()

        result = await project_service.get_project_type_by_label("Frontend", test_tenant_key)
        assert result is not None
        assert result.id == pt.id
        assert result.label == "Frontend"

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self, project_service: ProjectService, test_tenant_key: str, db_session):
        """Lowercase input matches capitalized label."""
        pt = TaxonomyType(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            label="Backend",
            abbreviation="BE",
        )
        db_session.add(pt)
        await db_session.commit()

        result = await project_service.get_project_type_by_label("backend", test_tenant_key)
        assert result is not None
        assert result.id == pt.id

    @pytest.mark.asyncio
    async def test_uppercase_input_matches(self, project_service: ProjectService, test_tenant_key: str, db_session):
        """All-caps input matches mixed-case label."""
        pt = TaxonomyType(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            label="DevOps",
            abbreviation="DO",
        )
        db_session.add(pt)
        await db_session.commit()

        result = await project_service.get_project_type_by_label("DEVOPS", test_tenant_key)
        assert result is not None
        assert result.id == pt.id

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, project_service: ProjectService, test_tenant_key: str):
        """Non-existent label returns None (no error)."""
        result = await project_service.get_project_type_by_label("NonExistent", test_tenant_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, project_service: ProjectService, test_tenant_key: str, db_session):
        """Another tenant's row is never returned.

        INF-6174d: the resolve path now seeds the tenant's own defaults first,
        so a fresh tenant legitimately resolves "Frontend" — to ITS OWN seeded
        row. The isolation property under test is that the OTHER tenant's row
        is not the one returned.
        """
        other_tenant = f"tk_{uuid4().hex}"
        pt = TaxonomyType(
            id=str(uuid4()),
            tenant_key=other_tenant,
            label="Frontend",
            abbreviation="FE",
        )
        db_session.add(pt)
        await db_session.commit()

        result = await project_service.get_project_type_by_label("Frontend", test_tenant_key)
        assert result is not None, "own-tenant defaults are seeded on resolve (INF-6174d)"
        assert result.id != pt.id
        assert result.tenant_key == test_tenant_key
