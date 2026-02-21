"""
Tests for Project Taxonomy System - Handover 0440a Phase 2

Tests cover:
- Lazy seeding of default project types per tenant
- Abbreviation uniqueness per tenant
- Taxonomy alias uniqueness (tenant_key, type_id, series_number, subseries)
- Deletion protection for types with assigned projects
- Next series number calculation
- Available series number gap detection
- Taxonomy alias computed property
- Tenant isolation for project types
- CRUD operations for project types
- Project creation with taxonomy fields
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, func

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.projects import ProjectType
from src.giljo_mcp.tenant import TenantManager
from tests.fixtures.base_fixtures import TestData
from tests.helpers.test_db_helper import PostgreSQLTestHelper, TransactionalTestContext


@pytest_asyncio.fixture(scope="function")
async def taxonomy_db_manager():
    """Function-scoped database manager for taxonomy tests."""
    from src.giljo_mcp.database import DatabaseManager

    await PostgreSQLTestHelper.ensure_test_database_exists()
    connection_string = PostgreSQLTestHelper.get_test_db_url()
    db_mgr = DatabaseManager(connection_string, is_async=True)

    try:
        await PostgreSQLTestHelper.create_test_tables(db_mgr)
    except Exception:
        pass

    yield db_mgr

    try:
        if db_mgr and db_mgr.async_engine:
            await db_mgr.close_async()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def taxonomy_session(taxonomy_db_manager):
    """Database session with transaction rollback for clean test state."""
    async with TransactionalTestContext(taxonomy_db_manager) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def tenant_a():
    """Generate tenant key A for isolation tests."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def tenant_b():
    """Generate tenant key B for isolation tests."""
    return TenantManager.generate_tenant_key()


class TestLazySeeding:
    """Test that default project types are lazily seeded per tenant."""

    @pytest.mark.asyncio
    async def test_seed_creates_eight_default_types(self, taxonomy_session, tenant_a):
        """First call to ensure_default_types_seeded should create 8 default types."""
        from api.endpoints.project_types.crud_ops import ensure_default_types_seeded

        await ensure_default_types_seeded(taxonomy_session, tenant_a)

        result = await taxonomy_session.execute(
            select(ProjectType).where(ProjectType.tenant_key == tenant_a)
        )
        types = result.scalars().all()
        assert len(types) == 8

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, taxonomy_session, tenant_a):
        """Calling ensure_default_types_seeded twice should not create duplicates."""
        from api.endpoints.project_types.crud_ops import ensure_default_types_seeded

        await ensure_default_types_seeded(taxonomy_session, tenant_a)
        await ensure_default_types_seeded(taxonomy_session, tenant_a)

        result = await taxonomy_session.execute(
            select(func.count()).select_from(ProjectType).where(ProjectType.tenant_key == tenant_a)
        )
        count = result.scalar()
        assert count == 8

    @pytest.mark.asyncio
    async def test_seed_includes_expected_abbreviations(self, taxonomy_session, tenant_a):
        """Seeded types should include standard abbreviations."""
        from api.endpoints.project_types.crud_ops import ensure_default_types_seeded

        await ensure_default_types_seeded(taxonomy_session, tenant_a)

        result = await taxonomy_session.execute(
            select(ProjectType.abbreviation).where(ProjectType.tenant_key == tenant_a)
        )
        abbreviations = set(result.scalars().all())
        expected = {"BE", "FE", "DB", "UI", "API", "INF", "DOC", "SEC"}
        assert abbreviations == expected

    @pytest.mark.asyncio
    async def test_seed_per_tenant_isolation(self, taxonomy_session, tenant_a, tenant_b):
        """Seeding for tenant A should not affect tenant B."""
        from api.endpoints.project_types.crud_ops import ensure_default_types_seeded

        await ensure_default_types_seeded(taxonomy_session, tenant_a)

        result = await taxonomy_session.execute(
            select(func.count()).select_from(ProjectType).where(ProjectType.tenant_key == tenant_b)
        )
        count = result.scalar()
        assert count == 0


class TestAbbreviationUniqueness:
    """Test that abbreviation uniqueness is enforced per tenant."""

    @pytest.mark.asyncio
    async def test_duplicate_abbreviation_rejected(self, taxonomy_session, tenant_a):
        """Creating a type with a duplicate abbreviation for the same tenant should fail."""
        from api.endpoints.project_types.crud_ops import create_project_type
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        data = ProjectTypeCreate(abbreviation="TST", label="Test Type")
        await create_project_type(taxonomy_session, tenant_a, data)

        with pytest.raises(ValueError, match="abbreviation.*already exists"):
            await create_project_type(taxonomy_session, tenant_a, data)

    @pytest.mark.asyncio
    async def test_same_abbreviation_different_tenants_allowed(self, taxonomy_session, tenant_a, tenant_b):
        """Same abbreviation should be allowed for different tenants."""
        from api.endpoints.project_types.crud_ops import create_project_type
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        data = ProjectTypeCreate(abbreviation="TST", label="Test Type")
        type_a = await create_project_type(taxonomy_session, tenant_a, data)
        type_b = await create_project_type(taxonomy_session, tenant_b, data)

        assert type_a.tenant_key == tenant_a
        assert type_b.tenant_key == tenant_b
        assert type_a.abbreviation == type_b.abbreviation


class TestTaxonomyUniqueness:
    """Test uniqueness of (tenant_key, type_id, series_number, subseries) tuples."""

    @pytest.mark.asyncio
    async def test_duplicate_taxonomy_rejected(self, taxonomy_session, tenant_a):
        """Creating two projects with same (tenant, type, series, subseries) should fail."""
        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="DUP",
            label="Duplicate Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project1 = Project(
            name="Project 1",
            description="Desc 1",
            mission="Mission 1",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=1,
            subseries=None,
        )
        taxonomy_session.add(project1)
        await taxonomy_session.flush()

        project2 = Project(
            name="Project 2",
            description="Desc 2",
            mission="Mission 2",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=1,
            subseries=None,
        )
        taxonomy_session.add(project2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await taxonomy_session.flush()

    @pytest.mark.asyncio
    async def test_different_subseries_allowed(self, taxonomy_session, tenant_a):
        """Same series number with different subseries should be allowed."""
        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="SUB",
            label="Subseries Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project1 = Project(
            name="Project 1a",
            description="Desc 1",
            mission="Mission 1",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=1,
            subseries="a",
        )
        project2 = Project(
            name="Project 1b",
            description="Desc 2",
            mission="Mission 2",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=1,
            subseries="b",
        )
        taxonomy_session.add(project1)
        taxonomy_session.add(project2)
        await taxonomy_session.flush()

        assert project1.series_number == project2.series_number
        assert project1.subseries != project2.subseries


class TestDeletionProtection:
    """Test that project types with assigned projects cannot be deleted."""

    @pytest.mark.asyncio
    async def test_cannot_delete_type_with_projects(self, taxonomy_session, tenant_a):
        """Deleting a type that has projects assigned should raise an error."""
        from api.endpoints.project_types.crud_ops import delete_project_type

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="DEL",
            label="Delete Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project = Project(
            name="Assigned Project",
            description="Has type",
            mission="Mission",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=1,
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        with pytest.raises(ValueError, match="Cannot delete.*project.*assigned"):
            await delete_project_type(taxonomy_session, tenant_a, project_type.id)

    @pytest.mark.asyncio
    async def test_can_delete_type_without_projects(self, taxonomy_session, tenant_a):
        """Deleting a type with no assigned projects should succeed."""
        from api.endpoints.project_types.crud_ops import delete_project_type

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="DEL",
            label="Delete Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        await delete_project_type(taxonomy_session, tenant_a, project_type.id)

        result = await taxonomy_session.execute(
            select(ProjectType).where(
                ProjectType.id == project_type.id,
                ProjectType.tenant_key == tenant_a,
            )
        )
        assert result.scalar_one_or_none() is None


class TestNextSeriesNumber:
    """Test the next available series number calculation."""

    @pytest.mark.asyncio
    async def test_first_series_number_is_one(self, taxonomy_session, tenant_a):
        """With no projects, next series should be 1."""
        from api.endpoints.project_types.crud_ops import get_next_series_number

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="NXT",
            label="Next Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        next_num = await get_next_series_number(taxonomy_session, tenant_a, project_type.id)
        assert next_num == 1

    @pytest.mark.asyncio
    async def test_series_increments_correctly(self, taxonomy_session, tenant_a):
        """Next series should be max + 1."""
        from api.endpoints.project_types.crud_ops import get_next_series_number

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="NXT",
            label="Next Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        for i in range(1, 4):
            project = Project(
                name=f"Project {i}",
                description=f"Desc {i}",
                mission=f"Mission {i}",
                tenant_key=tenant_a,
                project_type_id=project_type.id,
                series_number=i,
            )
            taxonomy_session.add(project)
        await taxonomy_session.flush()

        next_num = await get_next_series_number(taxonomy_session, tenant_a, project_type.id)
        assert next_num == 4

    @pytest.mark.asyncio
    async def test_series_with_gaps_returns_max_plus_one(self, taxonomy_session, tenant_a):
        """Next series should still be max + 1, even with gaps (gaps handled separately)."""
        from api.endpoints.project_types.crud_ops import get_next_series_number

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="GAP",
            label="Gap Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        for num in [1, 3, 5]:
            project = Project(
                name=f"Project {num}",
                description=f"Desc {num}",
                mission=f"Mission {num}",
                tenant_key=tenant_a,
                project_type_id=project_type.id,
                series_number=num,
            )
            taxonomy_session.add(project)
        await taxonomy_session.flush()

        next_num = await get_next_series_number(taxonomy_session, tenant_a, project_type.id)
        assert next_num == 6


class TestAvailableSeriesNumbers:
    """Test detection of gaps in series number sequences."""

    @pytest.mark.asyncio
    async def test_no_gaps_returns_empty(self, taxonomy_session, tenant_a):
        """With consecutive series, available should start after last used."""
        from api.endpoints.project_types.crud_ops import get_available_series_numbers

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="AVL",
            label="Available Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        for i in range(1, 4):
            project = Project(
                name=f"Project {i}",
                description=f"Desc {i}",
                mission=f"Mission {i}",
                tenant_key=tenant_a,
                project_type_id=project_type.id,
                series_number=i,
            )
            taxonomy_session.add(project)
        await taxonomy_session.flush()

        available = await get_available_series_numbers(taxonomy_session, tenant_a, project_type.id, limit=5)
        # No gaps in 1,2,3 - available should be 4,5,6,7,8
        assert available == [4, 5, 6, 7, 8]

    @pytest.mark.asyncio
    async def test_gaps_detected(self, taxonomy_session, tenant_a):
        """Gaps in the series should be returned first."""
        from api.endpoints.project_types.crud_ops import get_available_series_numbers

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="AVL",
            label="Available Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        for num in [1, 3, 5]:
            project = Project(
                name=f"Project {num}",
                description=f"Desc {num}",
                mission=f"Mission {num}",
                tenant_key=tenant_a,
                project_type_id=project_type.id,
                series_number=num,
            )
            taxonomy_session.add(project)
        await taxonomy_session.flush()

        available = await get_available_series_numbers(taxonomy_session, tenant_a, project_type.id, limit=5)
        # Gaps: 2, 4 come first, then 6, 7, 8
        assert available == [2, 4, 6, 7, 8]

    @pytest.mark.asyncio
    async def test_empty_type_returns_sequential(self, taxonomy_session, tenant_a):
        """With no projects, available should start at 1."""
        from api.endpoints.project_types.crud_ops import get_available_series_numbers

        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="EMP",
            label="Empty Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        available = await get_available_series_numbers(taxonomy_session, tenant_a, project_type.id, limit=3)
        assert available == [1, 2, 3]


class TestTaxonomyAlias:
    """Test the computed taxonomy_alias property on Project."""

    @pytest.mark.asyncio
    async def test_alias_format_without_subseries(self, taxonomy_session, tenant_a):
        """Taxonomy alias should be ABBR-NNNN format."""
        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="BE",
            label="Backend",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project = Project(
            name="Backend Project",
            description="Desc",
            mission="Mission",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=42,
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        # Need to eagerly load the relationship for computed property
        await taxonomy_session.refresh(project, ["project_type"])
        assert project.taxonomy_alias == "BE-0042"

    @pytest.mark.asyncio
    async def test_alias_format_with_subseries(self, taxonomy_session, tenant_a):
        """Taxonomy alias with subseries should be ABBR-NNNNx format."""
        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="BE",
            label="Backend",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project = Project(
            name="Backend Project A",
            description="Desc",
            mission="Mission",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=42,
            subseries="a",
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        await taxonomy_session.refresh(project, ["project_type"])
        assert project.taxonomy_alias == "BE-0042a"

    @pytest.mark.asyncio
    async def test_alias_fallback_without_series(self, taxonomy_session, tenant_a):
        """Without series_number, taxonomy_alias should fall back to random alias."""
        project = Project(
            name="Untyped Project",
            description="Desc",
            mission="Mission",
            tenant_key=tenant_a,
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        # Should return the 6-char random alias
        assert project.taxonomy_alias == project.alias
        assert len(project.taxonomy_alias) == 6


class TestTenantIsolation:
    """Test that project types are properly isolated between tenants."""

    @pytest.mark.asyncio
    async def test_list_types_only_returns_own_tenant(self, taxonomy_session, tenant_a, tenant_b):
        """Listing project types should only return types for the requesting tenant."""
        from api.endpoints.project_types.crud_ops import list_project_types

        type_a = ProjectType(tenant_key=tenant_a, abbreviation="AAA", label="Tenant A Type")
        type_b = ProjectType(tenant_key=tenant_b, abbreviation="BBB", label="Tenant B Type")
        taxonomy_session.add(type_a)
        taxonomy_session.add(type_b)
        await taxonomy_session.flush()

        types_a = await list_project_types(taxonomy_session, tenant_a)
        types_b = await list_project_types(taxonomy_session, tenant_b)

        assert len(types_a) == 1
        assert types_a[0].abbreviation == "AAA"
        assert len(types_b) == 1
        assert types_b[0].abbreviation == "BBB"

    @pytest.mark.asyncio
    async def test_cannot_delete_other_tenant_type(self, taxonomy_session, tenant_a, tenant_b):
        """Attempting to delete another tenant's type should fail."""
        from api.endpoints.project_types.crud_ops import delete_project_type

        type_a = ProjectType(tenant_key=tenant_a, abbreviation="OWN", label="Tenant A Type")
        taxonomy_session.add(type_a)
        await taxonomy_session.flush()

        with pytest.raises(ValueError, match="not found"):
            await delete_project_type(taxonomy_session, tenant_b, type_a.id)

    @pytest.mark.asyncio
    async def test_cannot_update_other_tenant_type(self, taxonomy_session, tenant_a, tenant_b):
        """Attempting to update another tenant's type should fail."""
        from api.endpoints.project_types.crud_ops import update_project_type
        from api.endpoints.project_types.schemas import ProjectTypeUpdate

        type_a = ProjectType(tenant_key=tenant_a, abbreviation="OWN", label="Tenant A Type")
        taxonomy_session.add(type_a)
        await taxonomy_session.flush()

        update_data = ProjectTypeUpdate(label="Hacked Label")
        with pytest.raises(ValueError, match="not found"):
            await update_project_type(taxonomy_session, tenant_b, type_a.id, update_data)

    @pytest.mark.asyncio
    async def test_next_series_isolated_per_tenant(self, taxonomy_session, tenant_a, tenant_b):
        """Next series number should only consider the requesting tenant's projects."""
        from api.endpoints.project_types.crud_ops import get_next_series_number

        type_a = ProjectType(tenant_key=tenant_a, abbreviation="ISO", label="Iso Type")
        type_b = ProjectType(tenant_key=tenant_b, abbreviation="ISO", label="Iso Type")
        taxonomy_session.add(type_a)
        taxonomy_session.add(type_b)
        await taxonomy_session.flush()

        for i in range(1, 6):
            project = Project(
                name=f"Tenant A Project {i}",
                description=f"Desc {i}",
                mission=f"Mission {i}",
                tenant_key=tenant_a,
                project_type_id=type_a.id,
                series_number=i,
            )
            taxonomy_session.add(project)
        await taxonomy_session.flush()

        next_a = await get_next_series_number(taxonomy_session, tenant_a, type_a.id)
        next_b = await get_next_series_number(taxonomy_session, tenant_b, type_b.id)

        assert next_a == 6
        assert next_b == 1


class TestCRUDOperations:
    """Test CRUD operations for project types."""

    @pytest.mark.asyncio
    async def test_create_project_type(self, taxonomy_session, tenant_a):
        """Creating a project type should set all fields correctly."""
        from api.endpoints.project_types.crud_ops import create_project_type
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        data = ProjectTypeCreate(
            abbreviation="NEW",
            label="New Type",
            color="#FF0000",
            sort_order=5,
        )
        result = await create_project_type(taxonomy_session, tenant_a, data)

        assert result.abbreviation == "NEW"
        assert result.label == "New Type"
        assert result.color == "#FF0000"
        assert result.sort_order == 5
        assert result.tenant_key == tenant_a

    @pytest.mark.asyncio
    async def test_list_project_types_returns_all(self, taxonomy_session, tenant_a):
        """Listing should return all types for the tenant."""
        from api.endpoints.project_types.crud_ops import list_project_types

        for i, (abbr, label) in enumerate([("AA", "Type A"), ("BB", "Type B"), ("CC", "Type C")]):
            pt = ProjectType(tenant_key=tenant_a, abbreviation=abbr, label=label, sort_order=i)
            taxonomy_session.add(pt)
        await taxonomy_session.flush()

        types = await list_project_types(taxonomy_session, tenant_a)
        assert len(types) == 3

    @pytest.mark.asyncio
    async def test_list_project_types_ordered_by_sort_order(self, taxonomy_session, tenant_a):
        """Types should be returned ordered by sort_order."""
        from api.endpoints.project_types.crud_ops import list_project_types

        for abbr, label, order in [("CC", "Last", 3), ("AA", "First", 1), ("BB", "Middle", 2)]:
            pt = ProjectType(tenant_key=tenant_a, abbreviation=abbr, label=label, sort_order=order)
            taxonomy_session.add(pt)
        await taxonomy_session.flush()

        types = await list_project_types(taxonomy_session, tenant_a)
        abbreviations = [t.abbreviation for t in types]
        assert abbreviations == ["AA", "BB", "CC"]

    @pytest.mark.asyncio
    async def test_update_project_type(self, taxonomy_session, tenant_a):
        """Updating a project type should change only specified fields."""
        from api.endpoints.project_types.crud_ops import update_project_type
        from api.endpoints.project_types.schemas import ProjectTypeUpdate

        pt = ProjectType(tenant_key=tenant_a, abbreviation="UPD", label="Original", color="#000000", sort_order=0)
        taxonomy_session.add(pt)
        await taxonomy_session.flush()

        update_data = ProjectTypeUpdate(label="Updated", color="#FFFFFF")
        updated = await update_project_type(taxonomy_session, tenant_a, pt.id, update_data)

        assert updated.label == "Updated"
        assert updated.color == "#FFFFFF"
        assert updated.abbreviation == "UPD"  # Not changed
        assert updated.sort_order == 0  # Not changed

    @pytest.mark.asyncio
    async def test_delete_project_type(self, taxonomy_session, tenant_a):
        """Deleting a project type with no projects should succeed."""
        from api.endpoints.project_types.crud_ops import delete_project_type

        pt = ProjectType(tenant_key=tenant_a, abbreviation="DEL", label="To Delete")
        taxonomy_session.add(pt)
        await taxonomy_session.flush()

        await delete_project_type(taxonomy_session, tenant_a, pt.id)

        result = await taxonomy_session.execute(
            select(ProjectType).where(ProjectType.id == pt.id, ProjectType.tenant_key == tenant_a)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_list_types_includes_project_count(self, taxonomy_session, tenant_a):
        """Listed types should include count of assigned projects."""
        from api.endpoints.project_types.crud_ops import list_project_types

        pt = ProjectType(tenant_key=tenant_a, abbreviation="CNT", label="Count Test")
        taxonomy_session.add(pt)
        await taxonomy_session.flush()

        for i in range(3):
            project = Project(
                name=f"Project {i}",
                description=f"Desc {i}",
                mission=f"Mission {i}",
                tenant_key=tenant_a,
                project_type_id=pt.id,
                series_number=i + 1,
            )
            taxonomy_session.add(project)
        await taxonomy_session.flush()

        types = await list_project_types(taxonomy_session, tenant_a)
        assert len(types) == 1
        assert types[0].project_count == 3


class TestProjectCreationWithTaxonomy:
    """Test creating projects with taxonomy classification fields."""

    @pytest.mark.asyncio
    async def test_create_project_with_type_and_series(self, taxonomy_session, tenant_a):
        """A project should accept project_type_id and series_number."""
        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="CRT",
            label="Create Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project = Project(
            name="Typed Project",
            description="Desc",
            mission="Mission",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=1,
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        await taxonomy_session.refresh(project, ["project_type"])
        assert project.project_type_id == project_type.id
        assert project.series_number == 1
        assert project.taxonomy_alias == "CRT-0001"

    @pytest.mark.asyncio
    async def test_create_project_without_taxonomy(self, taxonomy_session, tenant_a):
        """A project without taxonomy fields should still work (backwards compatible)."""
        project = Project(
            name="Plain Project",
            description="No taxonomy",
            mission="Mission",
            tenant_key=tenant_a,
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        assert project.project_type_id is None
        assert project.series_number is None
        assert project.subseries is None
        # Falls back to random alias
        assert project.taxonomy_alias == project.alias

    @pytest.mark.asyncio
    async def test_create_project_with_subseries(self, taxonomy_session, tenant_a):
        """A project with subseries should produce correct alias."""
        project_type = ProjectType(
            tenant_key=tenant_a,
            abbreviation="SUB",
            label="Subseries Test",
        )
        taxonomy_session.add(project_type)
        await taxonomy_session.flush()

        project = Project(
            name="Subseries Project",
            description="Desc",
            mission="Mission",
            tenant_key=tenant_a,
            project_type_id=project_type.id,
            series_number=7,
            subseries="c",
        )
        taxonomy_session.add(project)
        await taxonomy_session.flush()

        await taxonomy_session.refresh(project, ["project_type"])
        assert project.taxonomy_alias == "SUB-0007c"


class TestPydanticSchemaValidation:
    """Test Pydantic schema validation rules."""

    def test_abbreviation_must_be_uppercase(self):
        """Abbreviation must match ^[A-Z]+$ pattern."""
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        with pytest.raises(Exception):
            ProjectTypeCreate(abbreviation="be", label="Bad")

    def test_abbreviation_min_length(self):
        """Abbreviation must be at least 2 characters."""
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        with pytest.raises(Exception):
            ProjectTypeCreate(abbreviation="A", label="Too Short")

    def test_abbreviation_max_length(self):
        """Abbreviation must be at most 4 characters."""
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        with pytest.raises(Exception):
            ProjectTypeCreate(abbreviation="ABCDE", label="Too Long")

    def test_valid_abbreviation_accepted(self):
        """Valid abbreviation should be accepted."""
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        data = ProjectTypeCreate(abbreviation="API", label="API Integration")
        assert data.abbreviation == "API"

    def test_color_must_be_hex(self):
        """Color must match hex pattern #RRGGBB."""
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        with pytest.raises(Exception):
            ProjectTypeCreate(abbreviation="TST", label="Test", color="red")

    def test_color_defaults_to_grey(self):
        """Color should default to #607D8B if not provided."""
        from api.endpoints.project_types.schemas import ProjectTypeCreate

        data = ProjectTypeCreate(abbreviation="TST", label="Test")
        assert data.color == "#607D8B"

    def test_update_allows_partial(self):
        """Update schema should allow partial updates."""
        from api.endpoints.project_types.schemas import ProjectTypeUpdate

        data = ProjectTypeUpdate(label="New Label")
        assert data.label == "New Label"
        assert data.color is None
        assert data.sort_order is None

    def test_response_model_fields(self):
        """Response model should have all required fields."""
        from api.endpoints.project_types.schemas import ProjectTypeResponse
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        resp = ProjectTypeResponse(
            id="test-id",
            tenant_key="test-tenant",
            abbreviation="TST",
            label="Test",
            color="#607D8B",
            sort_order=0,
            project_count=5,
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "test-id"
        assert resp.project_count == 5
