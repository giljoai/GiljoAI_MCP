# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for ProjectService auto-assign series_number (Handover 0837a).

Verifies that create_project auto-assigns series_number when not provided,
preventing uq_project_taxonomy constraint violations for MCP callers.
"""

import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.project_service import ProjectService


@pytest.fixture
async def project_service(project_service_with_session):
    """Alias for project_service_with_session"""
    return project_service_with_session


class TestAutoAssignSeriesNumber:
    """Test auto-assignment of series_number when not provided."""

    @pytest.mark.asyncio
    async def test_create_project_without_taxonomy_assigns_series_1(
        self, project_service: ProjectService, test_tenant_key: str
    ):
        """First project without taxonomy gets series_number=1."""
        project = await project_service.create_project(
            name="Project Alpha",
            mission="Test mission",
            tenant_key=test_tenant_key,
        )
        assert project.series_number == 1

    @pytest.mark.asyncio
    async def test_create_two_projects_without_taxonomy_unique_series(
        self, project_service: ProjectService, test_tenant_key: str
    ):
        """Two projects without taxonomy get sequential series numbers."""
        p1 = await project_service.create_project(
            name="Project One",
            mission="Mission one",
            tenant_key=test_tenant_key,
        )
        p2 = await project_service.create_project(
            name="Project Two",
            mission="Mission two",
            tenant_key=test_tenant_key,
        )
        assert p1.series_number == 1
        assert p2.series_number == 2

    @pytest.mark.asyncio
    async def test_create_many_projects_without_taxonomy(
        self, project_service: ProjectService, test_tenant_key: str
    ):
        """Can create 5+ projects without taxonomy — no constraint violation."""
        projects = []
        for i in range(5):
            p = await project_service.create_project(
                name=f"Project {i}",
                mission=f"Mission {i}",
                tenant_key=test_tenant_key,
            )
            projects.append(p)

        series_numbers = [p.series_number for p in projects]
        assert series_numbers == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_explicit_taxonomy_still_works(
        self, project_service: ProjectService, test_tenant_key: str
    ):
        """Explicit series_number is preserved (no auto-assign)."""
        project = await project_service.create_project(
            name="Explicit Project",
            mission="Test mission",
            series_number=42,
            tenant_key=test_tenant_key,
        )
        assert project.series_number == 42

    @pytest.mark.asyncio
    async def test_auto_series_different_types_independent(
        self, project_service: ProjectService, test_tenant_key: str, db_session
    ):
        """Auto-series counts independently per project_type_id."""
        from src.giljo_mcp.models.projects import ProjectType

        # Create two project types
        pt1 = ProjectType(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            label="Frontend",
            abbreviation="FE",
        )
        pt2 = ProjectType(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            label="Backend",
            abbreviation="BE",
        )
        db_session.add_all([pt1, pt2])
        await db_session.commit()

        p1 = await project_service.create_project(
            name="FE Project",
            mission="Frontend work",
            project_type_id=pt1.id,
            tenant_key=test_tenant_key,
        )
        p2 = await project_service.create_project(
            name="BE Project",
            mission="Backend work",
            project_type_id=pt2.id,
            tenant_key=test_tenant_key,
        )
        # Each type starts at 1
        assert p1.series_number == 1
        assert p2.series_number == 1

    @pytest.mark.asyncio
    async def test_auto_series_accounts_for_soft_deleted(
        self, project_service: ProjectService, test_tenant_key: str, db_session
    ):
        """Auto-series includes deleted rows (constraint doesn't exclude them)."""
        from datetime import datetime, timezone

        # Create a soft-deleted project with series_number=1
        deleted_project = Project(
            id=str(uuid4()),
            name="Deleted Project",
            description="Deleted project description",
            mission="Old mission",
            tenant_key=test_tenant_key,
            status="inactive",
            series_number=1,
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(deleted_project)
        await db_session.commit()

        # New project gets series_number=2 (deleted row occupies 1 in constraint)
        project = await project_service.create_project(
            name="New Project",
            mission="New mission",
            tenant_key=test_tenant_key,
        )
        assert project.series_number == 2

    @pytest.mark.asyncio
    async def test_different_tenants_independent_series(
        self, project_service_with_session, test_tenant_key: str,
        db_manager, tenant_manager
    ):
        """Different tenants have independent series numbering."""
        from src.giljo_mcp.tenant import TenantManager

        # Create project for first tenant
        p1 = await project_service_with_session.create_project(
            name="Tenant1 Project",
            mission="Mission",
            tenant_key=test_tenant_key,
        )
        assert p1.series_number == 1

        # Create project for second tenant
        other_tenant = TenantManager.generate_tenant_key()
        p2 = await project_service_with_session.create_project(
            name="Tenant2 Project",
            mission="Mission",
            tenant_key=other_tenant,
        )
        assert p2.series_number == 1
