"""
Integration tests for ProjectService.get_project_type_by_label() (Handover 0837b).

Verifies case-insensitive lookup of ProjectType by label within a tenant.
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.models.projects import ProjectType
from src.giljo_mcp.services.project_service import ProjectService


@pytest.fixture
async def project_service(project_service_with_session):
    return project_service_with_session


class TestGetProjectTypeByLabel:
    """Test case-insensitive ProjectType label lookup."""

    @pytest.mark.asyncio
    async def test_exact_match(self, project_service: ProjectService, test_tenant_key: str, db_session):
        """Exact label match returns the ProjectType."""
        pt = ProjectType(
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
        pt = ProjectType(
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
        pt = ProjectType(
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
        """Type from another tenant is not visible."""
        other_tenant = f"tk_{uuid4().hex}"
        pt = ProjectType(
            id=str(uuid4()),
            tenant_key=other_tenant,
            label="Frontend",
            abbreviation="FE",
        )
        db_session.add(pt)
        await db_session.commit()

        result = await project_service.get_project_type_by_label("Frontend", test_tenant_key)
        assert result is None
