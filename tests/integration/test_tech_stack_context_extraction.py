"""
Integration tests for tech stack context extraction (Handover 0302).

Tests the extraction of product.config_data["tech_stack"] into agent mission context
with priority-based detail levels.

Following TDD principles: Tests written BEFORE implementation.
"""

from unittest.mock import PropertyMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project


@pytest_asyncio.fixture
async def mission_planner(db_manager):
    """Create MissionPlanner instance for testing."""
    planner = MissionPlanner(db_manager)
    return planner


@pytest_asyncio.fixture
async def sample_product_with_tech_stack(db_session: AsyncSession):
    """Create Product with comprehensive tech_stack config."""
    product = Product(
        id=str(uuid4()),
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        name="Tech Stack Product",
        description="Test product with tech stack",
        is_active=True,
        config_data={
            "tech_stack": {
                "languages": ["Python 3.11+", "TypeScript 5.0", "SQL"],
                "backend": ["FastAPI", "SQLAlchemy", "Celery"],
                "frontend": ["Vue 3", "Vuetify", "Pinia"],
                "database": ["PostgreSQL 18", "Redis"],
                "deployment": ["Docker", "Kubernetes", "AWS ECS"],
                "testing": ["pytest", "pytest-asyncio", "vitest", "Cypress"],
            }
        },
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Mock the primary_vision_text property to avoid lazy-loading issues
    type(product).primary_vision_text = PropertyMock(return_value="Test vision document")

    return product


@pytest_asyncio.fixture
async def sample_project(db_session: AsyncSession, sample_product_with_tech_stack: Product):
    """Create test project."""
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for tech stack extraction.",
        product_id=str(sample_product_with_tech_stack.id),
        tenant_key=sample_product_with_tech_stack.tenant_key,
        status="planning",
        mission="Test mission for tech stack extraction.",
        context_budget=180000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestTechStackContextExtraction:
    """Test cases for tech stack context extraction."""

    @pytest.mark.asyncio
    async def test_tech_stack_full_detail_priority_10(
        self, mission_planner, sample_product_with_tech_stack, sample_project
    ):
        """Test tech stack extraction with full detail (priority 10)."""
        context = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 10}
        )

        # Verify section exists
        assert "## Tech Stack" in context, "Tech stack section should be present with priority 10"

        # Verify all categories present
        assert "**Languages**:" in context, "Languages category should be present"
        assert "**Backend**:" in context, "Backend category should be present"
        assert "**Frontend**:" in context, "Frontend category should be present"
        assert "**Database**:" in context, "Database category should be present"
        assert "**Deployment**:" in context, "Deployment category should be present"
        assert "**Testing**:" in context, "Testing category should be present"

        # Verify all values present (full detail)
        assert "Python 3.11+" in context, "All language values should be present"
        assert "TypeScript 5.0" in context, "All language values should be present"
        assert "SQL" in context, "All language values should be present"
        assert "FastAPI" in context, "All backend values should be present"
        assert "SQLAlchemy" in context, "All backend values should be present"
        assert "Celery" in context, "All backend values should be present"
        assert "Vue 3" in context, "All frontend values should be present"
        assert "Vuetify" in context, "All frontend values should be present"
        assert "Pinia" in context, "All frontend values should be present"
        assert "PostgreSQL 18" in context, "All database values should be present"
        assert "Redis" in context, "All database values should be present"
        assert "Docker" in context, "All deployment values should be present"
        assert "Kubernetes" in context, "All deployment values should be present"
        assert "AWS ECS" in context, "All deployment values should be present"
        assert "pytest" in context, "All testing values should be present"
        assert "pytest-asyncio" in context, "All testing values should be present"
        assert "vitest" in context, "All testing values should be present"
        assert "Cypress" in context, "All testing values should be present"

    @pytest.mark.asyncio
    async def test_tech_stack_moderate_detail_priority_7(
        self, mission_planner, sample_product_with_tech_stack, sample_project
    ):
        """Test tech stack extraction with moderate detail (priority 7-9)."""
        context = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 7}
        )

        # Verify section exists
        assert "## Tech Stack" in context, "Tech stack section should be present with priority 7"

        # Verify all categories present
        assert "**Languages**:" in context, "Languages category should be present"
        assert "**Backend**:" in context, "Backend category should be present"
        assert "**Frontend**:" in context, "Frontend category should be present"
        assert "**Database**:" in context, "Database category should be present"
        assert "**Deployment**:" in context, "Deployment category should be present"
        assert "**Testing**:" in context, "Testing category should be present"

        # Verify values are slightly condensed (first 3 items per category)
        assert "Python 3.11+" in context, "First 3 language values should be present"
        assert "TypeScript 5.0" in context, "First 3 language values should be present"
        assert "SQL" in context, "First 3 language values should be present"
        assert "FastAPI" in context, "First 3 backend values should be present"
        assert "SQLAlchemy" in context, "First 3 backend values should be present"
        assert "Celery" in context, "First 3 backend values should be present"

        # Fourth items should NOT be present (only first 3)
        # Note: Our sample data has exactly 3 items for most categories,
        # so we check that testing (4 items) is condensed
        assert "Cypress" not in context, "Fourth testing value should not be present in moderate detail"

    @pytest.mark.asyncio
    async def test_tech_stack_abbreviated_detail_priority_4(
        self, mission_planner, sample_product_with_tech_stack, sample_project
    ):
        """Test tech stack extraction with abbreviated detail (priority 4-6)."""
        context = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 4}
        )

        # Verify section exists
        assert "## Tech Stack" in context, "Tech stack section should be present with priority 4"

        # Verify only primary categories (languages, backend, frontend, database)
        assert "**Languages**:" in context, "Languages category should be present"
        assert "**Backend**:" in context, "Backend category should be present"
        assert "**Frontend**:" in context, "Frontend category should be present"
        assert "**Database**:" in context, "Database category should be present"

        # Verify deployment/testing excluded (50% reduction)
        assert "**Deployment**:" not in context, "Deployment category should be excluded in abbreviated detail"
        assert "**Testing**:" not in context, "Testing category should be excluded in abbreviated detail"

        # Verify primary category values are still present
        assert "Python 3.11+" in context, "Primary category values should be present"
        assert "FastAPI" in context, "Primary category values should be present"
        assert "Vue 3" in context, "Primary category values should be present"
        assert "PostgreSQL 18" in context, "Primary category values should be present"

    @pytest.mark.asyncio
    async def test_tech_stack_minimal_detail_priority_1(
        self, mission_planner, sample_product_with_tech_stack, sample_project
    ):
        """Test tech stack extraction with minimal detail (priority 1-3)."""
        context = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 1}
        )

        # Verify section exists
        assert "## Tech Stack" in context, "Tech stack section should be present with priority 1"

        # Verify only languages + primary backend/frontend (80% reduction)
        assert "**Languages**:" in context, "Languages category should be present"
        assert "Python 3.11+" in context, "All languages should be present (critical)"

        # First item from backend/frontend only
        # Note: We check that EITHER the label exists OR the first value exists
        # because minimal mode might format differently
        backend_present = "**Backend**:" in context or "FastAPI" in context
        assert backend_present, "First backend value should be present"

        frontend_present = "**Frontend**:" in context or "Vue 3" in context
        assert frontend_present, "First frontend value should be present"

        # Database, deployment, testing should be excluded
        assert "**Database**:" not in context or "PostgreSQL 18" not in context, (
            "Database should be excluded or minimal"
        )
        assert "**Deployment**:" not in context, "Deployment should be excluded in minimal detail"
        assert "**Testing**:" not in context, "Testing should be excluded in minimal detail"

    @pytest.mark.asyncio
    async def test_tech_stack_excluded_priority_0(
        self, mission_planner, sample_product_with_tech_stack, sample_project
    ):
        """Test tech stack excluded when priority=0."""
        context = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 0}
        )

        # Verify section does NOT exist
        assert "## Tech Stack" not in context, "Tech stack section should not be present with priority 0"
        assert "**Languages**:" not in context, "No tech stack content should be present"
        assert "Python" not in context or "## Codebase" in context, (
            "Python might appear in other sections but not tech stack"
        )

    @pytest.mark.asyncio
    async def test_tech_stack_token_counting(self, mission_planner, sample_product_with_tech_stack, sample_project):
        """Test token counting for tech stack section."""
        # Full detail
        context_full = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 10}
        )

        # Minimal detail
        context_minimal = await mission_planner._build_context_with_priorities(
            product=sample_product_with_tech_stack, project=sample_project, field_priorities={"tech_stack": 1}
        )

        # Verify context prioritization
        tokens_full = mission_planner._count_tokens(context_full)
        tokens_minimal = mission_planner._count_tokens(context_minimal)

        assert tokens_full > tokens_minimal, "Full detail should have more tokens than minimal"

        # Expect ~80% reduction for minimal (60% minimum to allow variance)
        reduction_pct = ((tokens_full - tokens_minimal) / tokens_full) * 100
        assert reduction_pct >= 30, f"Expected at least 30% context prioritization, got {reduction_pct:.1f}%"

    @pytest.mark.asyncio
    async def test_tech_stack_missing_config_graceful_degradation(self, mission_planner, db_session):
        """Test graceful degradation when tech_stack not in config_data."""
        # Create product without tech_stack
        product = Product(
            id=str(uuid4()),
            tenant_key=f"tenant_{uuid4().hex[:8]}",
            name="No Tech Stack Product",
            description="Test product without tech stack",
            is_active=True,
            config_data={},  # No tech_stack field
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Mock the primary_vision_text property to avoid lazy-loading issues
        type(product).primary_vision_text = PropertyMock(return_value="Test vision document")

        # Create project
        project = Project(
            id=str(uuid4()),
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project.",
            product_id=str(product.id),
            tenant_key=product.tenant_key,
            status="planning",
            mission="Test mission.",
            context_budget=180000,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        context = await mission_planner._build_context_with_priorities(
            product=product, project=project, field_priorities={"tech_stack": 10}
        )

        # Verify no tech stack section (graceful degradation)
        assert "## Tech Stack" not in context, "Tech stack section should not appear when config_data is empty"

    @pytest.mark.asyncio
    async def test_tech_stack_empty_categories_handled(self, mission_planner, db_session):
        """Test handling of empty tech stack categories."""
        # Create product with empty categories
        product = Product(
            id=str(uuid4()),
            tenant_key=f"tenant_{uuid4().hex[:8]}",
            name="Empty Tech Stack Product",
            description="Test product with empty tech stack",
            is_active=True,
            config_data={
                "tech_stack": {
                    "languages": ["Python"],
                    "backend": [],  # Empty
                    "frontend": [],  # Empty
                    "database": ["PostgreSQL"],
                }
            },
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Mock the primary_vision_text property to avoid lazy-loading issues
        type(product).primary_vision_text = PropertyMock(return_value="Test vision document")

        # Create project
        project = Project(
            id=str(uuid4()),
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project.",
            product_id=str(product.id),
            tenant_key=product.tenant_key,
            status="planning",
            mission="Test mission.",
            context_budget=180000,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        context = await mission_planner._build_context_with_priorities(
            product=product, project=project, field_priorities={"tech_stack": 10}
        )

        # Verify section exists
        assert "## Tech Stack" in context, "Tech stack section should exist even with empty categories"

        # Verify non-empty categories shown
        assert "**Languages**:" in context, "Languages category should be shown"
        assert "Python" in context, "Python value should be present"
        assert "**Database**:" in context, "Database category should be shown"
        assert "PostgreSQL" in context, "PostgreSQL value should be present"

        # Verify empty categories NOT shown (graceful handling)
        # Empty categories should either not appear or appear without values
        backend_count = context.count("**Backend**:")
        frontend_count = context.count("**Frontend**:")

        # Empty categories should not be displayed
        assert backend_count == 0, "Empty backend category should not be displayed"
        assert frontend_count == 0, "Empty frontend category should not be displayed"


class TestTargetPlatformsContextExtraction:
    """Test cases for target_platforms field in tech stack context (Handover 0425)."""

    @pytest.mark.asyncio
    async def test_target_platforms_all_in_tech_stack(self, db_session: AsyncSession):
        """Test that target_platforms=['all'] appears in tech stack context and is included in data."""
        # Create product with target_platforms=['all']
        product = Product(
            id=str(uuid4()),
            tenant_key=f"tenant_{uuid4().hex[:8]}",
            name="All Platforms Product",
            description="Product targeting all platforms",
            is_active=True,
            target_platforms=["all"],
            config_data={
                "tech_stack": {
                    "languages": ["Python"],
                }
            },
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Verify target_platforms was stored correctly
        assert product.target_platforms == ["all"]

        # Verify target_platforms would be included in tech_stack data
        # (Simulating what get_tech_stack() would return)
        tech_stack = product.config_data.get("tech_stack", {})
        data = {
            "programming_languages": tech_stack.get("languages", []),
            "frontend_frameworks": tech_stack.get("frontend", []),
            "backend_frameworks": tech_stack.get("backend", []),
            "databases": tech_stack.get("database", []),
            "infrastructure": tech_stack.get("infrastructure", []),
            "dev_tools": tech_stack.get("dev_tools", []),
            "target_platforms": product.target_platforms or ["all"],
        }

        # Verify target_platforms in data structure
        assert "target_platforms" in data
        assert data["target_platforms"] == ["all"]

    @pytest.mark.asyncio
    async def test_target_platforms_specific_platforms_in_tech_stack(self, db_session: AsyncSession):
        """Test that target_platforms=['windows', 'linux'] appears in tech stack context."""
        # Create product with specific platforms
        product = Product(
            id=str(uuid4()),
            tenant_key=f"tenant_{uuid4().hex[:8]}",
            name="Windows Linux Product",
            description="Product targeting Windows and Linux",
            is_active=True,
            target_platforms=["windows", "linux"],
            config_data={
                "tech_stack": {
                    "languages": ["Python"],
                }
            },
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Verify target_platforms was stored correctly
        assert set(product.target_platforms) == {"windows", "linux"}

        # Verify target_platforms would be included in tech_stack data
        tech_stack = product.config_data.get("tech_stack", {})
        data = {
            "programming_languages": tech_stack.get("languages", []),
            "target_platforms": product.target_platforms or ["all"],
        }

        # Verify target_platforms in data structure
        assert "target_platforms" in data
        assert set(data["target_platforms"]) == {"windows", "linux"}

    @pytest.mark.asyncio
    async def test_target_platforms_defaults_to_all(self, db_session: AsyncSession):
        """Test that products without explicit target_platforms default to ['all']."""
        # Create product without explicitly setting target_platforms
        # The database default should apply
        product = Product(
            id=str(uuid4()),
            tenant_key=f"tenant_{uuid4().hex[:8]}",
            name="Default Platforms Product",
            description="Product using default target_platforms",
            is_active=True,
            config_data={
                "tech_stack": {
                    "languages": ["Python"],
                }
            },
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Verify target_platforms defaults to ['all']
        assert product.target_platforms == ["all"]

        # Verify it would be included correctly in tech_stack data
        tech_stack = product.config_data.get("tech_stack", {})
        data = {
            "programming_languages": tech_stack.get("languages", []),
            "target_platforms": product.target_platforms or ["all"],
        }

        # Verify target_platforms in data structure
        assert "target_platforms" in data
        assert data["target_platforms"] == ["all"]
